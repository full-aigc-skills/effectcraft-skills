"""分段预算、恢复、输入绑定与坏段拒绝的可观察行为。"""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from test_image_sequence import png

ROOT=Path(__file__).resolve().parents[1]
class SegmentTests(unittest.TestCase):
    def module(self):
        spec=importlib.util.spec_from_file_location('segments',ROOT/'skills/effectcraft-use/scripts/segmented_sequence.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

    def test_hd_and_fractional_ranges_have_no_gap(self):
        m=self.module();parts=m.plan_segments({'width':1920,'height':1080,'frameRate':'30000/1001','duration':5})
        self.assertEqual([p['frameCount'] for p in parts],[64,64,22])
        self.assertEqual([p['firstFrame'] for p in parts],[0,64,128])
        self.assertEqual(parts[1]['start'],{'num':4004,'den':1875})

    def test_single_frame_over_budget_rejects_before_files(self):
        m=self.module()
        with self.assertRaisesRegex(ValueError,'segment_single_frame_budget'):
            m.plan_segments({'width':16384,'height':16384,'frameRate':12,'duration':1})

    def test_resume_rechecks_frames_and_only_rebuilds_corrupt_segment(self):
        m=self.module();calls=[]
        def native(cli,project,comp,directory,part):
            calls.append(part['firstFrame'])
            for index in range(part['frameCount']):png(directory/f'frame_{index:05d}.png')
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve();project=root/'source.ecproj';project.write_bytes(b'project');cli=root/'cli';cli.write_bytes(b'native')
            comp={'name':'Intro','width':2,'height':1,'frameRate':4,'duration':1.25};out=root/'render'
            with patch.object(m,'render_segment',native):
                result=m.render_segments(cli,project,comp,out,chunk_bytes=16)
                self.assertEqual(calls,[0,2,4]);self.assertEqual(result['frameCount'],5)
                m.render_segments(cli,project,comp,out,chunk_bytes=16);self.assertEqual(calls,[0,2,4])
                (out/'segment_00001/frame_00000.png').write_bytes(b'corrupt')
                m.render_segments(cli,project,comp,out,chunk_bytes=16);self.assertEqual(calls,[0,2,4,2])
                project.write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError,'segment_binding_conflict'):m.render_segments(cli,project,comp,out,chunk_bytes=16)
                self.assertEqual(calls,[0,2,4,2])

    def test_failure_preserves_completed_segment_and_recovers(self):
        m=self.module();calls=[]
        def native(cli,project,comp,directory,part):
            calls.append(part['firstFrame'])
            if part['firstFrame']==2 and calls.count(2)==1:raise ValueError('sequence_render_failed')
            for index in range(part['frameCount']):png(directory/f'frame_{index:05d}.png')
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve();project=root/'source.ecproj';project.write_bytes(b'project');cli=root/'cli';cli.write_bytes(b'native')
            comp={'name':'Intro','width':2,'height':1,'frameRate':4,'duration':1};out=root/'render'
            with patch.object(m,'render_segment',native):
                with self.assertRaisesRegex(ValueError,'sequence_render_failed'):m.render_segments(cli,project,comp,out,chunk_bytes=16)
                self.assertTrue((out/'segment_00000/sequence.json').is_file());self.assertFalse((out/'segments.json').exists())
                m.render_segments(cli,project,comp,out,chunk_bytes=16);self.assertEqual(calls,[0,2,2])

    def test_unowned_output_and_symlink_refused(self):
        m=self.module()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve();project=root/'source.ecproj';project.write_bytes(b'project');cli=root/'cli';cli.write_bytes(b'native')
            comp={'name':'Intro','width':2,'height':1,'frameRate':4,'duration':1};out=root/'render';out.mkdir();(out/'personal.txt').write_text('keep')
            with self.assertRaisesRegex(ValueError,'segment_output_unowned'):m.render_segments(cli,project,comp,out)
            self.assertEqual((out/'personal.txt').read_text(),'keep')
            link=root/'link';link.symlink_to(out,target_is_directory=True)
            with self.assertRaisesRegex(ValueError,'segment_symlink'):m.render_segments(cli,project,comp,link)

    def test_changed_receipt_and_frame_cannot_be_accepted_as_reuse(self):
        import json
        m=self.module();calls=[]
        def native(cli,project,comp,directory,part):
            calls.append(part['firstFrame'])
            for index in range(part['frameCount']):png(directory/f'frame_{index:05d}.png')
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve();project=root/'source.ecproj';project.write_bytes(b'project');cli=root/'cli';cli.write_bytes(b'native')
            comp={'name':'Intro','width':2,'height':1,'frameRate':2,'duration':1};out=root/'render'
            with patch.object(m,'render_segment',native):
                m.render_segments(cli,project,comp,out)
                directory=out/'segment_00000';png(directory/'frame_00000.png',alpha=64)
                sequence=m.module('image_sequence')
                with tempfile.TemporaryDirectory() as check:
                    copy=Path(check)
                    for frame in directory.glob('frame_*.png'):
                        import shutil
                        shutil.copyfile(frame,copy/frame.name)
                    (directory/'sequence.json').write_text(json.dumps(sequence.inspect_sequence(copy,comp)))
                m.render_segments(cli,project,comp,out);self.assertEqual(calls,[0,0])

    def test_concurrent_owner_is_not_preempted(self):
        m=self.module()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve();project=root/'source.ecproj';project.write_bytes(b'project');cli=root/'cli';cli.write_bytes(b'native');out=root/'render';out.mkdir()
            comp={'name':'Intro','width':2,'height':1,'frameRate':2,'duration':1}
            parts=m.plan_segments(comp);m.atomic_json(out/'checkpoint.json',{'projectSha256':m.sha(project),'runtimeSha256':m.sha(cli),'composition':comp,'chunkBytes':m.CHUNK_BYTES,'parts':parts})
            with m.output_lock(out):
                with self.assertRaisesRegex(ValueError,'segment_render_busy'):m.render_segments(cli,project,comp,out)

    def test_personal_file_inside_owned_segment_is_not_deleted(self):
        m=self.module()
        def native(cli,project,comp,directory,part):
            for index in range(part['frameCount']):png(directory/f'frame_{index:05d}.png')
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve();project=root/'source.ecproj';project.write_bytes(b'project');cli=root/'cli';cli.write_bytes(b'native')
            comp={'name':'Intro','width':2,'height':1,'frameRate':2,'duration':1};out=root/'render'
            with patch.object(m,'render_segment',native):m.render_segments(cli,project,comp,out)
            personal=out/'segment_00000/personal.txt';personal.write_text('keep')
            with self.assertRaisesRegex(ValueError,'segment_output_unowned'):m.render_segments(cli,project,comp,out)
            self.assertEqual(personal.read_text(),'keep')
