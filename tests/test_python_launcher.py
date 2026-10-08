"""无系统 Python 时的独立启动入口，坏离线包不得执行。"""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]/'skills/effectcraft-use/scripts'


class PythonLauncherTests(unittest.TestCase):
    def test_corrupt_offline_package_fails_without_publishing_runtime(self):
        self.assertTrue((ROOT/'launch.sh').exists(), 'Python-free launcher is missing')
        with tempfile.TemporaryDirectory(prefix='launcher space ') as directory:
            root=Path(directory); archive=root/'bad.tar.gz'; archive.write_bytes(b'bad')
            env=dict(os.environ, CRAFT_PYTHON_HOME=str(root/'runtime'), CRAFT_PYTHON_ARCHIVE=str(archive), PATH='/usr/bin:/bin')
            result=subprocess.run(['/bin/sh',str(ROOT/'launch.sh'),'--python-version'],env=env,capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('checksum',result.stderr.lower())
            self.assertFalse(list((root/'runtime').glob('*/installation.json')))
