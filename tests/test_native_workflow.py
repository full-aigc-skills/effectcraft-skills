"""真实引擎往返、局部修改和解码验收；需要显式启用。"""
import importlib.util
import sys

# 宿主技能快照必须保持不可变；动态导入也不写字节码。
sys.dont_write_bytecode = True
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = Path(os.environ['CRAFT_INSTALLED_SKILL_ROOT']).resolve() if os.environ.get('CRAFT_INSTALLED_SKILL_ROOT') else ROOT / 'skills/effectcraft-use'
spec = importlib.util.spec_from_file_location('workflow', SKILL / 'scripts/workflow.py')
workflow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(workflow)


def property_at(node, path):
    if node.get('path') == path:
        return node
    for child in node.get('children', []):
        found = property_at(child, path)
        if found is not None:
            return found
    return None


@unittest.skipUnless(os.environ.get('CRAFT_LIVE_TEST') == '1', 'requires real runtime')
class NativeWorkflowTests(unittest.TestCase):
    def test_intro_roundtrip_and_text_revision(self):
        from PIL import Image
        plan = json.loads((SKILL / 'examples/brand-intro.json').read_text())
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first, second = root / 'v1', root / 'v2'
            delivered = workflow.execute(plan, first)
            native = json.loads((first / 'native.json').read_text())
            badge = str(delivered['bindings']['badge']['layer'])
            title = str(delivered['bindings']['title']['layer'])
            opacity = property_at(native['layers'][title]['properties'], 'transform/opacity')
            self.assertEqual([(x['time'], x['value']) for x in opacity['keys']], [(0, 0), (.5, 100)])
            with Image.open(first / 'frame-0001.png') as source:
                frame = source.convert('RGBA')
                self.assertEqual(frame.size, (320, 180))
                self.assertEqual(frame.getchannel('A').getextrema(), (0, 255))
            info = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-count_frames', '-show_streams', '-of', 'json', str(first / 'intro.mp4')]))
            streams = info['streams']
            self.assertEqual(len(streams), 1)
            self.assertEqual((streams[0]['codec_name'], streams[0]['width'], streams[0]['height'], streams[0]['nb_read_frames']), ('h264', 320, 180, '12'))
            change = {'expectedProjectSha256': delivered['files']['project.ecproj'],
                      'operations': [{'command': 'layer.setText', 'params': {'layer': {'$ref': 'title.layer'}, 'text': 'NOVA PLUS'}}],
                      'frames': [0, .5], 'exports': [{'format': 'mp4'}]}
            revised = workflow.execute(change, second, source=first)
            after = json.loads((second / 'native.json').read_text())
            self.assertEqual(native['layers'][badge], after['layers'][badge])
            self.assertEqual(opacity, property_at(after['layers'][title]['properties'], 'transform/opacity'))
            self.assertEqual(property_at(after['layers'][title]['properties'], 'text/sourceText')['value'], 'NOVA PLUS')
            self.assertEqual(delivered['files']['project.ecproj'], workflow.sha(first / 'project.ecproj'))
            self.assertEqual(delivered['files']['frame-0000.png'], revised['files']['frame-0000.png'])
            self.assertNotEqual(delivered['files']['frame-0001.png'], revised['files']['frame-0001.png'])
            change['expectedProjectSha256'] = '0' * 64
            with self.assertRaisesRegex(ValueError, 'revision_conflict'):
                workflow.execute(change, root / 'conflict', source=first)
            self.assertFalse((root / 'conflict').exists())

if __name__ == '__main__':
    unittest.main()
