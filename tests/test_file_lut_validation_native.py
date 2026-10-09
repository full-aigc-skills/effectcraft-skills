"""从只读单技能公开命令／桌面入口验证文件LUT采样、搬迁和共享预算。"""
import json,os,platform,shutil,subprocess,unittest
from pathlib import Path
from test_workflow_artifact_lineage_native import ROOT,load,files,sha

@unittest.skipUnless(os.environ.get('CRAFT_FILE_LUT_LIVE')=='1','explicit native file LUT acceptance')
@unittest.skipUnless(platform.system()=='Darwin' and platform.machine()=='arm64','macOS arm64 native acceptance')
class FileLutNativeTests(unittest.TestCase):
 def test_commands(self):self.exercise('commands')
 def test_desktop(self):self.exercise('desktop')
 def exercise(self,mode):
  root=Path(os.environ['CRAFT_FILE_LUT_ROOT'])/mode;root.mkdir(parents=True);skill=root/'single readonly skill';shutil.copytree(ROOT/'skills/effectcraft-use',skill,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
  for f in skill.rglob('*'):f.chmod(0o555 if f.is_dir() else 0o444)
  skill.chmod(0o555);installed=files(skill);output=root/'delivery';state=root/'state';cube='LUT_3D_SIZE 2\n'+''.join(f'{b} {g} {r}\n' for b in range(2) for g in range(2) for r in range(2));source=root/'look.cube';source.write_text(cube)
  ops=[{'command':'comp.new','params':{'name':'File LUT sample','width':64,'height':48,'frameRate':2,'duration':1},'as':'composition'},
   {'command':'layer.newShape','params':{'kind':'rect','name':'Subject','size':[24,24],'position':[32,24],'fill':'#ff6600'},'as':'subject'},
   {'command':'effect.apply','params':{'effect':'ec.utility.applylut','layers':[{'$ref':'subject.layer'}]}},
   {'command':'prop.set','params':{'layer':{'$ref':'subject.layer'},'path':'effects/#1/lut','value':{'$ref':'look.path'}}},
   {'tool':'save_project','params':{'path':{'$output':'scene.ecproj'}}},
   {'tool':'render_frame','params':{'comp':{'$ref':'composition.comp'},'time':0,'max_side':0,'transparent':True,'inline':False,'path':{'$output':'frame.png'}}}]
  if mode=='desktop':ops.append({'tool':'ui_inspect','params':{}})
  plan=root/'plan.json';plan.write_text(json.dumps({'schema':'craft-command-plan/v1','operations':ops}));criteria=root/'criteria.json';criteria.write_text(json.dumps({'goal':'Verify only bound static file LUT sample pixels, preserve sources'}))
  env=dict(os.environ,CRAFT_RUNTIME_HOME=os.environ['CRAFT_FILE_LUT_RUNTIME'],PATH='/opt/homebrew/bin:/usr/bin:/bin');actions=[]
  def public(action,*args):
   result=subprocess.run(['/bin/sh',str(skill/'scripts/launch.sh'),'--state-root',str(state),action,*map(str,args)],cwd=root,env=env,capture_output=True,timeout=300);(root/(str(len(actions))+'-'+action+'.stdout')).write_bytes(result.stdout);(root/(str(len(actions))+'-'+action+'.stderr')).write_bytes(result.stderr)
   self.assertEqual(result.returncode,0,result.stdout.decode(errors='replace')+result.stderr.decode(errors='replace'));actions.append({'action':action,'returncode':result.returncode});return json.loads(result.stdout)
  preflight=public('plan','--mode',mode,'--plan',plan,'--output',output,'--input','look='+str(source));self.assertEqual(preflight['result'],'VALID');self.assertFalse(state.exists())
  started=public('run','--mode',mode,'--task','file-lut','--plan',plan,'--output',output,'--input','look='+str(source));self.assertEqual(started['state'],'review_ready')
  managed=load(skill/'scripts/managed.py');store=managed.load('task_store').Store(state);before=files(output);source_bytes=source.read_bytes();budget=managed.load('resource_budget');used0=budget.usage(store.read('file-lut')['resources'])
  report=public('review','--task','file-lut','--criteria',criteria)['report'];self.assertEqual(report['engineering']['status'],'PASS',report);self.assertEqual(report['technical']['status'],'PASS');self.assertEqual(report['resourceValidation']['status'],'PASS',report);self.assertEqual(report['dependencyClosure']['status'],'NOT_RUN');self.assertEqual(report['creative']['status'],'NOT_RUN')
  decoded=subprocess.run(['ffmpeg','-v','error','-i',str(output/'frame.png'),'-f','rawvideo','-pix_fmt','rgba','-'],capture_output=True,check=True).stdout;self.assertEqual(len(decoded),64*48*4);pixel=list(decoded[(32*64+32)*4:(32*64+32)*4+4]);self.assertGreater(pixel[2],pixel[0]);self.assertEqual(pixel[3],255)
  case=report['resourceValidation']['projects'][0];self.assertEqual(case['verifiedLuts'],1);self.assertEqual(case['verifiedFrames'],1);self.assertTrue(case['originalsPreserved']);self.assertTrue(case['nonTargetPropertiesPreserved'])
  used1=budget.usage(store.read('file-lut')['resources']);self.assertEqual(used1['frames'],used0['frames']+1);self.assertEqual(used1['decodedBytes'],used0['decodedBytes']+64*48*4)
  data=managed.load('command_delivery').document(store,'file-lut');moved=root/'moved whole output';shutil.copytree(output,moved);managed.load('command_artifact').validate(moved,data['artifactMap'])
  # 隔离副本必须只消费搬迁包；删除原生进程CWD中的原始输入后再验证。
  source.unlink();lock=managed.read(skill/'scripts/runtime.lock.json');key=managed.load('platform_support').platform_key();cli=Path(env['CRAFT_RUNTIME_HOME'])/'effectcraft'/lock['resolvedVersion']/lock['artifacts'][key]['binaryPath']
  moved_report=managed.load('resource_validation').commands(moved,data,str(cli));self.assertEqual(moved_report['status'],'PASS',moved_report);source.write_bytes(source_bytes)
  public('resume','--task','file-lut');self.assertEqual(files(output),before);self.assertEqual(files(skill),installed);self.assertEqual(source.read_bytes(),source_bytes)
  record=managed.read(store.lifecycle_path(store.read('file-lut')));self.assertEqual(record['status'],'stopped');self.assertEqual(record['returncode'],0)
  proof={'schema':'effectcraft-file-lut-native-acceptance/v1','mode':mode,'platform':'darwin-arm64','status':'PASS_COMPONENT','sourceSkillFiles':installed,'testSha256':sha(Path(__file__)),'publicReview':report['resourceValidation'],'movedReview':moved_report,'originalInputRemovedDuringMovedReview':True,'nativeProjectAndOutputsUnchanged':True,'installedResourcesUnchanged':True,'nativeWorkerStopped':True,'fileLutAppliedPixel':pixel,'reviewBudgetDelta':{'frames':used1['frames']-used0['frames'],'decodedBytes':used1['decodedBytes']-used0['decodedBytes']},'actions':actions,'coldInstall':'NOT_RUN','workflowNative':'NOT_RUN','creative':'NOT_RUN','hostDispatch':'NOT_RUN','fullV1':'NOT_RUN'}
  (root/'result.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
