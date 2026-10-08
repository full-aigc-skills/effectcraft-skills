"""桌面原生版本、目标选择和时间状态变化必须在后续写入前停止旧计划。"""
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest

HERE=Path(__file__).resolve().parents[1]/'skills/effectcraft-use/scripts'
def load(name):
 path=HERE/(name+'.py');assert path.is_file(),'desktop revision guard is missing'
 spec=importlib.util.spec_from_file_location('guard_test_'+name,path);value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value

def reply(value):return {'content':[{'type':'text','text':json.dumps(value)}],'isError':False}
class Native:
 def __init__(self):self.token={'project':[0,None,None,[],[],False],'editor':{'times':{}}};self.calls=[];self.race=False;self.mutate_other=False
 def request(self,method,params):
  self.calls.append(params);name=params['name']
  if name=='run_script' and params['arguments']['name']=='readonly managed desktop token':return reply({'ok':True,'error':None,'result':self.token})
  if name=='run_script' and params['arguments']['name']=='atomic managed desktop command':
   expected=json.loads(re.search(r'var expected=(.*?);var before=',params['arguments']['code']).group(1))
   if self.race:self.token['project'][0]+=1
   if expected!=self.token:return reply({'ok':True,'error':None,'result':{'schema':'effectcraft-native-guard-result/v1','status':'conflict','current':self.token}})
   before=json.loads(json.dumps(self.token));self.token['project'][0]+=1;self.token['project'][4]=[1]
   return reply({'ok':True,'error':None,'result':{'schema':'effectcraft-native-guard-result/v1','status':'PASS','before':before,'after':self.token,'value':{'comp':1}}})
  if self.mutate_other:self.token['project'][0]+=1
  return reply({'query':True})
class DesktopRevisionGuardTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name);self.managed=load('managed');self.store=self.managed.load('task_store').Store(self.root/'state');self.store.create('task',plan={},output=str(self.root/'output'),runtime_sha='a'*64,inputs={},source=None,mode='desktop',authorization={});self.store.start('task');self.hooks=self.managed.Hooks(self.store,'task');self.native=Native()
 def guard(self):return load('desktop_revision').Guard(self.hooks,self.native.request)
 def call(self,guard,name='execute_command',arguments=None):return guard.request('tools/call',{'name':name,'arguments':arguments or {'command':'comp.new','params':{'name':'Owner'}}})
 def test_own_write_keeps_original_tool_return_type_and_receipt(self):
  guard=self.guard();self.assertEqual(load('commands').parse_reply(self.call(guard)),{'comp':1});self.assertEqual(self.store.read('task')['steps'][0]['state'],'succeeded');self.assertEqual(guard.record['token']['project'][0],1)
 def test_external_project_change_blocks_without_new_intent(self):
  guard=self.guard();self.call(guard);self.native.token['project'][0]+=1;before=self.store.path('task').read_bytes()
  with self.assertRaisesRegex(ValueError,'native_revision_conflict'):self.call(guard)
  self.assertEqual(self.store.path('task').read_bytes(),before)
 def test_editor_time_change_without_revision_change_is_a_conflict(self):
  guard=self.guard();self.call(guard);self.native.token['editor']['times']={'1':2};before=self.store.path('task').read_bytes()
  with self.assertRaisesRegex(ValueError,'native_revision_conflict'):self.call(guard)
  self.assertEqual(self.store.path('task').read_bytes(),before)
 def test_change_between_probe_and_atomic_call_retains_attempted_and_proof(self):
  guard=self.guard();self.call(guard);self.native.race=True
  with self.assertRaisesRegex(ValueError,'native_revision_conflict'):self.call(guard)
  steps=self.store.read('task')['steps'];self.assertEqual([s['state'] for s in steps],['succeeded','attempted']);self.assertTrue((self.store.path('task').parent/('desktop-conflict-'+steps[-1]['id']+'.json')).is_file())
 def test_unsupported_helper_is_refused_before_any_edit_or_intent(self):
  guard=self.guard();self.call(guard);self.native.mutate_other=True;before=self.store.path('task').read_bytes();count=len(self.native.calls)
  with self.assertRaisesRegex(ValueError,'unsupported_desktop_guard_tool'):self.call(guard,'unmapped_helper',{})
  self.assertEqual(self.store.path('task').read_bytes(),before);self.assertEqual(len(self.native.calls),count)
 def test_corrupt_guard_record_is_preserved_and_blocks_native_access(self):
  guard=self.guard();self.call(guard);guard.path.write_text('{broken',encoding='utf-8');count=len(self.native.calls)
  with self.assertRaisesRegex(ValueError,'desktop_revision_record_invalid'):self.call(guard)
  self.assertEqual(len(self.native.calls),count);self.assertEqual(guard.path.read_text(encoding='utf-8'),'{broken')
 def test_new_guard_cannot_reset_original_session_baseline(self):
  guard=self.guard();self.call(guard)
  with self.assertRaisesRegex(ValueError,'desktop_session_reconciliation_required'):self.call(self.guard())
 def test_nonempty_initial_native_project_is_not_silently_adopted(self):
  self.native.token['project'][4]=[1]
  with self.assertRaisesRegex(ValueError,'desktop_initial_state_conflict'):self.call(self.guard())

 def test_missing_initialized_record_does_not_reset_baseline(self):
  guard=self.guard();self.call(guard);guard.path.unlink();count=len(self.native.calls)
  with self.assertRaisesRegex(ValueError,'desktop_revision_record_invalid'):self.call(guard)
  self.assertEqual(len(self.native.calls),count)
 def test_previous_operations_without_record_do_not_create_new_session(self):
  operation=self.store.begin_step('task','old edit',{});self.store.finish_step('task',operation,{})
  with self.assertRaisesRegex(ValueError,'desktop_session_reconciliation_required'):self.call(self.guard())
  self.assertFalse(self.native.calls)
 def test_invalid_native_token_does_not_register_edit(self):
  self.native.token['project'][0]=True
  with self.assertRaisesRegex(ValueError,'desktop_native_token_invalid'):self.call(self.guard())
  self.assertFalse(self.store.read('task')['steps'])
 def test_response_loss_keeps_attempted_without_adopting_mutation(self):
  original=self.native.request
  def lost(method,params):
   result=original(method,params)
   if params.get('name')=='run_script' and params['arguments'].get('name')=='atomic managed desktop command':raise TimeoutError('lost reply')
   return result
  guard=load('desktop_revision').Guard(self.hooks,lost)
  with self.assertRaisesRegex(TimeoutError,'lost reply'):self.call(guard)
  self.assertEqual(self.store.read('task')['steps'][0]['state'],'attempted');self.assertEqual(guard.record['token']['project'][0],0);self.assertEqual(self.native.token['project'][0],1)


 def test_external_change_during_readonly_query_remains_unverified(self):
  guard=self.guard();self.call(guard);self.native.mutate_other=True
  with self.assertRaisesRegex(ValueError,'native_revision_unverified'):self.call(guard,'get_project',{})
  self.assertEqual(self.store.read('task')['steps'][-1]['state'],'attempted')


