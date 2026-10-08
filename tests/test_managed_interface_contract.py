"""三个模式共享管理契约；公开预检只读，未知编辑不能换身份重做。"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
BASE=Path(__file__).resolve().parents[1]/'skills/effectcraft-use'
class PublicInterfaceContractTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  spec=importlib.util.spec_from_file_location('interface_contract_store',BASE/'scripts/task_store.py');self.tasks=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.tasks)
 def inventory(self):return {p.relative_to(self.root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in self.root.rglob('*') if p.is_file()}
 def invoke(self,state,*args):
  r=subprocess.run([sys.executable,'-I','-B',str(BASE/'scripts/managed.py'),'--state-root',str(state),'--runtime-home',str(self.root/'absent runtime'),*map(str,args)],capture_output=True,text=True,encoding='utf-8',timeout=40)
  self.assertNotIn('Traceback',r.stderr);return r,json.loads(r.stdout)
 def plans(self):return [('workflow','brand-intro.json'),('commands','commands-revision-create.json'),('desktop','desktop-first-use.json')]
 def test_public_preflight_all_modes_and_input_digest_is_readonly(self):
  input_path=self.root/'input';input_path.write_bytes(b'unchanged');before=self.inventory()
  for mode,name in self.plans():
   with self.subTest(mode=mode):
    r,data=self.invoke(self.root/mode,'plan','--mode',mode,'--plan',BASE/'examples'/name,'--output',self.root/(mode+' output'),'--input','provided='+str(input_path))
    self.assertEqual(r.returncode,0,r.stdout+r.stderr);self.assertEqual(data['result'],'VALID');self.assertEqual(data['mode'],mode);self.assertEqual(data['inputHashes']['provided'],hashlib.sha256(b'unchanged').hexdigest());self.assertEqual(before,self.inventory());self.assertFalse((self.root/mode).exists())
 def test_public_preflight_missing_input_and_existing_output_are_rejected(self):
  output=self.root/'existing';output.mkdir();before=self.inventory()
  for mode,name in self.plans():
   for args,error in [(['--output',str(output)],'output_exists'),(['--output',str(self.root/'new'),'--input','missing='+str(self.root/'missing')],'invalid_file')]:
    with self.subTest(mode=mode,error=error):
     r,data=self.invoke(self.root/'state','plan','--mode',mode,'--plan',BASE/'examples'/name,*args);self.assertEqual(r.returncode,1);self.assertIn(error,data['error']);self.assertEqual(before,self.inventory());self.assertFalse((self.root/'state').exists());self.assertFalse((self.root/'absent runtime').exists())
 def test_public_new_task_and_output_cannot_replay_unknown_in_any_mode(self):
  for mode,name in self.plans():
   with self.subTest(mode=mode):
    store=self.tasks.Store(self.root/(mode+' state'));plan=json.loads((BASE/'examples'/name).read_text());store.create('original',plan=plan,output=str(self.root/(mode+' original')),runtime_sha='a'*64,inputs={},source=None,mode=mode,authorization={});store.start('original');store.begin_step('original','edit',{'text':'lost reply'});store.fail('original','reply missing',unknown=True);before=self.inventory()
    r,data=self.invoke(store.root,'run','--task','different','--mode',mode,'--plan',BASE/'examples'/name,'--output',self.root/(mode+' new'))
    self.assertEqual(r.returncode,1,r.stdout+r.stderr);self.assertIn('reconciliation_required',data['error']);self.assertEqual(before,self.inventory());self.assertFalse(store.path('different').exists());self.assertFalse((self.root/(mode+' new')).exists());self.assertFalse((self.root/'absent runtime').exists())
if __name__=='__main__':unittest.main()
