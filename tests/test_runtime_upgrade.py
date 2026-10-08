"""升级失败保全旧版本；组件夹具不替代真实原生双版本验收。"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'skills/effectcraft-use/scripts/bootstrap.py'

class RuntimeUpgradeTests(unittest.TestCase):
    def setUp(self):
        spec=importlib.util.spec_from_file_location('upgrade_bootstrap',SOURCE)
        self.boot=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.boot)
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.home=self.root/'runtime with spaces'
        self.old,self.old_archive=self.package('0.3.1');self.new,self.new_archive=self.package('0.4.0')
        self.execute=patch.object(self.boot.subprocess,'run',side_effect=lambda argv,**kw:subprocess.CompletedProcess(argv,0,Path(argv[0]).read_text(encoding='utf-8')+'\n',''))
        self.execute.start();self.addCleanup(self.execute.stop)
        self.first=self.boot.install(self.old,self.home,self.old_archive,'darwin-arm64')
        self.old_root=Path(self.first['executable']).parent;self.before=self.inventory(self.old_root)

    def package(self,version,extra=None):
        binary=('effectcraft-cli '+version).encode();archive=self.root/(version+'.zip')
        with zipfile.ZipFile(archive,'w') as z:
            z.writestr('effectcraft-cli',binary);z.writestr('LICENSE',b'fixture license')
            if extra:z.writestr(*extra)
        return {'artifact':'effectcraft-cli','resolvedVersion':version,'artifacts':{'darwin-arm64':{
            'url':f'https://github.com/storytold/effectcraft/releases/download/v{version}/fixture.zip',
            'archiveSha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
            'binarySha256':hashlib.sha256(binary).hexdigest()}}},archive

    def inventory(self,directory):
        return {p.relative_to(directory).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.rglob('*') if p.is_file()}

    def assert_old_preserved(self):
        self.assertEqual(self.inventory(self.old_root),self.before)
        self.assertTrue(self.boot.install(self.old,self.home,self.old_archive,'darwin-arm64')['reused'])

    def test_success_keeps_old_version_and_new_version_is_verified(self):
        result=self.boot.install(self.new,self.home,self.new_archive,'darwin-arm64')
        self.assertFalse(result['reused']);self.assertNotEqual(result['executable'],self.first['executable'])
        self.assertEqual(Path(result['executable']).read_bytes(),b'effectcraft-cli 0.4.0')
        self.assert_old_preserved()

    def test_failed_upgrade_preserves_old_version_and_publishes_nothing(self):
        for failure in ('checksum','traversal','license','version','rename','permission','download'):
            with self.subTest(failure=failure):
                lock,archive=self.package('0.4.0');run_patch=None;rename_patch=None;extract_patch=None;download_patch=None
                if failure=='checksum':archive.write_bytes(b'bad')
                elif failure=='traversal':lock,archive=self.package('0.4.0',('../escape',b'bad'))
                elif failure=='license':
                    with zipfile.ZipFile(archive,'w') as z:z.writestr('effectcraft-cli',b'effectcraft-cli 0.4.0')
                    lock['artifacts']['darwin-arm64']['archiveSha256']=hashlib.sha256(archive.read_bytes()).hexdigest()
                elif failure=='version':run_patch=patch.object(self.boot.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'effectcraft-cli 0.0.0',''))
                elif failure=='rename':rename_patch=patch.object(Path,'rename',side_effect=OSError('atomic publication failed'))
                elif failure=='permission':extract_patch=patch.object(self.boot,'extract',side_effect=PermissionError('staging denied'))
                elif failure=='download':download_patch=patch.object(self.boot,'download',side_effect=OSError('interrupted download'));archive=None
                from contextlib import ExitStack
                with ExitStack() as stack:
                    for item in (run_patch,rename_patch,extract_patch,download_patch):
                        if item:stack.enter_context(item)
                    with self.assertRaises((ValueError,OSError)):self.boot.install(lock,self.home,archive,'darwin-arm64')
                self.assertFalse((self.home/'effectcraft/0.4.0').exists())
                self.assertFalse(list((self.home/'effectcraft').glob('.install-*')))
                self.assert_old_preserved()

    def test_reuse_rejects_wrong_receipt_identity_without_overwrite_or_download(self):
        receipt=self.old_root/'installation.json';original=receipt.read_bytes()
        for field,value in [('version','0.4.0'),('platform','windows-x86'),('name','filmcraft'),('source','unknown'),('archiveSha256','f'*64),('binarySha256','f'*64),('url','https://example.invalid/other'),('versionOutput','effectcraft-cli 9.9.9')]:
            with self.subTest(field=field):
                changed=json.loads(original);changed[field]=value;receipt.write_text(json.dumps(changed),encoding='utf-8');before=receipt.read_bytes()
                with patch.object(self.boot,'download',side_effect=AssertionError('must not redownload')):
                    with self.assertRaisesRegex(ValueError,'installation_receipt_invalid'):
                        self.boot.install(self.old,self.home,None,'darwin-arm64')
                self.assertEqual(receipt.read_bytes(),before)
        receipt.write_bytes(original)

    def test_reuse_rejects_malformed_receipt_and_duplicate_identity(self):
        receipt=self.old_root/'installation.json'
        for data in (b'{broken',b'[]',b'null',b'{"version":"0.3.1","version":"0.4.0"}',b'\xff'):
            with self.subTest(data=data):
                receipt.write_bytes(data)
                with self.assertRaisesRegex(ValueError,'installation_receipt_invalid'):
                    self.boot.install(self.old,self.home,self.old_archive,'darwin-arm64')
                self.assertEqual(receipt.read_bytes(),data)

if __name__=='__main__':unittest.main()
