"""当前工程必须经固定引擎重开临时副本；历史保存回执不等于本次检查。"""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT=Path(__file__).resolve().parents[1]/'skills/effectcraft-use/scripts/engineering_review.py'

class EngineeringReviewTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SCRIPT.is_file(),'current engineering verifier missing')
        spec=importlib.util.spec_from_file_location('engineering_test',SCRIPT)
        self.module=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.module)
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)/'delivery';self.root.mkdir()
        (self.root/'project.ecproj').write_bytes(b'native fixture')
        self.comp={'id':1,'width':16,'height':16,'frameRate':1,'duration':1,'layers':[{'id':2}]}
        self.layers={'2':{'id':2,'name':'title','properties':[]}}
        self.native={'composition':self.comp,'layers':self.layers}
        (self.root/'native.json').write_text(json.dumps(self.native),encoding='utf-8')
        self.quality=self.module.load('quality_review')
        (self.root/'manifest.json').write_text(json.dumps({'files':{p.name:self.quality.sha(p) for p in self.root.iterdir()},'assets':{}}),encoding='utf-8')
        self.home=Path(self.tmp.name)/'runtime';self.calls=[];self.native_comp=self.comp;self.native_layers=self.layers
        self.footage={'checked':0,'missing':0,'probed':0};self.error=None;self.change_original=False
        original_load=self.module.load;owner=self
        class Session:
            def __init__(self,args,timeout):owner.calls.append(('spawn',args))
            def __enter__(self):return self
            def __exit__(self,*args):owner.calls.append(('closed',None))
            def request(self,method,params):
                name=params['name'];args=params['arguments'];owner.calls.append((name,args))
                if isinstance(owner.error,BaseException):raise owner.error
                if owner.error:raise RuntimeError(owner.error)
                if owner.change_original:(owner.root/'project.ecproj').write_bytes(b'outside edit')
                value={'open_project':{'dirty':False},'get_project':{'items':[{'id':1,'type':'Composition'}]},
                    'execute_command':owner.footage,'get_comp':owner.native_comp,'get_layer':owner.native_layers['2']}[name]
                return {'content':[{'type':'text','text':json.dumps(value)}],'isError':False}
        self.session=Session
        self.bootstrap=original_load('bootstrap');self.platform=original_load('platform_support')
        self.lock={'artifact':'effectcraft-cli','resolvedVersion':'0.4.0','artifacts':{'test':{'binarySha256':'a'*64}}}
        self.bootstrap.inspect_install=lambda *a:{'executable':'fixed-cli','binarySha256':'a'*64}
        self.platform.platform_key=lambda:'test'
        self.module.load=lambda name:({'bootstrap':self.bootstrap,'platform_support':self.platform,'mcp_session':type('M',(),{'Session':Session})}.get(name) or original_load(name))
        self.module.runtime_lock=lambda:self.lock

    def verify(self):return self.module.verify(self.root,self.home,'a'*64)

    def test_reopen_snapshot_matches_actual_comp_and_layers(self):
        before={p.name:p.read_bytes() for p in self.root.iterdir()}
        report=self.verify();self.assertEqual(report['status'],'PASS',report)
        self.assertEqual(report['schema'],'effectcraft-engineering-review/v1');self.assertTrue(report['fresh'])
        opened=next(args['path'] for name,args in self.calls if name=='open_project')
        self.assertNotEqual(Path(opened),self.root/'project.ecproj');self.assertFalse(Path(opened).exists())
        self.assertEqual({p.name:p.read_bytes() for p in self.root.iterdir()},before)
        self.assertNotIn('save_project',[name for name,args in self.calls])
        self.assertEqual([args['command'] for name,args in self.calls if name=='execute_command'],['footage.check'])

    def test_missing_runtime_does_not_install_or_create_cache(self):
        self.bootstrap.inspect_install=lambda *a:(_ for _ in ()).throw(ValueError('invalid_installed_path'))
        report=self.verify();self.assertEqual(report['status'],'NOT_RUN');self.assertFalse(self.home.exists());self.assertFalse(self.calls)

    def test_task_runtime_mismatch_cannot_launch(self):
        self.lock['artifacts']['test']['binarySha256']='b'*64
        self.assertEqual(self.verify()['status'],'NOT_RUN');self.assertFalse(self.calls)

    def test_native_open_error_is_engineering_failure(self):
        self.error='invalid project'
        self.assertEqual(self.verify()['status'],'FAIL');self.assertIn(('closed',None),self.calls)

    def test_native_structure_drift_is_engineering_failure(self):
        self.native_comp=dict(self.comp,width=17)
        report=self.verify();self.assertEqual(report['status'],'FAIL');self.assertIn('native_snapshot_mismatch',report['reason'])

    def test_missing_native_footage_is_engineering_failure(self):
        self.footage={'checked':1,'missing':1,'probed':0}
        report=self.verify();self.assertEqual(report['status'],'FAIL');self.assertIn('native_footage_missing',report['reason'])

    def test_original_changes_during_read_only_check_are_not_accepted(self):
        self.change_original=True
        report=self.verify();self.assertEqual(report['status'],'FAIL');self.assertIn('artifact_changed',report['reason'])
        self.assertEqual((self.root/'project.ecproj').read_bytes(),b'outside edit')

    def test_incomplete_native_timeout_is_not_run(self):
        self.error=TimeoutError('native read timed out')
        report=self.verify();self.assertEqual(report['status'],'NOT_RUN')
        self.assertIn(('closed',None),self.calls)

    def test_all_four_states_are_explicit_and_user_is_not_accepted_by_model(self):
        report=self.quality.inspect_delivery(self.root)
        self.assertEqual(report.get('userAcceptance',{}).get('status'),'NOT_RUN')
        self.assertFalse(report['accepted']);self.assertEqual(report['creative']['status'],'NOT_RUN')

