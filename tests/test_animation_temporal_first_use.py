"""单独安装动画技能后，逐时刻核对原生 RGBA 与实际视频解码。"""
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

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]


def tree_hash(directory):
    result = hashlib.sha256()
    for path in sorted(p for p in directory.rglob('*') if p.is_file()):
        result.update(path.relative_to(directory).as_posix().encode() + b'\0')
        result.update(hashlib.sha256(path.read_bytes()).hexdigest().encode() + b'\n')
    return result.hexdigest()


def property_at(node, path):
    if node.get('path') == path:
        return node
    for child in node.get('children', []):
        found = property_at(child, path)
        if found is not None:
            return found
    return None


@unittest.skipUnless(os.environ.get('CRAFT_TEMPORAL_FIRST_USE') == '1', 'requires installed animation skill, native public archives and existing Pillow/ffmpeg')
class AnimationTemporalTests(unittest.TestCase):
    def test_animation_rgba_video_and_text_revision(self):
        from PIL import Image
        original = Path(os.environ['CRAFT_INSTALLED_ANIMATION_SKILL'])
        original_hash = tree_hash(original)
        with tempfile.TemporaryDirectory(prefix='effect-temporal-') as temporary:
            root = Path(temporary)
            skill = root / '.agents/skills/effectcraft-cli-animation'
            shutil.copytree(original, skill)
            self.assertEqual(tree_hash(skill), original_hash)
            spec = importlib.util.spec_from_file_location('effect_temporal_workflow', skill / 'scripts/workflow.py')
            workflow = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(workflow)
            runtime = root / 'empty-runtime'
            self.assertFalse(runtime.exists())
            plan = json.loads((skill / 'examples/brand-intro.json').read_text())
            for time, value in [(0, 0), (.5, 100)]:
                plan['operations'].append({'command': 'prop.addKey', 'params': {'layer': {'$ref': 'badge.layer'}, 'path': 'transform/opacity', 'time': time, 'value': value}})
            plan['frames'] = [0, .25, .5, .75]
            first = root / 'first'
            receipt = workflow.execute(plan, first, runtime_home=runtime)
            native = json.loads((first / 'native.json').read_text())
            badge, title = str(receipt['bindings']['badge']['layer']), str(receipt['bindings']['title']['layer'])
            keys = property_at(native['layers'][badge]['properties'], 'transform/opacity')
            self.assertEqual([(k['time'], k['value']) for k in keys['keys']], [(0, 0), (.5, 100)])
            alpha = []
            for index in range(4):
                with Image.open(first / f'frame-{index:04}.png') as image:
                    alpha.append(image.convert('RGBA').getpixel((45, 75))[3])
            self.assertEqual(alpha[0], 0)
            self.assertTrue(120 <= alpha[1] <= 135, alpha)
            self.assertEqual(alpha[2:], [255, 255])
            def decode(directory):
                metadata = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-count_frames', '-show_streams', '-of', 'json', str(directory/'intro.mp4')]))['streams']
                self.assertEqual(len(metadata), 1)
                self.assertEqual((metadata[0]['codec_name'], metadata[0]['nb_read_frames'], metadata[0]['r_frame_rate']), ('h264', '12', '12/1'))
                raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(directory/'intro.mp4'), '-f', 'rawvideo', '-pix_fmt', 'rgb24', 'pipe:1'])
                size = 320*180*3
                self.assertEqual(len(raw), size*12)
                offset = (75*320+45)*3
                return [list(raw[i*size+offset:i*size+offset+3]) for i in range(12)]
            pixels = decode(first)
            self.assertLessEqual(max(pixels[0]), 5)
            self.assertTrue(110 <= pixels[3][0] <= 130, pixels)
            self.assertTrue(230 <= pixels[6][0] <= 245, pixels)
            self.assertTrue(all(pixels[i+1][0] >= pixels[i][0]-2 for i in range(11)), pixels)
            second = root / 'revised'
            revised = workflow.execute({'expectedProjectSha256': receipt['files']['project.ecproj'], 'operations': [{'command': 'layer.setText', 'params': {'layer': {'$ref': 'title.layer'}, 'text': 'NOVA PLUS'}}], 'frames': plan['frames'], 'exports': [{'format': 'mp4'}]}, second, runtime_home=runtime, source=first)
            updated = json.loads((second / 'native.json').read_text())
            self.assertEqual(native['layers'][badge], updated['layers'][badge])
            self.assertEqual(property_at(native['layers'][title]['properties'], 'transform/opacity'), property_at(updated['layers'][title]['properties'], 'transform/opacity'))
            self.assertEqual(property_at(updated['layers'][title]['properties'], 'text/sourceText')['value'], 'NOVA PLUS')
            revised_pixels = decode(second)
            self.assertTrue(all(abs(a-b) <= 3 for old,new in zip(pixels,revised_pixels) for a,b in zip(old,new)), (pixels,revised_pixels))
            self.assertEqual(receipt['files']['frame-0000.png'], revised['files']['frame-0000.png'])
            self.assertNotEqual(receipt['files']['frame-0002.png'], revised['files']['frame-0002.png'])
            for name, expected in receipt['files'].items():
                self.assertEqual(workflow.sha(first/name), expected)
            self.assertEqual(tree_hash(skill), original_hash)
            self.assertEqual(tree_hash(original), original_hash)
            evidence = {'schema':'craft-effect-temporal-first-use/v1', 'result':'passed', 'nativeVersion':'0.2.0', 'skillSha256':original_hash, 'runtimeMode':'single installed skill copied alone; empty runtime; default public installation', 'rgbaAlpha':alpha, 'videoBadgeRgb':pixels, 'revisedVideoBadgeRgb':revised_pixels, 'firstFiles':receipt['files'], 'revisedFiles':revised['files'], 'preserved':['badge layer and keys','title opacity keys','all first delivery files','installed skill bytes'], 'unverified':['animated transparent video','all interpolation modes','model dispatch','GUI','creative acceptance']}
            if os.environ.get('CRAFT_TEMPORAL_EVIDENCE'):
                target = Path(os.environ['CRAFT_TEMPORAL_EVIDENCE'])
                with target.open('x') as output:
                    json.dump(evidence, output, ensure_ascii=False, indent=2)
                    output.write('\n')


if __name__ == '__main__':
    unittest.main()
