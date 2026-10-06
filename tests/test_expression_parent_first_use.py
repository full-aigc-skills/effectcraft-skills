"""公开原生表达式与父子图层：独立安装、动态像素、源返工与循环父级拒绝。"""
import hashlib,json,os,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def hashes(root):return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
class RecipeContract(unittest.TestCase):
 def test_every_skill_contains_command_bound_recipe_and_guide(self):
  rows={r['id']:r for r in json.loads((ROOT/'skills/effectcraft-use/references/command-coverage.json').read_text())['commands']}
  for skill in (ROOT/'skills').iterdir():
   if not (skill/'SKILL.md').is_file():continue
   for name in ['expression-parent-create.json','expression-parent-revise.json']:
    plan=json.loads((skill/'examples'/name).read_text())
    for op in plan['operations']:
     command=op['params']['command'] if op['command']=='native.command' else op['command'];self.assertIn(command,rows);self.assertIn('examples/'+name,rows[command].get('usageRecipes',[]))
   self.assertTrue((skill/'references/expression-parent.md').is_file());self.assertIn('references/expression-parent.md',(skill/'SKILL.md').read_text())
@unittest.skipUnless(os.environ.get('CRAFT_EFFECT_EXPRESSION_FIRST_USE')=='1','explicit public native opt-in')
class ExpressionNativeFirstUse(unittest.TestCase):
 def test_parent_expression_pixels_source_revision_and_cycle_rejection(self):
  from PIL import Image
  original=Path(os.environ.get('CRAFT_EFFECT_EXPRESSION_SKILL',ROOT/'skills/effectcraft-cli-expressions'));before=hashes(original)
  with tempfile.TemporaryDirectory() as temporary:
   root=Path(temporary);skill=root/'.agents/skills'/original.name;shutil.copytree(original,skill,ignore=shutil.ignore_patterns('__pycache__'));copied=hashes(skill);runtime=root/'empty-runtime';self.assertFalse(runtime.exists())
   def run(plan,destination,source=None,success=True):
    p=root/(destination.name+'.json');p.write_text(json.dumps(plan));args=[sys.executable,'-I','-B',str(skill/'scripts/workflow.py'),str(p),'--output',str(destination),'--runtime-home',str(runtime)]
    if source:args+=['--source',str(source)]
    r=subprocess.run(args,capture_output=True,text=True,env=dict(os.environ,PATH='/usr/bin:/bin'),timeout=600)
    if not success:self.assertNotEqual(r.returncode,0);self.assertIn('cycle',r.stdout+r.stderr);self.assertFalse((destination/'manifest.json').exists());return
    self.assertEqual(r.returncode,0,r.stdout+r.stderr);m=json.loads((destination/'manifest.json').read_text());self.assertTrue((destination/'project.ecproj').is_file());self.assertTrue((destination/'exchange-loss.json').is_file())
    for f,sha in m['files'].items():self.assertEqual(hashlib.sha256((destination/f).read_bytes()).hexdigest(),sha)
    return m,json.loads((destination/'native.json').read_text())
   plan=json.loads((skill/'examples/expression-parent-create.json').read_text());first=root/'original';m,model=run(plan,first);old=hashes(first);target=str(m['bindings']['target']['layer']);parent=str(m['bindings']['parent']['layer']);control=str(m['bindings']['control']['layer']);layers=model['layers'];self.assertEqual(layers[target]['parent'],int(parent))
   def pixels(folder):
    values=[]
    for i in range(2):
     with Image.open(folder/f'frame-{i:04d}.png') as image:
      image=image.convert('RGBA');self.assertEqual(image.size,(128,64));values.append((image.getpixel((32,32)),image.crop((84,20,108,44)).tobytes()))
    return values
   first_pixels=pixels(first);self.assertAlmostEqual(first_pixels[0][0][3],128,delta=2);self.assertAlmostEqual(first_pixels[1][0][3],191,delta=2);self.assertEqual(first_pixels[0][1],first_pixels[1][1])
   revision=json.loads((skill/'examples/expression-parent-revise.json').read_text());revision['expectedProjectSha256']=m['files']['project.ecproj'];second=root/'revised';new,new_model=run(revision,second,first);second_pixels=pixels(second);self.assertAlmostEqual(second_pixels[0][0][3],64,delta=2);self.assertAlmostEqual(second_pixels[1][0][3],128,delta=2)
   self.assertEqual(set(layers),set(new_model['layers']));self.assertEqual(layers[parent],new_model['layers'][parent]);self.assertEqual(layers[control],new_model['layers'][control]);self.assertEqual(model['composition'],new_model['composition']);self.assertEqual(layers[target]['parent'],new_model['layers'][target]['parent'])
   self.assertEqual(first_pixels[0][1],second_pixels[0][1]);self.assertEqual(first_pixels[1][1],second_pixels[1][1]);self.assertEqual(old,hashes(first));self.assertNotEqual(m['files']['project.ecproj'],new['files']['project.ecproj'])
   bad=json.loads(json.dumps(revision));bad['operations']=[{'command':'layer.select','params':{'layers':[{'$ref':'parent.layer'}],'add':False,'toggle':False}},{'command':'native.command','params':{'command':'layer.setParent','params':{'layers':[{'$ref':'parent.layer'}],'parent':{'$ref':'target.layer'}}}}];run(bad,root/'rejected',first,False);self.assertEqual(old,hashes(first))
   self.assertEqual(before,hashes(original));self.assertEqual(copied,hashes(skill));self.assertFalse(list(skill.rglob('*.pyc')))
   if os.environ.get('CRAFT_EFFECT_EXPRESSION_REPORT'):
    Path(os.environ['CRAFT_EFFECT_EXPRESSION_REPORT']).write_text(json.dumps({'schema':'effectcraft-expression-parent-first-use/v1','result':'PASS','skill':original.name,'nativeProjectSha256':m['files']['project.ecproj'],'revisionSha256':new['files']['project.ecproj'],'timeSeconds':[0,.5],'initialAlpha':[p[0][3] for p in first_pixels],'revisedAlpha':[p[0][3] for p in second_pixels],'parentControlCompositionPreserved':True,'controlPixelsUnchanged':True,'originalDeliveryPreserved':True,'cycleRejected':True,'skillIdentityUnchanged':True,'scope':'native parent/opacity expression sample, not exhaustive640 commands/GUI/fullV1'},indent=2)+'\n')
