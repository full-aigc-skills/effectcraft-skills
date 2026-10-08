"""受管理路径的本地原生制品必须贯通安装器；离线失败不得回落下载。"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

BASE=Path(__file__).resolve().parents[1]/'skills/effectcraft-use/scripts'
def load():
    spec=importlib.util.spec_from_file_location('offline_boot',BASE/'bootstrap.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

class RuntimeOfflineTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='offline artifact space ');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name);self.home=self.root/'runtime';self.boot=load()
        self.archive=self.root/'official fixture.zip';binary=b'effectcraft-cli 0.4.0'
        with zipfile.ZipFile(self.archive,'w') as z:z.writestr('effectcraft-cli',binary);z.writestr('LICENSE.txt',b'fixture license')
        self.lock={'artifact':'effectcraft-cli','resolvedVersion':'0.4.0','artifacts':{'darwin-arm64':{'url':'https://example.invalid/never-used.zip','archiveSha256':hashlib.sha256(self.archive.read_bytes()).hexdigest(),'binarySha256':hashlib.sha256(binary).hexdigest()}}}
        self.version=patch.object(self.boot.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'effectcraft-cli 0.4.0',''));self.version.start();self.addCleanup(self.version.stop)
        self.network=patch.object(self.boot,'download',side_effect=AssertionError('offline selection must not download'));self.download=self.network.start();self.addCleanup(self.network.stop)

    def test_environment_archive_installs_without_downloading(self):
        with patch.dict(os.environ,{'CRAFT_RUNTIME_ARCHIVE':str(self.archive)}):result=self.boot.install(self.lock,self.home,None,'darwin-arm64')
        self.assertFalse(result['reused']);self.assertEqual(Path(result['executable']).read_bytes(),b'effectcraft-cli 0.4.0');self.download.assert_not_called()
        receipt=json.loads((Path(result['executable']).parent/'installation.json').read_text(encoding='utf-8'));self.assertNotIn('CRAFT_RUNTIME_ARCHIVE',json.dumps(receipt));self.assertNotIn(str(self.archive),json.dumps(receipt))

    def test_bad_selected_archive_never_falls_back_or_publishes(self):
        bad=self.root/'bad archive';bad.write_bytes(b'bad')
        for file in (bad,self.root/'missing archive'):
            with self.subTest(file=file),patch.dict(os.environ,{'CRAFT_RUNTIME_ARCHIVE':str(file)}):
                with self.assertRaises((ValueError,OSError)):self.boot.install(self.lock,self.home,None,'darwin-arm64')
                self.assertFalse((self.home/'effectcraft/0.4.0').exists());self.assertFalse(list((self.home/'effectcraft').glob('.install-*')))
        self.download.assert_not_called()

    def test_explicit_archive_takes_precedence_over_environment(self):
        with patch.dict(os.environ,{'CRAFT_RUNTIME_ARCHIVE':str(self.root/'missing')}):result=self.boot.install(self.lock,self.home,self.archive,'darwin-arm64')
        self.assertFalse(result['reused']);self.download.assert_not_called()

    def test_valid_existing_runtime_is_reused_without_reading_pending_archive(self):
        self.boot.install(self.lock,self.home,self.archive,'darwin-arm64')
        with patch.dict(os.environ,{'CRAFT_RUNTIME_ARCHIVE':str(self.root/'missing')}):result=self.boot.install(self.lock,self.home,None,'darwin-arm64')
        self.assertTrue(result['reused']);self.download.assert_not_called()

if __name__=='__main__':unittest.main()
