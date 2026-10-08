"""技能默认写入示例必须进入对应模式，旧状态诊断不能升级为执行。"""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'skills/effectcraft-use'
class ManagedSkillRoutingTests(unittest.TestCase):
 def test_every_skill_routes_command_and_desktop_writes_through_managed_launcher(self):
  for row in json.loads((ROOT/'skill-suite.json').read_text())['skills']:
   with self.subTest(skill=row['name']):
    text=(ROOT/'skills'/row['name']/'SKILL.md').read_text()
    self.assertIn('launch.sh" run --mode commands --plan "$SKILL_DIR/examples/commands-advanced.json"',text)
    self.assertIn('launch.sh" run --mode desktop --plan "$SKILL_DIR/examples/desktop-first-use.json"',text)
    self.assertNotRegex(text,r'(?m)^python3 .*commands\.py" run ')
    self.assertLess(len(text.splitlines()),500)
 def test_documented_mode_plans_preflight_from_every_independent_skill_without_writes(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp)
   for row in json.loads((ROOT/'skill-suite.json').read_text())['skills']:
    skill=ROOT/'skills'/row['name']
    for mode,name in [('workflow','brand-intro.json'),('commands','commands-advanced.json'),('desktop','desktop-first-use.json')]:
     with self.subTest(skill=row['name'],mode=mode):
      r=subprocess.run([sys.executable,'-I','-B',str(skill/'scripts/managed.py'),'--state-root',str(root/'state'),'--runtime-home',str(root/'runtime'),'plan','--mode',mode,'--plan',str(skill/'examples'/name),'--output',str(root/'output')],capture_output=True,text=True,encoding='utf-8')
      self.assertEqual(r.returncode,0,r.stdout+r.stderr);self.assertEqual(json.loads(r.stdout)['result'],'VALID');self.assertEqual(list(root.iterdir()),[])
 def test_legacy_inspect_is_readonly_in_all_modes_and_mutating_actions_refuse(self):
  spec=importlib.util.spec_from_file_location('routing_store',BASE/'scripts/task_store.py');tasks=importlib.util.module_from_spec(spec);spec.loader.exec_module(tasks)
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);criteria=root/'criteria.json';criteria.write_text('{}');plan=root/'revision.json';plan.write_text('{}')
   def snapshot():return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
   for mode in ['workflow','commands','desktop']:
    store=tasks.Store(root/mode);store.create('legacy',plan={},output=str(root/(mode+' old output')),runtime_sha='a'*64,inputs={},source=None,mode=mode,authorization={})
    state=store.read('legacy');state['schema']='effectcraft-managed-task/v1';store.save(state);before=snapshot()
    for action in ['inspect','cancel','reconcile','resume','review','revise']:
     args=[action,'--task','legacy']
     if action=='review':args+=['--criteria',str(criteria)]
     if action=='revise':args+=['--plan',str(plan),'--output',str(root/'new output')]
     r=subprocess.run([sys.executable,'-I','-B',str(BASE/'scripts/managed.py'),'--state-root',str(store.root),'--runtime-home',str(root/'absent runtime'),*args],capture_output=True,text=True,encoding='utf-8')
     v=json.loads(r.stdout)
     if action=='inspect':self.assertEqual(r.returncode,0);self.assertEqual(v['schema'],'effectcraft-managed-task/v1')
     else:self.assertEqual(r.returncode,1);self.assertIn('legacy',v['error'])
     self.assertEqual(snapshot(),before);self.assertNotIn('Traceback',r.stderr)
