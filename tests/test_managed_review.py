"""实际文件验证及过期评估拒绝；评分不能覆盖技术失败。"""
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

SCRIPT=Path(__file__).resolve().parents[1]/'skills/effectcraft-use/scripts/quality_review.py'


class ManagedReviewTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SCRIPT.exists(), 'artifact-bound quality review is missing')
        spec=importlib.util.spec_from_file_location('quality_test',SCRIPT)
        self.module=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.module)
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data))
        png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',1,1,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(b'\x00\xff\x00\x00\x00'))+chunk(b'IEND',b'')
        (self.root/'frame.png').write_bytes(png);(self.root/'project.ecproj').write_bytes(b'fixture-project')
        self.manifest={'schema':'effectcraft-delivery/v1','files':{n:hashlib.sha256((self.root/n).read_bytes()).hexdigest() for n in ['frame.png','project.ecproj']},'frames':[{'path':'frame.png','requestedAlpha':True}], 'video':None,'imageSequence':None}
        (self.root/'manifest.json').write_text(json.dumps(self.manifest))

    def test_png_is_decoded_and_engine_reopen_is_not_inferred(self):
        result=self.module.inspect_delivery(self.root)
        self.assertEqual(result['technical']['status'],'PASS')
        self.assertEqual(result['engineering']['status'],'NOT_RUN')
        self.assertEqual(result['creative']['status'],'NOT_RUN')

    def test_corrupt_media_with_matching_manifest_still_fails(self):
        (self.root/'frame.png').write_bytes(b'not a png')
        self.manifest['files']['frame.png']=hashlib.sha256(b'not a png').hexdigest()
        (self.root/'manifest.json').write_text(json.dumps(self.manifest))
        self.assertEqual(self.module.inspect_delivery(self.root)['technical']['status'],'FAIL')

    def test_preview_dimensions_must_match_native_composition(self):
        (self.root/'native.json').write_text(json.dumps({'composition':{'width':2,'height':2}}))
        report=self.module.inspect_delivery(self.root)
        self.assertEqual(report['technical']['status'],'FAIL')
        self.assertIn('preview_dimensions_mismatch',report['technical']['reason'])

    def test_judge_cannot_override_failed_technical_evidence(self):
        report=self.module.inspect_delivery(self.root)
        request=self.module.judge_request('task',self.root,report,{'goal':'red'},False)
        response=dict(requestId=request['requestId'],binding=request['binding'],score=1.0,passed=True,issues=[],temporalReviewed=False)
        report['technical']['status']='FAIL'
        with self.assertRaisesRegex(ValueError,'technical_gate'):
            self.module.accept_judge(self.root,report,request,response)

    def test_old_judge_receipt_is_rejected_after_artifact_changes(self):
        report=self.module.inspect_delivery(self.root)
        request=self.module.judge_request('task',self.root,report,{'goal':'red'},False)
        response=dict(requestId=request['requestId'],binding=request['binding'],score=.5,passed=False,issues=[{'description':'contrast'}],temporalReviewed=False)
        (self.root/'project.ecproj').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'artifact_changed'):
            self.module.accept_judge(self.root,report,request,response)

    def test_temporal_review_is_required_for_animation(self):
        report=self.module.inspect_delivery(self.root)
        request=self.module.judge_request('task',self.root,report,{'goal':'motion'},True)
        response=dict(requestId=request['requestId'],binding=request['binding'],score=1.0,passed=True,issues=[],temporalReviewed=False)
        with self.assertRaisesRegex(ValueError,'temporal_evidence_required'):
            self.module.accept_judge(self.root,report,request,response)

    def test_delivery_path_cannot_escape_root(self):
        self.manifest['files']['../outside']='a'*64
        (self.root/'manifest.json').write_text(json.dumps(self.manifest))
        self.assertEqual(self.module.inspect_delivery(self.root)['technical']['status'],'FAIL')

    def test_segmented_dimensions_are_read_from_checkpoint_binding(self):
        directory=self.root/'sequence';directory.mkdir()
        (directory/'frame.png').write_bytes((self.root/'frame.png').read_bytes())
        descriptor={'schema':'craft-segmented-render-checkpoint/v1','frameCount':1,
                    'binding':{'composition':{'width':1,'height':1}}}
        (directory/'segments.json').write_text(json.dumps(descriptor))
        self.manifest['imageSequence']={'path':'sequence/segments.json'};self.manifest['frames']=[]
        for p in directory.iterdir():self.manifest['files'][p.relative_to(self.root).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
        (self.root/'manifest.json').write_text(json.dumps(self.manifest))
        self.assertEqual(self.module.inspect_delivery(self.root)['technical']['status'],'PASS')
