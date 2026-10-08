"""真实原生编辑完成后中断分段导出，通过公开 resume 保全工程续跑。"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]


def load(path):
    spec=importlib.util.spec_from_file_location('native_segment_acceptance',path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


def hashes(directory):
    return {p.relative_to(directory).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
        for p in directory.rglob('*') if p.is_file() and '__pycache__' not in p.parts}


@unittest.skipUnless(os.environ.get('CRAFT_MANAGED_SEGMENT_LIVE')=='1','requires actual native engine')
class ManagedSegmentNativeTests(unittest.TestCase):
    def test_public_resume_reuses_verified_segment_without_replaying_edits(self):
        with tempfile.TemporaryDirectory(prefix='managed segment recovery ') as temporary:
            root=Path(temporary).resolve();skill=root/'single skill'
            shutil.copytree(ROOT/'skills/effectcraft-use',skill,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
            before=hashes(skill);managed=load(skill/'scripts/managed.py');tasks=managed.load('task_store')
            store=tasks.Store(root/'state');output=root/'delivery';runtime=root/'runtime'
            plan=json.loads((skill/'examples/brand-intro.json').read_text());plan['exports']=[{'format':'png-segmented','chunkFrames':4}]
            key=managed.load('platform_support').platform_key();lock=managed.read(skill/'scripts/runtime.lock.json')
            request={'inputs':{},'source':None}
            execution,execution_manifest=managed.load('runtime_binding').prepare(skill,runtime)
            initial=store.create('segment-task',plan=plan,output=str(output),runtime_sha=lock['artifacts'][key]['binarySha256'],
                inputs={},source=None,mode='workflow',authorization={'requestHash':tasks.digest(request)},runtime_binding=execution)
            tasks.atomic_json(store.path('segment-task').parent/'request.json',request)
            managed.load('runtime_binding').freeze(store,'segment-task',skill,execution_manifest)
            # 故障注入仅在验收驱动中；实际每一成功段仍由锁定原生 CLI 产生。
            driver=root/'interrupt_export.py'
            driver.write_text('import importlib.util,sys\nfrom pathlib import Path\n'
                's=importlib.util.spec_from_file_location("acceptance_managed",sys.argv[1]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)\n'
                'w=m.load("workflow");producer=w.load_module("segmented_sequence");native=producer.render_segment\n'
                'def interrupted(cli,project,composition,directory,part):\n'
                '    if part["firstFrame"]==4:\n'
                '        if sys.argv[4]=="orphan":native(cli,project,composition,directory,part)\n'
                '        if sys.argv[4] in ("kill","orphan"):\n'
                '            import os,signal\n'
                '            os.kill(os.getpid(),signal.SIGKILL)\n'
                '        raise RuntimeError("acceptance_export_interrupted")\n'
                '    return native(cli,project,composition,directory,part)\n'
                'producer.render_segment=interrupted;original=w.load_module\n'
                'w.load_module=lambda name:producer if name=="segmented_sequence" else original(name)\n'
                'original_load=m.load;m.load=lambda name:w if name=="workflow" else original_load(name)\n'
                'm.worker(m.load("task_store").Store(Path(sys.argv[2])),"segment-task",Path(sys.argv[3]))\n')
            guard=subprocess.Popen([sys.executable,'-I','-B',str(skill/'scripts/process_guard.py'),
                '--receipt',str(store.path('segment-task').parent/'lifecycle.json'),
                '--lease',str(store.root/'leases/segment-task.lifecycle.lock'),'--',sys.executable,'-I','-B',str(driver),
                str(skill/'scripts/managed.py'),str(store.root),str(runtime),os.environ.get('CRAFT_SEGMENT_INTERRUPT_KIND','exception')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            try:guard.wait(timeout=240)
            finally:
                if guard.poll() is None:guard.kill();guard.wait()
                guard.stdin.close()
                logs=guard.stdout.read()+guard.stderr.read();guard.stdout.close();guard.stderr.close()
            self.assertNotEqual(guard.returncode,0,logs.decode())
            interrupted=store.read('segment-task');self.assertIn(interrupted['state'],('running','reconciling'),logs.decode(errors='replace'))
            self.assertIn('renderRecovery',interrupted,'workflow did not persist export-only recovery context')
            orphan=next(output.glob('.effect-segment-*'),None)
            orphan_hashes=hashes(orphan) if orphan else None
            orphan_identity=(orphan.stat().st_dev,orphan.stat().st_ino) if orphan else None
            orphan_stats={p.name:(p.stat().st_ino,p.stat().st_mtime_ns) for p in orphan.iterdir()} if orphan else None
            first=output/'rgba-segments/segment_00000';first_hashes=hashes(first)
            first_stats={p.name:(p.stat().st_ino,p.stat().st_mtime_ns) for p in first.iterdir()}
            project_sha=tasks.file_sha(output/'project.ecproj')
            receipts={s['id']:tasks.file_sha(store.path('segment-task').parent/'receipts'/(s['id']+'.json'))
                for s in interrupted['steps'] if s['state']=='succeeded'}
            command=[sys.executable,'-I','-B',str(skill/'scripts/managed.py'),'--state-root',str(store.root),
                '--runtime-home',str(runtime),'resume','--task','segment-task']
            resumed=subprocess.run(command,capture_output=True,text=True,timeout=240)
            self.assertEqual(resumed.returncode,0,resumed.stdout+resumed.stderr)
            state=json.loads(resumed.stdout);self.assertEqual(state['state'],'review_ready')
            self.assertEqual([s['id'] for s in state['steps']],[s['id'] for s in interrupted['steps']])
            self.assertTrue(all(s['state']=='succeeded' for s in state['steps']))
            self.assertEqual(state['deadline'],initial['deadline']);self.assertEqual(state['identityHash'],initial['identityHash'])
            resources=state['resources']['entries']['segment-task']
            self.assertEqual(resources['frames'],12+len(plan.get('frames',[0])))
            self.assertEqual(resources['decodedBytes'],resources['frames']*320*180*4)
            self.assertGreater(resources['encodedBytes'],0)
            attempts=resources['segmentAttempts']
            self.assertEqual({key:len(rows) for key,rows in attempts.items()},
                {'segment_00000':1,'segment_00001':2,'segment_00002':1})
            used=managed.load('resource_budget').usage(state['resources'])
            self.assertEqual(used['frames'],resources['frames']+4)
            self.assertEqual(used['decodedBytes'],resources['decodedBytes']+4*320*180*4)
            self.assertEqual(len(state['resources']['entries']),1)
            if os.environ.get('CRAFT_SEGMENT_INTERRUPT_KIND')=='orphan':
                self.assertIsNotNone(orphan_hashes);self.assertEqual(len(orphan_hashes),4)
                archive=Path(state['orphanArchives']['entries'][0]['destination'])
                self.assertEqual(state['orphanArchives']['entries'][0]['phase'],'archived')
                self.assertEqual(hashes(archive),orphan_hashes)
                self.assertEqual((archive.stat().st_dev,archive.stat().st_ino),orphan_identity)
                self.assertEqual({p.name:(p.stat().st_ino,p.stat().st_mtime_ns) for p in archive.iterdir()},orphan_stats)
                self.assertFalse(archive.is_relative_to(output));self.assertFalse(orphan.exists())
                manifest=managed.read(output/'manifest.json')
                self.assertFalse(any('.effect-segment-' in name or '.effectcraft-recovery-' in name for name in manifest['files']))
                actual=sum(p.stat().st_size for p in managed.load('resource_meter').files(state))
                self.assertEqual(resources['encodedBytes'],actual)
            self.assertEqual(tasks.file_sha(output/'project.ecproj'),project_sha)
            self.assertEqual(hashes(first),first_hashes)
            self.assertEqual({p.name:(p.stat().st_ino,p.stat().st_mtime_ns) for p in first.iterdir()},first_stats)
            for operation,expected in receipts.items():
                self.assertEqual(tasks.file_sha(store.path('segment-task').parent/'receipts'/(operation+'.json')),expected)
            context=managed.read(store.path('segment-task').parent/'render-context.json')
            sequence=managed.load('image_sequence')
            baseline=root/'baseline';baseline.mkdir()
            sequence.export_sequence(context['cli'],output/'project.ecproj',context['comp'],baseline)
            frames=managed.read(baseline/'rgba-sequence/sequence.json')['frames']
            segments=managed.read(output/'rgba-segments/segments.json')
            for segment in segments['segments']:
                contents=managed.read(output/'rgba-segments'/segment['location'])
                for frame in contents['frames']:
                    self.assertEqual(frame['rgbaSha256'],frames[segment['firstFrame']+frame['index']]['rgbaSha256'])
            quality=managed.load('quality_review').inspect_delivery(output)
            self.assertEqual(quality['technical']['status'],'PASS',quality)
            # 真实原生序列也必须通过完整描述校验，刷新包摘要不能掩盖错误时间合同。
            inspector=managed.load('quality_review')
            shutil.copyfile(output/'native.json',baseline/'native.json')
            shutil.copyfile(output/'project.ecproj',baseline/'project.ecproj')
            ordinary={'path':'rgba-sequence/sequence.json','sha256':tasks.file_sha(baseline/'rgba-sequence/sequence.json')}
            self.assertEqual(inspector.inspect_sequence_contract(baseline,ordinary)['verifiedFrames'],12)
            manifest_path=output/'manifest.json';manifest_bytes=manifest_path.read_bytes()
            descriptor=output/'rgba-segments/segments.json';descriptor_bytes=descriptor.read_bytes()
            try:
                changed=json.loads(descriptor_bytes);changed['segments'][1]['firstFrame']+=1
                tasks.atomic_json(descriptor,changed)
                changed_manifest=json.loads(manifest_bytes)
                changed_manifest['files']['rgba-segments/segments.json']=tasks.file_sha(descriptor)
                changed_manifest['imageSequence']['sha256']=tasks.file_sha(descriptor)
                tasks.atomic_json(manifest_path,changed_manifest)
                rejected=inspector.inspect_delivery(output)
                self.assertEqual(rejected['technical']['status'],'FAIL',rejected)
                self.assertIn('sequence_segment_receipt_mismatch',rejected['technical']['reason'])
            finally:
                descriptor.write_bytes(descriptor_bytes);manifest_path.write_bytes(manifest_bytes)
            self.assertEqual(before,hashes(skill))
            repeat=subprocess.run(command,capture_output=True,text=True,timeout=30)
            self.assertEqual(repeat.returncode,0,repeat.stdout+repeat.stderr)
            self.assertEqual(json.loads(repeat.stdout)['state'],'review_ready')
            self.assertEqual(len(store.read('segment-task')['renderResumes']),1)
            self.assertEqual(store.read('segment-task')['resources'],state['resources'])
            if os.environ.get('CRAFT_SEGMENT_RESUME_EVIDENCE'):
                proof={'schema':'effectcraft-managed-segment-resume-component/v1','result':'PASS','platform':key,
                    'scope':'one copied skill; actual native editing and segmented render interrupted by test driver; public resume with no editing replay',
                    'skillFiles':before,'driverSha256':hashlib.sha256(driver.read_bytes()).hexdigest(),
                    'testSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'runtimeSha256':state['identity']['runtimeSha256'],
                    'identityHash':state['identityHash'],'projectSha256':project_sha,'manifestSha256':tasks.file_sha(output/'manifest.json'),
                    'completedSegmentByteAndInodeAndMtimePreserved':True,'existingEditingReceiptsPreserved':True,
                    'operationCountBefore':len(interrupted['steps']),'operationCountAfter':len(state['steps']),
                    'framesIndependentlyCompared':len(frames),'deadlinePreserved':True,'technical':quality['technical'],
                    'actualOrdinarySequenceContractVerified':True,'actualRefreshedPackageWithInvalidSegmentRangeRejected':True,
                    'interruptKind':os.environ.get('CRAFT_SEGMENT_INTERRUPT_KIND','exception'),'repeatResumeIsNoop':True,
                    'resources':state['resources'],
                    'orphanArchivedOutsideDelivery':bool(state.get('orphanArchives')),
                    'excluded':['process SIGKILL inside native CLI','Windows/Linux execution','host model dispatch','fixed release','complete V1']}
                Path(os.environ['CRAFT_SEGMENT_RESUME_EVIDENCE']).write_text(json.dumps(proof,indent=2)+'\n')


if __name__=='__main__':unittest.main()
