"""真实子进程启动失败必须形成可核对终态，不安装或启动原生引擎。"""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / 'skills/effectcraft-use/scripts/managed.py'


class ManagedSupervisorTests(unittest.TestCase):
    def test_durable_parent_cancel_stops_inflight_owned_worker(self):
        import threading
        import time
        spec=importlib.util.spec_from_file_location('ancestor_supervisor',SCRIPT)
        managed=importlib.util.module_from_spec(spec);spec.loader.exec_module(managed)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);store=managed.load('task_store').Store(root/'state')
            for task,parent in [('parent',None),('child','parent')]:
                store.create(task,plan={'name':task},output=str(root/task),runtime_sha='a'*64,
                    inputs={},source=None,mode='workflow',authorization={},parent=parent)
                if task=='parent':store.start(task);store.delivered(task,{})
            marker=root/'started'
            driver=root/'inflight_worker.py'
            driver.write_text('import importlib.util,time\nfrom pathlib import Path\n'
                f's=importlib.util.spec_from_file_location("store",{str(SCRIPT.with_name("task_store.py"))!r})\n'
                'm=importlib.util.module_from_spec(s);s.loader.exec_module(m)\n'
                f'store=m.Store(Path({str(store.root)!r}));store.start("child");store.begin_step("child","edit",{{}})\n'
                f'Path({str(marker)!r}).write_text("running")\n'
                'time.sleep(4)\n')
            managed.__file__=str(driver)
            errors=[]
            def cancel_ancestor():
                try:
                    deadline=time.monotonic()+5
                    while not marker.exists() and time.monotonic()<deadline:time.sleep(.01)
                    if not marker.exists():raise AssertionError('owned worker did not start')
                    with store.lock():
                        parent=store.read('parent');parent['cancellationRequestedAt']=time.time()
                        parent['state']='reconciling';store.save(parent)
                except BaseException as error:errors.append(error)
            watcher=threading.Thread(target=cancel_ancestor);watcher.start()
            try:result=managed.supervise(store,'child',root/'runtime')
            finally:watcher.join(timeout=6)
            self.assertFalse(errors,errors);self.assertFalse(watcher.is_alive())
            self.assertTrue(marker.exists());self.assertEqual(result['state'],'reconciling')
            self.assertEqual(result.get('termination',{}).get('status'),'confirmed')
            self.assertEqual(result['steps'][0]['state'],'attempted')
            receipt=managed.read(store.lifecycle_path(result));self.assertEqual(receipt['status'],'stopped')
            self.assertNotEqual(receipt['returncode'],0)

    @unittest.skipUnless(os.environ.get('CRAFT_MANAGED_LIVE')=='1','requires actual native engine and ffmpeg')
    def test_managed_native_creation_has_confirmed_tree_exit_and_decodable_video(self):
        import hashlib
        import shutil
        with tempfile.TemporaryDirectory(prefix='effectcraft-guard-native-') as directory:
            root=Path(directory).resolve();skill=root/'single skill'
            shutil.copytree(SCRIPT.parent.parent,skill,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
            before={p.relative_to(skill).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in skill.rglob('*') if p.is_file()}
            process=subprocess.run([sys.executable,'-I','-B',str(skill/'scripts/managed.py'),
                '--state-root',str(root/'state'),'--runtime-home',str(root/'runtime'),
                'run','--task','native-guard','--plan',str(skill/'examples/brand-intro.json'),'--output',str(root/'delivery')],
                capture_output=True,text=True,timeout=240)
            self.assertEqual(process.returncode,0,process.stdout+process.stderr)
            state=json.loads(process.stdout)
            self.assertEqual(state['state'],'review_ready')
            usage=state['resources']['entries']['native-guard']
            self.assertEqual(usage['frames'],15)
            self.assertEqual(usage['decodedBytes'],15*320*180*4)
            self.assertEqual(usage['encodedBytes'],sum(f.stat().st_size for f in (root/'delivery').glob('frame-*.png'))+(root/'delivery/intro.mp4').stat().st_size)
            lifecycle=json.loads((root/'state/tasks/native-guard/lifecycle.json').read_text())
            self.assertEqual(lifecycle['status'],'stopped');self.assertEqual(lifecycle['returncode'],0)
            self.assertTrue(state['steps']);self.assertTrue(all(s['state']=='succeeded' for s in state['steps']))
            video=root/'delivery/intro.mp4'
            info=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-show_streams','-of','json',str(video)]))['streams'][0]
            self.assertEqual((info['width'],info['height'],info['nb_read_frames']),(320,180,'12'))
            subprocess.run(['ffmpeg','-v','error','-i',str(video),'-f','null','-'],check=True,capture_output=True)
            after={p.relative_to(skill).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in skill.rglob('*') if p.is_file()}
            self.assertEqual(before,after)
            if os.environ.get('CRAFT_GUARD_EVIDENCE'):
                proof={'schema':'effectcraft-guard-native-component/v1','result':'PASS','platform':sys.platform,
                    'scope':'copied single skill; actual public managed creation; isolated native cache; no model dispatch claim',
                    'skillFiles':before,'lifecycle':lifecycle,'steps':len(state['steps']),
                    'manifestSha256':hashlib.sha256((root/'delivery/manifest.json').read_bytes()).hexdigest(),
                    'projectSha256':hashlib.sha256((root/'delivery/project.ecproj').read_bytes()).hexdigest(),
                    'videoSha256':hashlib.sha256(video.read_bytes()).hexdigest(),'decodedFrames':12,
                    'resources':state['resources'],
                    'excluded':['Windows Job native execution','other platform execution','segmented resume','host dispatch','fixed release']}
                Path(os.environ['CRAFT_GUARD_EVIDENCE']).write_text(json.dumps(proof,indent=2)+'\n')

    def test_source_conflict_before_worker_start_is_durably_failed(self):
        spec = importlib.util.spec_from_file_location('supervisor_acceptance', SCRIPT)
        managed = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(managed)
        task_store = managed.load('task_store')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source.ecproj'
            source.write_bytes(b'original project')
            store = task_store.Store(root / 'state')
            request = {'inputs': {}, 'source': str(root / 'source-delivery')}
            store.create('source-conflict', plan={'operations': []},
                         output=str(root / 'output'), runtime_sha='a' * 64,
                         inputs={}, source=str(source), mode='workflow',
                         authorization={'requestHash': task_store.digest(request)})
            task_store.atomic_json(store.path('source-conflict').parent / 'request.json', request)
            source.write_bytes(b'external revision')
            process = subprocess.run([sys.executable, '-I', '-B', str(SCRIPT),
                                      '--state-root', str(store.root),
                                      '--runtime-home', str(root / 'runtime'),
                                      'resume', '--task', 'source-conflict'],
                                     capture_output=True, text=True, timeout=20)
            result = json.loads(process.stdout)
            self.assertEqual(result['state'], 'failed')
            self.assertEqual(process.returncode, 1)
            self.assertEqual(result['steps'], [])
            self.assertIn('before durable start', result['error'])
            self.assertNotEqual(result['workerExitCode'], 0)
            restored = task_store.Store(root / 'state').read('source-conflict')
            self.assertEqual(restored['state'], 'failed')
            log = (store.path('source-conflict').parent / 'worker.log').read_text()
            self.assertIn('revision_conflict', log)
            self.assertEqual(source.read_bytes(), b'external revision')
            self.assertFalse((root / 'output').exists())
            self.assertFalse((root / 'runtime').exists())
            self.assertTrue((store.path('source-conflict').parent/'lifecycle.json').is_file(),'supervisor did not verify the owned process tree')
            lifecycle=json.loads((store.path('source-conflict').parent/'lifecycle.json').read_text())
            self.assertEqual(lifecycle['status'],'stopped')
            self.assertEqual(lifecycle['returncode'],result['workerExitCode'])

    def create_store(self, directory):
        spec = importlib.util.spec_from_file_location('supervisor_exit_store', SCRIPT)
        managed = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(managed)
        store = managed.load('task_store').Store(Path(directory) / 'state')
        store.create('task', plan={}, output=str(Path(directory) / 'output'),
                     runtime_sha='a' * 64, inputs={}, source=None,
                     mode='workflow', authorization={})
        return store

    def test_successful_delivery_is_not_downgraded_by_late_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self.create_store(directory)
            store.start('task')
            store.delivered('task', {'manifestSha256': 'b' * 64})
            result = store.worker_exited('task', 1)
            self.assertEqual(result['state'], 'review_ready')
            self.assertEqual(result['delivery'], {'manifestSha256': 'b' * 64})

    def test_cancelled_before_start_remains_cancelled(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self.create_store(directory)
            store.cancel('task')
            self.assertEqual(store.worker_exited('task', 1)['state'], 'cancelled')

    def test_unsettled_operation_after_exit_cannot_be_replayed(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self.create_store(directory)
            store.start('task')
            operation = store.begin_step('task', 'edit', {'text': 'changed'})
            result = store.worker_exited('task', 1)
            self.assertEqual(result['state'], 'reconciling')
            self.assertEqual(result['steps'][0]['id'], operation)
            self.assertEqual(result['steps'][0]['state'], 'attempted')
            with self.assertRaisesRegex(ValueError, 'reconciliation_required'):
                store.start('task')


if __name__ == '__main__':
    unittest.main()
