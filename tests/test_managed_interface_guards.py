"""管理公开入口拒绝无身份旧写入，错误诊断不创建恢复材料。"""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'skills/effectcraft-use';SCRIPT=BASE/'scripts/managed.py'
def load():
 spec=importlib.util.spec_from_file_location('interface_managed',SCRIPT);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
class ManagedInterfaceGuardTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.m=load();self.store=self.m.load('task_store').Store(self.root/'state');self.criteria=self.root/'criteria.json';self.criteria.write_text('{"goal":"test"}')
 def create(self,task='old',parent=None):return self.store.create(task,plan={'task':task},output=str(self.root/task),runtime_sha='a'*64,inputs={},source=None,mode='workflow',authorization={},parent=parent)
 def inventory(self):return {p.relative_to(self.root).as_posix():p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
 def invoke(self,action,task='old',root=None,extra=()):
  args=[sys.executable,'-I','-B',str(SCRIPT),'--state-root',str(root or self.store.root),'--runtime-home',str(self.root/'absent runtime'),action]
  if task is not None:args+=['--task',task]
  r=subprocess.run(args+list(extra),capture_output=True,text=True,encoding='utf-8',timeout=40);return r,json.loads(r.stdout)
 def test_old_records_inspect_but_all_mutations_are_readonly(self):
  self.create()
  for schema in ['effectcraft-managed-task/v1','effectcraft-managed-task/v2']:
   state=self.store.read('old');state['schema']=schema;self.store.save(state)
   with self.subTest(schema=schema):
    before=self.inventory();r,v=self.invoke('inspect');self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(v['schema'],schema);self.assertEqual(before,self.inventory())
    for action,extra in [('cancel',()),('reconcile',()),('resume',()),('review',('--criteria',str(self.criteria))),('revise',('--plan',str(BASE/'examples/brand-intro.json'),'--output',str(self.root/'new')))]:
     with self.subTest(action=action):
      r,v=self.invoke(action,extra=extra);self.assertNotEqual(r.returncode,0);self.assertIn('legacy_',v['error']);self.assertEqual(before,self.inventory())
 def test_cancel_dispatches_through_binding_handoff(self):
  self.create();binding=self.m.load('runtime_binding');calls=[];original=self.m.load
  def handoff(store,args,current):calls.append(args.action);raise ValueError('original_controller_marker')
  binding.handoff=handoff
  with patch.object(self.m,'load',side_effect=lambda name:binding if name=='runtime_binding' else original(name)),patch.object(sys,'argv',['managed','--state-root',str(self.store.root),'cancel','--task','old']),patch('builtins.print') as output,self.assertRaises(SystemExit):self.m.main()
  self.assertEqual(calls,['cancel']);self.assertIn('original_controller_marker',output.call_args.args[0])
 def test_missing_or_corrupt_state_does_not_create_leases(self):
  for action in ['inspect','cancel','reconcile','resume']:
   with self.subTest(action=action):
    before=self.inventory();r,v=self.invoke(action);self.assertEqual(r.returncode,1);self.assertIn('state_invalid',v['error']);self.assertEqual(before,self.inventory())
  self.create();self.store.path('old').write_text('{broken');before=self.inventory()
  for action in ['inspect','cancel','reconcile','resume']:
   r,v=self.invoke(action);self.assertEqual(r.returncode,1);self.assertIn('state_invalid',v['error']);self.assertEqual(before,self.inventory())
 def test_symlink_state_root_returns_structured_error(self):
  target=self.root/'target';target.mkdir();link=self.root/'linked'
  try:link.symlink_to(target,target_is_directory=True)
  except OSError as e:self.skipTest(str(e))
  before=self.inventory();r,v=self.invoke('inspect',root=link);self.assertEqual(r.returncode,1);self.assertIn('state_root_symlink',v['error']);self.assertEqual(before,self.inventory());self.assertNotIn('Traceback',r.stderr)
 def test_legacy_store_cancel_and_reconcile_do_not_create_materials(self):
  self.create();state=self.store.read('old');state['schema']='effectcraft-managed-task/v1';self.store.save(state);before=self.inventory()
  for fn in [lambda:self.store.cancel('old'),lambda:self.m.reconcile(self.store,'old')]:
   with self.assertRaisesRegex(ValueError,'legacy_task_read_only'):fn()
   self.assertEqual(before,self.inventory())
 def test_current_parent_cancels_without_migrating_legacy_descendant(self):
  self.create('parent');self.create('old','parent');state=self.store.read('old');state['schema']='effectcraft-managed-task/v1';self.store.save(state);old=self.store.path('old').read_bytes();result=self.store.cancel('parent')
  self.assertEqual(result['state'],'cancel_requested');self.assertIn('old',result['cancellationFamily']['pendingTasks']);self.assertEqual(self.store.path('old').read_bytes(),old)
 def test_dangling_receipt_is_diagnostic_without_repair(self):
  self.create();self.store.start('old');step=self.store.begin_step('old','edit',{'value':1});self.store.finish_step('old',step,{'saved':True});(self.store.path('old').parent/'receipts'/(step+'.json')).unlink();before=self.inventory()
  for action in ['inspect','cancel','reconcile','resume']:
   r,v=self.invoke(action);self.assertEqual(r.returncode,1);self.assertIn('state_invalid',v['error']);self.assertEqual(before,self.inventory())
 def test_direct_cli_cancel_reaches_original_frozen_controller(self):
  import test_task_entry as fixtures
  f=fixtures.TaskEntryTests();f.setUp();self.addCleanup(f.doCleanups)
  r=subprocess.run([sys.executable,'-I','-B',str(f.front/'scripts/managed.py'),'--state-root',str(f.store.root),'--runtime-home',str(f.root/'incorrect current native'),'cancel','--task','held'],env=f.env,capture_output=True,text=True,encoding='utf-8',timeout=40)
  self.assertEqual(r.returncode,0,r.stdout+r.stderr);v=json.loads(r.stdout);self.assertEqual(v['controller'],'original');self.assertEqual(v['argv'][v['argv'].index('--runtime-home')+1],str(f.home));f.unchanged()
 def test_invalid_run_does_not_prepare_environment_or_task(self):
  plan=self.root/'bad-plan.json';plan.write_text('{}');before=self.inventory();r,v=self.invoke('run',task='new',extra=('--plan',str(plan),'--output',str(self.root/'new')))
  self.assertEqual(r.returncode,1);self.assertEqual(v['result'],'FAIL');self.assertEqual(before,self.inventory())
 def test_doctor_and_plan_are_readonly_with_absent_environment(self):
  before=self.inventory();r,v=self.invoke('doctor',task=None);self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(before,self.inventory())
  r,v=self.invoke('plan',task=None,extra=('--plan',str(BASE/'examples/brand-intro.json'),'--output',str(self.root/'new')));self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(v['result'],'VALID');self.assertEqual(before,self.inventory())
if __name__=='__main__':unittest.main()
