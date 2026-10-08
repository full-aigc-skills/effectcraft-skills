"""诊断不得安装或编辑，实际能力必须来自已验证CLI的只读返回。"""
import copy
import base64
import importlib.util
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch,Mock

ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'skills/effectcraft-use'
def module(name):
    path=BASE/'scripts'/(name+'.py');spec=importlib.util.spec_from_file_location('doctor_test_'+name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result

class ManagedDoctorTests(unittest.TestCase):
    def setUp(self):
        self.managed=module('managed');self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.home=self.root/'runtime';self.original=self.managed.load
        self.probe=Mock(return_value={'status':'PASS','actualVersionOutput':'effectcraft-cli 0.4.0','scope':'readonly registry','executionAcceptance':'NOT_RUN'})
        self.platform=SimpleNamespace(platform_key=lambda:'darwin-arm64',check_minimum=Mock())
        self.bootstrap=SimpleNamespace(inspect_install=Mock(return_value={'executable':'verified-cli','binarySha256':'a'*64}))
        def load(name):
            if name=='platform_support':return self.platform
            if name=='bootstrap':return self.bootstrap
            if name=='native_diagnostics':return SimpleNamespace(observe=self.probe)
            return self.original(name)
        self.managed.load=load

    def installed(self):
        (self.home/'effectcraft/0.4.0').mkdir(parents=True)

    def test_missing_runtime_reports_locked_dependencies_and_executable_recovery_without_writes(self):
        result=self.managed.doctor(self.home)
        self.assertEqual(result['pythonRuntime']['lockedVersion'],'3.13.16')
        self.assertEqual(result['nativeCapabilities']['status'],'NOT_RUN')
        self.assertEqual(result['catalog']['commandCount'],655)
        self.assertEqual(result['recoveryActions'][0]['id'],'install_pinned_cli')
        self.assertIn('bootstrap.py',result['recoveryActions'][0]['argv'][3])
        self.assertFalse(self.home.exists());self.probe.assert_not_called()

    def test_default_valid_runtime_is_static_only(self):
        self.installed();result=self.managed.doctor(self.home)
        self.assertTrue(result['runtime']['installed']);self.probe.assert_not_called()
        self.assertEqual(result['nativeCapabilities']['status'],'NOT_RUN')
        self.assertEqual(result['recoveryActions'][0]['id'],'probe_native')

    def test_explicit_probe_uses_verified_executable_and_does_not_promote_creative_acceptance(self):
        self.installed();result=self.managed.doctor(self.home,probe_native=True)
        self.assertEqual(result['nativeCapabilities']['status'],'PASS');self.probe.assert_called_once()
        self.assertEqual(self.probe.call_args.args[0],'verified-cli')
        self.assertEqual(result['acceptance']['nativePlatform'],'NOT_RUN')
        self.assertEqual(result['runtime']['actualVersionOutput'],'effectcraft-cli 0.4.0')

    def test_minimum_system_failure_blocks_probe(self):
        self.installed();self.platform.check_minimum.side_effect=ValueError('minimum_macos_required')
        result=self.managed.doctor(self.home,probe_native=True)
        self.probe.assert_not_called();self.assertIn('platformError',result['runtime'])
        self.assertEqual(result['nativeCapabilities']['status'],'NOT_RUN')

    def test_corrupt_runtime_is_preserved_and_never_probed(self):
        self.installed();file=self.home/'effectcraft/0.4.0/corrupt';file.write_bytes(b'keep')
        self.bootstrap.inspect_install.side_effect=ValueError('installed_checksum_mismatch')
        result=self.managed.doctor(self.home,probe_native=True)
        self.assertFalse(result['runtime']['installed']);self.assertEqual(file.read_bytes(),b'keep')
        self.probe.assert_not_called();self.assertEqual(result['recoveryActions'][0]['id'],'inspect_preserved_runtime')

    def test_missing_runtime_probe_does_not_install(self):
        result=self.managed.doctor(self.home,probe_native=True)
        self.assertFalse(self.home.exists());self.probe.assert_not_called()
        self.assertEqual(result['nativeCapabilities']['status'],'NOT_RUN')

    def test_public_doctor_compares_catalog_without_state_or_runtime_writes(self):
        baseline=self.root/'old.json';baseline.write_bytes((BASE/'references/command-coverage.json').read_bytes())
        result=subprocess.run([sys.executable,'-I','-B',str(BASE/'scripts/managed.py'),'--runtime-home',str(self.home),'--state-root',str(self.root/'state'),'doctor','--compare-catalog',str(baseline)],capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr.decode('utf-8',errors='replace'))
        data=json.loads(result.stdout);self.assertEqual(data['commandDiff']['commands']['changed'],[])
        self.assertFalse(self.home.exists());self.assertFalse((self.root/'state').exists())

    def test_bad_comparison_baseline_prevents_native_probe(self):
        self.installed();bad=self.root/'bad.json';bad.write_text('{"schema":1,"schema":2}',encoding='utf-8')
        with self.assertRaises(ValueError):self.managed.doctor(self.home,probe_native=True,compare_catalog=bad)
        self.probe.assert_not_called();self.bootstrap.inspect_install.assert_not_called()

    def test_dangling_runtime_symlink_is_reported_and_preserved(self):
        self.bootstrap=self.original('bootstrap');parent=self.home/'effectcraft';parent.mkdir(parents=True)
        link=parent/'0.4.0'
        try:link.symlink_to(self.root/'absent',target_is_directory=True)
        except OSError as error:self.skipTest('symlink unavailable: '+str(error))
        result=self.managed.doctor(self.home,probe_native=True)
        self.assertFalse(result['runtime']['installed']);self.assertEqual(result['runtime']['error'],'invalid_installed_path')
        self.assertTrue(link.is_symlink());self.probe.assert_not_called()

    def test_no_python_launcher_returns_usable_recovery_argv_with_quoted_path(self):
        name='skill quoted path' if os.name=='nt' else 'skill "quoted" path'
        skill=self.root/name;shutil.copytree(BASE,skill,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        env={**os.environ,'CRAFT_PYTHON_HOME':str(self.root/'missing python'),'CRAFT_RUNTIME_HOME':str(self.home)}
        if os.name=='nt':
            call=['powershell.exe','-NoProfile','-NonInteractive','-File',str(skill/'scripts/launch.ps1'),'doctor']
        else:call=['/bin/sh',str(skill/'scripts/launch.sh'),'doctor']
        result=subprocess.run(call,capture_output=True,env=env,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr.decode('utf-8',errors='replace'))
        data=json.loads(result.stdout);action=data['recoveryActions'][0]
        self.assertEqual(action['id'],'prepare_pinned_python');self.assertFalse(action['automatic'])
        self.assertEqual(action['argv'][-1],'--python-version')
        entry=skill/'scripts'/('launch.ps1' if os.name=='nt' else 'launch.sh')
        self.assertIn(str(entry),action['argv'])
        self.assertFalse(Path(env['CRAFT_PYTHON_HOME']).exists());self.assertFalse(self.home.exists())

    def test_powershell_cold_recovery_json_preserves_unicode_under_non_utf8_console(self):
        engine=shutil.which('powershell.exe') or shutil.which('pwsh')
        if not engine:self.skipTest('PowerShell engine unavailable; target evidence remains NOT_RUN')
        # 单独执行实际JSON返回分支；这不运行或绕过Windows平台启动守卫。
        skill=self.root/'技能 space';entry=skill/'scripts/launch.ps1';quoted=str(skill/'scripts').replace("'","''")
        source=(BASE/'scripts/launch.ps1').read_text(encoding='utf-8')
        branch=source[source.index('if ($readOnly -and -not'):source.index('if (-not $readOnly)')]
        encoding='\n'.join(line for line in source.splitlines() if line.startswith('[Console]::OutputEncoding') or line.startswith('$OutputEncoding ='))
        code="[Console]::OutputEncoding=[Text.Encoding]::GetEncoding(1252);\n"+encoding+"\n$scriptRoot='"+quoted+"'; $base='"+str(self.root/'missing python').replace("'","''")+"'; $lockData=@{version='3.13.16'}; $key='windows-arm64'; $readOnly=$true;\n"+branch
        encoded=base64.b64encode(code.encode('utf-16le')).decode('ascii')
        result=subprocess.run([engine,'-NoProfile','-NonInteractive','-EncodedCommand',encoded],capture_output=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr.decode('utf-8',errors='replace'))
        data=json.loads(result.stdout.decode('utf-8'));self.assertIn(str(entry),data['recoveryActions'][0]['argv'])
        self.assertFalse((self.root/'missing python').exists())


class NativeDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((BASE/'scripts/native_diagnostics.py').is_file(),'native readonly diagnostics missing')
        self.module=module('native_diagnostics');self.original=self.module.load
        self.catalog=json.loads((BASE/'references/command-coverage.json').read_text(encoding='utf-8'))
        self.tools=[{'name':n,'inputSchema':s} for n,s in self.catalog['nativeToolSchemas'].items()]
        self.rows=[{'id':r['id'],'enabled':True} for r in self.catalog['commands']]
        self.calls=[];self.closed=False;outer=self
        class Session:
            def __init__(self,argv,timeout):outer.argv=argv;outer.timeout=timeout
            def __enter__(self):return self
            def __exit__(self,*args):outer.closed=True
            def request(self,method,params):
                outer.calls.append((method,params))
                if method=='tools/list':return {'tools':outer.tools}
                return {'content':[{'type':'text','text':json.dumps({'commands':outer.rows})}]}
        self.factory=Mock(side_effect=Session)
        self.module.load=lambda name:SimpleNamespace(Session=self.factory) if name=='mcp_session' else self.original(name)
        self.run=patch.object(self.module.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout='effectcraft-cli 0.4.0\n',stderr=''))
        self.process=self.run.start();self.addCleanup(self.run.stop)

    def observe(self):return self.module.observe('verified-cli',self.catalog,'effectcraft-cli 0.4.0')

    def test_actual_adapter_reply_types_and_queries_are_readonly_and_closed(self):
        r=self.observe();self.assertEqual(r['status'],'PASS');self.assertTrue(self.closed)
        self.assertEqual(r['commandCount'],655);self.assertEqual(r['toolCount'],22)
        self.assertEqual(self.argv,['verified-cli','--empty','mcp']);self.assertLessEqual(self.timeout,15)
        self.assertEqual(self.calls[1],('tools/call',{'name':'list_commands','arguments':{}}))
        self.assertEqual(r['executionAcceptance'],'NOT_RUN')

    def test_version_mismatch_prevents_mcp_launch(self):
        self.process.return_value.stdout='effectcraft-cli 999\n';r=self.observe()
        self.assertEqual(r['status'],'FAIL');self.factory.assert_not_called()

    def test_schema_drift_reports_failure_without_edits(self):
        self.tools[0]['inputSchema']={'unexpected':True};r=self.observe()
        self.assertEqual(r['status'],'FAIL');self.assertEqual(r['changedTools'],[self.tools[0]['name']])
        self.assertTrue(self.closed);self.assertEqual(len(self.calls),2)

    def test_missing_added_and_duplicate_commands(self):
        self.rows.pop();self.rows.append({'id':'new.command','enabled':True});r=self.observe()
        self.assertEqual(r['status'],'FAIL');self.assertEqual(r['addedCommands'],['new.command'])
        self.rows.append(copy.deepcopy(self.rows[0]));r=self.observe();self.assertEqual(r['status'],'FAIL')
        self.assertIn('identity_invalid',r['error'])

    def test_version_timeout_is_not_success_and_not_retried(self):
        self.process.side_effect=subprocess.TimeoutExpired('verified-cli',5);r=self.observe()
        self.assertEqual(r['status'],'NOT_RUN');self.assertEqual(self.process.call_count,1);self.factory.assert_not_called()

    def test_native_error_is_not_a_capability_success(self):
        self.rows=None;r=self.observe();self.assertEqual(r['status'],'FAIL');self.assertTrue(self.closed)

if __name__=='__main__':unittest.main()
