"""文件LUT重关联验收必须执行真实MCP返回契约和像素比较，保全原件。"""
import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from test_native_resources import load,native,lut,CUBE
from test_managed_command_delivery import png

class FileLutValidationTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
  (self.root/'look.cube').write_text(CUBE);(self.root/'scene.ecproj').write_text(json.dumps(native([lut('look.cube')])))
  (self.root/'frame.png').write_bytes(png());self.inventory=load('native_resources').inspect(self.root,'scene.ecproj')
  self.frames=[{'path':'frame.png','sha256':load('task_store').file_sha(self.root/'frame.png'),'composition':{'id':1,'width':2,'height':2},'seconds':0,'requestedAlpha':True,'maxSide':0}]
  self.before=self.files();self.calls=[];self.render=png();self.mutate=None;self.before_render=None
 def files(self):return {p.name:p.read_bytes() for p in self.root.iterdir() if p.is_file()}
 def invoke(self,inventory=None,frames=None,timeout=10):
  path=Path(load('native_resources').__file__).with_name('resource_validation.py');self.assertTrue(path.exists(),'file LUT native transport validation missing')
  test=self
  class Session:
   def __enter__(self):return self
   def __exit__(self,*args):pass
   def request(self,method,params):
    name=params['name'];args=params['arguments'];test.calls.append((name,copy.deepcopy(args)))
    if name=='open_project':
     target=Path(args['path']);test.assertFalse(target.is_relative_to(test.root));d=json.loads(target.read_text());value=d['items']['1']['kind']['layers'][0]['props']['children'][0]['children'][0]['value']['v']
     test.assertTrue(Path(value).is_absolute());test.assertFalse(Path(value).is_relative_to(test.root));test.assertEqual(Path(value).read_text(),CUBE)
     if test.mutate:test.mutate(target)
     result={'opened':args['path']}
    elif name=='render_frame':Path(args['path']).write_bytes(test.render);result={'path':args['path']}
    else:raise AssertionError(name)
    return {'content':[{'type':'text','text':json.dumps(result)}]}
  return load('resource_validation').verify(self.root,'scene.ecproj',inventory or self.inventory,self.frames if frames is None else frames,'native',timeout=timeout,session_factory=lambda *a,**kw:Session(),before_render=self.before_render)
 def test_isolated_file_lut_and_frame_pixels_match_without_touching_originals(self):
  result=self.invoke();self.assertEqual(result['status'],'PASS');self.assertEqual(result['verifiedFrames'],1);self.assertEqual(result['verifiedLuts'],1);self.assertTrue(result['originalsPreserved']);self.assertEqual(self.files(),self.before)
 def test_different_decoded_pixels_fail_and_preserve_sources(self):
  self.render=png(1,1);result=self.invoke();self.assertEqual(result['status'],'FAIL');self.assertIn('render_mismatch',result['reason']);self.assertEqual(self.files(),self.before)
 def test_missing_frame_evidence_is_not_run_without_engine(self):
  result=self.invoke(frames=[]);self.assertEqual(result['status'],'NOT_RUN');self.assertEqual(self.calls,[])
 def test_unknown_file_lut_is_not_run_and_never_read_outside_package(self):
  (self.root/'scene.ecproj').write_text(json.dumps(native([lut('../secret.cube')])));self.inventory=load('native_resources').inspect(self.root,'scene.ecproj')
  result=self.invoke();self.assertEqual(result['status'],'NOT_RUN');self.assertEqual(self.calls,[])
 def test_stale_inventory_or_changed_media_is_rejected_before_engine(self):
  forged=copy.deepcopy(self.inventory);forged['luts'][0]['sha256']='a'*64
  self.assertEqual(self.invoke(inventory=forged)['status'],'FAIL');self.assertEqual(self.calls,[])
  (self.root/'frame.png').write_bytes(png(1,1));self.assertEqual(self.invoke()['status'],'FAIL');self.assertEqual(self.calls,[])
 def test_engine_mutating_its_copy_is_detected_and_original_kept(self):
  self.mutate=lambda target:target.write_text('{}');result=self.invoke();self.assertEqual(result['status'],'FAIL');self.assertIn('snapshot_changed',result['reason']);self.assertEqual(self.files(),self.before)
 def test_exhausted_family_budget_is_not_run_before_native_render(self):
  def denied(size):raise ValueError('resource_budget_exceeded')
  self.before_render=denied;result=self.invoke();self.assertEqual(result['status'],'NOT_RUN');self.assertEqual([name for name,_ in self.calls],['open_project']);self.assertEqual(self.files(),self.before)
 def test_deadline_and_frame_budget_do_not_start_engine(self):
  self.assertEqual(self.invoke(timeout=-1)['status'],'NOT_RUN');self.assertEqual(self.invoke(frames=self.frames*9)['status'],'NOT_RUN');self.assertEqual(self.calls,[])

