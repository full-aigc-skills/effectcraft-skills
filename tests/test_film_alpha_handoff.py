"""EffectCraft 原生透明结果导入 FilmCraft 的实际合成交接。"""
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
TICKS = 254016000000


def load_workflow(skill, name):
    spec = importlib.util.spec_from_file_location(name, skill / 'scripts/workflow.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(os.environ.get('CRAFT_EFFECT_FILM_ALPHA_HANDOFF') == '1', 'requires two installed skills, public native runtimes and existing ffmpeg/Pillow')
class FilmAlphaHandoffTests(unittest.TestCase):
    def test_transparent_native_frame_composites_and_text_revision_preserves_animation(self):
        from PIL import Image
        with tempfile.TemporaryDirectory(prefix='craft-alpha-handoff-') as temporary:
            root = Path(temporary)
            effect = root / '.agents/skills/effectcraft-cli-export'
            film = root / '.agents/skills/filmcraft-cli-media'
            shutil.copytree(os.environ['CRAFT_INSTALLED_EFFECT_EXPORT_SKILL'], effect, ignore=shutil.ignore_patterns('__pycache__'))
            shutil.copytree(os.environ['CRAFT_INSTALLED_FILM_MEDIA_SKILL'], film, ignore=shutil.ignore_patterns('__pycache__'))
            ew = load_workflow(effect, 'effect_alpha_workflow')
            fw = load_workflow(film, 'film_alpha_workflow')
            eruntime, fruntime = root / 'effect-empty-runtime', root / 'film-empty-runtime'
            self.assertFalse(eruntime.exists()); self.assertFalse(fruntime.exists())
            first = root / 'intro'
            delivered = ew.execute(json.loads((effect / 'examples/brand-intro.json').read_text()), first, runtime_home=eruntime)
            native = json.loads((first / 'native.json').read_text())
            change = {'expectedProjectSha256': delivered['files']['project.ecproj'], 'operations': [{'command': 'layer.setText', 'params': {'layer': {'$ref': 'title.layer'}, 'text': 'NOVA PLUS'}}], 'frames': [0, .5], 'exports': [{'format': 'mp4'}]}
            second = root / 'revised-intro'
            revised = ew.execute(change, second, runtime_home=eruntime, source=first)
            updated = json.loads((second / 'native.json').read_text())
            badge, title = str(delivered['bindings']['badge']['layer']), str(delivered['bindings']['title']['layer'])
            self.assertEqual(native['layers'][badge], updated['layers'][badge])
            def opacity(node):
                if node.get('path') == 'transform/opacity': return node
                for child in node.get('children', []):
                    found = opacity(child)
                    if found is not None: return found
            self.assertEqual(opacity(native['layers'][title]['properties']), opacity(updated['layers'][title]['properties']))
            self.assertEqual(delivered['files']['frame-0000.png'], revised['files']['frame-0000.png'])
            self.assertNotEqual(delivered['files']['frame-0001.png'], revised['files']['frame-0001.png'])
            overlay = second / 'frame-0001.png'
            with Image.open(overlay) as image:
                alpha = image.convert('RGBA').getchannel('A')
                self.assertEqual(alpha.getextrema(), (0, 255))
                self.assertEqual(alpha.getpixel((5, 5)), 0)
                self.assertEqual(alpha.getpixel((40, 85)), 255)
            background = root / 'green.mp4'
            subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=green:s=320x180:r=12:d=1', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(background)], check=True)
            plan = {'document': {'name': 'Alpha handoff', 'width': 320, 'height': 180, 'frameRate': {'num': 12, 'den': 1}}, 'assets': {key: {'path': str(path), 'sha256': fw.sha(path)} for key, path in [('background', background), ('overlay', overlay)]}, 'operations': [
                {'command': 'asset.import', 'params': {'asset': 'background'}, 'as': 'background'},
                {'command': 'asset.import', 'params': {'asset': 'overlay'}, 'as': 'overlay'},
                {'command': 'timeline.place', 'params': {'item': {'$ref': 'background.item'}, 'track': 'V1', 'time': '0', 'sourceIn': '0', 'duration': str(TICKS), 'insert': False}},
                {'command': 'timeline.place', 'params': {'item': {'$ref': 'overlay.item'}, 'track': 'V2', 'time': '0', 'sourceIn': '0', 'duration': str(TICKS), 'insert': False}}], 'frames': [str(TICKS // 2)], 'export': {'audioRequired': False}}
            output = root / 'film'
            composite = fw.execute(plan, output, runtime_home=fruntime)
            probe = composite['assets']['overlay']['probe']
            self.assertEqual(probe['kind'], 'Still')
            self.assertTrue(probe['video']['has_alpha'])
            with Image.open(output / 'frame-0000.png') as frame:
                corner = frame.convert('RGB').getpixel((5, 5)); badge_pixel = frame.convert('RGB').getpixel((40, 85))
            self.assertGreater(corner[1], 100); self.assertLess(corner[0], 10); self.assertLess(corner[2], 10)
            with Image.open(overlay) as foreground, Image.open(output / 'frame-0000.png') as rendered:
                pairs = zip(foreground.convert('RGBA').getdata(), rendered.convert('RGB').getdata())
                opaque_count = 0
                for original, actual in pairs:
                    if original[3] == 255:
                        opaque_count += 1
                        self.assertLessEqual(max(abs(original[channel] - actual[channel]) for channel in range(3)), 2)
                self.assertGreater(opaque_count, 100)
            self.assertGreater(badge_pixel[0], 200); self.assertLess(badge_pixel[1], 120)
            pixels = subprocess.check_output(['ffmpeg', '-v', 'error', '-ss', '0.5', '-i', str(output / 'film.mp4'), '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'])
            decoded_corner = list(pixels[(5 * 320 + 5) * 3:(5 * 320 + 5) * 3 + 3])
            self.assertGreater(decoded_corner[1], 100); self.assertLess(decoded_corner[0], 10); self.assertLess(decoded_corner[2], 10)
            self.assertEqual(ew.sha(first / 'project.ecproj'), delivered['files']['project.ecproj'])
            self.assertEqual(ew.sha(overlay), revised['files']['frame-0001.png'])
            self.assertFalse(list(effect.rglob('*.pyc'))); self.assertFalse(list(film.rglob('*.pyc')))
            if os.environ.get('CRAFT_EFFECT_FILM_ALPHA_EVIDENCE'):
                evidence = {'schema': 'effectcraft-filmcraft-alpha-handoff/v1', 'result': 'passed', 'effectRuntimeSha256': revised['runtimeSha256'], 'filmRuntimeSha256': composite['runtimeSha256'], 'effectProjectSha256': revised['files']['project.ecproj'], 'overlaySha256': fw.sha(overlay), 'filmProjectSha256': composite['files']['project.fcproj'], 'filmVideoSha256': composite['files']['film.mp4'], 'overlayProbe': probe, 'previewCorner': corner, 'previewBadge': badge_pixel, 'decodedCorner': decoded_corner, 'opaquePixelsVerified': opaque_count, 'animationPreserved': True, 'badgeLayerPreserved': True, 'sourceProjectPreserved': True, 'scope': 'one installed skill per domain; each empty runtime; static transparent PNG handoff, not animated alpha video or all color pipelines'}
                with Path(os.environ['CRAFT_EFFECT_FILM_ALPHA_EVIDENCE']).open('x') as stream: json.dump(evidence, stream, indent=2)
