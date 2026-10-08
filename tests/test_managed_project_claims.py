"""不同账本也不能绕过同一原生工程的活跃或未知占用。"""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parents[1]/'skills/effectcraft-use/scripts'
def load_store():
 spec=importlib.util.spec_from_file_location('shared_project_store',HERE/'task_store.py');value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
class ManagedProjectClaimTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name);self.source=self.root/'project.ecproj';self.source.write_bytes(b'project')
  self.module=load_store();original=self.module.load
  def loader(name):
   value=original(name)
   if name=='project_claims':value.root=lambda:self.root/'shared claims'
   return value
  self.patch=patch.object(self.module,'load',side_effect=loader);self.patch.start();self.addCleanup(self.patch.stop)
  self.first=self.module.Store(self.root/'first');self.second=self.module.Store(self.root/'second')
 def create(self,store,task,source=None):
  return store.create(task,plan={'name':task},output=str(self.root/task),runtime_sha='a'*64,inputs={},source=str(source or self.source),mode='workflow',authorization={})
 def test_different_state_roots_cannot_run_the_same_source(self):
  self.create(self.first,'one');self.first.start('one')
  with self.assertRaisesRegex(ValueError,'project_resource_busy'):self.create(self.second,'two')
  self.assertFalse(self.second.path('two').exists())
 def test_unknown_owner_blocks_new_task_and_output_in_another_root(self):
  self.create(self.first,'one');self.first.start('one');self.first.begin_step('one','edit',{});self.first.fail('one','lost',unknown=True)
  with self.assertRaisesRegex(ValueError,'project_resource_busy'):self.create(self.second,'two')
  self.assertEqual(self.first.read('one')['state'],'reconciling');self.assertFalse(self.second.path('two').exists())
 def test_hardlink_source_alias_is_also_busy(self):
  alias=self.root/'alias.ecproj'
  try:os.link(self.source,alias)
  except OSError:self.skipTest('hardlinks unavailable')
  self.create(self.first,'one')
  with self.assertRaisesRegex(ValueError,'project_resource_busy'):self.create(self.second,'two',alias)
 def test_replacing_source_inode_does_not_evade_path_claim(self):
  self.create(self.first,'one');replacement=self.root/'replacement';replacement.write_bytes(b'user updated project');replacement.replace(self.source)
  with self.assertRaisesRegex(ValueError,'project_resource_busy'):self.create(self.second,'two')
  self.assertEqual(self.source.read_bytes(),b'user updated project')
 def test_missing_owner_state_blocks_without_recreating_it(self):
  self.create(self.first,'one');self.first.path('one').unlink()
  with self.assertRaisesRegex(ValueError,'project_claim_owner_unconfirmed'):self.create(self.second,'two')
  self.assertFalse(self.first.path('one').exists());self.assertFalse(self.second.path('two').exists())
 def test_verified_terminal_owner_allows_new_distinct_task(self):
  self.create(self.first,'one');self.first.start('one');op=self.first.begin_step('one','edit',{});self.first.finish_step('one',op,{});self.first.delivered('one',{})
  self.assertEqual(self.create(self.second,'two')['state'],'planned')
 def test_corrupt_claim_blocks_next_operation_without_new_intent(self):
  self.create(self.first,'one');self.first.start('one');paths=list((self.root/'shared claims').glob('*.json'));self.assertTrue(paths)
  paths[0].write_text('{broken',encoding='utf-8');before=self.first.path('one').read_bytes()
  with self.assertRaisesRegex(ValueError,'project_claim_invalid'):self.first.begin_step('one','edit',{})
  self.assertEqual(self.first.path('one').read_bytes(),before);self.assertEqual(paths[0].read_text(encoding='utf-8'),'{broken')

 def test_reused_inode_with_distinct_creation_generation_does_not_steal_old_claim(self):
  from types import SimpleNamespace
  old=self.source.resolve();new=(self.root/'different-project.ecproj').resolve();new.write_bytes(b'new project')
  stat=Path.stat
  def identity_stat(path,*args,**kwargs):
   result=stat(path,*args,**kwargs)
   if path in (old,new):
    fields={name:getattr(result,name) for name in dir(result) if name.startswith('st_')}
    fields.update(st_dev=123,st_ino=456)
    return SimpleNamespace(**fields)
   return result
  original=self.module.load
  def loader(name):
   value=original(name)
   if name=='project_claims':
    # 确定性重现两文件跨代际复用同一编号；不模拟认领器本身。
    value.creation_identity=lambda path,info: {'seconds':1 if Path(path)==old else 2,'nanoseconds':0}
   return value
  with patch.object(self.module,'load',side_effect=loader),patch.object(Path,'stat',identity_stat):
   self.create(self.first,'one');self.first.path('one').unlink()
   before={p.name:p.read_bytes() for p in (self.root/'shared claims').glob('*.json')}
   state=self.create(self.second,'two',new)
   self.assertEqual(state['state'],'planned')
   for name,data in before.items():self.assertEqual((self.root/'shared claims'/name).read_bytes(),data)


 def legacy(self):
  claims=self.module.load('project_claims');state=self.first.read('one');old_keys=claims.keys(self.source,legacy=True)
  old_record=claims.read_claim(state['projectClaims'][0]['key']);nonce=old_record['nonce']
  for row in state['projectClaims']:(claims.root()/(row['key']+'.json')).unlink()
  state.pop('projectClaimIdentity');state['projectClaims']=[{'key':key,'nonce':nonce} for key in old_keys]
  for key in old_keys:
   record=dict(old_record,key=key);self.module.atomic_json(claims.root()/(key+'.json'),record)
  self.first.save(state)
 def test_legacy_task_keeps_original_inode_binding_without_migration(self):
  self.create(self.first,'one');self.legacy();self.first.start('one')
  operation=self.first.begin_step('one','edit',{});self.first.finish_step('one',operation,{})
  self.assertNotIn('projectClaimIdentity',self.first.read('one'))
 def test_legacy_unknown_claim_is_preserved_and_blocks_new_hardlink_task(self):
  self.create(self.first,'one');self.legacy();self.first.path('one').unlink();alias=self.root/'alias'
  try:os.link(self.source,alias)
  except OSError:self.skipTest('hardlink unavailable')
  before={p.name:p.read_bytes() for p in (self.root/'shared claims').glob('*.json')}
  with self.assertRaisesRegex(ValueError,'project_claim_owner_unconfirmed'):self.create(self.second,'two',alias)
  self.assertEqual(before,{p.name:p.read_bytes() for p in (self.root/'shared claims').glob('*.json')})


 def test_two_real_processes_cannot_both_acquire_the_project(self):
  import subprocess,sys,time
  code=r'''
import importlib.util,json,sys,time
from pathlib import Path
here,root,name=Path(sys.argv[1]),Path(sys.argv[2]),sys.argv[3]
spec=importlib.util.spec_from_file_location('concurrent_store',here/'task_store.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);original=module.load
# 测试仅隔离内部协调目录；公开入口没有此覆盖参数。
def load(name):
 value=original(name)
 if name=='project_claims':value.root=lambda:root/'shared claims'
 return value
module.load=load
(root/(name+'.ready')).write_text('ready')
deadline=time.monotonic()+15
while not (root/'go').exists():
 if time.monotonic()>deadline:raise RuntimeError('test gate timed out')
 time.sleep(.01)
store=module.Store(root/name)
try:
 store.create(name,plan={'name':name},output=str(root/(name+'-output')),runtime_sha='a'*64,inputs={},source=str(root/'project.ecproj'),mode='workflow',authorization={});result='acquired'
except ValueError as error:result=str(error)
print(json.dumps({'name':name,'result':result}))
'''
  children=[subprocess.Popen([sys.executable,'-I','-B','-c',code,str(HERE),str(self.root),name],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8') for name in ('racer-a','racer-b')]
  try:
   deadline=time.monotonic()+15
   while not all((self.root/(name+'.ready')).exists() for name in ('racer-a','racer-b')):
    if time.monotonic()>deadline:self.fail('child ready gate timed out')
    time.sleep(.01)
   (self.root/'go').write_text('go',encoding='utf-8');results=[]
   for child in children:
    out,err=child.communicate(timeout=20);self.assertEqual(child.returncode,0,err);results.append(json.loads(out)['result'])
   self.assertEqual(results.count('acquired'),1);self.assertEqual(sum(r.startswith('project_resource_busy') for r in results),1)
   self.assertEqual(sum((self.root/name/'tasks'/name/'state.json').exists() for name in ('racer-a','racer-b')),1)
  finally:
   for child in children:
    if child.poll() is None:child.kill();child.wait(timeout=10)

 def test_same_bytes_replacement_changes_bound_file_object(self):
  self.create(self.first,'one');self.first.start('one');replacement=self.root/'new-inode';replacement.write_bytes(b'project');replacement.replace(self.source)
  before=self.first.path('one').read_bytes()
  with self.assertRaisesRegex(ValueError,'revision_conflict'):self.first.begin_step('one','edit',{})
  self.assertEqual(self.first.path('one').read_bytes(),before)
 def test_missing_owner_claim_reference_is_not_released_even_if_terminal(self):
  self.create(self.first,'one');self.first.start('one');self.first.delivered('one',{})
  state=self.first.read('one');state.pop('projectClaims');self.first.save(state)
  before=self.first.path('one').read_bytes()
  with self.assertRaisesRegex(ValueError,'project_claim_owner_unconfirmed'):self.create(self.second,'two')
  self.assertEqual(self.first.path('one').read_bytes(),before)

@unittest.skipUnless(os.environ.get('CRAFT_PROJECT_CLAIM_LIVE')=='1','explicit native project claim opt-in')
class ManagedProjectClaimNativeTests(unittest.TestCase):
 def test_native_owner_preserved_when_other_ledger_competes(self):
  import hashlib,shutil
  root=Path(os.environ['CRAFT_PROJECT_CLAIM_ROOT']);root.mkdir(parents=True,exist_ok=True);self.assertFalse(any(root.iterdir()))
  executable=Path(os.environ['CRAFT_PROJECT_CLAIM_CLI']);module=load_store();session_module=module.load('mcp_session');commands=module.load('commands');managed=module.load('managed')
  lock=json.loads((HERE/'runtime.lock.json').read_text(encoding='utf-8'));key=module.load('platform_support').platform_key();runtime_sha=hashlib.sha256(executable.read_bytes()).hexdigest();self.assertEqual(runtime_sha,lock['artifacts'][key]['binarySha256'])
  source=root/'source.ecproj';argv=[str(executable),'--empty','mcp']
  def call(session,name,args):return commands.parse_reply(session.request('tools/call',{'name':name,'arguments':args}))
  with session_module.Session(argv) as seed:
   call(seed,'execute_command',{'command':'comp.new','params':{'name':'Original','width':96,'height':64,'duration':1,'frameRate':12}});call(seed,'save_project',{'path':str(source)})
  original=source.read_bytes();one=module.Store(root/'ledger one');two=module.Store(root/'ledger two')
  def create(store,task):return store.create(task,plan={'name':task},output=str(root/task),runtime_sha=runtime_sha,inputs={},source=str(source),mode='commands',authorization={})
  create(one,'owner');one.start('owner')
  with managed.Hooks(one,'owner').session(argv) as session:
   call(session,'open_project',{'path':str(source)});before=one.path('owner').read_bytes()
   with self.assertRaisesRegex(ValueError,'project_resource_busy'):create(two,'competitor')
   self.assertEqual(one.path('owner').read_bytes(),before);self.assertFalse(two.path('competitor').exists())
   call(session,'execute_command',{'command':'comp.new','params':{'name':'Owner continues','width':96,'height':64,'duration':1,'frameRate':12}})
   call(session,'save_project',{'path':str(root/'owner-result.ecproj')})
  one.delivered('owner',{'projectSha256':hashlib.sha256((root/'owner-result.ecproj').read_bytes()).hexdigest()});self.assertEqual(source.read_bytes(),original)
  next_state=create(two,'next-owner');self.assertEqual(next_state['state'],'planned')
  with session_module.Session(argv) as check:
   call(check,'open_project',{'path':str(root/'owner-result.ecproj')});project=call(check,'get_project',{})
  self.assertIn('Owner continues',json.dumps(project));self.assertNotIn('competitor',json.dumps(project))
  report={'schema':'effectcraft-shared-project-native/v1','status':'PASS','platform':key,'runtimeSha256':runtime_sha,'sourcePreserved':True,'loserStateAbsent':True,'ownerStatePreservedDuringConflict':True,'ownerCompletedOperations':len(one.read('owner')['steps']),'terminalOwnerReleasedToNewLedger':True,'sourceSha256':hashlib.sha256(original).hexdigest(),'savedProjectSha256':hashlib.sha256((root/'owner-result.ecproj').read_bytes()).hexdigest(),'scope':'new task user-level source claims; actual native owner continues and saved result reopens; no interactive GUI or legacy-runtime coordination claim'}
  (root/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
