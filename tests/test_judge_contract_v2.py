"""Judge v2显式身份/范围与真实媒体观察证据合同；夹具不冒充宿主验收。"""
import copy
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

SCRIPT=Path(__file__).resolve().parents[1]/'skills/effectcraft-use/scripts/quality_review.py'

class JudgeV2Tests(unittest.TestCase):
    def setUp(self):
        spec=importlib.util.spec_from_file_location('judge_v2_quality',SCRIPT)
        self.quality=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.quality)
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        tasks=self.quality.load('task_store')
        def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data))
        png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',1,1,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(b'\x00\xff\x00\x00\x80'))+chunk(b'IEND',b'')
        (self.root/'project.ecproj').write_bytes(b'project')
        tasks.atomic_json(self.root/'native.json',{'composition':{'width':1,'height':1,'frameRate':4,'duration':1}})
        frames=[]
        for index in range(4):
            path=self.root/f'frame-{index}.png';path.write_bytes(png)
            frames.append({'path':path.name,'seconds':index/4,'requestedAlpha':True})
        tasks.atomic_json(self.root/'manifest.json',{'files':{p.name:tasks.file_sha(p) for p in self.root.iterdir()},'frames':frames})
        self.report=self.quality.inspect_delivery(self.root)
        self.report['engineering']={'status':'PASS'}

    def request(self):
        result=self.quality.judge_request('task',self.root,self.report,{'goal':'readable movement'},True)
        self.assertEqual(result['schema'],'effectcraft-judge-request/v2')
        return result

    def response(self,request):
        return {'schema':'effectcraft-judge-receipt/v2','requestId':request['requestId'],'taskId':request['taskId'],
            'binding':request['binding'],'criteriaHash':request['criteriaHash'],'scopeHash':request['scopeHash'],
            'capabilities':{'visual':True,'temporal':True},'score':.8,'passed':True,'issues':[],
            'temporalReviewed':True,'status':'PASS',
            'observations':[{'path':media['path'],'sha256':media['sha256'],'frameIndices':media['frameIndices'],
                'method':'fixture observation','description':'readable title'} for media in request['scope']['media']]}

    def test_request_binds_explicit_rational_frame_and_time_ranges(self):
        request=self.request();scope=request['scope']
        self.assertEqual(scope['frameRange'],{'start':0,'endExclusive':4})
        self.assertEqual(scope['timeRange'],{'start':{'num':0,'den':1},'end':{'num':1,'den':1}})
        self.assertEqual(scope['frameRate'],{'num':4,'den':1})
        self.assertEqual(scope['requiredFrameIndices'],[0,1,2,3])
        self.assertEqual(request['scopeHash'],self.quality.load('task_store').digest(scope))
        self.assertEqual(len(scope['media']),4)

    def test_bound_multiframe_observations_can_pass_without_user_acceptance(self):
        request=self.request();result=self.quality.accept_judge(self.root,self.report,request,self.response(request))
        self.assertEqual(result['creative']['status'],'PASS');self.assertFalse(result['accepted'])
        self.assertEqual(result['creative']['scope'],request['scope'])

    def test_wrong_task_criteria_scope_or_schema_is_rejected(self):
        request=self.request()
        for field,value in [('taskId','another'),('criteriaHash','f'*64),('scopeHash','f'*64),('schema','effectcraft-judge-receipt/v1')]:
            with self.subTest(field=field):
                response=self.response(request);response[field]=value
                with self.assertRaises(ValueError):self.quality.accept_judge(self.root,self.report,request,response)

    def test_missing_visual_or_temporal_capability_is_not_run(self):
        request=self.request()
        for capability in ['visual','temporal']:
            with self.subTest(capability=capability):
                response=self.response(request);response['capabilities'][capability]=False
                result=self.quality.accept_judge(self.root,self.report,request,response)
                self.assertEqual(result['creative']['status'],'NOT_RUN');self.assertFalse(result['readyForAcceptance'])

    def test_boolean_temporal_claim_without_multiframe_observation_is_not_run(self):
        request=self.request();response=self.response(request);response['observations']=response['observations'][:1]
        result=self.quality.accept_judge(self.root,self.report,request,response)
        self.assertEqual(result['creative']['status'],'NOT_RUN')
        self.assertIn('coverage',result['creative']['reason'])

    def test_wrong_media_digest_unlisted_path_and_out_of_range_frame_are_rejected(self):
        request=self.request()
        for changes in [{'sha256':'f'*64},{'path':'../outside.png'},{'frameIndices':[99]},{'frameIndices':[True]},{'frameIndices':[0,0]}]:
            with self.subTest(changes=changes):
                response=self.response(request);response['observations'][0].update(changes)
                with self.assertRaises(ValueError):self.quality.accept_judge(self.root,self.report,request,response)

    def test_request_scope_tampering_is_rejected_before_receipt_acceptance(self):
        request=self.request();request['scope']['requiredFrameIndices']=[0]
        request['scopeHash']=self.quality.load('task_store').digest(request['scope'])
        response=self.response(request)
        with self.assertRaisesRegex(ValueError,'judge_request_changed'):
            self.quality.accept_judge(self.root,self.report,request,response)

    def test_explicit_not_run_does_not_require_or_invent_a_score(self):
        request=self.request();response=self.response(request);response.update(status='NOT_RUN',score=None,passed=False)
        result=self.quality.accept_judge(self.root,self.report,request,response)
        self.assertEqual(result['creative']['status'],'NOT_RUN')
        self.assertNotIn('score',result['creative'])

    def test_passing_receipt_cannot_contain_unresolved_issues(self):
        request=self.request();response=self.response(request);response['issues']=[{'description':'clipped title'}]
        with self.assertRaisesRegex(ValueError,'judge_response_invalid'):
            self.quality.accept_judge(self.root,self.report,request,response)

    def test_changed_project_rejects_v2_receipt(self):
        request=self.request();response=self.response(request)
        (self.root/'project.ecproj').write_bytes(b'changed after request')
        with self.assertRaisesRegex(ValueError,'artifact_changed'):
            self.quality.accept_judge(self.root,self.report,request,response)
