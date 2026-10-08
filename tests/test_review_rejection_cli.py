"""公开CLI拒绝评价时返回当前NOT_RUN诊断，保全历史回执与状态。"""
import json
from pathlib import Path
import subprocess
import sys
import unittest
import test_managed_review_ledger as fixtures

class ReviewRejectionCliTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.ReviewLedgerTests();self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root=self.fixture.root;self.store=self.fixture.store
        self.criteria=self.root/'criteria.json';self.fixture.tasks.atomic_json(self.criteria,self.fixture.criteria)

    def invoke(self,judge=None):
        command=[sys.executable,'-I','-B',str(fixtures.SCRIPT),'--state-root',str(self.store.root),
                 '--runtime-home',str(self.root/'runtime'),'review','--task','root','--criteria',str(self.criteria)]
        if judge:command.extend(['--judge',str(judge)])
        result=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',timeout=30)
        return result,json.loads(result.stdout)

    def assert_rejection(self,error,technical=None):
        state_path=self.store.path('root');before=state_path.read_bytes()
        result,data=self.invoke(self.root/'root-response.json')
        self.assertNotEqual(result.returncode,0,result.stderr)
        self.assertIn(error,data['error'])
        self.assertEqual(data.get('schema'),'effectcraft-review-rejection/v1')
        self.assertEqual(data['taskId'],'root')
        self.assertEqual(data['report']['creative']['status'],'NOT_RUN')
        self.assertFalse(data['report']['readyForAcceptance']);self.assertFalse(data['report']['accepted'])
        if technical:self.assertEqual(data['report']['technical']['status'],technical)
        self.assertEqual(state_path.read_bytes(),before)
        self.assertFalse((self.root/'runtime').exists())
        return data

    def test_stale_settled_pass_is_not_returned_as_current_pass(self):
        self.fixture.accept(response_changes={'status':'PASS','passed':True,'issues':[]})
        state=self.store.read('root');report_path=self.store.path('root').parent/state['review']['path']
        old_report=report_path.read_bytes()
        (self.root/'root/project.ecproj').write_bytes(b'changed after successful review')
        self.assert_rejection('artifact_changed',technical='FAIL')
        self.assertEqual(report_path.read_bytes(),old_report)
        self.assertEqual(json.loads(old_report)['creative']['status'],'PASS')

    def test_changed_criteria_preserves_current_technical_pass_and_blocks_creative(self):
        self.fixture.accept();self.fixture.tasks.atomic_json(self.criteria,{'goal':'another goal'})
        self.assert_rejection('criteria_changed',technical='PASS')

    def test_corrupt_state_returns_unverified_diagnostic_without_reset(self):
        self.fixture.accept();self.store.path('root').write_text('{broken',encoding='utf-8')
        self.assert_rejection('state_invalid',technical='NOT_RUN')

    def test_expired_task_cannot_return_current_creative_pass(self):
        self.fixture.accept();state=self.store.read('root');state['deadline']=state['createdAt']-1;self.store.save(state)
        self.assert_rejection('deadline_exceeded')

    def test_pending_legacy_request_is_read_only_and_not_overwritten(self):
        request=self.fixture.request();request['schema']='effectcraft-judge-request/v1'
        request_path=self.store.path('root').parent/'judge-request.json';self.fixture.tasks.atomic_json(request_path,request)
        self.fixture.tasks.atomic_json(self.root/'root-response.json',{})
        before=request_path.read_bytes()
        self.assert_rejection('judge_request_changed')
        self.assertEqual(request_path.read_bytes(),before)

    def test_history_is_not_current_pass_when_native_runtime_is_absent(self):
        self.fixture.accept(response_changes={'status':'PASS','passed':True,'issues':[]})
        result,data=self.invoke(self.root/'root-response.json')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertEqual(data['report']['creative']['status'],'NOT_RUN')
        self.assertEqual(data['report']['engineering']['status'],'NOT_RUN')
        self.assertFalse(data['report']['readyForAcceptance'])
        self.assertNotEqual(data.get('schema'),'effectcraft-review-rejection/v1')