class DesktopRevisionFactoryTests(unittest.TestCase):
 setUp=DesktopRevisionGuardTests.setUp
 def test_managed_desktop_factory_routes_writes_through_atomic_guard(self):
  from unittest.mock import patch
  desktop=load('desktop_session');commands=desktop.load('commands');native=self.native
  class Owned:
   stopped=True;listener_verified=True
   def __init__(self,*args):pass
   def request(self,method,params):return native.request(method,params)
  def execute(plan,output,*args,**kwargs):
   output.mkdir();session=kwargs['session_factory'](['unused'])
   result=session.request('tools/call',{'name':'execute_command','arguments':{'command':'comp.new','params':{'name':'Owner'}}})
   return {'result':'PASS','steps':[{'state':'succeeded','result':commands.parse_reply(result)}]}
  with patch.object(desktop,'OwnedSession',Owned),patch.object(commands,'execute',side_effect=execute),patch.object(desktop,'load',side_effect=lambda name:commands if name=='commands' else load(name)):
   desktop.run({'schema':'craft-command-plan/v1','operations':[{'command':'comp.new','params':{'name':'Owner'}}]},self.root/'desktop output',task_hooks=self.hooks)
  self.assertTrue(any(item['name']=='run_script' and item['arguments'].get('name')=='atomic managed desktop command' for item in native.calls))
  self.assertTrue((self.store.path('task').parent/'desktop-revision.json').is_file())

class DesktopAtomicMappingContracts(unittest.TestCase):
 def test_missing_open_target_is_rejected_without_new_project(self):
  with self.assertRaisesRegex(ValueError,'desktop_tool_arguments_invalid'):load('desktop_revision').atomic_body('open_project',{})
 def test_empty_path_is_forwarded_for_native_validation(self):
  body=load('desktop_revision').atomic_body('open_project',{'path':''});self.assertIn('file.open',body);self.assertNotIn('file.newProject',body)
 def test_run_script_is_guarded_inside_original_interpreter(self):
  self.assertIn('eval(',load('desktop_revision').atomic_body('run_script',{'code':'1+2','name':'original script'}))
 def test_batch_json_string_matches_original_tool_contract(self):
  body=load('desktop_revision').atomic_body('batch',{'steps':'[{"command":"comp.new"}]'});self.assertIn('"steps":[{"command":"comp.new"}]',body)

