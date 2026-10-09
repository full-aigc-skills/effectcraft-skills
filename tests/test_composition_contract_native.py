"""只读独立技能公开入口的原生合成时间合同；需显式启用。"""
import hashlib,json,os,platform,shutil,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
@unittest.skipUnless(os.environ.get('CRAFT_COMPOSITION_LIVE')=='1','explicit native composition opt-in')
@unittest.skipUnless(platform.system()=='Darwin' and platform.machine()=='arm64','macOS arm64 native acceptance')
class NativeCompositionTests(unittest.TestCase):
 def test_public_readonly_single_skill_and_work_area_shortcuts(self):
  root=Path(os.environ.get('CRAFT_COMPOSITION_ROOT') or tempfile.mkdtemp(prefix='composition contract '));root.mkdir(parents=True,exist_ok=True)
  self.assertFalse(any(root.iterdir()),'preserve evidence')
  skill=root/'single readonly skill';shutil.copytree(ROOT/'skills/effectcraft-use',skill,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
  for p in skill.rglob('*'):p.chmod(0o555 if p.is_dir() else 0o444)
  skill.chmod(0o555)
  def files(path):return {str(p.relative_to(path)):hashlib.sha256(p.read_bytes()).hexdigest() for p in path.rglob('*') if p.is_file()}
  before=files(skill);env=dict(os.environ,PATH='/opt/homebrew/bin:/usr/bin:/bin');state=root/'state';output=root/'delivery'
  plan={'document':{'name':'Seconds contract','width':64,'height':48,'frameRate':29.97,'duration':1},'workArea':[.1,.8],
   'operations':[{'command':'layer.newShape','params':{'kind':'rect','size':[20,20],'position':[32,24],'fill':'#ef5b36'}}],'frames':[0,.5]}
  planpath=root/'plan.json';planpath.write_text(json.dumps(plan));actions=[]
  def public(action,*args):
   r=subprocess.run(['/bin/sh',str(skill/'scripts/launch.sh'),'--state-root',str(state),action,*map(str,args)],env=env,cwd=root,capture_output=True,timeout=300)
   (root/(str(len(actions))+'-'+action+'.stdout')).write_bytes(r.stdout);(root/(str(len(actions))+'-'+action+'.stderr')).write_bytes(r.stderr)
   self.assertEqual(r.returncode,0,r.stdout.decode()+r.stderr.decode());actions.append(action);return json.loads(r.stdout)
  self.assertEqual(public('plan','--plan',planpath,'--output',output)['result'],'VALID')
  self.assertEqual(public('run','--task','composition-contract','--plan',planpath,'--output',output)['state'],'review_ready')
  native=json.loads((output/'native.json').read_text());contract=json.loads((output/'composition-validation.json').read_text())
  self.assertEqual(contract['status'],'PASS');self.assertEqual(contract['observed']['duration'],1.001);self.assertEqual(contract['observed']['workArea'],[.1,.8]);self.assertAlmostEqual(contract['observed']['frameRate'],30000/1001)
  from PIL import Image
  for p in output.glob('frame-*.png'):
   with Image.open(p) as img:img.load();self.assertEqual(img.size,(64,48));self.assertEqual(img.mode,'RGBA')
  criteria=root/'criteria.json';criteria.write_text(json.dumps({'goal':'composition technical contract'}))
  report=public('review','--task','composition-contract','--criteria',criteria)['report'];self.assertEqual(report['engineering']['status'],'PASS',report)
  saved=files(output);public('resume','--task','composition-contract');self.assertEqual(files(output),saved)
  # 原生通用命令继续支持当前时间快捷方式，工作区预期独立推导。
  second=dict(plan);second.pop('workArea');second['operations']=[{'command':'native.command','params':{'command':'time.set','params':{'time':.25}}},{'command':'native.command','params':{'command':'comp.workArea','params':{'set':'begin'}}}]
  planpath.write_text(json.dumps(second));secondout=root/'shortcut delivery';public('run','--task','composition-shortcut','--plan',planpath,'--output',secondout)
  shortcut=json.loads((secondout/'composition-validation.json').read_text());self.assertAlmostEqual(shortcut['observed']['workArea'][0],7*1001/30000);self.assertEqual(shortcut['observed']['workArea'][1],1.001)
  self.assertEqual(files(skill),before)
  (root/'result.json').write_text(json.dumps({'status':'PASS','actions':actions,'composition':contract,'shortcut':shortcut,'engineering':report['engineering']['status'],'creative':'NOT_RUN','userAcceptance':'NOT_RUN','readonlyPreserved':True,'files':saved},indent=2))
