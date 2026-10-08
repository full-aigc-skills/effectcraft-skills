"""回执必须绑定原调用；孤立或冲突材料不得被忽略、覆盖或用于重放。"""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
BASE=Path(__file__).resolve().parents[1]/'skills/effectcraft-use/scripts'
def load():
 s=importlib.util.spec_from_file_location('receipt_identity',BASE/'task_store.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
class ReceiptIdentityTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.m=load();self.store=self.m.Store(self.root/'state');self.store.create('root',plan={},output=str(self.root/'out'),runtime_sha='a'*64,inputs={},source=None,mode='workflow',authorization={});self.store.start('root');self.op=self.store.begin_step('root','edit',{'text':'original'});self.receipt=self.store.path('root').parent/'receipts'/(self.op+'.json')
 def payload(self,result=None):return {'schema':'effectcraft-step-result/v1','taskId':'root','operationId':self.op,'argumentsHash':self.store.read('root')['steps'][0]['argumentsHash'],'result':result or {'ok':True}}
 def snapshot(self):return {p.relative_to(self.root).as_posix():p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
 def rejected(self):
  before=self.snapshot()
  with self.assertRaisesRegex(ValueError,'state_invalid'):self.store.read('root')
  self.assertEqual(before,self.snapshot())
 def test_succeeded_receipt_requires_schema_and_original_arguments(self):
  self.store.finish_step('root',self.op,{'ok':True});original=json.loads(self.receipt.read_text())
  for key,value in [('schema','effectcraft-step-result/v99'),('argumentsHash','b'*64),('taskId','other'),('operationId','c'*32)]:
   with self.subTest(key=key):
    changed=dict(original);changed[key]=value;self.m.atomic_json(self.receipt,changed);self.rejected();self.m.atomic_json(self.receipt,original)
 def test_orphan_receipt_blocks_read_and_new_task_without_changes(self):
  self.m.atomic_json(self.receipt.parent/('d'*32+'.json'),{'schema':'effectcraft-step-result/v1','taskId':'root','operationId':'d'*32,'argumentsHash':'b'*64,'result':{}});self.rejected();before=self.snapshot()
  with self.assertRaisesRegex(ValueError,'state_invalid'):self.store.create('new',plan={'different':True},output=str(self.root/'new'),runtime_sha='a'*64,inputs={},source=None,mode='workflow',authorization={})
  self.assertEqual(before,self.snapshot());self.assertFalse(self.store.path('new').exists())
 def test_attempted_receipt_is_validated_but_not_automatically_settled(self):
  value=self.payload();self.m.atomic_json(self.receipt,value);before=self.snapshot();self.assertEqual(self.store.read('root')['steps'][0]['state'],'attempted');self.assertEqual(before,self.snapshot())
  value['argumentsHash']='b'*64;self.m.atomic_json(self.receipt,value);self.rejected()
 def test_conflicting_settlement_preserves_original_receipt(self):
  original=self.payload();self.m.atomic_json(self.receipt,original);before=self.snapshot()
  with self.assertRaisesRegex(ValueError,'operation_receipt_conflict'):self.store.finish_step('root',self.op,{'other':True})
  self.assertEqual(before,self.snapshot())
 def test_identical_settlement_keeps_receipt_inode_and_bytes(self):
  value=self.payload();self.m.atomic_json(self.receipt,value);before=(self.receipt.read_bytes(),self.receipt.stat().st_ino,self.receipt.stat().st_mtime_ns)
  self.store.finish_step('root',self.op,value['result']);self.assertEqual(self.store.read('root')['steps'][0]['state'],'succeeded');self.assertEqual(before,(self.receipt.read_bytes(),self.receipt.stat().st_ino,self.receipt.stat().st_mtime_ns))
 def test_operation_id_cannot_escape_receipt_directory(self):
  state=self.store.read('root');state['steps'][0]['id']='../../outside';self.store.save(state);self.rejected()
 def test_receipt_directory_and_entries_are_not_followed(self):
  self.receipt.parent.mkdir();(self.receipt.parent/'unexpected-directory').mkdir();self.rejected();(self.receipt.parent/'unexpected-directory').rmdir()
  outside=self.root/'outside.json';outside.write_text('{}')
  try:(self.receipt.parent/'unexpected.json').symlink_to(outside)
  except OSError as e:self.skipTest(str(e))
  self.rejected();self.assertEqual(outside.read_text(),'{}')
 def test_receipt_written_before_state_save_crash_remains_unknown(self):
  before=self.store.read('root')['steps'];original=self.store.save
  with patch.object(self.store,'save',side_effect=OSError('injected state write loss')):
   with self.assertRaisesRegex(OSError,'injected state write loss'):self.store.finish_step('root',self.op,{'ok':True})
  restarted=self.m.Store(self.store.root);self.assertEqual(restarted.read('root')['steps'],before);self.assertTrue(self.receipt.is_file());self.assertEqual(restarted.read('root')['steps'][0]['state'],'attempted')

 def test_public_bound_interfaces_reject_orphan_and_misbound_receipts(self):
  import os,subprocess,sys
  spec=importlib.util.spec_from_file_location('receipt_binding',BASE/'runtime_binding.py');binding=importlib.util.module_from_spec(spec);spec.loader.exec_module(binding)
  value,manifest=binding.prepare(BASE.parent,self.root/'absent runtime');state=self.store.read('root');state['identity']['runtimeBinding']=value;state['identity']['runtimeSha256']=json.loads((BASE/'runtime.lock.json').read_text())['artifacts'][value['platform']]['binarySha256'];state['identityHash']=self.m.digest(state['identity']);self.store.save(state);binding.freeze(self.store,'root',BASE.parent,manifest)
  payload=self.payload();criteria=self.root/'criteria.json';criteria.write_text('{"goal":"test"}')
  direct=[sys.executable,'-I','-B',str(BASE/'managed.py'),'--state-root',str(self.store.root),'--runtime-home',str(self.root/'absent runtime')]
  shell=(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(BASE/'launch.ps1')] if os.name=='nt' else ['/bin/sh',str(BASE/'launch.sh')])+['--state-root',str(self.store.root)]
  actions=[('inspect',[]),('cancel',[]),('reconcile',[]),('resume',[]),('review',['--criteria',str(criteria)]),('revise',['--plan',str(BASE.parent/'examples/brand-intro.json'),'--output',str(self.root/'new delivery')])]
  env={**os.environ,'CRAFT_PYTHON_HOME':str(self.root/'empty python'),'CRAFT_RUNTIME_HOME':str(self.root/'absent runtime')}
  for kind in ['orphan','arguments','schema']:
   damaged=dict(payload)
   path=self.receipt
   if kind=='orphan':path=self.receipt.parent/('f'*32+'.json')
   elif kind=='arguments':damaged['argumentsHash']='f'*64
   else:damaged['schema']='effectcraft-step-result/v99'
   self.m.atomic_json(path,damaged);before=self.snapshot()
   for prefix in [direct,shell]:
    for action,args in actions:
     with self.subTest(kind=kind,entry=prefix[0],action=action):
      r=subprocess.run(prefix+[action,'--task','root',*args],env=env,capture_output=True,text=True,encoding='utf-8',timeout=40)
      self.assertNotEqual(r.returncode,0,r.stdout+r.stderr);self.assertNotIn('Traceback',r.stderr);self.assertEqual(before,self.snapshot());self.assertFalse((self.root/'empty python').exists());self.assertFalse((self.root/'new delivery').exists())
   path.unlink()

if __name__=='__main__':unittest.main()
