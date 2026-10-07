"""摄像机首用须改变实际投影、重开一致，并保全非目标对象。"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def tree(p):return {str(f.relative_to(p)):digest(f) for f in p.rglob('*') if f.is_file()}
def prop(value,path):
 if isinstance(value,dict):
  if value.get('path')==path:return value
  for child in value.values():
   found=prop(child,path)
   if found is not None:return found
 elif isinstance(value,list):
  for child in value:
   found=prop(child,path)
   if found is not None:return found
 return None
@unittest.skipUnless(os.environ.get('CRAFT_CAMERA_FIRST_USE')=='1','requires public native runtime and macOS arm64')
class CameraSceneFirstUseTests(unittest.TestCase):
 def test_camera_render_reopen_revision_and_rejection(self):
  from PIL import Image,ImageChops
  source=Path(os.environ.get('CRAFT_INSTALLED_SKILL_ROOT',ROOT/'skills/effectcraft-cli-camera'))
  if os.environ.get('CRAFT_CAMERA_OUTPUT_ROOT'):
   root=Path(os.environ['CRAFT_CAMERA_OUTPUT_ROOT']);root.mkdir(parents=True,exist_ok=False)
  else:
   temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);root=Path(temporary.name)
  skill=root/'项目 空格/.agents/skills/effectcraft-cli-camera';shutil.copytree(source,skill,ignore=shutil.ignore_patterns('__pycache__'))
  before=tree(skill);source_before=tree(source);self.assertEqual({p.name for p in skill.parent.iterdir()},{skill.name})
  runtime=root/'runtime 空缓存';self.assertFalse(runtime.exists())
  spec=importlib.util.spec_from_file_location('camera_commands',skill/'scripts/commands.py');commands=importlib.util.module_from_spec(spec);spec.loader.exec_module(commands)
  env={k:v for k,v in os.environ.items() if not k.startswith('CRAFT_')};env['PATH']='/usr/bin:/bin';receipts={}
  def run(name,project=None,output=None):
   plan=json.loads((skill/f'examples/camera-scene-{name}.json').read_text());inputs={} if project is None else {'project':str(project)};commands.validate(plan,inputs)
   with patch.dict(os.environ,env,clear=True):result=commands.execute(plan,root/(output or name),runtime_home=runtime,inputs=inputs)
   self.assertEqual(result['result'],'PASS',result.get('error'));self.assertTrue(all(s['state']=='succeeded' for s in result['steps']));receipts[output or name]=result
   return {p['as']:s['result'] for p,s in zip(plan['operations'],result['steps']) if 'as' in p}
  def state(p):return {k:v for k,v in p.items() if k!='time'}
  def red_pixels(path):
   with Image.open(path) as im:
    pixels=im.convert('RGB');self.assertEqual(im.size,(128,96));self.assertEqual(pixels.getpixel((120,8)),(0,255,0))
    return {(x,y) for y in range(im.height) for x in range(im.width) if (lambda c:c[0]>30 and c[0]>1.5*c[1] and c[0]>1.5*c[2])(pixels.getpixel((x,y)))}
  def equal_images(a,b):
   with Image.open(a) as x,Image.open(b) as y:self.assertEqual(x.convert('RGBA').tobytes(),y.convert('RGBA').tobytes())
  created=run('create');self.assertEqual(created['renderer']['renderer'],'advanced3d');self.assertEqual(created['subject']['advanced3d'],True)
  self.assertEqual(created['dolly']['layer'],created['camera']['layer']);self.assertEqual(created['dolly']['position'],[64,48,-200]);self.assertEqual(created['dolly']['poi'],[64,48,50]);self.assertEqual(created['view']['view'],'activeCamera')
  self.assertEqual(created['view']['activeCameraLayer']['id'],created['camera']['layer']);self.assertTrue(any(l['id']==created['light']['layer'] for l in created['view']['lights']))
  pre=red_pixels(root/'create/before-dolly.png');post=red_pixels(root/'create/preview.png');self.assertGreater(len(post),len(pre));self.assertTrue(pre.issubset(post));self.assertGreater(len(pre),0)
  self.assertEqual(prop(created['cameraProperties'],'transform/position')['value'],[64,48,-200]);self.assertEqual(prop(created['cameraProperties'],'cameraOptions/focusDistance')['expression'],'length(transform.pointOfInterest, transform.position)')
  original=root/'create/project.ecproj';original_sha=digest(original);reopened=run('reopen',original)
  for name in ('cameraProperties','subjectProperties','lightProperties','controlProperties'):self.assertEqual(state(reopened[name]),state(created[name]))
  equal_images(root/'create/preview.png',root/'reopen/preview.png')
  revised=run('revise',original);self.assertEqual(revised['dolly']['position'],[64,48,-225]);self.assertEqual(revised['dolly']['poi'],[64,48,25])
  for name in ('subjectProperties','lightProperties','controlProperties'):self.assertEqual(state(revised[name]),state(created[name]))
  for path in ('cameraOptions/zoom','cameraOptions/focusDistance','cameraOptions/dof'):
   self.assertIsNotNone(prop(created['cameraProperties'],path));self.assertEqual(prop(revised['cameraProperties'],path),prop(created['cameraProperties'],path))
  revised_pixels=red_pixels(root/'revise/preview.png');self.assertGreater(len(revised_pixels),len(pre));self.assertLess(len(revised_pixels),len(post))
  again=run('reopen',root/'revise/project.ecproj','revised-reopened')
  for name in ('cameraProperties','subjectProperties','lightProperties','controlProperties'):self.assertEqual(state(again[name]),state(revised[name]))
  equal_images(root/'revise/preview.png',root/'revised-reopened/preview.png');self.assertEqual(digest(original),original_sha)
  failures=[]
  for name,command,params in [('empty','camera.dolly',{'amount':10}),('wrongCamera','camera.dolly',{'layer':'Control','amount':10}),('wrongSettings','layer.cameraSettings',{'layer':'Control','zoom':300})]:
   steps=[] if name=='empty' else [{'tool':'open_project','params':{'path':{'$ref':'project.path'}}},{'command':'view.set3DView','params':{'view':'activeCamera'}}]
   steps += [{'command':command,'params':params},{'tool':'save_project','params':{'path':{'$output':'forbidden.ecproj'}}}]
   with patch.dict(os.environ,env,clear=True):result=commands.execute({'schema':'craft-command-plan/v1','operations':steps},root/name,runtime_home=runtime,inputs={} if name=='empty' else {'project':str(original)})
   self.assertEqual(result['result'],'FAIL',result);self.assertFalse((root/name/'forbidden.ecproj').exists());self.assertFalse(any(s.get('tool')=='save_project' for s in result['steps']));self.assertEqual(digest(original),original_sha);failures.append({'case':name,'result':'FAIL','error':result['error']})
  self.assertEqual(tree(skill),before);self.assertEqual(tree(source),source_before)
  if os.environ.get('CRAFT_CAMERA_EVIDENCE_FILE'):
   evidence={'schema':'craft-camera-scene-first-use/v1','result':'PASS','skill':source.name,'runtimeSha256':receipts['create']['runtimeSha256'],'createPlanSha256':digest(skill/'examples/camera-scene-create.json'),'commands':sorted({s['command'] for s in receipts['create']['steps'] if s.get('command')}),'redPixelCounts':{'before':len(pre),'dolly':len(post),'revised':len(revised_pixels)},'originalProjectSha256':original_sha,'revisedProjectSha256':digest(root/'revise/project.ecproj'),'failures':failures,'checks':['single skill public cold install','native Advanced 3D renderer','returned camera and light identities','actual dolly projection growth','native reopen properties and pixel identity','targeted camera revision and unchanged material/light/control','preserved original project and skill files'],'unverified':['all 46 command contexts','camera solving and stereo/model rigs','GUI','DOF/shadows/creative quality'],'scope':'bounded self-contained static 3D camera scene, not full CM-001'}
   Path(os.environ['CRAFT_CAMERA_EVIDENCE_FILE']).write_text(json.dumps(evidence,indent=2)+'\n')
if __name__=='__main__':unittest.main()
