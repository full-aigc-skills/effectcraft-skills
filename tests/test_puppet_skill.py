"""木偶图层动画有独立入口和完整针脚命令归属。"""
from pathlib import Path
import json,unittest
ROOT=Path(__file__).resolve().parents[1]
class PuppetSkillTests(unittest.TestCase):
 def test_puppet_family_has_independent_local_resources(self):
  name='effectcraft-cli-puppet';suite=json.loads((ROOT/'skill-suite.json').read_text());skills={x['name']:x for x in suite['skills']};self.assertIn(name,skills);self.assertEqual(skills[name]['kind'],'scenario')
  rows=json.loads((ROOT/'skills/effectcraft-use/references/command-coverage.json').read_text())['commands'];family=[x for x in rows if x['id'].startswith('puppet.')];self.assertEqual(len(family),10);self.assertTrue(all(x['ownerSkill']==name for x in family))
  for item in ['SKILL.md','scripts/bootstrap.py','scripts/commands.py','scripts/runtime.lock.json','references/puppet-scene.md']:
   self.assertTrue((ROOT/'skills'/name/item).is_file(),item)
if __name__=='__main__':unittest.main()
