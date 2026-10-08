"""分发生成器显式读取UTF-8，不能依赖Windows默认cp1252。"""
from pathlib import Path
import runpy
import sys
import unittest
import importlib.util
import json
import tempfile
import subprocess
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]


class GeneratorEncodingTests(unittest.TestCase):
    def test_cli_help_survives_redirected_windows_codepage(self):
        script=ROOT/'skills/effectcraft-use/scripts/cli.py'
        code="import sys,runpy;sys.stdout.reconfigure(encoding='cp1252');sys.stderr.reconfigure(encoding='cp1252');runpy.run_path(sys.argv.pop(1),run_name='__main__')"
        result=subprocess.run([sys.executable,'-I','-B','-c',code,str(script),'--help'],capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr.decode('utf-8',errors='replace'))
        self.assertIn('独立技能',result.stdout.decode('utf-8'))

    def test_runtime_contract_and_unicode_receipt_use_utf8(self):
        read=Path.read_text;write=Path.write_text
        def windows_read(path,encoding=None,errors=None,**kwargs):
            return read(path,encoding=encoding or 'cp1252',errors=errors,**kwargs)
        def windows_write(path,data,encoding=None,errors=None,**kwargs):
            return write(path,data,encoding=encoding or 'cp1252',errors=errors,**kwargs)
        with patch.object(Path,'read_text',windows_read),patch.object(Path,'write_text',windows_write),tempfile.TemporaryDirectory() as directory:
            spec=importlib.util.spec_from_file_location('utf8_commands',ROOT/'skills/effectcraft-use/scripts/commands.py')
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            self.assertTrue(module.catalog()['commands'])
            path=Path(directory)/'receipt.json';module.write(path,{'text':'中文作品'})
            self.assertEqual(json.loads(path.read_bytes().decode('utf-8')),{'text':'中文作品'})

    def test_generators_read_unicode_contracts_with_windows_default_encoding(self):
        native=Path.read_text
        def windows_default(path,encoding=None,errors=None,**kwargs):
            return native(path,encoding=encoding or 'cp1252',errors=errors,**kwargs)
        for name in ['build_command_coverage','build_scenario_catalog','build_capability_matrix','sync_skill_suite']:
            with self.subTest(generator=name),patch.object(Path,'read_text',windows_default),patch.object(sys,'argv',[name,'--check']):
                runpy.run_path(str(ROOT/'scripts'/(name+'.py')),run_name='__main__')
