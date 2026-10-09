"""公开只读单技能：真实素材创建、整包移动、血缘修订及旧包兼容。"""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import struct
import subprocess
import tempfile
import unittest
import zlib

ROOT=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def files(root):return {p.relative_to(root).as_posix():sha(p) for p in sorted(root.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
def load(path):
    spec=importlib.util.spec_from_file_location('native_lineage',path);v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v);return v

@unittest.skipUnless(os.environ.get('CRAFT_ARTIFACT_LINEAGE_LIVE')=='1','explicit native artifact lineage opt-in')
@unittest.skipUnless(platform.system()=='Darwin' and platform.machine()=='arm64','macOS arm64 native acceptance')
class NativeWorkflowArtifactLineageTests(unittest.TestCase):
    def test_public_moved_source_revision_and_legacy_source(self):
        root=Path(os.environ.get('CRAFT_ARTIFACT_LINEAGE_ROOT') or tempfile.mkdtemp(prefix='native artifact lineage '))
        root.mkdir(parents=True,exist_ok=True);self.assertFalse(any(root.iterdir()),'preserve previous evidence')
        skill=root/'single readonly skill';shutil.copytree(ROOT/'skills/effectcraft-use',skill,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        for p in skill.rglob('*'):p.chmod(0o555 if p.is_dir() else 0o444)
        skill.chmod(0o555);installed=files(skill)
        env=dict(os.environ,CRAFT_RUNTIME_HOME=os.environ['CRAFT_ARTIFACT_LINEAGE_RUNTIME_HOME'],PATH='/opt/homebrew/bin:/usr/bin:/bin')
        self.assertIn('CRAFT_PYTHON_HOME',env,'prepared isolated Python cache required')
        state=root/'state';actions=[]
        def public(action,*args,success=True):
            r=subprocess.run(['/bin/sh',str(skill/'scripts/launch.sh'),'--state-root',str(state),action,*map(str,args)],env=env,cwd=root,capture_output=True,timeout=300)
            label=str(len(actions))+'-'+action;(root/(label+'.stdout')).write_bytes(r.stdout);(root/(label+'.stderr')).write_bytes(r.stderr)
            self.assertEqual(r.returncode==0,success,r.stdout.decode(errors='replace')+r.stderr.decode(errors='replace'))
            actions.append({'action':action,'returncode':r.returncode});return json.loads(r.stdout)
        def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data))
        asset=root/'input asset.png';asset.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',16,16,8,6,0,0,0))+chunk(b'IDAT',zlib.compress((b'\x00'+b'\xff\x66\x00\xff'*16)*16))+chunk(b'IEND',b''))
        criteria=root/'criteria.json';criteria.write_text(json.dumps({'goal':'Technical lineage and moved-source acceptance; creative not evaluated'}))
        managed=load(skill/'scripts/managed.py');quality=managed.load('quality_review');store=managed.load('task_store').Store(state)
        rows=[]
        def run_case(task,plan,output,source=None):
            planpath=root/(task+' plan.json');planpath.write_text(json.dumps(plan))
            sourceargs=['--source',source] if source else []
            checked=public('plan','--plan',planpath,'--output',output,*sourceargs);self.assertEqual(checked['result'],'VALID')
            started=public('run','--task',task,'--plan',planpath,'--output',output,*sourceargs);self.assertEqual(started['state'],'review_ready')
            self.assertTrue(all(x['state']=='succeeded' for x in started['steps']))
            before=files(output);receiptfiles=files(store.path(task).parent/'receipts')
            response=public('review','--task',task,'--criteria',criteria);report=response['report']
            self.assertEqual(report['engineering']['status'],'PASS',report);self.assertEqual(report['technical']['status'],'PASS',report)
            self.assertEqual(report['technical']['verifiedAssets'],1)
            self.assertEqual(report['creative']['status'],'NOT_RUN');self.assertEqual(report['userAcceptance']['status'],'NOT_RUN');self.assertFalse(report['accepted'])
            current=store.read(task);manifest=managed.read(output/'manifest.json');bound=managed.load('runtime_binding').resolve(store,task)
            frozen=managed.load('runtime_binding').source_files(Path(bound['script']).parent.parent)
            self.assertTrue(all(installed[k]==v for k,v in frozen.items()))
            self.assertEqual(manifest['artifact']['producerTaskId'],task);self.assertEqual(manifest['artifactBinding']['producer']['taskIdentityHash'],current['identityHash'])
            self.assertEqual(manifest['artifactBinding']['producer']['mode'],'managed')
            self.assertEqual(manifest['artifactBinding']['planSha256'],current['identity']['planHash'])
            self.assertEqual(manifest['artifactBinding']['runtimeSha256'],current['identity']['runtimeSha256'])
            if source:
                self.assertEqual(current['identity']['authorization']['sourcePackage'],managed.load('artifact_lineage').source_binding(source))
            self.assertEqual(sum(m.get('verifiedFrames',0) for m in report['technical']['media']),4)
            self.assertEqual(manifest['artifact']['protocolVersion'],'craft-artifact/v1')
            self.assertEqual(manifest['artifact']['bytes'],(output/'project.ecproj').stat().st_size)
            self.assertEqual(manifest['artifact']['sha256'],sha(output/'project.ecproj'))
            self.assertEqual(len(manifest['artifact']['dependencies']),1)
            self.assertEqual(sha(output/manifest['assets']['fixture']['path']),sha(asset))
            self.assertNotIn(str(root),json.dumps([manifest['artifact'],manifest['artifactBinding']]))
            lifecycle=managed.read(store.lifecycle_path(current));self.assertEqual(lifecycle['status'],'stopped');self.assertEqual(lifecycle['returncode'],0)
            public('resume','--task',task);self.assertEqual(files(output),before);self.assertEqual(files(store.path(task).parent/'receipts'),receiptfiles)
            rows.append({'taskId':task,'format':(plan.get('exports') or [{}])[0].get('format'),'artifact':manifest['artifact'],'binding':manifest['artifactBinding'],
                'manifestSha256':sha(output/'manifest.json'),'nativeOutputs':before,'installedResourcesMatchFrozen':True,'frozenResourceCount':len(frozen),
                'engineering':'PASS','technical':'PASS','creative':'NOT_RUN','userAcceptance':'NOT_RUN','verifiedAssets':1,
                'decodedFrames':sum(m.get('verifiedFrames',0) for m in report['technical']['media']),'steps':len(current['steps']),
                'workerReturncode':0,'lifecycleSha256':sha(store.lifecycle_path(current)),'filesAndReceiptsPreservedOnResume':True,
                'sourcePackageAuthorizationBound':bool(current['identity']['authorization'].get('sourcePackage'))})
            return manifest,managed.read(output/'native.json')
        plan={'document':{'name':'Lineage sample','width':64,'height':48,'frameRate':4,'duration':1},
            'assets':{'fixture':{'path':str(asset),'sha256':sha(asset)}},'operations':[
                {'command':'asset.import','params':{'asset':'fixture'},'as':'footage'},
                {'command':'layer.addItem','params':{'item':{'$ref':'footage.item'},'position':[32,24]},'as':'subject'}],
            'frames':[0,.5],'exports':[{'format':'mp4'}]}
        original=root/'original delivery';old,oldnative=run_case('lineage-original',plan,original)
        original_files=files(original);moved=root/'moved whole delivery';original.rename(moved)
        self.assertFalse(original.exists());self.assertEqual(files(moved),original_files)
        self.assertEqual(quality.binding(moved)['projectSha256'],old['artifact']['sha256'])
        bad=root/'tampered moved source';shutil.copytree(moved,bad)
        badmanifest=managed.read(bad/'manifest.json');frame=badmanifest['frames'][0]['path'];(bad/frame).write_bytes(b'replaced same name')
        badmanifest['files'][frame]=sha(bad/frame);(bad/'manifest.json').write_text(json.dumps(badmanifest))
        change={'expectedProjectSha256':old['artifact']['sha256'],'operations':[{'command':'prop.set','params':{'layer':{'$ref':'subject.layer'},'path':'transform/opacity','value':70}}],
            'frames':[0,.5],'exports':[{'format':'png-sequence'}]}
        badplan=root/'bad source plan.json';badplan.write_text(json.dumps(change));before_tasks=sorted(x.name for x in (state/'tasks').iterdir())
        rejected=public('plan','--plan',badplan,'--output',root/'must not exist','--source',bad,success=False)
        self.assertIn('artifact_lineage',json.dumps(rejected));self.assertFalse((root/'must not exist').exists())
        self.assertEqual(sorted(x.name for x in (state/'tasks').iterdir()),before_tasks)
        second=root/'revised delivery';new,newnative=run_case('lineage-revision',change,second,moved)
        parent={k:old['artifact'][k] for k in ('assetId','version','sha256')}
        self.assertEqual(new['artifact']['assetId'],old['artifact']['assetId']);self.assertNotEqual(new['artifact']['version'],old['artifact']['version'])
        self.assertEqual(new['artifact']['sourceRefs'],[parent]);self.assertEqual(new['artifactBinding']['sourceRef'],parent)
        self.assertNotEqual(sha(second/'frame-0000.png'),sha(moved/'frame-0000.png'))
        self.assertEqual(files(moved),original_files)
        def remove_opacity(value):
            if isinstance(value,dict):return {k:remove_opacity(v) for k,v in value.items() if k!='properties'} if value.get('path')=='transform/opacity' else {k:remove_opacity(v) for k,v in value.items()}
            if isinstance(value,list):return [remove_opacity(v) for v in value if not isinstance(v,dict) or v.get('path')!='transform/opacity']
            return value
        self.assertEqual(oldnative['composition'],newnative['composition'])
        self.assertEqual(remove_opacity(oldnative['layers']),remove_opacity(newnative['layers']))
        legacy=root/'legacy source copy';shutil.copytree(moved,legacy);legacy_manifest=managed.read(legacy/'manifest.json')
        del legacy_manifest['artifact'];del legacy_manifest['artifactBinding'];(legacy/'manifest.json').write_text(json.dumps(legacy_manifest));legacy_before=files(legacy)
        change3=copy.deepcopy(change);change3['operations'][0]['params']['value']=50;change3['exports']=[{'format':'png-segmented','chunkFrames':2}]
        third,thirdnative=run_case('lineage-legacy-revision',change3,root/'legacy revised delivery',legacy)
        self.assertEqual(third['artifact']['sourceRefs'],[{'assetId':'legacy-project:'+old['artifact']['sha256'],'version':old['artifact']['sha256'],'sha256':old['artifact']['sha256']}])
        self.assertEqual(files(legacy),legacy_before);self.assertEqual(files(moved),original_files);self.assertEqual(files(skill),installed)
        self.assertEqual(oldnative['composition'],thirdnative['composition'])
        self.assertEqual(remove_opacity(oldnative['layers']),remove_opacity(thirdnative['layers']))
        proof={'schema':'effectcraft-workflow-artifact-native/v1','status':'PASS_COMPONENT','platform':'darwin-arm64','testSha256':sha(Path(__file__)),
            'sourceSkillFiles':installed,'cases':rows,'actions':actions,'movedWholePackagePreserved':True,'legacySourcePreserved':True,
            'tamperedSourceBlockedBeforeTaskRegistration':True,'nonTargetNativeContentPreserved':True,'installedSkillPreserved':True,
            'python':store.read('lineage-revision')['identity']['runtimeBinding']['python'],'nativeCacheReused':True,
            'hostDispatch':'NOT_RUN','fullV1':'NOT_RUN','limitations':['workflow only, not command/desktop public artifact qualification','explicit new source revision, not automatic revise or unknown-task replay','existing isolated Python/native caches; not cold install','legacy source fixture deliberately removes lineage; no historical task identity reconstructed']}
        (root/'result.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
