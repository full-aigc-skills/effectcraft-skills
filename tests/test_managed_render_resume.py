"""受管理渲染只续跑同一导出操作，工程和旧编辑回执必须保全。"""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]


def managed_module():
    spec=importlib.util.spec_from_file_location('managed_resume_test',ROOT/'skills/effectcraft-use/scripts/managed.py')
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


class RenderResumeTests(unittest.TestCase):
    def test_explicit_empty_exports_keeps_public_workflow_compatible(self):
        output=self.root/'empty-export';output.mkdir();(output/'project.ecproj').write_text(json.dumps({'schema':1,'items':{}}))
        plan=dict(self.plan,exports=[])
        store=self.tasks.Store(self.root/'empty-state')
        store.create('empty',plan=plan,output=str(output),runtime_sha=self.tasks.file_sha(self.cli),
            inputs={},source=None,mode='workflow',authorization={});store.start('empty')
        context=dict(self.context,plan=plan,output=str(output),stage=str(output),project=str(output/'project.ecproj'))
        try:
            result=self.managed.load('workflow').finish_export(context,self.managed.Hooks(store,'empty'))
        except IndexError:self.fail('explicit empty exports must not be indexed as a segmented export')
        self.assertIsNone(result['imageSequence']);self.assertIsNone(result['video'])
        self.assertTrue(all(s['state']=='succeeded' for s in store.read('empty')['steps']))
        usage=store.read('empty')['resources']['entries']['empty']
        self.assertEqual(usage['frames'],len(plan.get('frames',[0])))
        self.assertEqual(usage['encodedBytes'],0)

    def setUp(self):
        self.managed=managed_module();self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.output=self.root/'output';self.output.mkdir()
        self.project=self.output/'project.ecproj';self.project.write_bytes(b'native saved project')
        self.cli=self.root/'effectcraft-cli';self.cli.write_bytes(b'fixed runtime')
        self.tasks=self.managed.load('task_store');self.store=self.tasks.Store(self.root/'state')
        self.plan={'document':{'name':'Intro','width':2,'height':1,'frameRate':4,'duration':1},
            'operations':[],'frames':[],'exports':[{'format':'png-segmented','chunkFrames':2}]}
        self.store.create('task',plan=self.plan,output=str(self.output),runtime_sha=self.tasks.file_sha(self.cli),
            inputs={},source=None,mode='workflow',authorization={})
        self.store.start('task')
        op=self.store.begin_step('task','save_project',{'path':str(self.project)})
        self.store.finish_step('task',op,{'saved':True})
        self.export=self.store.begin_step('task','render_and_deliver',{'project':str(self.project),'exports':self.plan['exports']})
        self.context={'schema':'effectcraft-export-context/v1','plan':self.plan,'output':str(self.output),
            'stage':str(self.output),'working':str(self.output),'project':str(self.project),
            'sourceProject':None,'sourceHash':None,'comp':dict(self.plan['document']),
            'layers':{},'frames':[],'bindings':{},'assets':{},'receipts':[],
            'cli':str(self.cli),'runtimeSha256':self.tasks.file_sha(self.cli),'executionIdentity':{}}

    def checkpoint(self):
        hooks=self.managed.Hooks(self.store,'task')
        self.assertTrue(hasattr(hooks,'checkpoint_export'),'managed segmented export checkpoint is missing')
        hooks.checkpoint_export(self.export,self.context)
        self.store.fail('task','render interrupted',unknown=True)
        self.tasks.atomic_json(self.store.path('task').parent/'lifecycle.json',{
            'schema':'effectcraft-process-lifecycle/v1','status':'stopped','returncode':1})

    def test_reconcile_marks_only_bound_render_ready_without_replaying_steps(self):
        self.checkpoint();before=self.store.read('task')
        result=self.managed.reconcile(self.store,'task')
        self.assertEqual(result['reconciliation']['result'],'render_resume_ready')
        self.assertEqual(result['state'],'reconciling')
        self.assertEqual(result['steps'],before['steps'])
        self.assertEqual(result['deadline'],before['deadline'])

    def test_changed_project_or_runtime_refuses_render_recovery(self):
        self.checkpoint();self.project.write_bytes(b'GUI external edit')
        with self.assertRaisesRegex(ValueError,'render_recovery_input_changed'):
            self.managed.reconcile(self.store,'task')
        self.assertEqual(self.project.read_bytes(),b'GUI external edit')
        self.project.write_bytes(b'native saved project');self.cli.write_bytes(b'new runtime')
        with self.assertRaisesRegex(ValueError,'render_recovery_runtime_changed'):
            self.managed.reconcile(self.store,'task')

    def test_live_guardian_prevents_render_recovery(self):
        self.checkpoint()
        with self.managed.load('platform_support').exclusive_lock(self.store.root/'leases/task.lifecycle.lock',timeout=0):
            with self.assertRaises(TimeoutError):self.managed.reconcile(self.store,'task')

    def test_corrupt_context_or_unrelated_file_is_preserved_and_refused(self):
        self.checkpoint();extra=self.output/'personal.txt';extra.write_text('keep')
        with self.assertRaisesRegex(ValueError,'render_recovery_unowned_file'):
            self.managed.reconcile(self.store,'task')
        self.assertEqual(extra.read_text(),'keep');extra.unlink()
        path=self.store.path('task').parent/'render-context.json';path.write_text('{broken')
        with self.assertRaisesRegex(ValueError,'render_recovery_context_changed'):
            self.managed.reconcile(self.store,'task')
        self.assertEqual(path.read_text(),'{broken')

    def test_unknown_edit_cannot_be_promoted_to_render_resume(self):
        # 未知编辑无导出检查点，不因产物存在就认定可以重放。
        self.store.fail('task','unknown edit',unknown=True)
        self.tasks.atomic_json(self.store.path('task').parent/'lifecycle.json',{
            'schema':'effectcraft-process-lifecycle/v1','status':'stopped','returncode':1})
        result=self.managed.reconcile(self.store,'task')
        self.assertEqual(result['reconciliation']['result'],'unknown')

    def test_cancelled_render_cannot_be_promoted_to_resume(self):
        self.checkpoint();self.store.cancel('task')
        result=self.managed.reconcile(self.store,'task')
        self.assertEqual(result['reconciliation']['result'],'unknown')
        with self.assertRaisesRegex(ValueError,'cancel_requested'):
            self.managed.supervise(self.store,'task',self.root/'runtime',recover=True)


if __name__=='__main__':unittest.main()
