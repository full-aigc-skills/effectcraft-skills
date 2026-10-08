"""命令已成功但交付登记崩溃时，只核对原产物，绝不重发创作。"""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parents[1]/'skills/effectcraft-use/scripts'
def load(name):
    spec=importlib.util.spec_from_file_location('completion_test_'+name,HERE/(name+'.py'))
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value

spec=importlib.util.spec_from_file_location('completion_delivery_fixture',Path(__file__).with_name('test_managed_command_delivery.py'))
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)


class CommandCompletionTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((HERE/'command_completion.py').is_file(),'completion crash recovery is missing')
        self.completion=load('command_completion');self.tasks=load('task_store');self.managed=load('managed');self.delivery=load('command_delivery')
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name).resolve();self.output=self.root/'output'
        self.store=self.tasks.Store(self.root/'state');self.home=self.root/'runtime';self.request={'inputs':{},'source':None}
        self.plan={'schema':'craft-command-plan/v1','operations':[{'tool':'save_project','params':{'path':{'$output':'project.ecproj'}}},{'tool':'render_frame','params':{'path':{'$output':'preview.png'},'comp':1,'time':0,'max_side':0,'transparent':True,'inline':False}}]}
        binding,manifest=load('runtime_binding').prepare(HERE.parent,self.home);lock=json.loads((HERE/'runtime.lock.json').read_text(encoding='utf-8'));runtime=lock['artifacts'][binding['platform']]['binarySha256']
        self.store.create('task',plan=self.plan,output=str(self.output),runtime_sha=runtime,inputs={},source=None,mode='commands',authorization={'requestHash':self.tasks.digest(self.request)},runtime_binding=binding)
        self.tasks.atomic_json(self.store.path('task').parent/'request.json',self.request)
        load('runtime_binding').freeze(self.store,'task',HERE.parent,manifest);self.store.start('task');self.output.mkdir()
        self.store.reserve_resources('task',{'frames':1,'decodedBytes':0},self.store.read('task')['identity']['planHash'])
        load('resource_meter').watch(self.store,'task',self.output,self.output,'commands')
        self.lifecycle={'schema':'effectcraft-process-lifecycle/v1','status':'running','guardianPid':100,'workerGroup':101,'startedAt':time.time()}
        self.tasks.atomic_json(self.store.lifecycle_path(self.store.read('task')),self.lifecycle)
        observer=self.delivery.Observer(self.store,'task');session=fixture.Session();records=[]
        for index,op in enumerate(self.plan['operations']):
            args=load('commands').resolve(op['params'],{'output':str(self.output)})
            row={'index':index,'tool':op['tool'],'command':None,'params':args,'state':'started'}
            observer(session,row,'before');identifier=self.store.begin_step('task',op['tool'],{'name':op['tool'],'arguments':args})
            if index==0:self.tasks.atomic_json(self.output/'project.ecproj',{'schema':1,'settings':{},'items':{}})
            else:(self.output/'preview.png').write_bytes(fixture.png())
            result={'path':args['path']};self.store.finish_step('task',identifier,result);row.update(state='succeeded',result=result);observer(session,row,'after');records.append(row)
        state=self.store.read('task')
        import hashlib
        self.receipt={'schema':'craft-command-receipt/v1','pluginId':'effectcraft','mode':'headless','result':'PASS','runtimeSha256':runtime,'steps':records,'planSha256':hashlib.sha256(json.dumps(self.plan,ensure_ascii=False,sort_keys=True,allow_nan=False).encode()).hexdigest()}
        for name in ('success.json','journal.json'):self.tasks.atomic_json(self.output/name,self.receipt)

    def seal_and_stop(self):
        self.completion.capture(self.store,'task');self.store.fail('task','crash after command completion',unknown=True)
        self.tasks.atomic_json(self.store.lifecycle_path(self.store.read('task')),dict(self.lifecycle,status='stopped',returncode=1))

    def inspectors(self, change=None):
        delivery=self.delivery;original=delivery.load
        def modules(name):
            if name=='bootstrap':return SimpleNamespace(inspect_install=lambda *a,**k:{'executable':'fixture-native'})
            if name=='mcp_session':
                class Native(fixture.Session):
                    def __init__(self,*args,**kwargs):super().__init__()
                    def __exit__(inner,*args):
                        if change:change()
                return SimpleNamespace(Session=Native)
            return original(name)
        existing=self.completion.load
        return patch.object(self.completion,'load',side_effect=lambda name:delivery if name=='command_delivery' else existing(name)),patch.object(delivery,'load',side_effect=modules)

    def test_recover_completed_outputs_without_resending_edits(self):
        self.seal_and_stop();before=copy.deepcopy(self.store.read('task'));files={p.name:p.read_bytes() for p in self.output.iterdir()}
        a,b=self.inspectors()
        with a,b:result=self.completion.recover(self.store,'task')
        self.assertEqual(result['state'],'review_ready');self.assertEqual(result['reconciliation']['result'],'verified_completed_commands')
        self.assertEqual(result['steps'],before['steps']);self.assertEqual(result['deadline'],before['deadline']);self.assertEqual(result['budget'],before['budget'])
        self.assertEqual({p.name:p.read_bytes() for p in self.output.iterdir()},files)
        self.assertEqual(result['delivery']['engineeringReopen'],'PASS')
        again=self.completion.recover(self.store,'task');self.assertEqual(again,result)

    def test_missing_proof_keeps_legacy_unknown_without_reconstruction(self):
        self.store.fail('task','old unknown',unknown=True);before=self.store.path('task').read_bytes()
        self.assertEqual(self.completion.recover(self.store,'task')['state'],'reconciling');self.assertEqual(self.store.path('task').read_bytes(),before)
        self.assertFalse((self.store.path('task').parent/'command-completion.json').exists())

    def test_capture_refuses_unresolved_operation(self):
        self.store.begin_step('task','edit',{})
        with self.assertRaisesRegex(ValueError,'completion_unresolved'):self.completion.capture(self.store,'task')

    def test_corrupt_proof_preserves_original_task(self):
        self.seal_and_stop();path=self.store.path('task').parent/'command-completion.json';path.write_text('{broken');before=self.store.path('task').read_bytes()
        with self.assertRaisesRegex(ValueError,'completion_proof_invalid'):self.completion.recover(self.store,'task')
        self.assertEqual(self.store.path('task').read_bytes(),before);self.assertEqual(path.read_text(),'{broken')

    def test_changed_artifacts_and_receipt_are_refused(self):
        self.seal_and_stop()
        for name in ('project.ecproj','preview.png','success.json','journal.json'):
            with self.subTest(name=name):
                path=self.output/name;content=path.read_bytes();path.write_bytes(content+b' ')
                with self.assertRaisesRegex(ValueError,'completion_proof_invalid'):self.completion.recover(self.store,'task')
                path.write_bytes(content)

    def test_added_output_or_directory_replacement_is_refused(self):
        self.seal_and_stop();extra=self.output/'personal.txt';extra.write_text('preserve')
        with self.assertRaisesRegex(ValueError,'completion_proof_invalid'):self.completion.recover(self.store,'task')
        self.assertEqual(extra.read_text(),'preserve');extra.unlink();moved=self.root/'moved';self.output.rename(moved);self.output.mkdir()
        with self.assertRaisesRegex(ValueError,'completion_proof_invalid'):self.completion.recover(self.store,'task')

    def test_wrong_lifecycle_owner_cannot_complete_task(self):
        self.seal_and_stop();self.tasks.atomic_json(self.store.lifecycle_path(self.store.read('task')),dict(self.lifecycle,status='stopped',returncode=1,guardianPid=200))
        with self.assertRaisesRegex(ValueError,'completion_process_unconfirmed'):self.completion.recover(self.store,'task')

    def test_running_lifecycle_cannot_complete_task(self):
        self.seal_and_stop();self.tasks.atomic_json(self.store.lifecycle_path(self.store.read('task')),self.lifecycle)
        with self.assertRaisesRegex(ValueError,'completion_process_unconfirmed'):self.completion.recover(self.store,'task')

    def test_cancellation_during_readonly_reopen_does_not_publish_late_delivery(self):
        self.seal_and_stop();a,b=self.inspectors(lambda:self.store.cancel('task'))
        with a,b:
            with self.assertRaisesRegex(ValueError,'cancel_requested'):self.completion.recover(self.store,'task')
        self.assertIsNone(self.store.read('task')['delivery']);self.assertIsNotNone(self.store.read('task').get('cancellationRequestedAt'))

    def test_change_during_readonly_reopen_is_not_committed(self):
        self.seal_and_stop();a,b=self.inspectors(lambda:(self.output/'preview.png').write_bytes(b'foreign'))
        with a,b:
            with self.assertRaisesRegex(ValueError,'completion_proof_invalid'):self.completion.recover(self.store,'task')
        self.assertIsNone(self.store.read('task')['delivery']);self.assertEqual((self.output/'preview.png').read_bytes(),b'foreign')

    def test_expired_task_does_not_start_new_native_verification(self):
        self.seal_and_stop();state=self.store.read('task');state['deadline']=state['createdAt']-1;self.store.save(state)
        with self.assertRaisesRegex(ValueError,'deadline_exceeded'):self.completion.recover(self.store,'task')

    def test_orphan_completion_file_is_not_silently_adopted(self):
        path=self.store.path('task').parent/'command-completion.json';path.write_text('{}')
        with self.assertRaisesRegex(ValueError,'completion_orphan_proof'):self.completion.capture(self.store,'task')

    def test_incomplete_public_plan_cannot_be_sealed(self):
        changed=copy.deepcopy(self.receipt);changed['steps'].pop();self.tasks.atomic_json(self.output/'success.json',changed)
        with self.assertRaisesRegex(ValueError,'completion_unresolved'):self.completion.capture(self.store,'task')


if __name__=='__main__':unittest.main()
