"""分段重试计入持久父子预算；完整段复用不进入原生尝试入口。"""
import unittest
import test_managed_tasks


class SegmentAttemptBudgetTests(unittest.TestCase):
    setUp=test_managed_tasks.ManagedTaskTests.setUp
    create=test_managed_tasks.ManagedTaskTests.create

    def prepare(self, frames=12):
        self.create();self.store.start('first')
        self.store.reserve_resources('first',{'frames':frames,'decodedBytes':frames*4},'a'*64)
        return self.module.load('resource_budget')

    def test_first_attempt_is_covered_retry_and_restart_are_counted(self):
        budget=self.prepare()
        budget.reserve_segment(self.store,'first','segment_00000','b'*64,4,16)
        budget.reserve_segment(self.store,'first','segment_00000','b'*64,4,16)
        self.assertEqual(budget.usage(self.store.read('first')['resources'])['frames'],12)
        restored=self.module.Store(self.root/'state')
        budget.reserve_segment(restored,'first','segment_00000','c'*64,4,16)
        ledger=restored.read('first')['resources']
        self.assertEqual(budget.usage(ledger),{'frames':16,'decodedBytes':64,'encodedBytes':0})
        self.assertEqual(len(ledger['entries']['first']['segmentAttempts']['segment_00000']),2)
        restored.reserve_resources('first',{'frames':12,'decodedBytes':48},'a'*64)

    def test_retry_overflow_is_durable_and_blocks_next_call(self):
        budget=self.prepare(10000)
        budget.reserve_segment(self.store,'first','segment_00000','b'*64,4,16)
        with self.assertRaisesRegex(ValueError,'resource_budget_exceeded'):
            budget.reserve_segment(self.store,'first','segment_00000','c'*64,4,16)
        state=self.module.Store(self.root/'state').read('first')
        self.assertEqual(budget.usage(state['resources'])['frames'],10004)
        with self.assertRaisesRegex(ValueError,'resource_budget_exceeded'):self.store.allowed(state)

    def test_attempt_conflict_and_duplicate_identity_across_segments_rejected(self):
        budget=self.prepare()
        budget.reserve_segment(self.store,'first','segment_00000','b'*64,4,16)
        for segment,frames in [('segment_00000',5),('segment_00001',4)]:
            with self.assertRaisesRegex(ValueError,'resource_attempt_conflict'):
                budget.reserve_segment(self.store,'first',segment,'b'*64,frames,frames*4)

    def test_first_segment_reservations_cannot_exceed_original_plan(self):
        budget=self.prepare(4)
        budget.reserve_segment(self.store,'first','segment_00000','b'*64,4,16)
        with self.assertRaisesRegex(ValueError,'resource_attempt_coverage_invalid'):
            budget.reserve_segment(self.store,'first','segment_00001','c'*64,4,16)

    def test_child_retry_uses_root_limit(self):
        budget=self.prepare(9996);self.store.delivered('first',{})
        self.create('child',plan={'child':True},parent='first');self.store.start('child')
        self.store.reserve_resources('child',{'frames':4,'decodedBytes':16},'d'*64)
        budget.reserve_segment(self.store,'child','segment_00000','b'*64,4,16)
        with self.assertRaisesRegex(ValueError,'resource_budget_exceeded'):
            budget.reserve_segment(self.store,'child','segment_00000','c'*64,4,16)
        self.assertEqual(budget.usage(self.store.read('first')['resources'])['frames'],10004)

    def test_corrupt_attempt_ledger_is_preserved(self):
        self.prepare();state=self.store.read('first')
        state['resources']['entries']['first']['segmentAttempts']={'segment_00000':[{'attemptId':'x','frames':True,'decodedBytes':4}]}
        self.store.save(state);before=self.store.path('first').read_bytes()
        with self.assertRaisesRegex(ValueError,'state_invalid'):self.store.read('first')
        self.assertEqual(before,self.store.path('first').read_bytes())

    def test_managed_segment_hook_blocks_native_retry_when_family_is_full(self):
        from unittest.mock import patch
        budget=self.prepare(10000)
        managed=self.module.load('managed');producer=managed.load('segmented_sequence')
        hooks=managed.Hooks(self.store,'first')
        output=self.root.resolve()/'first';output.mkdir()
        project=output/'project.ecproj';project.write_bytes(b'project')
        cli=self.root.resolve()/'cli';cli.write_bytes(b'native')
        composition={'name':'Test','width':2,'height':1,'frameRate':2,'duration':1}
        calls=[]
        def failed_native(*args):
            calls.append('attempted');raise RuntimeError('native_interrupted')
        with patch.object(producer,'render_segment',failed_native):
            with self.assertRaisesRegex(RuntimeError,'native_interrupted'):
                producer.render_segments(cli,project,composition,output/'rgba-segments',
                    before_native=hooks.watch_segment,after_native=hooks.finish_segment)
            with self.assertRaisesRegex(ValueError,'resource_budget_exceeded'):
                producer.render_segments(cli,project,composition,output/'rgba-segments',
                    before_native=hooks.watch_segment,after_native=hooks.finish_segment)
        self.assertEqual(calls,['attempted'])
        self.assertEqual(budget.usage(self.store.read('first')['resources'])['frames'],10002)
