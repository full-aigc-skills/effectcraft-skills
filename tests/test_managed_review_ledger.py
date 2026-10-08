"""公开review的持久评价、幂等预算及最佳版本回执。"""
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

SCRIPT=Path(__file__).resolve().parents[1]/'skills/effectcraft-use/scripts/managed.py'

class ReviewLedgerTests(unittest.TestCase):
    def setUp(self):
        spec=importlib.util.spec_from_file_location('ledger_managed',SCRIPT)
        self.managed=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.managed)
        self.tasks=self.managed.load('task_store')
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.store=self.tasks.Store(self.root/'state')
        self.criteria={'goal':'clear title'}
        self.delivery('root')

    def delivery(self,task,parent=None,engineering='PASS'):
        output=self.root/task;output.mkdir()
        def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data))
        png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',1,1,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(b'\x00\xff\x00\x00\x00'))+chunk(b'IEND',b'')
        (output/'frame.png').write_bytes(png);(output/'project.ecproj').write_bytes(task.encode())
        self.tasks.atomic_json(output/'native.json',{'composition':{'width':1,'height':1,'duration':1,'frameRate':1}})
        manifest={'bindings':{'title':{'layer':1}},'files':{p.name:self.tasks.file_sha(p) for p in output.iterdir()},'frames':[{'path':'frame.png','seconds':0,'requestedAlpha':True}]}
        self.tasks.atomic_json(output/'manifest.json',manifest)
        self.store.create(task,plan={'task':task,'revisionScope':[{'layer':'title','properties':['text/sourceText']}]},output=str(output),runtime_sha='a'*64,inputs={},source=None,mode='workflow',authorization={},parent=parent)
        self.store.start(task);self.store.delivered(task,{'engineeringReopen':engineering,'manifestSha256':self.tasks.file_sha(output/'manifest.json')})

    def request(self,task='root',criteria=None):
        return self.managed.review(self.store,task,criteria or self.criteria)['judgeRequest']

    def accept(self,task='root',score=.8,request=None,response_changes=None):
        request=request or self.request(task)
        response={'requestId':request['requestId'],'binding':request['binding'],
                  'score':score,'passed':False,'issues':[{'description':'title spacing'}],'temporalReviewed':True}
        response.update(schema='effectcraft-judge-receipt/v2',taskId=task,criteriaHash=request['criteriaHash'],scopeHash=request['scopeHash'],
            status='FAIL',capabilities={'visual':True,'temporal':True},
            observations=[{'path':media['path'],'sha256':media['sha256'],'frameIndices':media['frameIndices'],
                'method':'fixture observation','description':'title spacing'} for media in request['scope']['media']])
        response.update(response_changes or {})
        path=self.root/(task+'-response.json');self.tasks.atomic_json(path,response)
        return self.managed.review(self.store,task,self.criteria,path)

    def test_pending_and_settled_request_id_remains_stable(self):
        first=self.request();second=self.request()
        self.assertEqual(first['requestId'],second['requestId'])
        self.accept(request=first)
        self.assertEqual(self.request()['requestId'],first['requestId'])
        self.assertEqual(self.store.read('root')['budget']['stagnant'],0)

    def test_conflicting_response_does_not_replace_original_report_or_budget(self):
        request=self.request();self.accept(request=request)
        before=self.store.read('root');path=self.store.path('root').parent/before['review']['path']
        original=path.read_bytes()
        with self.assertRaisesRegex(ValueError,'judge_response_conflict'):
            self.accept(score=.1,request=request)
        self.assertEqual(path.read_bytes(),original)
        self.assertEqual(self.store.read('root'),before)

    def test_repeat_receipt_after_restart_does_not_charge_stagnation(self):
        request=self.request();self.accept(request=request)
        self.store=self.tasks.Store(self.root/'state');self.accept(request=request)
        state=self.store.read('root')
        self.assertEqual(state['budget']['stagnant'],0)
        self.assertEqual(state['bestTask'],'root')
        self.assertIn('bestVerified',state)
        self.assertEqual(state['bestVerified']['binding'],request['binding'])

    def test_task_family_cannot_compare_different_criteria(self):
        self.accept();self.delivery('child',parent='root')
        with self.assertRaisesRegex(ValueError,'criteria_changed'):
            self.request('child',{'goal':'different target'})
        self.assertFalse((self.store.path('child').parent/'judge-request.json').exists())

    def test_two_distinct_no_improvement_versions_charge_exactly_twice(self):
        self.accept(score=.8);self.delivery('child',parent='root');self.accept('child',.7)
        self.delivery('grandchild',parent='child');request=self.request('grandchild');self.accept('grandchild',.6,request)
        self.accept('grandchild',.6,request)
        state=self.store.read('root')
        self.assertEqual(state['budget']['stagnant'],2)
        self.assertEqual(state['bestTask'],'root')
        self.assertEqual(len(state['qualityReviews']['entries']),3)

    def test_changed_best_artifact_prevents_new_authoritative_evaluation(self):
        self.accept();self.delivery('child',parent='root')
        (self.root/'root/project.ecproj').write_bytes(b'external change')
        with self.assertRaisesRegex(ValueError,'artifact_changed'):
            self.request('child')

    def test_unverified_engineering_does_not_become_best(self):
        self.delivery('unverified',engineering='NOT_RUN')
        request=self.request('unverified')
        with self.assertRaisesRegex(ValueError,'engineering_gate'):
            self.accept('unverified',request=request)
        self.assertNotIn('bestTask',self.store.read('unverified'))

    def test_ancestor_cancel_blocks_child_review_mutation(self):
        self.accept();self.delivery('child',parent='root');self.store.cancel('root')
        before=self.store.read('root')
        with self.assertRaisesRegex(ValueError,'parent_cancelled_or_expired'):
            self.request('child')
        self.assertEqual(self.store.read('root'),before)

    def test_root_commit_survives_child_reference_write_failure(self):
        from unittest.mock import patch
        self.accept();self.delivery('child',parent='root');request=self.request('child')
        original=self.store.save
        def interrupted(state):
            if state['taskId']=='child' and state.get('review'):raise OSError('injected child pointer loss')
            return original(state)
        with patch.object(self.store,'save',side_effect=interrupted):
            with self.assertRaisesRegex(OSError,'injected child pointer loss'):
                self.accept('child',.7,request)
        self.assertEqual(self.store.read('root')['budget']['stagnant'],1)
        self.assertIsNone(self.store.read('child')['review'])
        self.store=self.tasks.Store(self.root/'state');self.accept('child',.7,request)
        self.assertIsNotNone(self.store.read('child')['review'])
        self.assertEqual(self.store.read('root')['budget']['stagnant'],1)

    def test_frozen_report_corruption_and_selection_tampering_fail_closed(self):
        self.accept();state=self.store.read('root')
        changed=dict(state);changed['bestTask']='nonexistent';self.store.save(changed)
        with self.assertRaisesRegex(ValueError,'review_selection_changed'):self.request()
        self.store.save(state)
        path=self.store.path('root').parent/state['review']['path'];path.write_text('{}',encoding='utf-8')
        with self.assertRaises((ValueError,KeyError)):self.request()
        self.assertEqual(path.read_text(encoding='utf-8'),'{}')

    def test_expired_task_cannot_settle_review(self):
        request=self.request();state=self.store.read('root');state['deadline']=state['createdAt']-1;self.store.save(state)
        before=self.store.read('root')
        with self.assertRaisesRegex(ValueError,'deadline_exceeded'):self.accept(request=request)
        self.assertEqual(self.store.read('root'),before)

    def test_symlinked_receipt_parent_cannot_receive_writes(self):
        request=self.request();outside=self.root/'outside';outside.mkdir()
        (self.store.path('root').parent/'reviews').symlink_to(outside,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'review_receipt_symlink'):self.accept(request=request)
        self.assertEqual(list(outside.iterdir()),[])
        self.assertNotIn('bestTask',self.store.read('root'))

    def test_historical_scoring_without_ledger_remains_read_only(self):
        state=self.store.read('root');state.update(bestTask='root',bestScore=.8,reviewedRequests=['old-request'])
        self.store.save(state)
        with self.assertRaisesRegex(ValueError,'legacy_review_read_only'):self.request()
        self.assertEqual(self.store.read('root'),state)

    def test_pending_request_cannot_disable_timing_or_escape_receipt_directory(self):
        request=self.request();path=self.store.path('root').parent/'judge-request.json'
        for change in [{'temporalRequired':False},{'requestId':'../../outside'}, {'criteria':{'goal':'different target'}}]:
            with self.subTest(change=change):
                self.tasks.atomic_json(path,dict(request,**change))
                with self.assertRaisesRegex(ValueError,'judge_request_changed'):
                    self.accept(request=dict(request,**change))
                self.assertNotIn('bestTask',self.store.read('root'))
                self.assertFalse((self.store.path('root').parent/'reviews').exists())

    def test_not_run_observation_is_retained_without_score_or_stagnation(self):
        request=self.request()
        result=self.accept(request=request,response_changes={'capabilities':{'visual':False,'temporal':False}})
        self.assertEqual(result['report']['creative']['status'],'NOT_RUN')
        state=self.store.read('root')
        self.assertNotIn('bestTask',state)
        self.assertEqual(state['budget']['stagnant'],0)
        self.assertEqual(state['qualityReviews']['entries'],{})
        self.assertIn('reviewAttempt',state)
        self.accept(request=request)
        self.assertEqual(self.store.read('root')['bestTask'],'root')

    def test_old_v1_pending_request_is_not_automatically_upgraded(self):
        request=self.request();request['schema']='effectcraft-judge-request/v1'
        path=self.store.path('root').parent/'judge-request.json';self.tasks.atomic_json(path,request)
        before=path.read_bytes()
        with self.assertRaisesRegex(ValueError,'judge_request_changed'):self.request()
        self.assertEqual(path.read_bytes(),before)

    def test_linked_immutable_receipt_is_rejected_even_when_content_matches(self):
        self.accept();state=self.store.read('root')
        request_path=self.store.path('root').parent/state['review']['path']
        request_path=request_path.with_name('request.json')
        outside=self.root/'old-request.json';outside.write_bytes(request_path.read_bytes())
        request_path.unlink();request_path.symlink_to(outside)
        with self.assertRaises(ValueError):self.request()

    def test_missing_media_decoder_does_not_pin_incomplete_judge_request(self):
        from unittest.mock import patch
        output=self.root/'root';(output/'clip.mp4').write_bytes(b'fixture requires a decoder')
        manifest=self.managed.read(output/'manifest.json');manifest['video']={'path':'clip.mp4'}
        manifest['files']['clip.mp4']=self.tasks.file_sha(output/'clip.mp4');self.tasks.atomic_json(output/'manifest.json',manifest)
        state=self.store.read('root');state['delivery']['manifestSha256']=self.tasks.file_sha(output/'manifest.json');self.store.save(state)
        with patch('shutil.which',return_value=None):
            result=self.managed.review(self.store,'root',self.criteria)
        self.assertEqual(result['report']['technical']['status'],'NOT_RUN')
        self.assertIsNone(result['judgeRequest'])
        self.assertEqual(result['requiredAction'],'technical_verification')
        self.assertFalse((self.store.path('root').parent/'judge-request.json').exists())

    def assert_revision_rejected_without_execution(self,task,error,operation=None):
        from unittest.mock import patch
        module=self.managed.load('revision');original_load=module.load
        module.load=lambda name:self.managed if name=='managed' else original_load(name)
        source=self.managed.read(self.root/task/'manifest.json')
        plan={'expectedProjectSha256':source['files']['project.ecproj'],
              'operations':[operation or {'command':'layer.setText','params':{'layer':1,'text':'short'}}]}
        output=self.root/'rejected-revision'
        before=self.store.read('root')
        with patch.object(self.managed,'run',side_effect=AssertionError('native executor must not start')):
            with self.assertRaisesRegex(ValueError,error):
                module.revise(self.store,task,plan,output,self.root/'runtime')
        self.assertEqual(self.store.read('root'),before)
        self.assertFalse(output.exists());self.assertFalse((self.root/'runtime').exists())

    def test_two_revision_round_limit_stops_without_changing_best(self):
        self.accept();state=self.store.read('root');state['budget']['revisions']=2;self.store.save(state)
        self.assert_revision_rejected_without_execution('root','revision_budget_exhausted')

    def test_two_stagnant_versions_stop_further_revision(self):
        self.accept(score=.8);self.delivery('child',parent='root');self.accept('child',.7)
        self.delivery('grandchild',parent='child');self.accept('grandchild',.6)
        self.assert_revision_rejected_without_execution('grandchild','revision_budget_exhausted')
        self.assertEqual(self.store.read('root')['bestTask'],'root')

    def test_revision_cannot_expand_authorized_property_scope(self):
        self.accept()
        self.assert_revision_rejected_without_execution('root','revision_scope_exceeded',
            {'command':'prop.set','params':{'layer':1,'path':'transform/position','value':[0,0]}})

    def test_expired_revision_stops_without_spending_another_round(self):
        self.accept();state=self.store.read('root');state['deadline']=state['createdAt']-1;self.store.save(state)
        self.assert_revision_rejected_without_execution('root','deadline_exceeded')

    def test_changed_target_project_stops_revision_before_native_call(self):
        self.accept();(self.root/'root/project.ecproj').write_bytes(b'changed target')
        self.assert_revision_rejected_without_execution('root','artifact_changed')
