"""升级后任务继续使用原执行组合；未知和损坏绑定不能自动重建。"""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'skills/effectcraft-use'
def load(name):
    spec=importlib.util.spec_from_file_location('binding_test_'+name,BASE/'scripts'/(name+'.py'))
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result

class RuntimeBindingTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((BASE/'scripts/runtime_binding.py').exists(),'task execution binding is missing')
        self.m=load('runtime_binding');self.tasks=load('task_store');self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.source=self.root/'skill';shutil.copytree(BASE,self.source,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        self.store=self.tasks.Store(self.root/'state');self.home=self.root/'native'
        self.binding,self.manifest=self.m.prepare(self.source,self.home)

    def create(self,task='task',plan=None,binding=None):
        binding=binding or self.binding
        lock=json.loads((self.source/'scripts/runtime.lock.json').read_text(encoding='utf-8'))
        return self.store.create(task,plan=plan or {'name':'task'},output=str(self.root/task),runtime_sha=lock['artifacts'][binding['platform']]['binarySha256'],
            inputs={},source=None,mode='workflow',authorization={},runtime_binding=binding)

    def frozen(self):
        self.create();self.m.freeze(self.store,'task',self.source,self.manifest)
        return self.store.path('task').parent/'execution/skill'

    def test_snapshot_is_self_contained_and_unchanged_after_source_upgrade(self):
        frozen=self.frozen();before=(frozen/'scripts/managed.py').read_bytes()
        (self.source/'scripts/managed.py').write_text('raise RuntimeError("new implementation")',encoding='utf-8')
        result=self.m.resolve(self.store,'task')
        self.assertEqual(result['script'],str(frozen/'scripts/managed.py'));self.assertEqual((frozen/'scripts/managed.py').read_bytes(),before)
        self.assertEqual(result['runtimeHome'],str(self.home))

    def test_snapshot_contains_parameter_and_additional_platform_contracts(self):
        frozen=self.frozen()
        for name in ('parameter-contract.json','additional-platforms.lock.json','web_adapter.mjs'):
            self.assertEqual((frozen/'scripts'/name).read_bytes(),(self.source/'scripts'/name).read_bytes())

    def test_new_task_uses_changed_source_without_mutating_old_snapshot(self):
        old=self.frozen();old_bytes=(old/'scripts/managed.py').read_bytes()
        (self.source/'scripts/managed.py').write_text('# upgraded implementation\n',encoding='utf-8')
        binding,manifest=self.m.prepare(self.source,self.home)
        self.assertNotEqual(binding['skillSha256'],self.binding['skillSha256'])
        self.create('new',plan={'different':True},binding=binding);self.m.freeze(self.store,'new',self.source,manifest)
        self.assertEqual((old/'scripts/managed.py').read_bytes(),old_bytes);self.m.resolve(self.store,'task');self.m.resolve(self.store,'new')

    def test_unknown_work_cannot_bypass_identity_with_new_executor_binding(self):
        self.frozen();self.store.start('task');self.store.begin_step('task','edit',{})
        self.store.fail('task','unknown',unknown=True)
        changed=copy.deepcopy(self.binding);changed['skillSha256']='b'*64
        with self.assertRaisesRegex(ValueError,'reconciliation_required'):self.create('new',binding=changed)
        self.assertFalse(self.store.path('new').exists())

    def test_missing_snapshot_is_preserved_and_not_regenerated(self):
        self.create();before=self.store.path('task').read_bytes()
        with self.assertRaisesRegex(ValueError,'execution_snapshot'):self.m.resolve(self.store,'task')
        self.assertEqual(self.store.path('task').read_bytes(),before);self.assertFalse((self.store.path('task').parent/'execution').exists())

    def test_changed_snapshot_and_extra_file_refuse_execution(self):
        frozen=self.frozen();file=frozen/'scripts/managed.py';file.write_bytes(file.read_bytes()+b'\n# changed')
        with self.assertRaisesRegex(ValueError,'execution_snapshot'):self.m.resolve(self.store,'task')
        file.write_bytes((self.source/'scripts/managed.py').read_bytes());extra=frozen/'scripts/extra.py';extra.write_bytes(b'keep')
        with self.assertRaisesRegex(ValueError,'execution_snapshot'):self.m.resolve(self.store,'task')
        self.assertEqual(extra.read_bytes(),b'keep')

    def test_changed_interpreter_is_rejected_without_launch(self):
        self.frozen()
        with patch.object(self.m,'file_sha',return_value='0'*64):
            with self.assertRaisesRegex(ValueError,'bound_python_changed'):self.m.verify_python(self.binding['python'],self.source)

    def test_source_drift_between_prepare_and_freeze_keeps_registered_task(self):
        self.create();path=self.source/'scripts/managed.py';path.write_bytes(path.read_bytes()+b'\n# race')
        with self.assertRaisesRegex(ValueError,'execution_source_changed'):self.m.freeze(self.store,'task',self.source,self.manifest)
        self.assertEqual(self.store.read('task')['state'],'planned');self.assertFalse((self.store.path('task').parent/'execution').exists())

    def test_partial_snapshot_copy_is_preserved_and_not_resumed(self):
        self.create();real_copy=self.m.shutil.copyfile;calls=[]
        def failing_copy(source,target):
            calls.append(str(target))
            if len(calls)==2:raise OSError('controlled snapshot copy failure')
            return real_copy(source,target)
        with patch.object(self.m.shutil,'copyfile',side_effect=failing_copy),self.assertRaisesRegex(OSError,'controlled snapshot'):
            self.m.freeze(self.store,'task',self.source,self.manifest)
        partial=list(self.store.path('task').parent.glob('.execution-*'));self.assertEqual(len(partial),1)
        self.assertTrue(Path(calls[0]).is_file());before=self.store.path('task').read_bytes()
        with self.assertRaisesRegex(ValueError,'execution_snapshot_invalid'):self.m.resolve(self.store,'task')
        self.assertEqual(self.store.path('task').read_bytes(),before);self.assertTrue(partial[0].exists())

    def test_all_independent_skill_entries_freeze_before_any_native_call(self):
        suite=json.loads((ROOT/'skill-suite.json').read_text(encoding='utf-8'))
        for row in suite['skills']:
            name=row['name'];path=ROOT/'skills'/name/'scripts/managed.py'
            with self.subTest(skill=name):
                spec=importlib.util.spec_from_file_location('independent_'+name,path);managed=importlib.util.module_from_spec(spec);spec.loader.exec_module(managed)
                store=managed.load('task_store').Store(self.root/'standalone state'/name)
                plan=json.loads((BASE/'examples/brand-intro.json').read_text(encoding='utf-8'))
                with patch.object(managed,'supervise',side_effect=lambda s,t,h:s.read(t)):
                    state=managed.run(store,plan,self.root/'outputs'/name,self.home,task='registered')
                self.m.resolve(store,'registered');self.assertEqual(state['state'],'planned')
        self.assertFalse(self.home.exists());self.assertFalse((self.root/'outputs').exists())

    def test_source_symlink_is_not_copied(self):
        path=self.source/'scripts/extra.py'
        try:path.symlink_to(self.root/'outside')
        except OSError as error:self.skipTest(str(error))
        with self.assertRaisesRegex(ValueError,'execution_source_symlink'):self.m.prepare(self.source,self.home)

    def test_root_and_resource_directory_symlinks_are_refused(self):
        alias=self.root/'alias'
        try:alias.symlink_to(self.source,target_is_directory=True)
        except OSError as error:self.skipTest(str(error))
        with self.assertRaisesRegex(ValueError,'execution_source_symlink'):self.m.prepare(alias,self.home)
        original=self.source/'scripts';moved=self.root/'scripts';original.rename(moved);original.symlink_to(moved,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'execution_source_symlink'):self.m.prepare(self.source,self.home)

    def test_malformed_binding_types_have_stable_diagnostics(self):
        for key,value in [('skillSha256',None),('runtimeHome',5),('nativeVersion',[]),('platform',None)]:
            bad=copy.deepcopy(self.binding);bad[key]=value
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'execution_binding_invalid'):self.m.validate_binding(bad)
        for key,value in [('sha256',None),('executable',5),('version',[]),('mode',[])]:
            bad=copy.deepcopy(self.binding);bad['python'][key]=value
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'execution_binding_invalid'):self.m.validate_binding(bad)

    def test_snapshot_manifest_symlink_is_refused(self):
        self.frozen();manifest=self.store.path('task').parent/'execution/manifest.json';external=self.root/'manifest.json';manifest.rename(external)
        try:manifest.symlink_to(external)
        except OSError as error:self.skipTest(str(error))
        with self.assertRaisesRegex(ValueError,'execution_snapshot_invalid'):self.m.resolve(self.store,'task')

    def test_manifest_path_escape_is_rejected_before_copy(self):
        self.create();bad=copy.deepcopy(self.manifest);bad['../outside']='a'*64
        with self.assertRaises(ValueError):self.m.freeze(self.store,'task',self.source,bad)
        self.assertFalse((self.store.path('task').parent/'outside').exists())

    def test_legacy_task_cannot_acquire_binding_implicitly(self):
        self.store.create('legacy',plan={},output=str(self.root/'legacy'),runtime_sha='a'*64,inputs={},source=None,mode='workflow',authorization={})
        before=self.store.path('legacy').read_bytes()
        with self.assertRaisesRegex(ValueError,'legacy_execution_binding_missing'):self.m.resolve(self.store,'legacy')
        self.assertEqual(before,self.store.path('legacy').read_bytes())

    def test_retention_includes_original_runtime_and_python_references(self):
        self.frozen();report=self.m.references(self.store)
        self.assertIn(str(self.home/'effectcraft'/'0.4.0'),report['nativeVersions'])
        self.assertIn(self.binding['python']['executable'],report['pythonExecutables'])
        self.assertFalse(report['destructiveCleanupAllowed'])

    def test_corrupt_state_blocks_retention_instead_of_hiding_reference(self):
        self.create();self.store.path('task').write_text('{broken',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'state_invalid'):self.m.references(self.store)

    def test_public_legacy_resume_is_diagnostic_and_does_not_start_worker(self):
        import subprocess
        self.store.create('legacy',plan={},output=str(self.root/'legacy'),runtime_sha='a'*64,inputs={},source=None,mode='workflow',authorization={})
        result=subprocess.run([sys.executable,'-I','-B',str(BASE/'scripts/managed.py'),'--state-root',str(self.store.root),'resume','--task','legacy'],capture_output=True)
        self.assertEqual(result.returncode,1);self.assertIn('legacy_execution_binding_missing',json.loads(result.stdout)['error'])
        self.assertFalse((self.store.path('legacy').parent/'worker.log').exists());self.assertEqual(self.store.read('legacy')['state'],'planned')

    def test_handoff_uses_frozen_controller_and_original_home(self):
        frozen=self.frozen();args=SimpleNamespace(action='resume',task='task',runtime_home=self.root/'new native')
        with patch.object(self.m.os,'execv') as execute:
            if self.m.os.name=='nt':
                with patch.object(self.m,'windows_handoff') as bridge:self.m.handoff(self.store,args,BASE/'scripts/managed.py')
                argv=bridge.call_args.args[-1]
            else:
                self.m.handoff(self.store,args,BASE/'scripts/managed.py');argv=execute.call_args.args[1]
        self.assertEqual(argv[0],self.binding['python']['executable']);self.assertIn(str(frozen/'scripts/managed.py'),argv)
        self.assertEqual(argv[argv.index('--runtime-home')+1],str(self.home));self.assertEqual(argv[-3:],['resume','--task','task'])

    def test_already_bound_controller_does_not_dispatch_again(self):
        frozen=self.frozen();args=SimpleNamespace(action='resume',task='task')
        with patch.object(self.m.os,'execv') as execute,patch.object(self.m,'windows_handoff') as bridge:
            self.m.handoff(self.store,args,frozen/'scripts/managed.py');execute.assert_not_called();bridge.assert_not_called()

    def test_public_run_registers_complete_snapshot_before_supervision(self):
        managed=load('managed');plan=json.loads((BASE/'examples/brand-intro.json').read_text(encoding='utf-8'))
        with patch.object(managed,'HERE',self.source/'scripts'),patch.object(managed,'supervise',side_effect=lambda s,t,h:s.read(t)):
            state=managed.run(self.store,plan,self.root/'delivery',self.home,task='registered')
        self.assertEqual(state['state'],'planned');bound=self.m.resolve(self.store,'registered')
        self.assertEqual(bound['runtimeHome'],str(self.home));self.assertIn('/execution/skill/scripts/managed.py',bound['script'].replace('\\','/'))
        self.assertFalse(self.home.exists());self.assertFalse((self.root/'delivery').exists())

    def test_supervisor_refuses_legacy_before_any_process(self):
        managed=load('managed')
        self.store.create('legacy',plan={},output=str(self.root/'legacy'),runtime_sha='a'*64,inputs={},source=None,mode='workflow',authorization={})
        with patch.object(managed.subprocess,'Popen') as launch,self.assertRaisesRegex(ValueError,'legacy_execution_binding_missing'):
            managed.supervise(self.store,'legacy',self.home)
        launch.assert_not_called();self.assertEqual(self.store.read('legacy')['state'],'planned')

    def test_windows_controller_handoff_requires_matching_stopped_receipt(self):
        import io
        self.frozen();bound=self.m.resolve(self.store,'task');before=self.store.path('task').read_bytes()
        for status,code,expected in [('stopped',0,SystemExit),('stopped',7,ValueError),('unknown',0,ValueError)]:
            def launch(command,**kwargs):
                receipt=Path(command[command.index('--receipt')+1])
                class Child:
                    stdin=io.BytesIO()
                    def wait(inner,**unused):
                        self.tasks.atomic_json(receipt,{'schema':'effectcraft-process-lifecycle/v1','status':status,'returncode':code})
                        return 0
                return Child()
            with self.subTest(status=status,code=code),patch.object(self.m.subprocess,'Popen',side_effect=launch) as process:
                with self.assertRaises(expected):self.m.windows_handoff(self.store,'task',bound,[bound['python'],'old-controller'])
                argv=process.call_args.args[0];self.assertEqual(argv[0],bound['python']);self.assertIn(bound['guard'],argv)
            self.assertEqual(self.store.path('task').read_bytes(),before)

if __name__=='__main__':unittest.main()
