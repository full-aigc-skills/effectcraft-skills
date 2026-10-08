"""多合成帧不能混用；命令Judge与真实持久账本组合。"""
import copy
import json
import unittest
from unittest.mock import patch
import test_managed_command_delivery as fixtures


class CommandJudgeTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.CommandDeliveryTests('runTest');self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.m=self.f.module;self.store=self.f.store;self.output=self.f.output
        self.criteria={'goal':'subject readable in every requested context'}
        self.f.session.comps[1].update(frameRate=1,duration=1)
        self.f.save();self.f.frame();self.f.finish()
        original=self.m.inspect
        def inspected(*args,**kwargs):
            report=original(*args,**kwargs);report['engineering']={'status':'PASS','fresh':True,'projects':[{'path':'scene.ecproj'}]};return report
        self.patch=patch.object(self.m,'inspect',side_effect=inspected);self.patch.start();self.addCleanup(self.patch.stop)
        self.bind_quality()

    def bind_quality(self):
        # Native engineering startup is the only substituted boundary; request,
        # media checks, hashes, task state and settlement use production code.
        loader=self.m.load;ledger=loader('review_ledger');quality=loader('command_judge').Quality(self.store,'case')
        quality.inspect_delivery=lambda root,runtime_home=None:self.m.inspect(self.store,'case',runtime_home)
        for patcher in [patch.object(ledger,'quality_adapter',return_value=quality),
                        patch.object(self.m,'load',side_effect=lambda name:ledger if name=='review_ledger' else loader(name))]:
            patcher.start();self.addCleanup(patcher.stop)

    def request(self):
        result=self.m.review(self.store,'case',self.criteria,runtime_home='prepared')
        self.assertIsNotNone(result['judgeRequest'],'managed commands must produce an actual Judge request after native gates')
        self.assertEqual(result['requiredAction'],'host_visual_review');return result['judgeRequest']

    def response(self,request):
        response={key:request[key] for key in ['requestId','taskId','binding','criteriaHash','scopeHash']}
        response.update(schema='effectcraft-judge-receipt/v2',status='PASS',score=.9,passed=True,issues=[],capabilities={'visual':True,'temporal':True},temporalReviewed=True,
            observations=[{'path':m['path'],'sha256':m['sha256'],'frameIndices':m['frameIndices'],'method':'unit fixture actual PNG read','description':'fixture red subject is legible'} for m in request['scope']['media']])
        return response

    def submit(self,response):
        path=self.f.root/'judge.json';path.write_text(json.dumps(response));return self.m.review(self.store,'case',self.criteria,path,'prepared')

    def test_request_is_stable_and_contains_real_media_digest(self):
        a=self.request();b=self.request();self.assertEqual(a,b)
        self.assertEqual(a['schema'],'effectcraft-judge-request/v2')
        self.assertEqual(a['scope']['media'][0]['path'],'preview.png')
        self.assertEqual(a['scope']['media'][0]['frameIndices'],[0])
        self.assertEqual(len(a['scope']['contexts']),1)
        self.assertEqual(a['scope']['contexts'][0]['frameRange'],{'start':0,'endExclusive':1})
        self.assertFalse(a['temporalRequired']);self.assertFalse((self.output/'manifest.json').exists())

    def test_valid_receipt_settles_once_and_never_signs_user_acceptance(self):
        request=self.request();response=self.response(request);result=self.submit(response)
        self.assertEqual(result['report']['creative']['status'],'PASS')
        self.assertFalse(result['report']['accepted']);self.assertEqual(result['report']['userAcceptance']['status'],'NOT_RUN')
        state=self.store.read('case');self.assertEqual(state['qualityReviews']['order'],['case']);self.assertEqual(state['bestScore'],.9)
        before=self.store.path('case').read_bytes();self.submit(response);self.assertEqual(before,self.store.path('case').read_bytes())

    def test_conflicting_receipt_preserves_first_settlement(self):
        request=self.request();response=self.response(request);self.submit(response);before=self.store.path('case').read_bytes()
        response['score']=.95
        with self.assertRaisesRegex(ValueError,'judge_response_conflict'):self.submit(response)
        self.assertEqual(before,self.store.path('case').read_bytes())

    def test_changed_criteria_cannot_reset_request(self):
        self.request();self.criteria={'goal':'different goal'}
        with self.assertRaisesRegex(ValueError,'criteria_changed'):self.m.review(self.store,'case',self.criteria,runtime_home='prepared')

    def test_missing_visual_is_retained_without_settlement(self):
        response=self.response(self.request());response['capabilities']['visual']=False;result=self.submit(response)
        self.assertEqual(result['report']['creative']['status'],'NOT_RUN')
        state=self.store.read('case');self.assertEqual(state['qualityReviews']['entries'],{});self.assertNotIn('bestTask',state)
        self.assertTrue(state['reviewAttempt'])

    def test_changed_artifact_cannot_reuse_historical_creative_pass(self):
        response=self.response(self.request());self.submit(response);before=self.store.path('case').read_bytes()
        (self.output/'preview.png').write_bytes(b'broken')
        with self.assertRaisesRegex(ValueError,'artifact_changed|command_') as error:
            self.m.review(self.store,'case',self.criteria,runtime_home='prepared')
        report=error.exception.review_report
        self.assertEqual(report['technical']['status'],'FAIL');self.assertEqual(report['creative']['status'],'NOT_RUN')
        self.assertEqual(before,self.store.path('case').read_bytes())

    def test_no_engineering_proof_means_no_judge_request(self):
        self.patch.stop()
        result=self.m.review(self.store,'case',self.criteria,runtime_home=None)
        self.assertIsNone(result['judgeRequest']);self.assertEqual(result['requiredAction'],'engineering_verification')

    def test_tampered_scope_is_rejected_without_new_request(self):
        self.request();path=self.store.path('case').parent/'judge-request.json';data=json.loads(path.read_text());data['scope']['coverage']='all';path.write_text(json.dumps(data))
        before=path.read_bytes()
        with self.assertRaisesRegex(ValueError,'judge_request_changed'):self.m.review(self.store,'case',self.criteria,runtime_home='prepared')
        self.assertEqual(before,path.read_bytes())

    def make_two_contexts(self):
        # Separate task fixture avoids altering an already finalized delivery baseline.
        self.patch.stop()
        # Recreate current task before delivery using a fresh fixture; no recovery/replay under test.
        fresh=fixtures.CommandDeliveryTests('runTest');fresh.setUp();self.addCleanup(fresh.doCleanups)
        self.f=fresh;self.m=fresh.module;self.store=fresh.store;self.output=fresh.output
        fresh.session.comps[1].update(frameRate=2,duration=1)
        fresh.session.comps[2]=dict(fresh.session.comps[1],id=2,name='B',layers=[])
        fresh.save()
        for comp in [1,2]:
            for index,seconds in enumerate([0,.5]):
                record={'index':len(fresh.steps),'tool':'render_frame','command':None,'params':{'path':str(self.output/f'{comp}-{index}.png'),'comp':comp,'time':seconds,'max_side':0,'transparent':True,'inline':False},'state':'started'}
                fresh.observer(fresh.session,record,'before');(self.output/f'{comp}-{index}.png').write_bytes(fixtures.png())
                record.update(state='succeeded',result={});fresh.observer(fresh.session,record,'after');fresh.steps.append(record)
        fresh.finish();original=self.m.inspect
        def inspected(*args,**kwargs):
            report=original(*args,**kwargs);report['engineering']={'status':'PASS','fresh':True,'projects':[{'path':'scene.ecproj'}]};return report
        patcher=patch.object(self.m,'inspect',side_effect=inspected);patcher.start();self.addCleanup(patcher.stop)
        self.bind_quality()

    def test_observations_from_one_composition_cannot_cover_another(self):
        self.make_two_contexts();request=self.request();self.assertEqual(len(request['scope']['contexts']),2)
        response=self.response(request);response['observations']=[r for r in response['observations'] if r['path'].startswith('1-')]
        result=self.submit(response);self.assertEqual(result['report']['creative']['status'],'NOT_RUN')
        self.assertEqual(self.store.read('case')['qualityReviews']['entries'],{})

    def test_all_contexts_with_actual_media_can_settle(self):
        self.make_two_contexts();request=self.request();result=self.submit(self.response(request))
        self.assertTrue(request['temporalRequired']);self.assertEqual(result['report']['creative']['status'],'PASS')
        self.assertEqual(len(result['report']['creative']['scope']['contexts']),2)