class FileLutRoutingTests(unittest.TestCase):
 def test_commands_review_calls_transport_validation_and_failure_closes_engineering_gate(self):
  import test_command_artifact_lineage as fixtures
  f=fixtures.CommandArtifactLineageTests();f.setUp();self.addCleanup(f.doCleanups);f.fixture.save();f.fixture.frame();_,data,_=f.finish();module=f.delivery
  bootstrap=module.load('bootstrap');platform=module.load('platform_support');expected=module.read(Path(module.__file__).with_name('runtime.lock.json'))['artifacts'][platform.platform_key()]
  def routed(name):
   if name=='bootstrap':return type('Bootstrap',(),{'inspect_install':staticmethod(lambda *a,**k:{'executable':'native'})})
   if name=='resource_validation':return type('Resource',(),{'commands':staticmethod(lambda *a,**k:{'status':'FAIL','reason':'file_lut_render_mismatch'}),'budget_hook':staticmethod(lambda *a,**k:None)})
   return original(name)
  original=module.load
  with patch.object(module,'load',side_effect=routed),patch.object(module,'verify_projects',return_value={'status':'PASS','fresh':True}):report=module.inspect(f.store,'case','runtime')
  self.assertIn('resourceValidation',report,'public commands review must route LUT validation')
  self.assertEqual(report['resourceValidation']['status'],'FAIL');self.assertEqual(report['engineering']['status'],'FAIL')
 def test_commands_unverified_lut_validation_closes_engineering_gate(self):
  import test_command_artifact_lineage as fixtures
  f=fixtures.CommandArtifactLineageTests();f.setUp();self.addCleanup(f.doCleanups);f.fixture.save();f.fixture.frame();_,data,_=f.finish();module=f.delivery
  bootstrap=module.load('bootstrap');platform=module.load('platform_support');expected=module.read(Path(module.__file__).with_name('runtime.lock.json'))['artifacts'][platform.platform_key()]
  def routed(name):
   if name=='bootstrap':return type('Bootstrap',(),{'inspect_install':staticmethod(lambda *a,**k:{'executable':'native'})})
   if name=='resource_validation':return type('Resource',(),{'commands':staticmethod(lambda *a,**k:{'status':'NOT_RUN','projects':[{'status':'NOT_RUN'}]}),'budget_hook':staticmethod(lambda *a,**k:None)})
   return original(name)
  original=module.load
  with patch.object(module,'load',side_effect=routed),patch.object(module,'verify_projects',return_value={'status':'PASS','fresh':True}):report=module.inspect(f.store,'case','runtime')
  self.assertIn('resourceValidation',report,'public commands review must route LUT validation')
  self.assertEqual(report['resourceValidation']['status'],'NOT_RUN');self.assertEqual(report['engineering']['status'],'NOT_RUN')
 def test_workflow_engineering_routes_transport_failure_and_preserves_original(self):
  import test_managed_engineering_review as fixtures
  f=fixtures.EngineeringReviewTests();f.setUp();self.addCleanup(f.doCleanups)
  manifest=f.quality.read(f.root/'manifest.json');manifest['nativeResources']={};(f.root/'manifest.json').write_text(json.dumps(manifest))
  before={p.name:p.read_bytes() for p in f.root.iterdir()};original=f.module.load
  def routed(name):
   if name=='resource_validation':return type('Resource',(),{'workflow':staticmethod(lambda *a,**k:{'status':'FAIL','reason':'file_lut_render_mismatch'})})
   return original(name)
  with patch.object(f.module,'load',side_effect=routed):report=f.verify()
  self.assertIn('resourceValidation',report,'public workflow engineering must route LUT validation');self.assertEqual(report['status'],'FAIL');self.assertEqual(report['resourceValidation']['status'],'FAIL');self.assertEqual({p.name:p.read_bytes() for p in f.root.iterdir()},before)

class FileLutBudgetTests(unittest.TestCase):
 def test_review_render_attempts_are_durable_extra_cost_and_idempotent(self):
  import test_managed_command_delivery as fixtures
  f=fixtures.CommandDeliveryTests();f.setUp();self.addCleanup(f.doCleanups);budget=f.module.load('resource_budget')
  self.assertTrue(hasattr(budget,'reserve_review'),'native review renders require durable family budget')
  budget.reserve_review(f.store,'case','a'*64,16);budget.reserve_review(f.store,'case','a'*64,16)
  value=f.store.read('case')['resources'];self.assertEqual(budget.usage(value)['frames'],1);self.assertEqual(budget.usage(value)['decodedBytes'],16)
  budget.reserve_review(f.store,'case','b'*64,32);self.assertEqual(budget.usage(f.store.read('case')['resources'])['frames'],2)
  with self.assertRaisesRegex(ValueError,'resource_attempt_conflict'):budget.reserve_review(f.store,'case','a'*64,32)
 def test_review_budget_failure_is_retained_before_any_render(self):
  import test_managed_command_delivery as fixtures
  f=fixtures.CommandDeliveryTests();f.setUp();self.addCleanup(f.doCleanups);budget=f.module.load('resource_budget')
  self.assertTrue(hasattr(budget,'reserve_review'),'native review budget missing')
  with self.assertRaisesRegex(ValueError,'resource_budget_exceeded'):budget.reserve_review(f.store,'case','a'*64,budget.LIMITS['decodedBytes']+1)
  value=f.store.read('case')['resources'];self.assertGreater(budget.usage(value)['decodedBytes'],budget.LIMITS['decodedBytes'])

class FileLutRelocationTests(unittest.TestCase):
 def test_moved_absolute_lut_uses_bound_relative_content_without_old_location(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)/'original';root.mkdir();(root/'look.cube').write_text(CUBE);(root/'scene.ecproj').write_text(json.dumps(native([lut(str(root/'look.cube'))])))
   module=load('native_resources');inventory=module.inspect(root,'scene.ecproj')
   import shutil
   moved=Path(tmp)/'moved';shutil.copytree(root,moved);shutil.rmtree(root)
   self.assertEqual(module.inspect(moved,'scene.ecproj',declared=inventory),inventory)
 def test_relocation_cannot_borrow_wrong_project_declaration_or_content(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'look.cube').write_text(CUBE);(root/'scene.ecproj').write_text(json.dumps(native([lut('/missing/original/look.cube')])))
   module=load('native_resources');inventory=module.inspect(root,'scene.ecproj');resource=inventory['luts'][0];resource.update(packaged=True,path='look.cube',sha256='a'*64,bytes=len(CUBE));resource.pop('missingReason')
   with self.assertRaisesRegex(ValueError,'native_resources'):module.inspect(root,'scene.ecproj',declared=inventory)