class EngineeringLedgerTests(unittest.TestCase):
    def setUp(self):
        import test_managed_review_ledger as fixtures
        self.fixture=fixtures.ReviewLedgerTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        # 公开review测试使用新任务绑定；旧无绑定记录由管理入口保护测试覆盖。
        f=self.fixture;binding=f.managed.load('runtime_binding');value,manifest=binding.prepare(fixtures.SCRIPT.parent.parent,f.root/'absent-runtime')
        state=f.store.read('root');state['identity']['runtimeBinding']=value
        state['identity']['runtimeSha256']=json.loads((fixtures.SCRIPT.parent/'runtime.lock.json').read_text())['artifacts'][value['platform']]['binarySha256']
        state['identityHash']=f.tasks.digest(state['identity']);f.store.save(state)
        binding.freeze(f.store,'root',fixtures.SCRIPT.parent.parent,manifest)

    def invoke(self):
        import subprocess,sys
        f=self.fixture;criteria=f.root/'criteria.json';f.tasks.atomic_json(criteria,f.criteria)
        cmd=[sys.executable,'-I','-B',str(f.managed.HERE/'managed.py'),'--state-root',str(f.store.root),
            '--runtime-home',str(f.root/'absent-runtime'),'review','--task','root','--criteria',str(criteria)]
        p=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',timeout=30)
        self.assertEqual(p.returncode,0,p.stdout+p.stderr);return json.loads(p.stdout)

    def test_historical_save_receipt_does_not_generate_new_visual_request(self):
        result=self.invoke()
        self.assertEqual(result['report']['technical']['status'],'PASS')
        self.assertEqual(result['report']['engineering']['status'],'NOT_RUN')
        self.assertIsNone(result['judgeRequest']);self.assertEqual(result['requiredAction'],'engineering_verification')
        self.assertFalse((self.fixture.store.path('root').parent/'judge-request.json').exists())

    def test_settled_history_cannot_substitute_current_engineering(self):
        f=self.fixture;f.accept(response_changes={'status':'PASS','passed':True,'issues':[]})
        state=f.store.path('root');before=state.read_bytes();reference=f.store.read('root')['review'];history=state.parent/reference['path'];original=history.read_bytes()
        result=self.invoke()
        self.assertEqual(result['report']['engineering']['status'],'NOT_RUN')
        self.assertEqual(result['report']['creative']['status'],'NOT_RUN')
        self.assertFalse(result['report']['readyForAcceptance']);self.assertFalse(result['report']['accepted'])
        self.assertEqual(state.read_bytes(),before);self.assertEqual(history.read_bytes(),original)

    def test_current_engineering_failure_does_not_return_settled_creative_pass(self):
        f=self.fixture;f.accept(response_changes={'status':'PASS','passed':True,'issues':[]})
        statefile=f.store.path('root');before=statefile.read_bytes()
        f.engineering_status['root']='FAIL'
        result=f.managed.review(f.store,'root',f.criteria)
        self.assertEqual(result['report']['engineering']['status'],'FAIL')
        self.assertEqual(result['report']['creative']['status'],'NOT_RUN')
        self.assertFalse(result['report']['readyForAcceptance']);self.assertIsNone(result['judgeRequest'])
        self.assertEqual(statefile.read_bytes(),before)

    def test_revision_requires_fresh_engineering_before_spending_budget(self):
        self.fixture.accept()
        self.fixture.assert_revision_rejected_without_execution('root','engineering_gate')
