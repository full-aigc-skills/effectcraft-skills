"""单独复制技能、空运行时公开安装及动态透明序列真实修订。"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def hashes(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file()}


@unittest.skipUnless(os.environ.get('CRAFT_EFFECT_SEQUENCE_FIRST_USE') == '1', 'requires public runtime download and existing Pillow')
class SequenceFirstUseTests(unittest.TestCase):
    def test_cold_sequence_and_text_revision_preserve_other_animation(self):
        from PIL import Image
        original = Path(os.environ.get('CRAFT_INSTALLED_EFFECT_SEQUENCE_SKILL', ROOT/'skills/effectcraft-cli-export'))
        before = hashes(original)
        with tempfile.TemporaryDirectory(prefix='effect-sequence-first-use-') as temporary:
            root = Path(temporary); skill = root/'.agents/skills/effectcraft-cli-export'
            shutil.copytree(original, skill); copied = hashes(skill); runtime = root/'empty-runtime'
            spec = importlib.util.spec_from_file_location('sequence_workflow', skill/'scripts/workflow.py')
            workflow = importlib.util.module_from_spec(spec); spec.loader.exec_module(workflow)
            self.assertFalse(runtime.exists())
            plan = json.loads((skill/'examples/brand-intro.json').read_text()); plan['exports'] = [{'format': 'png-sequence'}]
            first = root/'first'; delivered = workflow.execute(plan, first, runtime_home=runtime)
            manifest = json.loads((first/'rgba-sequence/sequence.json').read_text())
            self.assertEqual(manifest['frameCount'], 12); self.assertEqual(manifest['frameRate'], {'num': 12, 'den': 1})
            self.assertIsNone(delivered['video'])
            self.assertNotEqual(manifest['frames'][0]['rgbaSha256'], manifest['frames'][6]['rgbaSha256'])
            for frame in manifest['frames']:
                path = first/'rgba-sequence'/frame['location']
                with Image.open(path) as image:
                    self.assertEqual(image.mode, 'RGBA'); self.assertEqual(image.size, (320, 180))
                    self.assertEqual(hashlib.sha256(image.tobytes()).hexdigest(), frame['rgbaSha256'])
                    self.assertEqual(list(image.getchannel('A').getextrema()), frame['alphaExtrema'])
                    self.assertLess(frame['alphaExtrema'][0], 255)
                self.assertEqual(workflow.sha(path), frame['sha256'])
            old = hashes(first); native = json.loads((first/'native.json').read_text())
            revised = root/'revised'
            change = {'expectedProjectSha256': delivered['files']['project.ecproj'],
                      'operations': [{'command': 'layer.setText', 'params': {'layer': {'$ref': 'title.layer'}, 'text': 'NOVA PLUS'}}],
                      'frames': [0, .5], 'exports': [{'format': 'png-sequence'}]}
            result = workflow.execute(change, revised, runtime_home=runtime, source=first)
            after = json.loads((revised/'native.json').read_text())
            badge = str(delivered['bindings']['badge']['layer']); title = str(delivered['bindings']['title']['layer'])
            self.assertEqual(native['layers'][badge], after['layers'][badge])
            def opacity(node):
                if node.get('path') == 'transform/opacity': return node
                for child in node.get('children', []):
                    value = opacity(child)
                    if value is not None: return value
            self.assertEqual(opacity(native['layers'][title]['properties']), opacity(after['layers'][title]['properties']))
            self.assertEqual(delivered['files']['rgba-sequence/frame_00000.png'], result['files']['rgba-sequence/frame_00000.png'])
            self.assertNotEqual(delivered['files']['rgba-sequence/frame_00006.png'], result['files']['rgba-sequence/frame_00006.png'])
            self.assertEqual(hashes(first), old); self.assertEqual(hashes(skill), copied); self.assertEqual(hashes(original), before)
            if os.environ.get('CRAFT_EFFECT_SEQUENCE_EVIDENCE'):
                proof = {'schema': 'effectcraft-dynamic-sequence-first-use/v1', 'result': 'PASS', 'runtimeSha256': result['runtimeSha256'],
                         'copiedSkillHashes': copied, 'frameCount': 12, 'frameRate': manifest['frameRate'],
                         'frames': manifest['frames'], 'revisedSequence': result['imageSequence'],
                         'allFramesIndependentlyDecoded': True, 'actualTransparencyVerified': True,
                         'nonTargetLayerAndAnimationPreserved': True, 'sourceAndSkillHashesPreserved': True,
                         'scope': 'single copied export skill; empty runtime; public native download; Effect sequence candidate',
                         'excluded': ['Film dynamic import', 'Art mixed handoff', 'fixed new plugin installation', 'creative/color/model/GUI acceptance']}
                Path(os.environ['CRAFT_EFFECT_SEQUENCE_EVIDENCE']).write_text(json.dumps(proof, indent=2)+'\n')
