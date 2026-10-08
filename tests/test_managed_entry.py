"""公开管理入口的只读预检与实际执行接线。"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT=Path(__file__).resolve().parents[1]/'skills/effectcraft-use/scripts/managed.py'


class ManagedEntryTests(unittest.TestCase):
    def invoke(self, *args, env=None):
        self.assertTrue(SCRIPT.exists(), 'managed public entry is missing')
        result=subprocess.run([sys.executable,'-I','-B',str(SCRIPT),*map(str,args)],capture_output=True,text=True,env=env)
        return result,json.loads(result.stdout)

    def test_doctor_is_read_only_when_no_runtime_installed(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            result,data=self.invoke('--runtime-home',root/'runtime','--state-root',root/'state','doctor')
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertFalse(data['runtime']['installed'])
            self.assertFalse((root/'runtime').exists());self.assertFalse((root/'state').exists())

    def test_invalid_plan_does_not_install_or_register_task(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);plan=root/'bad.json'
            plan.write_text(json.dumps({'schema':'craft-command-plan/v1','operations':[{'command':'missing','params':{}}]}))
            result,data=self.invoke('--runtime-home',root/'runtime','--state-root',root/'state','run','--plan',plan,'--output',root/'output','--mode','commands')
            self.assertNotEqual(result.returncode,0)
            self.assertIn('unknown_command',data['error'])
            self.assertFalse((root/'runtime').exists());self.assertFalse((root/'state').exists())

    def test_valid_plan_preflight_has_no_side_effects(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);plan=root/'plan.json'
            plan.write_text(json.dumps({'document':{'name':'preview','width':320,'height':240,'frameRate':24,'duration':1},'operations':[]}))
            result,data=self.invoke('--runtime-home',root/'runtime','--state-root',root/'state','plan','--plan',plan,'--output',root/'output')
            self.assertEqual(result.returncode,0,data)
            self.assertEqual(data['result'],'VALID')
            self.assertFalse((root/'runtime').exists());self.assertFalse((root/'state').exists())
