"""原生资源登记只使用保存内容；字体名称不能冒充字体字节。"""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import test_workflow_artifact_lineage as workflows
load=workflows.load
import test_command_artifact_lineage as commands

CUBE='LUT_3D_SIZE 2\n'+''.join(f'{r} {g} {b}\n' for b in range(2) for g in range(2) for r in range(2))
def prop(match,value,**kw):return dict(node='Prop',match=match,value=value,**kw)
def group(children,kind=None):return {'node':'Group','match':'root','kind':kind or {'kind':'Plain'},'children':children}
def native(children):return {'schema':1,'items':{'1':{'id':1,'kind':{'type':'Comp','layers':[{'id':2,'props':group(children)}]}}}}
def text(font,style='Regular'):return {'t':'Text','v':{'text':'ABC','font':font,'style':style}}
def lut(value):return group([prop('lut',{'t':'Str','v':value})],{'kind':'Effect','effect':'ec.utility.applylut'})
class NativeResourcesTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name);self.path=self.root/'scene.ecproj'
 def scan(self,data):
  self.path.write_text(json.dumps(data));module=load('artifact_lineage')
  self.assertTrue((Path(module.__file__).parent/'native_resources.py').is_file(),'native font/LUT discovery missing')
  return load('native_resources').inspect(self.root,'scene.ecproj')
 def test_fonts_cover_base_runs_keyframes_without_invented_file_hash(self):
  value=text('Inter');value['v']['runs']=[{'len':1,'style':{'font':'Noto Serif','style':'Bold'}}]
  d=self.scan(native([prop('sourceText',value,keys=[{'time':10,'value':text('JetBrains Mono')}])]))
  self.assertEqual({r['font'] for r in d['fonts']},{'Inter','Noto Serif','JetBrains Mono'})
  self.assertEqual(d['closure']['status'],'NOT_RUN');self.assertTrue(all(r['status']=='NOT_RUN' and 'sha256' not in r for r in d['fonts']))
  self.assertEqual(load('native_resources').public_dependencies(d),[])
 def test_inline_lut_binds_actual_bytes_without_format_fidelity_claim(self):
  d=self.scan(native([lut(CUBE)]));r=d['luts'][0]
  self.assertEqual(r['sha256'],hashlib.sha256(CUBE.encode()).hexdigest());self.assertTrue(r['packaged'])
  self.assertEqual(r['source'],'inline');self.assertEqual(r['fidelity'],'NOT_RUN')
  public=load('native_resources').public_dependencies(d);self.assertEqual(public[0]['kind'],'lut');self.assertEqual(public[0]['assetRef']['sha256'],r['sha256'])
 def test_packaged_file_is_content_bound_but_runtime_path_resolution_unknown(self):
  asset=self.root/'look.cube';asset.write_text(CUBE);d=self.scan(native([lut('look.cube')]))
  self.assertEqual(d['luts'][0]['path'],'look.cube');self.assertEqual(d['luts'][0]['sha256'],hashlib.sha256(asset.read_bytes()).hexdigest())
  self.assertTrue(d['luts'][0]['packaged']);self.assertEqual(d['luts'][0]['runtimeResolution'],'NOT_RUN');self.assertEqual(d['closure']['status'],'NOT_RUN')
 def test_external_missing_and_symlink_luts_never_read_or_claim_packaged(self):
  external=self.root.parent/(self.root.name+' secret.cube');external.write_text(CUBE);self.addCleanup(external.unlink)
  for value in (str(external),'missing.cube','../'+external.name):
   with self.subTest(value=value):
    d=self.scan(native([lut(value)]));r=d['luts'][0];self.assertFalse(r['packaged']);self.assertNotIn('sha256',r);self.assertEqual(load('native_resources').public_dependencies(d),[])
  target=self.root/'linked.cube'
  try:target.symlink_to(external)
  except OSError:return
  d=self.scan(native([lut('linked.cube')]));self.assertFalse(d['luts'][0]['packaged'])
 def test_lumetri_nested_inputs_and_disabled_keyframed_luts_are_not_omitted(self):
  effects=group([group([prop('inputLutFile',{'t':'Str','v':CUBE})]),group([prop('lookFile',{'t':'Str','v':''},keys=[{'time':1,'value':{'t':'Str','v':'missing.cube'}}])])],{'kind':'Effect','effect':'ec.color.lumetri'})
  effects['enabled']=False;d=self.scan(native([effects]));self.assertEqual(len(d['luts']),2)
 def test_dynamic_values_are_unknown_even_with_current_self_contained_value(self):
  value=lut(CUBE);value['children'][0]['expr']={'enabled':True,'text':'readExternal()'}
  d=self.scan(native([value]));self.assertEqual(len(d['dynamic']),1);self.assertEqual(d['closure']['status'],'NOT_RUN')
 def test_unrelated_string_named_lut_is_not_misclassified(self):
  d=self.scan(native([prop('lut',{'t':'Str','v':CUBE})]));self.assertEqual(d['luts'],[])
 def test_native_schema_and_tree_limits_fail_closed(self):
  for value in ({'schema':2,'items':{}},native([{'node':'Group','children':'bad'}])):
   with self.assertRaisesRegex(ValueError,'native_resources'):self.scan(value)
  deep=group([])
  for _ in range(70):deep=group([deep])
  with self.assertRaisesRegex(ValueError,'native_resources'):self.scan(native([deep]))
 def test_workflow_inventory_public_lut_and_review_are_bound_and_legacy_readable(self):
  f=workflows.WorkflowArtifactLineageTests();f.setUp();self.addCleanup(f.doCleanups)
  (f.root/'project.ecproj').write_text(json.dumps(native([lut(CUBE),prop('sourceText',text('Inter'))])))
  m=f.finish();self.assertIn('nativeResources',m,'workflow native resource contract missing')
  self.assertEqual(m['artifact']['dependencies'][0]['kind'],'lut')
  report=f.review.inspect_delivery(f.root);self.assertEqual(report['nativeResources'],m['nativeResources']);self.assertEqual(report['dependencyClosure']['status'],'NOT_RUN');self.assertEqual(report['technical']['status'],'PASS')
  m['nativeResources']['fonts']=[];f.save(m);self.assertEqual(f.review.inspect_delivery(f.root)['technical']['status'],'FAIL')
 def test_commands_map_resources_version_and_old_absent_extension(self):
  f=commands.CommandArtifactLineageTests();f.setUp();self.addCleanup(f.doCleanups);f.fixture.save();f.fixture.frame()
  path=f.output/'scene.ecproj';d=json.loads(path.read_text());d['items']['999']={'id':999,'kind':{'type':'Comp','layers':[{'id':3,'props':group([lut(CUBE)])}]}};path.write_text(json.dumps(d))
  # 单元夹具以保存后原生字节为观察，不声称原生快照符合此追加层。
  after=f.store.path('case').parent/'command-delivery/observations/0.json'
  self.assertTrue(after.is_file());row=json.loads(after.read_text());row['sha256']=f.delivery.sha(path);f.tasks.atomic_json(after,row)
  proof,data,m=f.finish();self.assertIn('nativeResources',m,'command resource mapping missing');self.assertEqual(m['artifacts'][0]['dependencies'][0]['kind'],'lut')
  adapter=f.delivery.load('command_artifact');self.assertEqual(adapter.validate(f.output,m),m['artifacts'])
  forged=copy.deepcopy(m);forged['nativeResources'][0]['luts']=[]
  with self.assertRaisesRegex(ValueError,'command_artifact'):adapter.validate(f.output,forged)

 def test_legacy_workflow_extension_absent_preserves_identity_without_upgrade(self):
  f=workflows.WorkflowArtifactLineageTests();f.setUp();self.addCleanup(f.doCleanups)
  m=f.finish();m.pop('nativeResources');adapter=load('artifact_lineage');m['artifact']=adapter.record(f.root,m,m['artifactBinding']);f.save(m)
  before=(f.root/'manifest.json').read_bytes();identity=copy.deepcopy(m['artifact']);adapter.verify(f.root,m)
  self.assertEqual(adapter.validate_source(f.root)['artifact'],identity);self.assertNotIn('nativeResources',m);self.assertEqual((f.root/'manifest.json').read_bytes(),before)
 def test_legacy_command_mapping_absent_extension_preserves_identity(self):
  f=commands.CommandArtifactLineageTests();f.setUp();self.addCleanup(f.doCleanups);f.fixture.save();f.fixture.frame()
  _,_,m=f.finish();adapter=f.delivery.load('command_artifact');old=adapter.compile_map(f.output,m['files'],m['binding'],m['contexts'],resources=False)
  before=copy.deepcopy(old);self.assertNotIn('nativeResources',old);self.assertEqual(adapter.validate(f.output,old),old['artifacts']);self.assertEqual(old,before)
