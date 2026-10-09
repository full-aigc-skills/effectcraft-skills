"""合成计划的时间转换、工作区和渲染前配置门禁。"""
import importlib.util,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];SCRIPTS=ROOT/'skills/effectcraft-use/scripts'
def load(name):
 path=SCRIPTS/(name+'.py')
 if not path.exists():raise AssertionError('composition contract implementation missing')
 spec=importlib.util.spec_from_file_location('composition_test_'+name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
class CompositionContractTests(unittest.TestCase):
 def document(self):return {'name':'Composition','width':64,'height':48,'frameRate':24,'duration':1}
 def test_explicit_seconds_and_default_full_work_area(self):
  m=load('composition_contract');expected=m.document(self.document());self.assertEqual(expected,{'width':64,'height':48,'frameRate':24,'duration':1,'workArea':[0,1]})
  self.assertEqual(m.document(self.document(),[.25,.75])['workArea'],[.25,.75])
 def test_ntsc_and_half_frame_duration_use_native_tick_contract(self):
  m=load('composition_contract');d=self.document();d.update(frameRate=29.97,duration=1)
  expected=m.document(d);self.assertAlmostEqual(expected['frameRate'],30000/1001);self.assertEqual(expected['duration'],1.001)
  d.update(frameRate=24,duration=1/48);self.assertAlmostEqual(m.document(d)['duration'],1/24)
  d.update(duration=3/48);self.assertAlmostEqual(m.document(d)['duration'],1/24)
 def test_observed_difference_is_named_and_not_tolerated(self):
  m=load('composition_contract');expected=m.document(self.document())
  for field,value in [('width',65),('height',49),('frameRate',25),('duration',2),('workArea',[.25,1])]:
   with self.subTest(field=field),self.assertRaisesRegex(ValueError,'composition_config_mismatch.*'+field):m.verify(expected,dict(expected,**{field:value}))
  self.assertEqual(m.verify(expected,dict(expected,id=1,layers=[]))['status'],'PASS')
 def test_invalid_work_area_is_rejected_before_install(self):
  m=load('workflow')
  for area in (None,[],[1,0],[-1,1],[0,2],[0,.001],[True,1],[0,float('nan')]):
   with self.subTest(area=area),tempfile.TemporaryDirectory() as tmp:
    original=m.load_module
    def dependency(name):
     if name=='composition_contract':return original(name)
     raise AssertionError('installer must not start')
    with patch.object(m,'load_module',side_effect=dependency):
     with self.assertRaisesRegex(ValueError,'invalid_work_area'):m.execute({'document':self.document(),'operations':[],'workArea':area},Path(tmp)/'out')
 def test_workflow_settings_update_expected_contract(self):
  m=load('composition_contract');expected=m.document(self.document());changed=m.updated(expected,'comp.settings',{'frameRate':12,'duration':2},1)
  self.assertEqual(changed['frameRate'],12);self.assertEqual(changed['duration'],2);self.assertEqual(changed['workArea'],[0,2]);self.assertEqual(expected['duration'],1)
  self.assertEqual(m.updated(expected,'comp.settings',{'comp':2,'duration':2},1),expected)
 def test_workflow_mismatch_is_refused_before_save_or_render(self):
  m=load('workflow');calls=[]
  class Session:
   def __init__(self,*a,**kw):pass
   def __enter__(self):return self
   def __exit__(self,*a):pass
   def request(self,method,params):
    name=params['name'];args=params['arguments'];calls.append((name,args))
    if name=='execute_command':value={'comp':1} if args['command']=='comp.new' else {'start':0,'end':1}
    elif name=='get_comp':value={'id':1,'name':'Composition','width':64,'height':48,'frameRate':25,'duration':1,'workArea':[0,1],'layers':[]}
    elif name=='get_project':value={'items':[]}
    else:raise AssertionError('unverified composition reached '+name)
    return {'content':[{'type':'text','text':json.dumps(value)}]}
  original=m.load_module
  def dependency(name):
   if name=='bootstrap':return type('Bootstrap',(),{'install':staticmethod(lambda *a:{'executable':'fixture-cli','binarySha256':'a'*64})})
   if name=='mcp_session':return type('Mcp',(),{'Session':Session})
   return original(name)
  with tempfile.TemporaryDirectory() as tmp,patch.object(m,'load_module',side_effect=dependency):
   with self.assertRaisesRegex(ValueError,'composition_config_mismatch.*frameRate'):m.execute({'document':self.document(),'operations':[]},Path(tmp)/'out')
  self.assertNotIn('save_project',[name for name,args in calls]);self.assertNotIn('render_frame',[name for name,args in calls])

 def test_native_work_area_clamps_and_current_time_shortcuts_remain_compatible(self):
  m=load('composition_contract');expected=m.document(self.document())
  self.assertEqual(m.updated(expected,'comp.workArea',{'start':-2,'end':4},1)['workArea'],[0,1])
  self.assertEqual(m.updated(expected,'comp.workArea',{'set':'begin'},1,current_time=.25)['workArea'],[.25,1])
  self.assertAlmostEqual(m.updated(expected,'comp.workArea',{'set':'end'},1,current_time=.5)['workArea'][1],13/24)
 def test_reopened_configuration_drift_blocks_sampling(self):
  m=load('workflow');calls=[];reads=[]
  class Session:
   def __init__(self,*a,**kw):pass
   def __enter__(self):return self
   def __exit__(self,*a):pass
   def request(self,method,params):
    name=params['name'];args=params['arguments'];calls.append(name)
    if name=='execute_command':value={'comp':1} if args['command']=='comp.new' else {'start':0,'end':1}
    elif name=='get_comp':
     reads.append(True);value={'id':1,'name':'Composition','width':64,'height':48,'frameRate':24 if len(reads)==1 else 25,'duration':1,'workArea':[0,1],'layers':[]}
    elif name=='get_project':value={'items':[]}
    elif name=='save_project':Path(args['path']).write_bytes(b'fixture');value={}
    elif name=='open_project':value={}
    else:raise AssertionError('drift reached '+name)
    return {'content':[{'type':'text','text':json.dumps(value)}]}
  original=m.load_module
  def dependency(name):
   if name=='bootstrap':return type('Bootstrap',(),{'install':staticmethod(lambda *a:{'executable':'fixture-cli','binarySha256':'a'*64})})
   if name=='mcp_session':return type('Mcp',(),{'Session':Session})
   return original(name)
  with tempfile.TemporaryDirectory() as tmp,patch.object(m,'load_module',side_effect=dependency):
   with self.assertRaisesRegex(ValueError,'composition_config_mismatch.*frameRate'):m.execute({'document':self.document(),'operations':[]},Path(tmp)/'out')
  self.assertIn('open_project',calls);self.assertNotIn('render_frame',calls)

 def test_pinned_native_current_time_uses_active_composition_ticks(self):
  m=load('composition_contract');self.assertEqual(m.current_time({'state':{'active_comp':1,'times':{'1':63504000000}}}),.25)
  self.assertEqual(m.current_time({'state':{'time':.25}}),.25)
  with self.assertRaisesRegex(ValueError,'composition_current_time_unavailable'):m.current_time({'state':{}})
