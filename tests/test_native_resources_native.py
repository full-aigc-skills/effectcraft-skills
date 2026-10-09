"""实际安装副本三种公开模式：字体声明、内联LUT、迁移及像素。"""
import copy
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import unittest
from test_workflow_artifact_lineage_native import ROOT,load,files,sha
from test_native_resources import CUBE

@unittest.skipUnless(os.environ.get('CRAFT_NATIVE_RESOURCES_LIVE')=='1','explicit native resource acceptance')
@unittest.skipUnless(platform.system()=='Darwin' and platform.machine()=='arm64','macOS arm64 native acceptance')
class NativeResourceAcceptance(unittest.TestCase):
 def test_workflow(self):self.exercise('workflow')
 def test_commands(self):self.exercise('commands')
 def test_desktop(self):self.exercise('desktop')
 def exercise(self,mode):
  base=Path(os.environ['CRAFT_NATIVE_RESOURCES_ROOT']);root=base/mode;root.mkdir(parents=True);self.assertFalse(any(root.iterdir()))
  skill=root/'single readonly skill';shutil.copytree(ROOT/'skills/effectcraft-use',skill,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
  for f in skill.rglob('*'):f.chmod(0o555 if f.is_dir() else 0o444)
  skill.chmod(0o555);installed=files(skill);env=dict(os.environ,CRAFT_RUNTIME_HOME=os.environ['CRAFT_NATIVE_RESOURCES_RUNTIME'],PATH='/opt/homebrew/bin:/usr/bin:/bin');state=root/'state';output=root/'delivery';actions=[]
  cube='LUT_3D_SIZE 2\n'+''.join(f'{b} {g} {r}\n' for b in range(2) for g in range(2) for r in range(2))
  ops=[{'command':'layer.newShape','params':{'kind':'rect','name':'Subject','size':[24,24],'position':[32,24],'fill':'#ff6600'},'as':'subject'},
   {'command':'effect.apply','params':{'effect':'ec.utility.applylut','layers':[{'$ref':'subject.layer'}]}},
   {'command':'prop.set','params':{'layer':{'$ref':'subject.layer'},'path':'effects/#1/lut','value':cube}},
   {'command':'layer.newText','params':{'text':'Ab','font':'Inter','style':'Regular','size':8,'position':[4,8]},'as':'title'}]
  doc={'name':'Native resource proof','width':64,'height':48,'frameRate':2,'duration':1}
  if mode=='workflow':
   ops[1]={'command':'native.command','params':{'command':'effect.apply','params':ops[1]['params']}}
   plan={'document':doc,'operations':ops,'frames':[0]}
  else:
   plan={'schema':'craft-command-plan/v1','operations':[{'command':'comp.new','params':doc,'as':'composition'}]+ops+[
    {'tool':'save_project','params':{'path':{'$output':'scene.ecproj'}}},
    {'tool':'render_frame','params':{'comp':{'$ref':'composition.comp'},'time':0,'max_side':0,'transparent':True,'inline':False,'path':{'$output':'frame.png'}}}]}
   if mode=='desktop':plan['operations'].append({'tool':'ui_inspect','params':{}})
  planfile=root/'plan.json';planfile.write_text(json.dumps(plan));criteria=root/'criteria.json';criteria.write_text(json.dumps({'goal':'Native static resource transport; creative and font fidelity remain unverified'}))
  def public(action,*args):
   result=subprocess.run(['/bin/sh',str(skill/'scripts/launch.sh'),'--state-root',str(state),action,*map(str,args)],env=env,capture_output=True,timeout=300,cwd=root)
   (root/(str(len(actions))+'-'+action+'.stdout')).write_bytes(result.stdout);(root/(str(len(actions))+'-'+action+'.stderr')).write_bytes(result.stderr)
   self.assertEqual(result.returncode,0,result.stdout.decode(errors='replace')+result.stderr.decode(errors='replace'));actions.append({'action':action,'returncode':result.returncode});return json.loads(result.stdout)
  self.assertEqual(public('plan','--mode',mode,'--plan',planfile,'--output',output)['result'],'VALID');self.assertFalse(state.exists())
  current=public('run','--mode',mode,'--task','resources','--plan',planfile,'--output',output);self.assertEqual(current['state'],'review_ready')
  managed=load(skill/'scripts/managed.py');store=managed.load('task_store').Store(state)
  if mode=='workflow':
   manifest=managed.read(output/'manifest.json');inventory=manifest['nativeResources'];artifacts=[manifest['artifact']];frame=output/'frame-0000.png'
  else:
   data=managed.load('command_delivery').document(store,'resources');mapping=data['artifactMap'];inventory=mapping['nativeResources'][0];artifacts=mapping['artifacts'];frame=output/'frame.png'
  self.assertEqual({x['font'] for x in inventory['fonts']},{'Inter'});self.assertTrue(all(x['status']=='NOT_RUN' and 'sha256' not in x for x in inventory['fonts']))
  self.assertEqual(len(inventory['luts']),1);lut=inventory['luts'][0];self.assertTrue(lut['packaged']);self.assertEqual(lut['source'],'inline');self.assertEqual(lut['sha256'],managed.load('native_resources').sha(cube.encode()))
  self.assertEqual(inventory['closure']['status'],'NOT_RUN');self.assertEqual(inventory['fidelity'],'NOT_RUN')
  self.assertEqual(artifacts[0]['dependencies'][0]['assetRef']['sha256'],lut['sha256']);self.assertEqual(artifacts[0]['dependencies'][0]['kind'],'lut')
  import jsonschema
  owner=json.loads((ROOT/'tests/fixtures/craft-artifact-v1.schema.json').read_text())
  for a in artifacts:jsonschema.Draft202012Validator(owner).validate(a)
  report=public('review','--task','resources','--criteria',criteria)['report'];self.assertEqual(report['engineering']['status'],'PASS');self.assertEqual(report['technical']['status'],'PASS');self.assertEqual(report['dependencyClosure']['status'],'NOT_RUN');self.assertEqual(report['creative']['status'],'NOT_RUN')
  decoded=subprocess.run(['ffmpeg','-v','error','-i',str(frame),'-f','rawvideo','-pix_fmt','rgba','-'],capture_output=True,check=True).stdout;self.assertEqual(len(decoded),64*48*4);pixel=list(decoded[(32*64+32)*4:(32*64+32)*4+4]);self.assertGreater(pixel[2],pixel[0]);self.assertEqual(pixel[3],255)
  before=files(output);receipts=files(store.path('resources').parent/'receipts');moved=root/'moved whole output';shutil.copytree(output,moved)
  if mode=='workflow':managed.load('artifact_lineage').verify(moved,manifest)
  else:self.assertEqual(managed.load('command_artifact').validate(moved,mapping),artifacts)
  runtime=managed.load('runtime_binding').resolve(store,'resources');key=managed.load('platform_support').platform_key();lock=managed.read(skill/'scripts/runtime.lock.json');cli=Path(runtime['runtimeHome'])/'effectcraft'/lock['resolvedVersion']/lock['artifacts'][key]['binaryPath']
  # 命令交付使用隔离副本重开；工作流已由公开review重开，移动验证保留原协议。
  if mode!='workflow':self.assertEqual(managed.load('command_delivery').verify_projects(moved,data['projects'],str(cli))['status'],'PASS')
  public('resume','--task','resources');self.assertEqual(files(output),before);self.assertEqual(files(store.path('resources').parent/'receipts'),receipts);self.assertEqual(files(skill),installed)
  lifecycle=managed.read(store.lifecycle_path(store.read('resources')));self.assertEqual(lifecycle['status'],'stopped');self.assertEqual(lifecycle['returncode'],0)
  proof={'schema':'effectcraft-native-resources-acceptance/v1','mode':mode,'platform':'darwin-arm64','status':'PASS_COMPONENT','sourceSkillFiles':installed,'testSha256':sha(Path(__file__)),'inventory':inventory,'publicArtifacts':artifacts,'engineering':'PASS','technical':'PASS','pixel':pixel,'inlineLutPixelChangeVerified':True,'ownerSchema':'PASS','movedPackageVerified':True,'outputsAndReceiptsPreserved':True,'installedResourcesPreserved':True,'workerStopped':True,'actions':actions,'fontBinaryAndFallback':'NOT_RUN','creative':'NOT_RUN','userAcceptance':'NOT_RUN','hostDispatch':'NOT_RUN','cacheReused':True,'fullV1':'NOT_RUN'}
  (root/'result.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
