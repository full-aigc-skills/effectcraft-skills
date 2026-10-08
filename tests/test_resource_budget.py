"""父子共享渲染预算跨重启保留；恢复与失败不能重置计数。"""
import unittest
import test_managed_tasks


class ResourceBudgetTests(unittest.TestCase):
    setUp=test_managed_tasks.ManagedTaskTests.setUp
    create=test_managed_tasks.ManagedTaskTests.create
    def test_resource_reservation_survives_restart_and_resume_is_idempotent(self):
        self.create();self.store.start('first')
        self.store.reserve_resources('first',{'frames':12,'decodedBytes':120},'a'*64)
        restored=self.module.Store(self.root/'state')
        restored.reserve_resources('first',{'frames':12,'decodedBytes':120},'a'*64)
        ledger=restored.read('first')['resources']
        self.assertEqual(len(ledger['entries']),1)
        self.assertEqual(ledger['entries']['first']['frames'],12)
        with self.assertRaisesRegex(ValueError,'resource_binding_conflict'):
            restored.reserve_resources('first',{'frames':13,'decodedBytes':130},'b'*64)

    def test_revision_shares_root_reservations_and_limit(self):
        self.create();self.store.start('first')
        self.store.reserve_resources('first',{'frames':9999,'decodedBytes':120},'a'*64)
        self.store.delivered('first',{})
        self.create('child',plan={'child':True},parent='first');self.store.start('child')
        with self.assertRaisesRegex(ValueError,'resource_budget_exceeded'):
            self.store.reserve_resources('child',{'frames':2,'decodedBytes':120},'b'*64)
        self.assertEqual(set(self.store.read('first')['resources']['entries']),{'first'})

    def test_actual_encoded_bytes_are_monotonic_and_overflow_is_durable(self):
        self.create();self.store.start('first')
        self.store.reserve_resources('first',{'frames':1,'decodedBytes':4},'a'*64)
        self.store.observe_resources('first',100)
        self.module.Store(self.root/'state').observe_resources('first',0)
        self.assertEqual(self.store.read('first')['resources']['entries']['first']['encodedBytes'],100)
        with self.assertRaisesRegex(ValueError,'resource_budget_exceeded'):
            self.store.observe_resources('first',2*1024**3+1)
        with self.assertRaisesRegex(ValueError,'resource_budget_exceeded'):
            self.store.allowed(self.store.read('first'))
        self.assertEqual(self.store.read('first')['resources']['entries']['first']['encodedBytes'],2*1024**3+1)

    def test_corrupt_ledger_is_preserved_and_cannot_reset_usage(self):
        self.create();state=self.store.read('first')
        state['resources']['entries']={'first':{'frames':-1}}
        self.store.save(state)
        before=self.store.path('first').read_bytes()
        with self.assertRaisesRegex(ValueError,'state_invalid'):
            self.store.read('first')
        self.assertEqual(before,self.store.path('first').read_bytes())

    def test_missing_legacy_budget_is_inspectable_but_not_executable(self):
        self.create();state=self.store.read('first');del state['resources'];self.store.save(state)
        self.assertEqual(self.store.read('first')['state'],'planned')
        before=self.store.path('first').read_bytes()
        with self.assertRaisesRegex(ValueError,'legacy_resource_budget_missing'):
            self.store.start('first')
        self.assertEqual(before,self.store.path('first').read_bytes())

    def test_deleted_reservation_entry_cannot_reset_consumed_frames(self):
        self.create();self.store.start('first')
        self.store.reserve_resources('first',{'frames':9999,'decodedBytes':39996},'a'*64)
        state=self.store.read('first');state['resources']['entries']={};self.store.save(state)
        with self.assertRaisesRegex(ValueError,'resource_reservation_invalid'):
            self.store.allowed(self.store.read('first'))

    def test_missing_child_entry_blocks_new_sibling_reservation(self):
        self.create();self.store.start('first');self.store.delivered('first',{})
        self.create('one',plan={'name':'one'},parent='first');self.store.start('one')
        self.store.reserve_resources('one',{'frames':9999,'decodedBytes':39996},'a'*64)
        self.store.delivered('one',{})
        state=self.store.read('first');state['resources']['entries']={};self.store.save(state)
        with self.assertRaisesRegex(ValueError,'resource_reservation_invalid'):
            self.create('two',plan={'name':'two'},parent='first')

    def test_parent_cycle_cannot_hang_resource_root_resolution(self):
        self.create();self.store.start('first');self.store.delivered('first',{})
        self.create('child',plan={'child':True},parent='first')
        state=self.store.read('first');state['parent']='child';self.store.save(state)
        with self.assertRaisesRegex(ValueError,'task_ancestry_cycle'):
            self.store.reserve_resources('child',{'frames':1,'decodedBytes':4},'a'*64)

    def test_parallel_children_cannot_overbook_shared_root(self):
        import subprocess
        import sys
        self.create();self.store.start('first');self.store.delivered('first',{})
        for task in ('one','two'):
            self.create(task,plan={'name':task},parent='first');self.store.start(task)
        driver=self.root/'reserve.py'
        driver.write_text('import importlib.util,sys\nfrom pathlib import Path\n'
            f's=importlib.util.spec_from_file_location("tasks",{str(test_managed_tasks.SCRIPT)!r})\n'
            'm=importlib.util.module_from_spec(s);s.loader.exec_module(m)\n'
            'store=m.Store(Path(sys.argv[1]))\n'
            'try:store.reserve_resources(sys.argv[2],{"frames":6000,"decodedBytes":24000},"a"*64)\n'
            'except ValueError as e:print(e);sys.exit(1)\n')
        children=[subprocess.Popen([sys.executable,'-I','-B',str(driver),str(self.store.root),task],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            for task in ('one','two')]
        outputs=[child.communicate(timeout=20) for child in children]
        self.assertEqual(sorted(child.returncode for child in children),[0,1],outputs)
        self.assertIn(b'resource_budget_exceeded',b''.join(out for out,err in outputs))
        self.assertEqual(sum(e['frames'] for e in self.store.read('first')['resources']['entries'].values()),6000)


import os


@unittest.skipUnless(os.environ.get('CRAFT_RESOURCE_LIVE')=='1','requires actual native engine')
class SharedResourceNativeTests(unittest.TestCase):
    def test_actual_parent_child_exports_charge_one_root(self):
        import importlib.util
        import json
        import tempfile
        from pathlib import Path
        script=test_managed_tasks.SCRIPT.with_name('managed.py')
        spec=importlib.util.spec_from_file_location('resource_native_managed',script)
        managed=importlib.util.module_from_spec(spec);spec.loader.exec_module(managed)
        with tempfile.TemporaryDirectory(prefix='shared resource native ') as temporary:
            root=Path(temporary);store=managed.load('task_store').Store(root/'state')
            plan=managed.read(script.parent.parent/'examples/brand-intro.json')
            first=managed.run(store,plan,root/'first',root/'runtime',task='root')
            self.assertEqual(first['state'],'review_ready',first)
            manifest=managed.read(root/'first/manifest.json');original=managed.load('task_store').file_sha(root/'first/project.ecproj')
            change={'expectedProjectSha256':manifest['files']['project.ecproj'],
                'operations':[{'command':'layer.setText','params':{'layer':{'$ref':'title.layer'},'text':'NOVA PLUS'}}],
                'frames':plan.get('frames',[0]),'exports':[{'format':'mp4'}]}
            child=managed.run(store,change,root/'second',root/'runtime',source=root/'first',task='child',parent='root')
            self.assertEqual(child['state'],'review_ready',child)
            latest=store.read('root');entries=latest['resources']['entries']
            self.assertEqual(set(entries),{'root','child'})
            expected=12+len(plan.get('frames',[0]))
            self.assertEqual(sum(entry['frames'] for entry in entries.values()),expected*2)
            for task,output in [('root',root/'first'),('child',root/'second')]:
                size=sum(f.stat().st_size for f in output.glob('frame-*.png'))+(output/'intro.mp4').stat().st_size
                self.assertEqual(entries[task]['encodedBytes'],size)
                self.assertEqual(entries[task]['decodedBytes'],expected*320*180*4)
            self.assertEqual(latest['deadline'],first['deadline']);self.assertLessEqual(child['deadline'],first['deadline'])
            self.assertEqual(original,managed.load('task_store').file_sha(root/'first/project.ecproj'))
            if os.environ.get('CRAFT_RESOURCE_EVIDENCE'):
                import hashlib
                skill=script.parent.parent
                proof={'schema':'effectcraft-shared-resources-native/v1','result':'PASS','candidateOnly':True,
                    'platform':managed.load('platform_support').platform_key(),'scope':'actual workflow parent and child native exports; not a Judge/host-dispatch acceptance',
                    'resources':latest['resources'],'deadlineShared':True,'originalProjectPreserved':True,
                    'skillFiles':{p.relative_to(skill).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in skill.rglob('*') if p.is_file() and '__pycache__' not in p.parts},
                    'testSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    'excluded':['host visual Judge','public revise budget acceptance','commands/desktop resource accounting','CPU/memory metering','other platforms','immutable release','complete V1']}
                Path(os.environ['CRAFT_RESOURCE_EVIDENCE']).write_text(json.dumps(proof,indent=2)+'\n')
