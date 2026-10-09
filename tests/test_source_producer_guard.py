"""复制／移动包使用原生产账本；换任务或账本不构成未知编辑恢复。"""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import Mock,patch
import test_workflow_artifact_lineage as fixtures

load=fixtures.load
class SourceProducerGuardTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.WorkflowArtifactLineageTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.base=Path(self.temp.name)
        self.home=patch.object(Path,'home',return_value=self.base/'user');self.home.start();self.addCleanup(self.home.stop)
        self.tasks=load('task_store');self.managed=load('managed');self.lineage=load('artifact_lineage')
        self.store=self.tasks.Store(self.base/'original state');self.source=self.fixture.root
        self.plan=copy.deepcopy(self.fixture.context['plan'])
        self.original=self.store.create('producer',plan=self.plan,output=str(self.source),runtime_sha='a'*64,inputs={},source=None,mode='workflow',authorization={})
        self.store.start('producer');op=self.store.begin_step('producer','save_project',{'path':'project.ecproj'});self.store.finish_step('producer',op,{'saved':True})
        context=copy.deepcopy(self.fixture.context);context['plan']=self.plan
        context['artifactProducer']=self.managed.Hooks(self.store,'producer').artifact_identity()
        self.manifest=self.fixture.finish(context)
        self.copy=self.base/'copied delivery';shutil.copytree(self.source,self.copy)
        self.change={'operations':[],'expectedProjectSha256':self.manifest['files']['project.ecproj']}
    def confirm(self):
        self.store.delivered('producer',{'manifestSha256':self.tasks.file_sha(self.source/'manifest.json'),'projectSha256':self.tasks.file_sha(self.source/'project.ecproj'),'engineeringReopen':'PASS'})
        self.tasks.atomic_json(self.store.lifecycle_path(self.store.read('producer')),{'schema':'effectcraft-process-lifecycle/v1','status':'stopped','returncode':0})
    def deny_run(self,store=None,parent=None):
        store=store or self.store;before=self.store.path('producer').read_bytes();prepare=Mock(side_effect=AssertionError('runtime must not be prepared before source producer verification'))
        runtime=Mock(prepare=prepare);original=self.managed.load
        with patch.object(self.managed,'load',side_effect=lambda n:runtime if n=='runtime_binding' else original(n)):
            with self.assertRaisesRegex(ValueError,'source_producer'):
                self.managed.run(store,self.change,self.base/'new output',self.base/'runtime',source=self.copy,task='new-task',parent=parent)
        prepare.assert_not_called();self.assertFalse(store.path('new-task').exists());self.assertFalse((self.base/'new output').exists())
        self.assertEqual(self.store.path('producer').read_bytes(),before)
    def test_copied_unknown_source_rejects_new_id_and_output_before_runtime(self):self.deny_run()
    def test_cross_store_copy_resolves_original_unknown_producer(self):self.deny_run(self.tasks.Store(self.base/'other state'))
    def test_parent_argument_cannot_bypass_unknown_source(self):self.deny_run(parent='producer')
    def test_confirmed_whole_package_copy_resolves_across_stores(self):
        self.confirm();bound=self.lineage.producer_binding(self.tasks.Store(self.base/'other state'),self.copy)
        self.assertEqual(bound['owner']['stateRoot'],str(self.store.root));self.assertEqual(bound['owner']['taskId'],'producer')
        self.assertEqual(bound['owner']['identityHash'],self.original['identityHash'])
        self.assertEqual(bound['manifestSha256'],self.tasks.file_sha(self.copy/'manifest.json'))
        self.assertNotIn(str(self.base),json.dumps(self.manifest['artifactBinding']))
    def test_delivery_and_stop_must_both_be_proven(self):
        self.confirm()
        for corruption in ('delivery','stop','receipt','missing'):
            with self.subTest(corruption=corruption):
                statefile=self.store.path('producer');saved=statefile.read_bytes();life=self.store.lifecycle_path(self.store.read('producer'));life_saved=life.read_bytes()
                receipt=next((statefile.parent/'receipts').iterdir());receipt_saved=receipt.read_bytes()
                if corruption=='delivery':
                    state=self.store.read('producer');state['delivery']['manifestSha256']='0'*64;self.store.save(state)
                elif corruption=='stop':life.unlink()
                elif corruption=='receipt':receipt.write_bytes(b'corrupt')
                else:statefile.unlink()
                self.deny_run(self.tasks.Store(self.base/'other state')) if corruption!='missing' else self.assert_missing_rejected()
                statefile.write_bytes(saved);life.write_bytes(life_saved);receipt.write_bytes(receipt_saved)
    def assert_missing_rejected(self):
        with self.assertRaisesRegex(ValueError,'source_producer'):self.lineage.producer_binding(self.tasks.Store(self.base/'other state'),self.copy)
    def test_conflicting_or_corrupt_locator_is_preserved(self):
        self.confirm();bound=self.lineage.producer_binding(self.store,self.copy)
        locator=self.lineage.producer_locator(self.original['identityHash'],'producer');locator.write_bytes(b'corrupt');before=locator.read_bytes()
        with self.assertRaisesRegex(ValueError,'source_producer'):self.managed.Hooks(self.store,'producer').artifact_identity()
        self.assertEqual(locator.read_bytes(),before)
        with self.assertRaisesRegex(ValueError,'source_producer'):self.lineage.verify_producer(bound)
    def test_source_producer_changes_block_registered_step_and_delivery(self):
        self.confirm();bound=self.lineage.producer_binding(self.store,self.copy)
        auth={'sourceProducer':bound,'sourcePackage':self.lineage.source_binding(self.copy)}
        child=self.store.create('child',plan=self.change,output=str(self.base/'child output'),runtime_sha='a'*64,inputs={},source=str(self.copy/'project.ecproj'),mode='workflow',authorization=auth)
        self.store.start('child');state=self.store.read('producer');state['delivery']['manifestSha256']='0'*64;self.store.save(state)
        before=self.store.path('child').read_bytes()
        for action in (lambda:self.store.begin_step('child','edit',{}),lambda:self.store.delivered('child',{})):
            with self.assertRaisesRegex(ValueError,'source_producer'):action()
            self.assertEqual(self.store.path('child').read_bytes(),before)
    def test_old_local_producer_can_be_checked_without_backfilling_locator(self):
        self.confirm();directory=self.base/'user/.local/share/craft-tasks/effectcraft-artifact-producers'
        if directory.exists():shutil.rmtree(directory)
        state=self.store.read('producer');state.pop('artifactProducerLocator',None);self.store.save(state)
        bound=self.lineage.producer_binding(self.store,self.copy)
        self.assertIsNone(bound['locatorSha256']);self.assertFalse(directory.exists())
        with self.assertRaisesRegex(ValueError,'source_producer'):self.lineage.producer_binding(self.tasks.Store(self.base/'other state'),self.copy)

    def test_distinct_task_ids_with_equal_execution_hash_do_not_collide(self):
        other=self.tasks.Store(self.base/'equal identity state')
        second=other.create('other-task',plan=self.plan,output=str(self.base/'other delivery'),runtime_sha='a'*64,inputs={},source=None,mode='workflow',authorization={})
        self.assertEqual(second['identityHash'],self.original['identityHash'])
        self.assertEqual(self.managed.Hooks(other,'other-task').artifact_identity()['producerTaskId'],'other-task')
    def test_missing_registered_locator_is_not_backfilled(self):
        locator=self.lineage.producer_locator(self.original['identityHash'],'producer');locator.unlink()
        with self.assertRaisesRegex(ValueError,'source_producer'):self.managed.Hooks(self.store,'producer').artifact_identity()
        self.assertFalse(locator.exists())
