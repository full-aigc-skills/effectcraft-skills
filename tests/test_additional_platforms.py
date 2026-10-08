"""Web 与 FreeBSD 单独路由，不能借 Linux 制品通过平台门禁。"""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

BASE=Path(__file__).resolve().parents[1]/'skills/effectcraft-use/scripts'

class AdditionalPlatformTests(unittest.TestCase):
    def module(self):
        self.assertTrue((BASE/'additional_platforms.py').exists())
        spec=importlib.util.spec_from_file_location('additional_test',BASE/'additional_platforms.py')
        m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

    def test_freebsd_requires_actual_target_before_any_write(self):
        m=self.module()
        with tempfile.TemporaryDirectory() as d,patch.object(m.platform,'system',return_value='Linux'):
            root=Path(d)/'runtime'
            with self.assertRaisesRegex(ValueError,'freebsd_host_required'):m.build_freebsd(root)
            self.assertFalse(root.exists())

    def test_bad_web_archive_does_not_publish(self):
        m=self.module()
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);archive=root/'bad.zip';archive.write_bytes(b'bad')
            with self.assertRaisesRegex(ValueError,'archive_checksum_mismatch'):m.install_web(root/'runtime',archive)
            self.assertFalse((root/'runtime/effectcraft-web/0.4.0').exists())
