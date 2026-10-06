"""独立复制导出技能、空运行时、原生分段与逐帧基准对照。"""
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
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result
def hashes(root):
    return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
@unittest.skipUnless(os.environ.get('CRAFT_EFFECT_SEGMENT_FIRST_USE')=='1','requires public native download and existing Pillow')
class SegmentFirstUse(unittest.TestCase):
    def test_cold_segmented_pixels_match_baseline_and_corrupt_segment_recovers(self):
        from PIL import Image
        original=ROOT/'skills/effectcraft-cli-export';before=hashes(original)
        with tempfile.TemporaryDirectory(prefix='effect-segment-first-use-') as temp:
            root=Path(temp).resolve();skill=root/'.agents/skills/effectcraft-cli-export';shutil.copytree(original,skill);copied=hashes(skill);runtime=root/'empty-runtime'
            workflow=load('segment_workflow',skill/'scripts/workflow.py');segments=load('segment_producer',skill/'scripts/segmented_sequence.py')
            plan=json.loads((skill/'examples/brand-intro.json').read_text());plan['exports']=[{'format':'png-sequence'}]
            self.assertFalse(runtime.exists())
            delivered=workflow.execute(plan,root/'baseline',runtime_home=runtime)
            baseline=root/'baseline';source_hashes=hashes(baseline)
            installed=segments.module('bootstrap').install(json.loads((skill/'scripts/runtime.lock.json').read_text()),runtime)
            comp=json.loads((baseline/'native.json').read_text())['composition'];out=root/'segmented';calls=[];native=segments.render_segment
            def tracked(cli,project,composition,directory,part):
                calls.append(part['firstFrame']);return native(cli,project,composition,directory,part)
            with patch.object(segments,'render_segment',tracked):
                report=segments.render_segments(installed['executable'],baseline/'project.ecproj',comp,out,chunk_bytes=1024*1024)
                self.assertEqual(calls,[0,4,8]);self.assertEqual(report['frameCount'],12)
                baseline_frames=json.loads((baseline/'rgba-sequence/sequence.json').read_text())['frames']
                for segment in report['segments']:
                    manifest=json.loads((out/segment['location']).read_text())
                    for frame in manifest['frames']:
                        index=segment['firstFrame']+frame['index']
                        with Image.open((out/segment['location']).parent/frame['location']) as image:
                            self.assertEqual(hashlib.sha256(image.tobytes()).hexdigest(),baseline_frames[index]['rgbaSha256'])
                immutable=hashes(out/'segment_00000');segments.render_segments(installed['executable'],baseline/'project.ecproj',comp,out,chunk_bytes=1024*1024)
                self.assertEqual(calls,[0,4,8]);self.assertEqual(hashes(out/'segment_00000'),immutable)
                (out/'segment_00001/frame_00000.png').write_bytes(b'corrupt')
                repaired=segments.render_segments(installed['executable'],baseline/'project.ecproj',comp,out,chunk_bytes=1024*1024)
                self.assertEqual(calls,[0,4,8,4]);self.assertEqual(repaired,report);self.assertEqual(hashes(out/'segment_00000'),immutable)
            composition=root/'composition.json';composition.write_text(json.dumps(comp))
            fresh=root/'public-cli-runtime';public=root/'public-cli';self.assertFalse(fresh.exists())
            command=[sys.executable,'-I','-B',str(skill/'scripts/segmented_sequence.py'),'--project',str(baseline/'project.ecproj'),'--composition',str(composition),'--output',str(public),'--chunk-frames','4','--runtime-home',str(fresh)]
            environment=dict(os.environ,PATH='/usr/bin:/bin:/usr/sbin:/sbin');environment.pop('CRAFT_NATIVE_ARCHIVE_DIRECTORY',None);environment.pop('CRAFT_BUNDLE_DIRECTORY',None)
            first=subprocess.run(command,capture_output=True,text=True,timeout=180,env=environment);self.assertEqual(first.returncode,0,first.stdout+first.stderr)
            self.assertEqual(json.loads(first.stdout),{'state':'verified','frameCount':12,'segments':3})
            public_hashes=hashes(public);repeat=subprocess.run(command,capture_output=True,text=True,timeout=180,env=environment);self.assertEqual(repeat.returncode,0,repeat.stdout+repeat.stderr);self.assertEqual(hashes(public),public_hashes)
            self.assertEqual(hashes(baseline),source_hashes);self.assertEqual(hashes(skill),copied);self.assertEqual(hashes(original),before)
            if os.environ.get('CRAFT_EFFECT_SEGMENT_EVIDENCE'):
                proof={'schema':'effectcraft-segment-producer-candidate/v1','result':'PASS','scope':'one copied export skill; empty runtime; public default download; three actual native render segments','runtimeSha256':report['binding']['runtimeSha256'],'sourceProjectSha256':report['binding']['projectSha256'],'driverSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'publicCliEmptyRuntimeAndRepeatPassed':True,'framesComparedIndependently':12,'nativeRenderFirstFrames':calls,'allThreeCompletedSegmentsReused':True,'onlyCorruptSegmentRebuilt':True,'inputsAndSkillsPreserved':True,'skillHashes':copied,'excluded':['full HD native long render','Film and Art segment consumption','fixed new plugin installation','model/GUI/creative acceptance']}
                Path(os.environ['CRAFT_EFFECT_SEGMENT_EVIDENCE']).write_text(json.dumps(proof,indent=2)+'\n')
