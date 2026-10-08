"""父子取消须等待整个已绑定任务族停止，未知编辑仍保留占用。"""
import importlib.util,json,tempfile,unittest
from unittest.mock import patch
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def managed():
 s=importlib.util.spec_from_file_location('cancel_family_test',ROOT/'skills/effectcraft-use/scripts/managed.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
class CancelFamilyTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.m=managed();self.store=self.m.load('task_store').Store(self.root/'state');self.create('root')
 def create(self,task,parent=None):return self.store.create(task,plan={'task':task},output=str(self.root/task),runtime_sha='a'*64,inputs={},source=None,mode='workflow',authorization={},parent=parent)
 def receipt(self,task,**extra):
  v={'schema':'effectcraft-process-lifecycle/v1','status':'stopped','returncode':1};v.update(extra);self.m.load('task_store').atomic_json(self.store.lifecycle_path(self.store.read(task)),v)
 def stop(self,task):self.receipt(task);return self.store.stopped(task,'fixture verified owned stop')
 def test_planned_parent_does_not_finish_while_child_running(self):
  self.create('child','root');self.store.start('child');result=self.store.cancel('root')
  self.assertEqual(result['state'],'cancel_requested');self.assertIn('child',result['cancellationFamily']['pendingTasks'])
  self.assertEqual(result['cancellationLocal']['kind'],'not-started')
 def test_parent_can_finish_after_descendant_reconciled_without_inventing_local_exit(self):
  self.create('child','root');self.store.start('child');self.store.cancel('root');self.receipt('child');self.m.reconcile(self.store,'child')
  result=self.m.reconcile(self.store,'root');self.assertEqual(result['state'],'cancelled');self.assertEqual(result['cancellationFamily']['status'],'stopped');self.assertNotIn('processExit',result)
 def test_stopped_parent_waits_for_living_descendant(self):
  self.store.start('root');self.create('child','root');self.store.start('child');self.store.cancel('root');result=self.stop('root')
  self.assertEqual(result['state'],'cancel_requested');self.assertIn('child',result['cancellationFamily']['pendingTasks'])
 def test_child_unknown_keeps_parent_reconciling_and_duplicate_blocked(self):
  self.create('child','root');self.store.start('child');self.store.begin_step('child','edit',{'text':'unknown'});self.store.cancel('root');self.receipt('child');self.m.reconcile(self.store,'child')
  result=self.m.reconcile(self.store,'root');self.assertEqual(result['state'],'reconciling');self.assertEqual(result['cancellationFamily']['unknownTasks'],['child'])
  with self.assertRaisesRegex(ValueError,'reconciliation_required'):
   self.store.create('replacement',plan={'task':'root'},output=str(self.root/'different'),runtime_sha='a'*64,inputs={},source=None,mode='workflow',authorization={})
 def test_descendant_live_lease_wins_over_stopped_receipt(self):
  self.create('child','root');self.store.start('child');self.store.cancel('root');self.stop('child')
  with self.m.load('platform_support').exclusive_lock(self.store.root/'leases/child.supervisor.lock',timeout=0):
   result=self.m.reconcile(self.store,'root');self.assertEqual(result['state'],'cancel_requested');self.assertIn('child',result['cancellationFamily']['pendingTasks'])
 def test_multilevel_planned_family_cancels_bottom_up(self):
  self.create('child','root');self.create('grandchild','child');result=self.store.cancel('root')
  self.assertEqual(result['state'],'cancelled');self.assertEqual(result['cancellationFamily']['status'],'stopped')
  self.assertTrue(all(self.store.read(x)['state']=='cancelled' for x in ['root','child','grandchild']))
 def test_cancel_restart_never_fabricates_missing_local_stop_proof(self):
  self.store.start('root');self.store.cancel('root');before=self.store.path('root').read_bytes()
  with self.assertRaisesRegex(ValueError,'process_termination_unconfirmed'):self.m.reconcile(self.store,'root')
  self.assertEqual(self.store.path('root').read_bytes(),before)
 def test_missing_bound_descendant_cannot_be_dropped(self):
  self.create('child','root');self.store.start('child');self.store.cancel('root');path=self.store.path('child');path.rename(path.with_suffix('.preserved'));before=self.store.path('root').read_bytes()
  with self.assertRaises(ValueError):self.m.reconcile(self.store,'root')
  self.assertEqual(self.store.path('root').read_bytes(),before)
 def test_cancel_propagation_crash_keeps_root_intent_and_roster(self):
  self.create('child','root');original=self.store.save
  def save(state):
   if state['taskId']=='child' and state.get('cancellationRequestedAt'):raise OSError('injected propagation crash')
   return original(state)
  with patch.object(self.store,'save',side_effect=save),self.assertRaisesRegex(OSError,'propagation crash'):self.store.cancel('root')
  root=self.store.read('root');self.assertEqual(root['state'],'cancel_requested');self.assertEqual({x['taskId'] for x in root['cancellationFamily']['members']},{'root','child'})
  with self.assertRaisesRegex(ValueError,'parent_cancelled_or_expired'):self.store.start('child')
  again=self.store.cancel('root');self.assertEqual(again['state'],'cancelled');self.assertEqual(again['cancellationRequestedAt'],root['cancellationRequestedAt'])
 def test_changed_child_identity_or_parent_preserves_root_and_refuses(self):
  self.create('child','root');self.store.start('child');self.store.cancel('root');original=self.store.path('child').read_bytes()
  for change in ['identity','parent']:
   with self.subTest(change=change):
    child=json.loads(original)
    if change=='parent':child['parent']=None
    else:
     child['identity']['authorization']['changed']=True;child['identityHash']=self.m.load('task_store').digest(child['identity'])
    self.store.path('child').write_text(json.dumps(child));before=self.store.path('root').read_bytes()
    with self.assertRaisesRegex(ValueError,'cancellation_family_identity_conflict|state_invalid: cancellation_family_invalid'):self.m.reconcile(self.store,'root')
    self.assertEqual(self.store.path('root').read_bytes(),before)
    self.store.path('child').write_bytes(original)
 def test_late_exit_does_not_fabricate_business_result_for_unstarted_cancel(self):
  self.store.cancel('root');before=self.store.path('root').read_bytes();result=self.store.worker_exited('root',1)
  self.assertEqual(result['state'],'cancelled');self.assertNotIn('processExit',result);self.assertEqual(self.store.path('root').read_bytes(),before)
 def test_corrupt_cancel_proof_or_roster_is_readonly_diagnostic(self):
  self.store.cancel('root');valid=self.store.path('root').read_bytes()
  changes=[('cancellationLocal','at',float('nan')),('cancellationLocal','at',self.store.read('root')['updatedAt']+100),('cancellationFamily','checkedAt',self.store.read('root')['updatedAt']+100),('cancellationFamily','pendingTasks',['unknown']),('cancellationFamily','status','unknown')]
  for section,key,value in changes:
   with self.subTest(section=section,key=key,value=value):
    state=json.loads(valid);state[section][key]=value;self.store.path('root').write_text(json.dumps(state));before=self.store.path('root').read_bytes()
    with self.assertRaisesRegex(ValueError,'state_invalid'):self.store.read('root')
    self.assertEqual(self.store.path('root').read_bytes(),before);self.store.path('root').write_bytes(valid)
 def test_pending_family_cannot_be_relabelled_terminal(self):
  self.create('child','root');self.store.start('child');self.store.cancel('root');valid=self.store.path('root').read_bytes()
  for status in ['cancelled','completed','review_ready']:
   with self.subTest(status=status):
    value=json.loads(valid);value['state']=status;self.store.path('root').write_text(json.dumps(value));before=self.store.path('root').read_bytes()
    with self.assertRaisesRegex(ValueError,'state_invalid'):self.store.read('root')
    self.assertEqual(self.store.path('root').read_bytes(),before);self.store.path('root').write_bytes(valid)
 def test_existing_successful_delivery_is_retained(self):
  self.store.start('root');self.store.delivered('root',{'manifestSha256':'b'*64});self.receipt('root',returncode=0)
  result=self.store.cancel('root');self.assertEqual(result['delivery'],{'manifestSha256':'b'*64});self.assertEqual(result['state'],'review_ready')
 def test_stopped_unknown_grandchild_propagates_through_cancelled_parent(self):
  self.create('child','root');self.create('grandchild','child');self.store.start('grandchild');self.store.begin_step('grandchild','edit',{});self.store.cancel('root');self.receipt('grandchild');self.m.reconcile(self.store,'grandchild');self.m.reconcile(self.store,'child');result=self.m.reconcile(self.store,'root')
  self.assertEqual(result['state'],'reconciling');self.assertIn('grandchild',result['cancellationFamily']['unknownTasks'])
if __name__=='__main__':unittest.main()
