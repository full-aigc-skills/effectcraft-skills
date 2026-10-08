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
        request=self.module.judge_request('task',self.root,report,{'goal':'red'},False,version=1)
        response=dict(requestId=request['requestId'],binding=request['binding'],score=1.0,passed=True,issues=[],temporalReviewed=False)
        report['technical']['status']='FAIL'
        with self.assertRaisesRegex(ValueError,'technical_gate'):
            self.module.accept_judge(self.root,report,request,response)

    def test_old_judge_receipt_is_rejected_after_artifact_changes(self):
        report=self.module.inspect_delivery(self.root)
        request=self.module.judge_request('task',self.root,report,{'goal':'red'},False,version=1)
        response=dict(requestId=request['requestId'],binding=request['binding'],score=.5,passed=False,issues=[{'description':'contrast'}],temporalReviewed=False)
        (self.root/'project.ecproj').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'artifact_changed'):
            self.module.accept_judge(self.root,report,request,response)

    def test_temporal_review_is_required_for_animation(self):
        report=self.module.inspect_delivery(self.root)
        request=self.module.judge_request('task',self.root,report,{'goal':'motion'},True,version=1)
        response=dict(requestId=request['requestId'],binding=request['binding'],score=1.0,passed=True,issues=[],temporalReviewed=False)
        with self.assertRaisesRegex(ValueError,'temporal_evidence_required'):
            self.module.accept_judge(self.root,report,request,response)

    def test_delivery_path_cannot_escape_root(self):
        self.manifest['files']['../outside']='a'*64
        (self.root/'manifest.json').write_text(json.dumps(self.manifest))
        self.assertEqual(self.module.inspect_delivery(self.root)['technical']['status'],'FAIL')

    def sequence_fixture(self, segmented=False):
        directory=self.root/'sequence';directory.mkdir()
        (directory/'frame_00000.png').write_bytes((self.root/'frame.png').read_bytes())
        composition={'name':'review','width':1,'height':1,'frameRate':2,'duration':.5}
        descriptor=self.module.load('image_sequence').inspect_sequence(directory,composition)
        (directory/'sequence.json').write_text(json.dumps(descriptor),encoding='utf-8')
        if segmented:
            part=self.module.load('segmented_sequence').plan_segments(composition,4)[0]
            child=directory/'segment_00000';child.mkdir()
            for path in list(directory.iterdir()):
                if path.is_file():path.rename(child/path.name)
            descriptor={'schema':'craft-segmented-render-checkpoint/v1','state':'verified',
                'binding':{'composition':composition,'chunkBytes':4,'parts':[part],
                    'projectSha256':self.manifest['files']['project.ecproj'],'runtimeSha256':'a'*64},
                'frameCount':1,'frameRate':{'num':2,'den':1},
                'segments':[dict(part,location='segment_00000/sequence.json',sha256=self.module.sha(child/'sequence.json'))]}
            path=directory/'segments.json'
        else:path=directory/'sequence.json'
        path.write_text(json.dumps(descriptor),encoding='utf-8')
        (self.root/'native.json').write_text(json.dumps({'composition':composition}),encoding='utf-8')
        self.manifest['imageSequence']={'path':path.relative_to(self.root).as_posix(),'sha256':self.module.sha(path)}
        self.manifest['frames']=[]
        self.refresh_manifest()
        return path,descriptor

    def refresh_manifest(self):
        sequence=self.manifest.get('imageSequence')
        if sequence:sequence['sha256']=self.module.sha(self.root/sequence['path'])
        self.manifest['files']={p.relative_to(self.root).as_posix():self.module.sha(p)
            for p in self.root.rglob('*') if p.is_file() and p.name!='manifest.json'}
        (self.root/'manifest.json').write_text(json.dumps(self.manifest),encoding='utf-8')

    def test_actual_sequence_and_segment_contracts_pass(self):
        self.sequence_fixture()
        self.assertEqual(self.module.inspect_delivery(self.root)['technical']['status'],'PASS')

    def test_actual_segment_contract_passes(self):
        self.sequence_fixture(True)
        self.assertEqual(self.module.inspect_delivery(self.root)['technical']['status'],'PASS')

    def test_sequence_descriptor_drift_fails_even_when_package_hashes_match(self):
        path,data=self.sequence_fixture()
        for field,value in [('frameRate',{'num':3,'den':1}),('timeBase',{'num':1,'den':3}),
                            ('frames',[dict(data['frames'][0],index=1)]),
                            ('frames',[dict(data['frames'][0],sha256='f'*64)]),
                            ('frames',[dict(data['frames'][0],alphaExtrema=[255,255])])]:
            with self.subTest(field=field,value=value):
                changed=dict(data);changed[field]=value
                path.write_text(json.dumps(changed),encoding='utf-8');self.refresh_manifest()
                self.assertEqual(self.module.inspect_delivery(self.root)['technical']['status'],'FAIL')

    def test_same_count_renamed_frame_is_not_complete_sequence(self):
        self.sequence_fixture()
        (self.root/'sequence/frame_00000.png').rename(self.root/'sequence/frame_00009.png')
        self.refresh_manifest()
        self.assertEqual(self.module.inspect_delivery(self.root)['technical']['status'],'FAIL')

    def test_segment_binding_range_and_receipts_must_match(self):
        path,data=self.sequence_fixture(True)
        import copy
        mutations=[]
        changed=copy.deepcopy(data);changed['segments'][0]['firstFrame']=1;mutations.append(changed)
        changed=copy.deepcopy(data);changed['segments'][0]['sha256']='f'*64;mutations.append(changed)
        changed=copy.deepcopy(data);changed['binding']['projectSha256']='f'*64;mutations.append(changed)
        changed=copy.deepcopy(data);changed['frameRate']={'num':3,'den':1};mutations.append(changed)
        for changed in mutations:
            with self.subTest(data=changed):
                path.write_text(json.dumps(changed),encoding='utf-8');self.refresh_manifest()
                self.assertEqual(self.module.inspect_delivery(self.root)['technical']['status'],'FAIL')

    def test_missing_sequence_contract_is_not_accepted(self):
        path,data=self.sequence_fixture(True)
        path.write_text(json.dumps({'schema':data['schema'],'frameCount':1,
            'binding':{'composition':{'width':1,'height':1}}}),encoding='utf-8')
        self.refresh_manifest()
        self.assertEqual(self.module.inspect_delivery(self.root)['technical']['status'],'FAIL')
