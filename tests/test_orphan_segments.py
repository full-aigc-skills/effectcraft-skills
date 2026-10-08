"""自有未发布分段保全与移动结果核对；未知文件不得自动归档。"""
import unittest
from unittest.mock import patch
import test_managed_render_resume


class OrphanSegmentTests(unittest.TestCase):
    setUp=test_managed_render_resume.RenderResumeTests.setUp
    checkpoint=test_managed_render_resume.RenderResumeTests.checkpoint

    def prepare(self):
        self.checkpoint()
        self.store.reserve_resources('task',{'frames':4,'decodedBytes':32},'a'*64)
        source=self.output/'.effect-segment-orphan';source.mkdir()
        self.managed.load('resource_meter').watch(self.store,'task',source,
            self.output/'rgba-segments/segment_00000','segment')
        (source/'frame_00000.png').write_bytes(b'actual native bytes')
        return source

    def test_reconcile_keeps_orphan_then_resume_archives_without_edit_replay(self):
        source=self.prepare();before=source.stat();original=self.store.read('task')
        result=self.managed.reconcile(self.store,'task')
        self.assertEqual(result['reconciliation']['result'],'render_resume_ready')
        self.assertTrue(source.exists())
        helper=self.managed.load('orphan_segments');helper.archive_pending(self.store,'task')
        state=self.store.read('task');row=state['orphanArchives']['entries'][0]
        destination=self.output.__class__(row['destination'])
        self.assertEqual(row['phase'],'archived');self.assertFalse(source.exists())
        self.assertEqual(destination.stat().st_ino,before.st_ino)
        self.assertEqual((destination/'frame_00000.png').read_bytes(),b'actual native bytes')
        self.assertFalse(destination.is_relative_to(self.output))
        self.assertEqual(state['steps'],original['steps']);self.assertEqual(state['deadline'],original['deadline'])
        self.managed.load('resource_meter').sample(self.store,'task')
        self.assertEqual(self.store.read('task')['resources']['entries']['task']['encodedBytes'],19)

    def test_unexpected_file_is_preserved_and_refused(self):
        source=self.prepare();personal=source/'personal.txt';personal.write_text('keep')
        with self.assertRaisesRegex(ValueError,'orphan_segment_unowned_file'):
            self.managed.reconcile(self.store,'task')
        self.assertEqual(personal.read_text(),'keep')
        self.assertNotIn('orphanArchives',self.store.read('task'))

    def test_move_failure_leaves_prepared_journal_and_original_bytes(self):
        source=self.prepare();helper=self.managed.load('orphan_segments')
        with patch.object(helper,'move',side_effect=OSError('same device move refused')):
            with self.assertRaisesRegex(OSError,'move refused'):helper.archive_pending(self.store,'task')
        self.assertTrue(source.exists());self.assertEqual(self.store.read('task')['orphanArchives']['entries'][0]['phase'],'prepared')
        self.managed.reconcile(self.store,'task')
        self.assertTrue(source.exists(),'reconcile must not start a filesystem move')
        helper.archive_pending(self.store,'task')
        self.assertFalse(source.exists())

    def test_crash_after_move_is_settled_without_repeating_move(self):
        source=self.prepare();helper=self.managed.load('orphan_segments');native=helper.move
        def interrupted(*args):native(*args);raise RuntimeError('after move crash')
        with patch.object(helper,'move',side_effect=interrupted):
            with self.assertRaisesRegex(RuntimeError,'after move'):helper.archive_pending(self.store,'task')
        self.assertFalse(source.exists())
        self.assertEqual(self.store.read('task')['orphanArchives']['entries'][0]['phase'],'prepared')
        result=self.managed.reconcile(self.store,'task')
        self.assertEqual(result['orphanArchives']['entries'][0]['phase'],'archived')
        self.assertEqual(result['reconciliation']['result'],'render_resume_ready')

    def test_archive_tampering_blocks_recovery(self):
        source=self.prepare();helper=self.managed.load('orphan_segments');helper.archive_pending(self.store,'task')
        state=self.store.read('task');destination=self.output.__class__(state['orphanArchives']['entries'][0]['destination'])
        (destination/'frame_00000.png').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'orphan_segment_changed'):
            self.managed.reconcile(self.store,'task')

    def test_missing_archive_cannot_be_ignored_as_retired(self):
        import shutil
        self.prepare();helper=self.managed.load('orphan_segments');helper.archive_pending(self.store,'task')
        state=self.store.read('task');destination=self.output.__class__(state['orphanArchives']['entries'][0]['destination'])
        shutil.rmtree(destination)
        with self.assertRaisesRegex(ValueError,'orphan_segment_missing'):
            self.managed.reconcile(self.store,'task')

    def test_prepared_source_changes_are_preserved_and_refused(self):
        source=self.prepare();helper=self.managed.load('orphan_segments')
        with patch.object(helper,'move',side_effect=OSError('move refused')):
            with self.assertRaises(OSError):helper.archive_pending(self.store,'task')
        (source/'frame_00000.png').write_bytes(b'changed after preparation')
        with self.assertRaisesRegex(ValueError,'orphan_segment_changed'):
            self.managed.reconcile(self.store,'task')
        self.assertEqual((source/'frame_00000.png').read_bytes(),b'changed after preparation')

    def test_private_target_with_unknown_content_is_not_overwritten(self):
        self.prepare();helper=self.managed.load('orphan_segments')
        with patch.object(helper,'move',side_effect=OSError('move refused')):
            with self.assertRaises(OSError):helper.archive_pending(self.store,'task')
        row=self.store.read('task')['orphanArchives']['entries'][0]
        personal=self.output.__class__(row['container'])/'personal.txt';personal.write_text('keep')
        with self.assertRaisesRegex(ValueError,'orphan_archive_container_changed'):
            helper.archive_pending(self.store,'task')
        self.assertEqual(personal.read_text(),'keep')

    def test_corrupt_journal_remains_diagnostic(self):
        self.prepare();state=self.store.read('task');state['orphanArchives']={'schema':'bad'};self.store.save(state)
        before=self.store.path('task').read_bytes()
        with self.assertRaisesRegex(ValueError,'state_invalid'):self.store.read('task')
        self.assertEqual(before,self.store.path('task').read_bytes())
