"""持久化副作用身份与恢复行为，不启动原生引擎。"""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1]/'skills/effectcraft-use/scripts/task_store.py'


class ManagedTaskTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SCRIPT.exists(), 'durable task store is missing')
        spec = importlib.util.spec_from_file_location('managed_store_test', SCRIPT)
        self.module = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.module)
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = self.module.Store(self.root/'state')
        self.plan = {'document': {'name':'test'}, 'operations': []}

    def create(self, task='first', **changes):
        args = dict(plan=self.plan, output=str(self.root/task), runtime_sha='a'*64,
                    inputs={}, source=None, mode='workflow', authorization={'writeRoot':str(self.root)})
        args.update(changes)
        return self.store.create(task, **args)

    def test_creation_roundtrips_and_preserves_deadline(self):
        first = self.create()
        another = self.module.Store(self.root/'state').read('first')
        self.assertEqual(first, another)
        self.assertEqual(first['budget']['maxRevisions'], 2)
        self.assertAlmostEqual(first['deadline']-first['createdAt'], 1800, places=3)

    def test_durable_ancestor_cancel_blocks_descendant_after_restart(self):
        self.create();self.store.start('first');self.store.delivered('first',{})
        self.create('child',plan={'child':True},parent='first');self.store.start('child')
        self.store.delivered('child',{})
        self.create('grandchild',plan={'grandchild':True},parent='child')
        root=self.store.read('first');root['state']='reconciling';root['cancellationRequestedAt']=1
        self.store.save(root)
        restored=self.module.Store(self.root/'state')
        with self.assertRaisesRegex(ValueError,'parent_cancelled_or_expired'):
            restored.start('grandchild')
        with self.assertRaisesRegex(ValueError,'parent_cancelled_or_expired'):
            self.create('another',plan={'another':True},parent='child')
        self.assertFalse(restored.path('another').exists())

    def test_shortened_ancestor_deadline_blocks_grandchild(self):
        self.create();self.store.start('first');self.store.delivered('first',{})
        self.create('child',plan={'child':True},parent='first');self.store.start('child');self.store.delivered('child',{})
        self.create('grandchild',plan={'grandchild':True},parent='child')
        root=self.store.read('first');root['deadline']=root['createdAt']-1;self.store.save(root)
        with self.assertRaisesRegex(ValueError,'parent_cancelled_or_expired'):
            self.store.start('grandchild')

    def test_parent_cycle_fails_closed_without_recursive_overflow(self):
        self.create();self.store.start('first');self.store.delivered('first',{})
        self.create('child',plan={'child':True},parent='first')
        root=self.store.read('first');root['parent']='child';self.store.save(root)
        with self.assertRaisesRegex(ValueError,'task_ancestry_cycle'):
            self.store.allowed(self.store.read('child'))

    def test_corruption_is_preserved_and_not_reinitialized(self):
        self.create(); path=self.root/'state/tasks/first/state.json'; path.write_text('{broken')
        with self.assertRaisesRegex(ValueError, 'state_invalid'):
            self.store.read('first')
        with self.assertRaises(ValueError): self.create()
        self.assertEqual(path.read_text(), '{broken')

    def test_unknown_cannot_be_replayed_under_new_task_or_output(self):
        self.create(); self.store.start('first')
        self.store.begin_step('first', 'edit', {'text':'changed'})
        self.store.fail('first', 'response lost', unknown=True)
        with self.assertRaisesRegex(ValueError, 'reconciliation_required'):
            self.create('second')
        with self.assertRaisesRegex(ValueError, 'reconciliation_required'):
            self.store.start('first')

    def test_attempt_identity_survives_restart_and_blocks_duplicate(self):
        self.create(); self.store.start('first')
        op = self.store.begin_step('first', 'edit', {'value':1})
        restored = self.module.Store(self.root/'state')
        self.assertEqual(restored.read('first')['steps'][0]['id'], op)
        with self.assertRaisesRegex(ValueError, 'unresolved_operation'):
            restored.begin_step('first', 'edit', {'value':1})

    def test_same_source_project_is_single_writer_across_plans(self):
        source=self.root/'project.ecproj'; source.write_bytes(b'project')
        self.create(source=str(source)); self.store.start('first')
        with self.assertRaisesRegex(ValueError, 'resource_busy'):
            self.create('second', source=str(source), plan={'operations':[{'different':True}]})

    def test_cancel_request_does_not_claim_running_process_stopped(self):
        self.create(); self.store.start('first')
        self.assertEqual(self.store.cancel('first')['state'], 'cancel_requested')
        with self.assertRaisesRegex(ValueError, 'cancel_requested'):
            self.store.begin_step('first','edit',{})

    def test_plan_tampering_is_rejected(self):
        self.create(); path=self.root/'state/tasks/first/state.json'
        data=json.loads(path.read_text()); data['plan']['operations'].append({'changed':True})
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,'identity_mismatch'): self.store.read('first')

    def test_stale_worker_cannot_write_after_unknown(self):
        self.create(); self.store.start('first'); op=self.store.begin_step('first','edit',{})
        self.store.fail('first','lost',unknown=True)
        with self.assertRaisesRegex(ValueError,'state_conflict'):
            self.store.finish_step('first',op,{'ok':True})

    def test_deadline_checked_before_side_effect(self):
        self.create(seconds=.001)
        import time
        time.sleep(.01)
        with self.assertRaisesRegex(ValueError,'deadline_exceeded'): self.store.start('first')

    def test_runtime_change_cannot_replay_unknown_intent(self):
        self.create(); self.store.start('first'); self.store.fail('first','lost',unknown=True)
        with self.assertRaisesRegex(ValueError,'reconciliation_required'):
            self.create('second',runtime_sha='b'*64)

    def test_cancel_parent_stops_active_revision(self):
        self.create(); self.store.start('first'); self.store.delivered('first',{})
        state=self.store.read('first');state['activeRevision']='child';self.store.save(state)
        self.create('child',plan={'child':True},parent='first');self.store.start('child')
        self.store.cancel('first')
        self.assertEqual(self.store.read('child')['state'],'cancel_requested')

    def test_confirmed_stop_preserves_unknown_effects(self):
        self.create();self.store.start('first');self.store.begin_step('first','edit',{})
        result=self.store.stopped('first','cancelled')
        self.assertEqual(result['state'],'reconciling')
        self.assertEqual(result['termination']['status'],'confirmed')

    def test_confirmed_stop_without_unknown_operations_completes_cancel(self):
        self.create();self.store.start('first')
        self.assertEqual(self.store.stopped('first','cancelled')['state'],'cancelled')

    def test_successful_step_has_durable_result_and_missing_receipt_blocks_resume(self):
        self.create();self.store.start('first');op=self.store.begin_step('first','edit',{})
        state=self.store.finish_step('first',op,{'layer':4})
        path=self.store.path('first').parent/'receipts'/(op+'.json')
        self.assertTrue(path.is_file());self.assertEqual(json.loads(path.read_text())['result'],{'layer':4})
        path.unlink()
        with self.assertRaisesRegex(ValueError,'state_invalid'):self.store.read('first')
