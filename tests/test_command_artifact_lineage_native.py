"""真实commands／自有桌面：多工程、多合成、素材和相对产物映射。"""
import copy
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
import unittest
from test_workflow_artifact_lineage_native import ROOT,load,files,sha
from test_managed_command_delivery import png

@unittest.skipUnless(os.environ.get('CRAFT_COMMAND_ARTIFACT_LIVE')=='1','explicit native command artifact mapping opt-in')
@unittest.skipUnless(platform.system()=='Darwin' and platform.machine()=='arm64','macOS arm64 native acceptance')
class CommandArtifactNativeTests(unittest.TestCase):
    def test_commands_multiple_projects_and_moved_media(self):self.exercise('commands')
    def test_desktop_multiple_projects_and_moved_media(self):self.exercise('desktop')
    def exercise(self,mode):
        base=Path(os.environ.get('CRAFT_COMMAND_ARTIFACT_ROOT') or tempfile.mkdtemp(prefix='command artifact native '));root=base/mode;root.mkdir(parents=True,exist_ok=True)
        self.assertFalse(any(root.iterdir()),'preserve previous evidence')
        skill=root/'single readonly skill';shutil.copytree(ROOT/'skills/effectcraft-use',skill,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        for p in skill.rglob('*'):p.chmod(0o555 if p.is_dir() else 0o444)
        skill.chmod(0o555);installed=files(skill)
        runtime=Path(os.environ['CRAFT_COMMAND_ARTIFACT_RUNTIME_HOME']);env=dict(os.environ,CRAFT_RUNTIME_HOME=str(runtime),PATH='/opt/homebrew/bin:/usr/bin:/bin')
        self.assertIn('CRAFT_PYTHON_HOME',env)
        asset=root/'real input asset.png';asset.write_bytes(png(16,16))
        plan={'schema':'craft-command-plan/v1','operations':[
            {'command':'comp.new','params':{'name':'Early comp','width':64,'height':48,'frameRate':2,'duration':1},'as':'first'},
            {'command':'file.import','params':{'paths':[{'$ref':'fixture.path'}],'addToComp':True}},
            {'command':'layer.newShape','params':{'kind':'rect','name':'Early subject','size':[24,24],'position':[32,24],'fill':'#ff6600'}},
            {'tool':'save_project','params':{'path':{'$output':'early.ecproj'}}},
            {'tool':'render_frame','params':{'comp':{'$ref':'first.comp'},'time':0,'max_side':0,'transparent':True,'inline':False,'path':{'$output':'early.png'}}},
            {'command':'comp.new','params':{'name':'Late comp','width':32,'height':32,'frameRate':3,'duration':1},'as':'second'},
            {'command':'layer.newShape','params':{'kind':'rect','name':'Late subject','size':[12,12],'position':[16,16],'fill':'#22aa88'}},
            {'tool':'save_project','params':{'path':{'$output':'late.ecproj'}}},
            {'tool':'render_frame','params':{'comp':{'$ref':'second.comp'},'time':0,'max_side':0,'transparent':True,'inline':False,'path':{'$output':'late.png'}}}]}
        if mode=='desktop':plan['operations'].append({'tool':'ui_inspect','params':{}})
        planfile=root/'plan.json';planfile.write_text(json.dumps(plan));output=root/'delivery';state=root/'state';actions=[]
        def public(action,*args,ok=True):
            r=subprocess.run(['/bin/sh',str(skill/'scripts/launch.sh'),'--state-root',str(state),action,*map(str,args)],env=env,cwd=root,capture_output=True,timeout=420)
            label=str(len(actions))+'-'+action;(root/(label+'.stdout')).write_bytes(r.stdout);(root/(label+'.stderr')).write_bytes(r.stderr)
            self.assertEqual(r.returncode==0,ok,r.stdout.decode(errors='replace')+r.stderr.decode(errors='replace'))
            actions.append({'action':action,'returncode':r.returncode});return json.loads(r.stdout)
        checked=public('plan','--mode',mode,'--plan',planfile,'--output',output,'--input','fixture='+str(asset));self.assertEqual(checked['result'],'VALID');self.assertFalse(state.exists())
        started=public('run','--mode',mode,'--task','multi-project','--plan',planfile,'--output',output,'--input','fixture='+str(asset));self.assertEqual(started['state'],'review_ready')
        managed=load(skill/'scripts/managed.py');store=managed.load('task_store').Store(state);delivery=managed.load('command_delivery');data=delivery.document(store,'multi-project');mapping=data['artifactMap']
        adapter=managed.load('command_artifact');self.assertEqual(started['delivery']['commandArtifacts'],adapter.reference(mapping))
        artifacts={a['location']:a for a in mapping['artifacts']};self.assertEqual(set(artifacts),{'early.ecproj','late.ecproj'})
        self.assertEqual(artifacts['early.ecproj']['technicalMetadata']['width'],64);self.assertNotIn('width',artifacts['late.ecproj']['technicalMetadata'])
        self.assertEqual([a['location'] for a in artifacts['early.ecproj']['renditions']],['early.png']);self.assertEqual([a['location'] for a in artifacts['late.ecproj']['renditions']],['late.png'])
        self.assertEqual(len(data['projects'][0]['snapshot']['compositions']),1);self.assertEqual(len(data['projects'][1]['snapshot']['compositions']),2)
        self.assertEqual(mapping['unmatchedFrames'],[]);self.assertEqual(mapping['unreviewed'],[]);self.assertEqual(mapping['exchangeLoss'],'NOT_RUN')
        for a in artifacts.values():
            self.assertEqual(a['producerTaskId'],'multi-project');self.assertEqual(a['sha256'],sha(output/a['location']));self.assertEqual(len(a['dependencies']),1)
            self.assertEqual(a['dependencies'][0]['assetRef']['sha256'],sha(asset));self.assertTrue(a['dependencies'][0]['packaged']);self.assertIsNone(a['lossReportRef'])
        try:import jsonschema
        except ImportError:self.fail('native owner-schema validation requires local jsonschema')
        raw=(ROOT/'tests/fixtures/craft-artifact-v1.schema.json').read_bytes()
        self.assertEqual(sha(ROOT/'tests/fixtures/craft-artifact-v1.schema.json'),'c3385db540db71fccfdb049f79f05a9adba55ec008958579eab6fac46dd6ea5d')
        for a in artifacts.values():jsonschema.Draft202012Validator(json.loads(raw)).validate(a)
        self.assertNotIn(str(root),json.dumps(mapping['artifacts']))
        before=files(output);receipts=files(store.path('multi-project').parent/'receipts');criteria=root/'criteria.json';criteria.write_text(json.dumps({'goal':'Native multiple-project mapping; visual acceptance not evaluated'}))
        reviewed=public('review','--task','multi-project','--criteria',criteria)['report'];self.assertEqual(reviewed['engineering']['status'],'PASS',reviewed);self.assertEqual(reviewed['technical']['status'],'PASS',reviewed)
        self.assertEqual(reviewed['creative']['status'],'NOT_RUN');self.assertEqual(reviewed['userAcceptance']['status'],'NOT_RUN');self.assertEqual(reviewed['commandArtifacts'],mapping)
        for action in ('inspect','reconcile','resume'):
            current=public(action,'--task','multi-project');self.assertEqual(current['delivery']['commandArtifacts'],started['delivery']['commandArtifacts'])
        self.assertEqual(files(output),before);self.assertEqual(files(store.path('multi-project').parent/'receipts'),receipts)
        moved=root/'moved whole delivery';shutil.copytree(output,moved);self.assertEqual(adapter.validate(moved,mapping),mapping['artifacts'])
        frozen=managed.load('runtime_binding').resolve(store,'multi-project');lock=managed.read(skill/'scripts/runtime.lock.json');key=managed.load('platform_support').platform_key()
        installed_runtime=managed.load('bootstrap').inspect_install(runtime/'effectcraft'/lock['resolvedVersion'],lock['artifact'],lock['artifacts'][key],lock['resolvedVersion'],key)
        reopened=delivery.verify_projects(moved,data['projects'],installed_runtime['executable']);self.assertEqual(reopened['status'],'PASS',reopened);self.assertEqual(len(reopened['projects']),2)
        moved_files=files(moved);old=copy.deepcopy(mapping);(moved/'early.png').write_bytes(png(1,1));old['files']['early.png']=sha(moved/'early.png');old['binding']['filesHash']=managed.load('task_store').digest(old['files'])
        with self.assertRaisesRegex(ValueError,'command_artifact'):adapter.validate(moved,old)
        (moved/'early.png').write_bytes((output/'early.png').read_bytes());self.assertEqual(files(moved),moved_files)
        desktop=managed.read(output/'desktop-session.json') if mode=='desktop' else None
        if desktop:self.assertTrue(desktop['ownedProcessesStopped']);self.assertTrue(desktop['listenerOwnedByPID']);self.assertEqual(desktop['sessionsStarted'],1)
        lifecycle=managed.read(store.lifecycle_path(store.read('multi-project')));self.assertEqual(lifecycle['status'],'stopped');self.assertEqual(lifecycle['returncode'],0)
        self.assertEqual(files(skill),installed);self.assertEqual(files(output),before)
        frozen_files=managed.load('runtime_binding').source_files(Path(frozen['script']).parent.parent);self.assertTrue(all(installed[k]==v for k,v in frozen_files.items()))
        proof={'schema':'effectcraft-native-command-artifact-lineage/v1','status':'PASS_COMPONENT','mode':mode,'platform':'darwin-arm64','sourceSkillFiles':installed,'testSha256':sha(Path(__file__)),'ownerSchemaSha256':sha(ROOT/'tests/fixtures/craft-artifact-v1.schema.json'),'generatedObjectsValidated':2,'artifactMap':mapping,'taskId':'multi-project','identityHash':started['identityHash'],'planHash':started['identity']['planHash'],'runtimeSha256':started['identity']['runtimeSha256'],'outputFiles':before,'deliveryDocumentSha256':sha(store.path('multi-project').parent/'command-delivery/delivery.json'),'nativeEngineering':'PASS','nativeTechnical':'PASS','movedNativeProjectsReopened':2,'movedPackageRevalidated':True,'staleVersionRejected':True,'outputAndReceiptsPreserved':True,'installedAndFrozenResourcesPreserved':True,'workerReturncode':0,'desktopOwnershipVerified':bool(desktop),'actions':actions,'creative':'NOT_RUN','userAcceptance':'NOT_RUN','hostDispatch':'NOT_RUN','cacheReused':True,'python':started['identity']['runtimeBinding']['python']['version'],'fullV1':'NOT_RUN'}
        (root/'result.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
