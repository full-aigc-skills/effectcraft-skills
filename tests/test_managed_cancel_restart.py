"""启动窗口和控制器重启后取消结算；持久取消不等于已经停止。"""
import importlib.util,json,os,subprocess,sys,tempfile,threading,time,unittest
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def managed():
 spec=importlib.util.spec_from_file_location('cancel_restart',ROOT/'skills/effectcraft-use/scripts/managed.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
class CancelRestartTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.m=managed();self.store=self.m.load('task_store').Store(self.root/'state');self.create('task')
 def create(self,task,parent=None):
  return self.store.create(task,plan={'name':task},output=str(self.root/task),runtime_sha='a'*64,inputs={},source=None,mode='workflow',authorization={},parent=parent)
 def receipt(self,task='task',**extra):
  value={'schema':'effectcraft-process-lifecycle/v1','status':'stopped','returncode':-9};value.update(extra);self.m.load('task_store').atomic_json(self.store.lifecycle_path(self.store.read(task)),value)
 def test_planned_task_with_any_active_execution_lease_is_only_requested(self):
  for index,suffix in enumerate(['supervisor.lock','lifecycle.lock','lock']):
   task='window'+str(index);self.create(task)
   with self.m.load('platform_support').exclusive_lock(self.store.root/'leases'/(task+'.'+suffix),timeout=0):
    self.assertEqual(self.store.cancel(task)['state'],'cancel_requested')
 def test_reconcile_requires_all_execution_leases_to_be_released(self):
  self.store.start('task');self.store.cancel('task');self.receipt()
  for suffix in ['supervisor.lock','lifecycle.lock','lock']:
   with self.subTest(suffix=suffix),self.m.load('platform_support').exclusive_lock(self.store.root/'leases'/('task.'+suffix),timeout=0):
    before=self.store.path('task').read_bytes()
    with self.assertRaises(TimeoutError):self.m.reconcile(self.store,'task')
    self.assertEqual(self.store.path('task').read_bytes(),before)
 def test_planned_with_existing_execution_record_is_not_prematurely_cancelled(self):
  for index,status in enumerate(['starting','running','unknown','stopped']):
   task='record'+str(index);self.create(task);self.receipt(task,status=status)
   self.assertEqual(self.store.cancel(task)['state'],'cancel_requested')
 def test_restart_settles_proven_stop_without_unresolved_operations(self):
  self.store.start('task');self.store.cancel('task');before=self.store.read('task');self.receipt()
  result=self.m.reconcile(self.store,'task');self.assertEqual(result['state'],'cancelled');self.assertEqual(result['termination']['status'],'confirmed');self.assertEqual(result['workerExitCode'],-9)
  for key in ['identity','identityHash','deadline','steps','cancellationRequestedAt']:self.assertEqual(result[key],before[key])
 def test_restart_preserves_unknown_edit_and_operation_identity(self):
  self.store.start('task');op=self.store.begin_step('task','edit',{'text':'new'});self.store.cancel('task');before=self.store.read('task');self.receipt()
  result=self.m.reconcile(self.store,'task');self.assertEqual(result['state'],'reconciling');self.assertEqual(result['termination']['status'],'confirmed');self.assertEqual(result['reconciliation']['result'],'unknown');self.assertEqual(result['steps'],before['steps']);self.assertEqual(result['steps'][0]['id'],op)
  with self.assertRaisesRegex(ValueError,'cancel_requested'):self.store.start('task')
 def test_invalid_stop_exit_or_unknown_record_preserves_entire_state(self):
  self.store.start('task');self.store.cancel('task')
  for extra in [{'returncode':True},{'returncode':None},{'returncode':'0'},{'status':'unknown'}]:
   with self.subTest(extra=extra):
    self.receipt(**extra);before=self.store.path('task').read_bytes()
    with self.assertRaisesRegex(ValueError,'process_termination_unconfirmed'):self.m.reconcile(self.store,'task')
    self.assertEqual(self.store.path('task').read_bytes(),before)
 def test_forced_group_stop_is_not_a_verified_business_exit(self):
  self.store.start('task');self.store.cancel('task');self.receipt(ownership={
   'schema':'effectcraft-posix-group-lease/v1','workerResultVerified':False,
   'workerReturncode':None,'exitCodeSource':'group-holder-forced-stop','gateReturncode':-9,'forcedDrain':True})
  result=self.m.reconcile(self.store,'task');self.assertEqual(result['state'],'cancelled')
  self.assertIsNone(result.get('workerExitCode'));self.assertEqual(result['processExit']['schema'],'effectcraft-managed-process-exit/v1')
  self.assertFalse(result['processExit']['workerResultVerified']);self.assertEqual(result['processExit']['source'],'group-holder-forced-stop')
 @unittest.skipIf(os.name=='nt','POSIX forced-stop source; native Windows Job has a separate contract')
 def test_supervisor_keeps_unreceived_business_exit_unknown_after_forced_stop(self):
  marker=self.root/'worker-ready';driver=self.root/'worker.py'
  driver.write_text('import importlib.util,signal,time\nfrom pathlib import Path\n'
   +f's=importlib.util.spec_from_file_location("store",{str(ROOT/"skills/effectcraft-use/scripts/task_store.py")!r})\n'
   +'m=importlib.util.module_from_spec(s);s.loader.exec_module(m)\n'
   +f'store=m.Store(Path({str(self.store.root)!r}));store.start("task")\n'
   +'signal.signal(signal.SIGTERM,signal.SIG_IGN)\n'
   +f'Path({str(marker)!r}).write_text("running")\n'
   +'time.sleep(20)\n')
  errors=[]
  def cancel():
   try:
    deadline=time.monotonic()+8
    while not marker.exists() and time.monotonic()<deadline:time.sleep(.01)
    if not marker.exists():raise AssertionError('controlled worker did not start')
    self.store.cancel('task')
   except BaseException as e:errors.append(e)
  watcher=threading.Thread(target=cancel);watcher.start();original=self.m.load
  binding=SimpleNamespace(resolve=lambda *args:{'python':sys.executable,'guard':str(ROOT/'skills/effectcraft-use/scripts/process_guard.py'),'script':str(driver),'runtimeHome':str(self.root/'runtime')})
  try:
   with patch.object(self.m,'load',side_effect=lambda name:binding if name=='runtime_binding' else original(name)):
    result=self.m.supervise(self.store,'task',self.root/'runtime')
  finally:watcher.join(timeout=10)
  self.assertFalse(errors,errors);self.assertFalse(watcher.is_alive());self.assertEqual(result['state'],'cancelled')
  self.assertIsNone(result['workerExitCode']);self.assertFalse(result['processExit']['workerResultVerified'])
  self.assertEqual(result['processExit']['source'],'group-holder-forced-stop');self.assertEqual(result['termination']['status'],'confirmed')
 def test_conflicting_business_exit_evidence_is_preserved_and_refused(self):
  self.store.start('task');self.store.cancel('task')
  for ownership in [
   {'schema':'effectcraft-posix-group-lease/v1','workerResultVerified':True,'workerReturncode':0,'exitCodeSource':'business-result'},
   {'schema':'effectcraft-posix-group-lease/v1','workerResultVerified':False,'workerReturncode':7,'exitCodeSource':'group-holder-forced-stop'},
   {'schema':'effectcraft-posix-group-lease/v1','workerResultVerified':False,'workerReturncode':None,'exitCodeSource':'business-result'}]:
   with self.subTest(ownership=ownership):
    self.receipt(ownership=ownership);before=self.store.path('task').read_bytes()
    with self.assertRaisesRegex(ValueError,'process_exit_evidence_invalid'):self.m.reconcile(self.store,'task')
    self.assertEqual(self.store.path('task').read_bytes(),before)
 def test_corrupt_versioned_process_exit_is_readonly_diagnostic(self):
  self.store.start('task');self.store.worker_exited('task',7);valid=self.store.read('task')
  for change in [{'schema':'unknown/v1'},{'returncode':True},{'workerResultVerified':False},{'source':'unknown'},{'observedAt':float('nan')}]:
   with self.subTest(change=change):
    value=json.loads(json.dumps(valid));value['processExit'].update(change)
    self.store.path('task').write_text(json.dumps(value));before=self.store.path('task').read_bytes()
    with self.assertRaisesRegex(ValueError,'state_invalid'):self.store.read('task')
    self.assertEqual(self.store.path('task').read_bytes(),before)
 def test_missing_start_window_receipt_cannot_confirm_cancellation(self):
  with self.m.load('platform_support').exclusive_lock(self.store.root/'leases/task.supervisor.lock',timeout=0):self.store.cancel('task')
  before=self.store.path('task').read_bytes()
  with self.assertRaisesRegex(ValueError,'process_termination_unconfirmed'):self.m.reconcile(self.store,'task')
  self.assertEqual(self.store.path('task').read_bytes(),before)
 def test_child_in_start_window_retains_requested_intent_from_parent(self):
  self.create('child','task')
  with self.m.load('platform_support').exclusive_lock(self.store.root/'leases/child.supervisor.lock',timeout=0):self.store.cancel('task')
  self.assertEqual(self.store.read('child')['state'],'cancel_requested')
if __name__=='__main__':unittest.main()
