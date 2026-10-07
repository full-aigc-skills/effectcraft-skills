"""三维摄像机场景须有可执行的渲染、重开和受限修订计划。"""
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class CameraSceneTests(unittest.TestCase):
 def test_camera_scene_contains_native_prerequisites_and_revision(self):
  base=ROOT/'skills/effectcraft-use'
  plan=json.loads((base/'examples/camera-scene-create.json').read_text())
  ids={x.get('command') for x in plan['operations']}
  self.assertTrue({'comp.new','comp.renderer','layer.new3dPrimitive','material.set','layer.newLight','layer.newCamera','layer.cameraSettings','view.set3DView','camera.orbit','camera.pan','camera.dolly','view.get3D','camera.linkFocusToPoi'}.issubset(ids))
  self.assertTrue(any(x.get('tool')=='render_frame' for x in plan['operations']))
  for name in ('reopen','revise'):
   q=json.loads((base/f'examples/camera-scene-{name}.json').read_text());self.assertEqual(q['operations'][0]['tool'],'open_project')
  guide=(base/'references/camera-scene.md').read_text();self.assertIn('view.set3DView',guide);self.assertIn('camera.solveStatus',guide)
  owned=json.loads((base/'references/command-coverage.json').read_text())['commands']
  for row in owned:
   if row['ownerSkill']=='effectcraft-cli-camera':self.assertIn(row['id'],guide)
if __name__=='__main__':unittest.main()
