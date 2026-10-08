"""启动后的源工程变化必须在下一次原生调用和交付前阻止旧任务。"""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

HERE=Path(__file__).resolve().parents[1]/'skills/effectcraft-use/scripts'
def module(name):
 spec=importlib.util.spec_from_file_location('source_conflict_'+name,HERE/(name+'.py'))
 value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value

class ManagedSourceConflictTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
  self.source=self.root/'source.ecproj';self.source.write_bytes(b'original native project')
  self.tasks=module('task_store');self.store=self.tasks.Store(self.root/'state')
 def start(self,mode):
  self.store.create(mode,plan={'mode':mode},output=str(self.root/mode),runtime_sha='a'*64,inputs={},source=str(self.source),mode=mode,authorization={})
  return self.store.start(mode)
 def inventory(self):
  return {p.relative_to(self.root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in self.root.rglob('*') if p.is_file()}
 def test_each_mode_rechecks_source_before_registering_next_operation(self):
  for mode in ('workflow','commands','desktop'):
   with self.subTest(mode=mode):
    self.store=self.tasks.Store(self.root/('state-'+mode));self.source=self.root/(mode+'.ecproj');self.source.write_bytes(b'original native project');self.start(mode)
    first=self.store.begin_step(mode,'open_project',{});self.store.finish_step(mode,first,{'ok':True})
    self.source.write_bytes(b'user saved another project version');before=self.inventory()
    with self.assertRaisesRegex(ValueError,'revision_conflict'):
     self.store.begin_step(mode,'execute_command',{'command':'layer.set'})
    self.assertEqual(self.inventory(),before);self.assertEqual(len(self.store.read(mode)['steps']),1)
 def test_source_changed_after_last_operation_cannot_be_delivered(self):
  self.start('workflow');first=self.store.begin_step('workflow','save_project',{});self.store.finish_step('workflow',first,{'ok':True})
  self.source.write_bytes(b'new user version');before=self.inventory()
  with self.assertRaisesRegex(ValueError,'revision_conflict'):self.store.delivered('workflow',{'engineering':'PASS'})
  self.assertEqual(self.inventory(),before);self.assertIsNone(self.store.read('workflow')['delivery'])
 def test_missing_and_link_replaced_source_are_conflicts_without_new_intent(self):
  self.start('workflow');self.source.unlink();before=self.inventory()
  with self.assertRaisesRegex(ValueError,'revision_conflict'):self.store.begin_step('workflow','edit',{})
  self.assertEqual(self.inventory(),before)
  other=self.root/'other.ecproj';other.write_bytes(b'original native project')
  try:self.source.symlink_to(other)
  except OSError:self.skipTest('symlink privilege unavailable')
  before=self.inventory()
  with self.assertRaisesRegex(ValueError,'revision_conflict'):self.store.begin_step('workflow','edit',{})
  self.assertEqual(self.inventory(),before);self.assertTrue(self.source.is_symlink())
 def test_unchanged_source_allows_operations_and_delivery(self):
  self.start('workflow');operation=self.store.begin_step('workflow','edit',{});self.store.finish_step('workflow',operation,{'ok':True})
  self.assertEqual(self.store.delivered('workflow',{})['state'],'review_ready')
 def test_managed_session_does_not_send_edit_after_external_save(self):
  self.start('commands');managed=module('managed');calls=[]
  class Session:
   def __init__(self,*args,**kwargs):pass
   def request(self,method,params):
    calls.append(params);return {'content':[{'type':'text','text':'{"ok":true}'}]}
   def close(self):pass
  original=managed.load
  def loader(name):return SimpleNamespace(Session=Session) if name=='mcp_session' else original(name)
  with patch.object(managed,'load',side_effect=loader),managed.Hooks(self.store,'commands').session(['unused-native']) as session:
   session.request('tools/call',{'name':'open_project','arguments':{}})
   self.source.write_bytes(b'user saved source');before=self.inventory()
   with self.assertRaisesRegex(ValueError,'revision_conflict'):
    session.request('tools/call',{'name':'execute_command','arguments':{'command':'layer.set'}})
   self.assertEqual(self.inventory(),before)
  self.assertEqual(len(calls),1);self.assertEqual(len(self.store.read('commands')['steps']),1)

import json
import os
import platform
import shutil
import sys

@unittest.skipUnless(os.environ.get('CRAFT_SOURCE_CONFLICT_LIVE')=='1','explicit native conflict opt-in')
class ManagedSourceConflictNativeTests(unittest.TestCase):
 def test_external_native_save_blocks_next_managed_edit_and_preserves_both_versions(self):
  root=Path(os.environ['CRAFT_SOURCE_CONFLICT_ROOT']);root.mkdir(parents=True,exist_ok=True)
  self.assertFalse(any(root.iterdir()),'preserve old acceptance tasks; select a fresh root')
  executable=Path(os.environ['CRAFT_SOURCE_CONFLICT_CLI']);lock=json.loads((HERE/'runtime.lock.json').read_text(encoding='utf-8'))
  key=module('platform_support').platform_key();native_sha=hashlib.sha256(executable.read_bytes()).hexdigest();self.assertEqual(native_sha,lock['artifacts'][key]['binarySha256'])
  managed=module('managed');sessions=module('mcp_session');commands=module('commands');source=root/'source.ecproj';copy=root/'original.ecproj';argv=[str(executable),'--empty','mcp']
  def call(session,name,args):return commands.parse_reply(session.request('tools/call',{'name':name,'arguments':args}))
  with sessions.Session(argv) as seed:
   call(seed,'execute_command',{'command':'comp.new','params':{'name':'Original','width':96,'height':64,'duration':1,'frameRate':12}})
   call(seed,'save_project',{'path':str(source)})
  shutil.copyfile(source,copy);original=source.read_bytes();tasks=module('task_store');store=tasks.Store(root/'state')
  store.create('conflict',plan={'nativeConflict':True},output=str(root/'delivery'),runtime_sha=native_sha,inputs={},source=str(source),mode='commands',authorization={});store.start('conflict')
  with managed.Hooks(store,'conflict').session(argv) as owner:
   call(owner,'open_project',{'path':str(source)})
   with sessions.Session(argv) as external:
    call(external,'open_project',{'path':str(source)})
    call(external,'execute_command',{'command':'comp.new','params':{'name':'User saved comp','width':96,'height':64,'duration':1,'frameRate':12}})
    call(external,'save_project',{'path':str(source)})
   user=source.read_bytes();self.assertNotEqual(original,user);before=store.read('conflict');state_bytes=store.path('conflict').read_bytes()
   with self.assertRaisesRegex(ValueError,'revision_conflict'):
    call(owner,'execute_command',{'command':'comp.new','params':{'name':'Must never execute','width':96,'height':64,'duration':1,'frameRate':12}})
   self.assertEqual(store.path('conflict').read_bytes(),state_bytes);self.assertEqual(len(before['steps']),1)
  self.assertEqual(source.read_bytes(),user);self.assertEqual(copy.read_bytes(),original);self.assertFalse((root/'delivery').exists())
  with sessions.Session(argv) as check:
   call(check,'open_project',{'path':str(source)});project=call(check,'get_project',{})
  self.assertNotIn('Must never execute',json.dumps(project));self.assertIn('User saved comp',json.dumps(project))
  state=store.read('conflict');report={'schema':'effectcraft-source-conflict-native/v1','status':'PASS','platform':key,'runtimeSha256':native_sha,'sourceBeforeSha256':hashlib.sha256(original).hexdigest(),'userSourceSha256':hashlib.sha256(user).hexdigest(),'steps':state['steps'],'originalCopyPreserved':True,'userSourcePreserved':True,'taskStatePreserved':True,'newOutputAbsent':True,'reopenedProject':project,'scope':'actual independent native CLI save after managed source open; not an interactive GUI or full desktop conflict matrix'}
  (root/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
