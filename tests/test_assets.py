"""依赖收集及移动后的 Logo 替换；使用程序化 PNG 验证真实引擎。"""
import importlib.util
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('workflow', ROOT / 'skills/effectcraft-use/scripts/workflow.py')
workflow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(workflow)


def image(path, color):
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
    scan = b''.join(b'\0' + bytes(color) * 64 for _ in range(48))
    path.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 64, 48, 8, 6, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(scan)) + chunk(b'IEND', b''))


@unittest.skipUnless(os.environ.get('CRAFT_LIVE_TEST') == '1', 'requires real CLI and Pillow')
class AssetTests(unittest.TestCase):
    def test_collect_move_and_replace_asset_without_changing_animation(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original, replacement = root / 'logo.png', root / 'new.png'
            image(original, (240, 60, 10, 255)); image(replacement, (10, 80, 240, 255))
            plan = {'document': {'name': 'Logo intro', 'width': 160, 'height': 120, 'frameRate': 12, 'duration': 1},
                    'assets': {'logo': {'path': str(original), 'sha256': workflow.sha(original)}},
                    'operations': [{'command': 'asset.import', 'params': {'asset': 'logo'}, 'as': 'logo'},
                                   {'command': 'layer.addItem', 'params': {'item': {'$ref': 'logo.item'}, 'duration': 1}, 'as': 'logoLayer'},
                                   {'command': 'prop.addKey', 'params': {'layer': {'$ref': 'logoLayer.layer'}, 'path': 'transform/opacity', 'time': 0, 'value': 0}},
                                   {'command': 'prop.addKey', 'params': {'layer': {'$ref': 'logoLayer.layer'}, 'path': 'transform/opacity', 'time': .5, 'value': 100}}],
                    'frames': [0, .5], 'exports': [{'format': 'mp4'}]}
            first = root / 'v1'; manifest = workflow.execute(plan, first)
            collected = first / manifest['assets']['logo']['path']
            self.assertEqual(workflow.sha(collected), workflow.sha(original))
            before = json.loads((first / 'native.json').read_text())
            first.rename(root / 'moved'); original.unlink()
            change = {'expectedProjectSha256': manifest['files']['project.ecproj'],
                      'assets': {'replacement': {'path': str(replacement), 'sha256': workflow.sha(replacement)}},
                      'operations': [{'command': 'asset.replace', 'params': {'asset': 'logo', 'replacement': 'replacement'}}],
                      'frames': [0, .5], 'exports': [{'format': 'mp4'}]}
            revised = workflow.execute(change, root / 'v2', source=root / 'moved')
            after = json.loads((root / 'v2/native.json').read_text())
            self.assertEqual(before['layers'], after['layers'])
            self.assertEqual(workflow.sha(root / 'moved/project.ecproj'), manifest['files']['project.ecproj'])
            self.assertEqual(workflow.sha(root / 'v2' / revised['assets']['logo']['path']), workflow.sha(replacement))
            with Image.open(root / 'v2/frame-0001.png') as rendered:
                pixel = rendered.convert('RGBA').getpixel((80, 60))
                self.assertGreater(pixel[2], pixel[0])
            bad = dict(change, assets={'replacement': {'path': str(replacement), 'sha256': '0'*64}})
            with self.assertRaisesRegex(ValueError, 'asset_digest_mismatch'):
                workflow.execute(bad, root / 'bad', source=root / 'moved')
            self.assertFalse((root / 'bad').exists())

if __name__ == '__main__':
    unittest.main()
