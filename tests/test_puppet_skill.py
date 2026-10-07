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
 def test_record_follow_recipe_covers_each_puppet_command_and_revision(self):
  base=ROOT/'skills/effectcraft-use'
  create=json.loads((base/'examples/puppet-record-follow-create.json').read_text())
  family={row['id'] for row in json.loads((base/'references/command-coverage.json').read_text())['commands'] if row['id'].startswith('puppet.')}
  self.assertTrue(family.issubset({step.get('command') for step in create['operations']}))
  for name in ['puppet-record-follow-reopen.json','puppet-record-follow-revise.json']:
   plan=json.loads((base/'examples'/name).read_text())
   self.assertEqual(plan['operations'][0]['tool'],'open_project')
   self.assertEqual(plan['operations'][0]['params']['path'],{'$ref':'project.path'})
  revise=json.loads((base/'examples/puppet-record-follow-revise.json').read_text())
  self.assertTrue(any(step.get('command')=='puppet.recordOptions' for step in revise['operations']))
  self.assertTrue(any(step.get('command')=='puppet.recordPin' for step in revise['operations']))
if __name__=='__main__':unittest.main()
