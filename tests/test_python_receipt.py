"""公开双平台启动入口的安装回执保护；小载荷夹具不冒充官方Python运行时。"""
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
import unittest

SOURCE=Path(__file__).resolve().parents[1]/'skills/effectcraft-use/scripts'

class PythonReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='python receipt space ');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.skill=self.root/'one skill/scripts';self.skill.mkdir(parents=True)
        arch=platform.machine().lower();arch={'amd64':'x86_64','arm64':'arm64','aarch64':'aarch64'}.get(arch,arch)
        system=platform.system();self.windows=os.name=='nt'
        self.key=('windows-'+('arm64' if arch in ('arm64','aarch64') else 'x86_64' if arch=='x86_64' else 'x86')) if self.windows else ('darwin-' if system=='Darwin' else 'linux-')+('arm64' if system=='Darwin' and arch in ('arm64','aarch64') else 'aarch64' if arch in ('arm64','aarch64') else 'x86_64')
        self.base=self.root/'python runtimes';self.destination=self.base/('3.13.16-'+self.key);self.destination.mkdir(parents=True)
        executable='python.cmd' if self.windows else 'python'
        binary=self.destination/executable;binary.write_text('@echo off\r\necho fixture-python-executed\r\n' if self.windows else '#!/bin/sh\necho fixture-python-executed\n',encoding='utf-8');binary.chmod(0o755)
        checksum=hashlib.sha256(binary.read_bytes()).hexdigest();self.manifest=self.skill/'fixture.tsv';self.manifest.write_text(f'f\t{checksum}\t{executable}\n',encoding='utf-8')
        self.archive_sha='a'*64;self.identity={'version':'3.13.16','platform':self.key,'archiveSha256':self.archive_sha}
        entry={'url':'https://github.com/astral-sh/python-build-standalone/releases/download/fixed/fixture.tar.gz','archiveSha256':self.archive_sha,'executable':executable,'integrityFile':'fixture.tsv','integritySha256':hashlib.sha256(self.manifest.read_bytes()).hexdigest(),'minimumSystem':{'windows':'6.1'}}
        if self.windows:
            shutil.copyfile(SOURCE/'launch.ps1',self.skill/'launch.ps1')
            (self.skill/'python.lock.json').write_text(json.dumps({'version':'3.13.16','artifacts':{self.key:entry}}),encoding='utf-8')
            self.argv=['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(self.skill/'launch.ps1'),'--python-version']
        else:
            shutil.copyfile(SOURCE/'launch.sh',self.skill/'launch.sh')
            fields=[self.key,'3.13.16',entry['url'],self.archive_sha,executable,'fixture.tsv',entry['integritySha256'],'0.0']
            (self.skill/'python-platforms.tsv').write_text('\t'.join(fields)+'\n',encoding='utf-8')
            self.argv=['/bin/sh',str(self.skill/'launch.sh'),'--python-version']
        shutil.copyfile(SOURCE/('task_entry.ps1' if self.windows else 'task_entry.sh'),self.skill/('task_entry.ps1' if self.windows else 'task_entry.sh'))
        self.env={**os.environ,'CRAFT_PYTHON_HOME':str(self.base)};self.receipt=self.destination/'installation.json'
        self.receipt.write_text(json.dumps(self.identity),encoding='utf-8')

    def call(self):return subprocess.run(self.argv,env=self.env,capture_output=True,text=True,timeout=30)

    def test_valid_current_and_legacy_field_orders_reuse_without_download(self):
        import itertools
        for order in itertools.permutations(self.identity):
            self.receipt.write_text(json.dumps({k:self.identity[k] for k in order},indent=2),encoding='utf-8')
            r=self.call();self.assertEqual(r.returncode,0,r.stderr);self.assertIn('fixture-python-executed',r.stdout)

    def test_invalid_receipt_never_executes_and_is_not_repaired(self):
        invalid=[b'{broken',b'null',b'[]',b'\xff',json.dumps({**self.identity,'version':'3.13.15'}).encode(),json.dumps({**self.identity,'platform':'other'}).encode(),json.dumps({**self.identity,'archiveSha256':'b'*64}).encode(),json.dumps({**self.identity,'unknown':'extra'}).encode(),b'{"version":"3.13.16","version":"3.13.15"}',json.dumps({**self.identity,'version':'3.13. 16'}).encode(),json.dumps(self.identity).encode()+b'\\',b'\x0c'+json.dumps(self.identity).encode(),b'\xc2\xa0'+json.dumps(self.identity).encode()]
        for data in invalid:
            with self.subTest(data=data):
                self.receipt.write_bytes(data);r=self.call()
                self.assertNotEqual(r.returncode,0)
                self.assertIn('python_installation_receipt_invalid',r.stderr)
                self.assertNotIn('fixture-python-executed',r.stdout)
                self.assertEqual(self.receipt.read_bytes(),data)

    def test_missing_receipt_never_executes_or_reinstalls(self):
        self.receipt.unlink();r=self.call();self.assertNotEqual(r.returncode,0)
        self.assertIn('python_installation_receipt_invalid',r.stderr)
        self.assertFalse(self.receipt.exists());self.assertNotIn('fixture-python-executed',r.stdout)

    @unittest.skipIf(os.name=='nt','native Windows symlink privilege acceptance remains separate')
    def test_symlink_receipt_keeps_external_target(self):
        target=self.root/'user receipt';target.write_bytes(self.receipt.read_bytes());self.receipt.unlink();self.receipt.symlink_to(target)
        before=target.read_bytes();r=self.call();self.assertNotEqual(r.returncode,0)
        self.assertIn('python_installation_receipt_invalid',r.stderr);self.assertEqual(target.read_bytes(),before)
        self.assertNotIn('fixture-python-executed',r.stdout)

if __name__=='__main__':unittest.main()