import hashlib
import os

@unittest.skipUnless(os.environ.get('CRAFT_DESKTOP_REVISION_LIVE')=='1','explicit native desktop revision opt-in')
class DesktopRevisionNativeTests(unittest.TestCase):
 def setup_case(self,name):
  root=Path(os.environ['CRAFT_DESKTOP_REVISION_ROOT'])/name;root.mkdir(parents=True,exist_ok=True);self.assertFalse(any(root.iterdir()),'preserve previous acceptance tasks')
  cli=Path(os.environ['CRAFT_DESKTOP_REVISION_CLI']);lock=json.loads((HERE/'runtime.lock.json').read_text(encoding='utf-8'));key=load('platform_support').platform_key();self.assertEqual(hashlib.sha256(cli.read_bytes()).hexdigest(),lock['artifacts'][key]['binarySha256'])
  managed=load('managed');store=managed.load('task_store').Store(root/'state');store.create('native',plan={'case':name},output=str(root/'output'),runtime_sha=hashlib.sha256(cli.read_bytes()).hexdigest(),inputs={},source=None,mode='desktop',authorization={});store.start('native')
  return root,cli,store,managed.Hooks(store,'native')
 def call(self,guard,name,args):return load('commands').parse_reply(guard.request('tools/call',{'name':name,'arguments':args}))
 def test_actual_native_atomic_command_batch_save_reopen_and_media(self):
  root,cli,store,hooks=self.setup_case('headless mappings')
  with load('mcp_session').Session([str(cli),'--empty','mcp']) as session:
   guard=load('desktop_revision').Guard(hooks,session.request)
   comp=self.call(guard,'execute_command',{'command':'comp.new','params':{'name':'Owner','width':96,'height':64,'duration':1,'frameRate':12}});self.assertIn('comp',comp)
   layer=self.call(guard,'execute_command',{'command':'layer.newShape','params':{'kind':'rect','name':'Subject','size':[30,30],'position':[32,32],'fill':'#ff0000'}});self.assertIn('layer',layer)
   code='writeLn("Original script output"); ({answer:3})'
   expected=load('commands').parse_reply(session.request('tools/call',{'name':'run_script','arguments':{'code':code,'name':'original script'}}))
   actual=self.call(guard,'run_script',{'code':code,'name':'original script'});self.assertEqual(actual,expected)
   script=self.call(guard,'run_script',{'code':'app.run("layer.rename",'+json.dumps({'layer':layer['layer'],'name':'Script owned'})+')','name':'script edit'})
   self.assertTrue(script['ok']);self.assertIn('Script owned',json.dumps(self.call(guard,'get_layer',{'layer':layer['layer']})))
   batch=self.call(guard,'batch',{'steps':[{'command':'layer.rename','params':{'layer':layer['layer'],'name':'Renamed owner'}}]});self.assertIn('results',batch)
   saved=self.call(guard,'save_project',{'path':str(root/'project.ecproj')});self.assertEqual(saved['dirty'],False)
   self.call(guard,'render_frame',{'time':0.5,'max_side':96,'transparent':True,'inline':False,'path':str(root/'preview.png')})
   self.assertGreater((root/'preview.png').stat().st_size,0)
   reopened=self.call(guard,'open_project',{'path':str(root/'project.ecproj')});self.assertEqual(reopened['path'],str(root/'project.ecproj'))
   details=self.call(guard,'get_layer',{'layer':layer['layer']});self.assertIn('Renamed owner',json.dumps(details))
   self.call(guard,'get_comp',{})
   self.assertTrue(all(step['state']=='succeeded' for step in store.read('native')['steps']))
   store.delivered('native',{})
   proof={'schema':'effectcraft-native-desktop-revision/v1','status':'PASS','kind':'actual headless backend mapping contract','runtimeSha256':hashlib.sha256(cli.read_bytes()).hexdigest(),'operations':len(store.read('native')['steps']),'projectSha256':hashlib.sha256((root/'project.ecproj').read_bytes()).hexdigest(),'mediaSha256':hashlib.sha256((root/'preview.png').read_bytes()).hexdigest(),'guardToken':guard.record['token']}
   (root/'result.json').write_text(json.dumps(proof,indent=2)+'\n')
 def test_actual_native_race_rejects_stale_command_without_overwriting_foreign_comp(self):
  root,cli,store,hooks=self.setup_case('headless atomic race');inject=[False]
  with load('mcp_session').Session([str(cli),'--empty','mcp']) as session:
   def request(method,params):
    if inject[0] and params.get('name')=='run_script' and params['arguments'].get('name')=='atomic managed desktop command':
     inject[0]=False;session.request('tools/call',{'name':'execute_command','arguments':{'command':'comp.new','params':{'name':'Foreign change'}}})
    return session.request(method,params)
   guard=load('desktop_revision').Guard(hooks,request);self.call(guard,'execute_command',{'command':'comp.new','params':{'name':'Owner'}});inject[0]=True
   with self.assertRaisesRegex(ValueError,'native_revision_conflict'):self.call(guard,'execute_command',{'command':'comp.new','params':{'name':'Must never execute'}})
   actual=load('commands').parse_reply(session.request('tools/call',{'name':'get_project','arguments':{}}));self.assertIn('Foreign change',json.dumps(actual));self.assertNotIn('Must never execute',json.dumps(actual))
   self.assertEqual([s['state'] for s in store.read('native')['steps']],['succeeded','attempted'])
   (root/'result.json').write_text(json.dumps({'schema':'effectcraft-native-desktop-revision/v1','status':'PASS','kind':'actual headless atomic race','foreignChangePreserved':True,'staleCommandExecuted':False,'steps':[s['state'] for s in store.read('native')['steps']]},indent=2)+'\n')

 def test_actual_owned_desktop_rejects_external_memory_and_time_changes(self):
  import socket
  root,cli,store,hooks=self.setup_case('owned desktop conflicts');home=Path(os.environ['CRAFT_DESKTOP_REVISION_RUNTIME_HOME'])
  desktop=load('desktop').install(json.loads((HERE/'desktop.lock.json').read_text(encoding='utf-8')),home)
  output=root/'owned session';output.mkdir()
  with socket.socket() as probe:probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
  argv=load('commands').backend_argv(str(cli),output,'bridge','127.0.0.1:'+str(port))
  owned=load('desktop_session').OwnedSession(argv,desktop,'effectcraft',output,port)
  with owned:
   guard=load('desktop_revision').Guard(hooks,owned.request)
   self.call(guard,'execute_command',{'command':'comp.new','params':{'name':'Owner','width':96,'height':64,'duration':1,'frameRate':12}})
   layer=self.call(guard,'execute_command',{'command':'layer.newShape','params':{'kind':'rect','name':'Original owner layer','size':[30,30],'position':[32,32],'fill':'#ff0000'}})
   self.call(guard,'save_project',{'path':str(root/'owner.ecproj')})
   with load('mcp_session').Session(argv) as foreign:
    raw=lambda name,args:load('commands').parse_reply(foreign.request('tools/call',{'name':name,'arguments':args}))
    revision=guard.record['token']['project'][0];raw('execute_command',{'command':'time.set','params':{'time':0.25}})
    before=store.path('native').read_bytes()
    with self.assertRaisesRegex(ValueError,'native_revision_conflict'):self.call(guard,'execute_command',{'command':'layer.rename','params':{'layer':layer['layer'],'name':'Must never rename'}})
    self.assertEqual(store.path('native').read_bytes(),before);self.assertIn('Original owner layer',json.dumps(raw('get_layer',{'layer':layer['layer']})))
    current=guard.query();self.assertEqual(current['project'][0],revision);self.assertNotEqual(current['editor'],guard.record['token']['editor'])
    raw('execute_command',{'command':'comp.new','params':{'name':'External desktop change','width':96,'height':64,'duration':1,'frameRate':12}})
    raw('save_project',{'path':str(root/'external.ecproj')});user_hash=hashlib.sha256((root/'external.ecproj').read_bytes()).hexdigest()
    with self.assertRaisesRegex(ValueError,'native_revision_conflict'):self.call(guard,'execute_command',{'command':'comp.new','params':{'name':'Must never execute'}})
    self.assertEqual(store.path('native').read_bytes(),before);self.assertEqual(hashlib.sha256((root/'external.ecproj').read_bytes()).hexdigest(),user_hash)
    actual=raw('get_project',{});self.assertIn('External desktop change',json.dumps(actual));self.assertNotIn('Must never execute',json.dumps(actual))
  self.assertTrue(owned.stopped);self.assertTrue(owned.listener_verified)
  proof={'schema':'effectcraft-native-desktop-revision/v1','status':'PASS','kind':'owned signed desktop with independent control-bridge edits; no human click or model dispatch claim','desktopBinarySha256':desktop['binarySha256'],'runtimeSha256':hashlib.sha256(cli.read_bytes()).hexdigest(),'ownedProcessStopped':owned.stopped,'listenerVerified':owned.listener_verified,'timeOnlyConflictWithoutRevisionChange':True,'externalNativeProjectPreserved':True,'noNewManagedIntentAfterConflict':True,'managedOperations':len(store.read('native')['steps']),'foreignProjectSha256':user_hash}
  (root/'result.json').write_text(json.dumps(proof,indent=2)+'\n')
