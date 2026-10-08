"""平台归一化、真实进程互斥与无 select 管道读取回归。"""
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'skills/effectcraft-use/scripts/platform_support.py'


class PlatformSupportTests(unittest.TestCase):
    def module(self):
        self.assertTrue(SCRIPT.is_file(), 'portable platform adapter is missing')
        spec = importlib.util.spec_from_file_location('portable_test', SCRIPT)
        value = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(value)
        return value

    def test_platform_aliases_and_unknown_architecture(self):
        module = self.module()
        for system, machine, expected in [('Windows', 'AMD64', 'windows-x86_64'),
                ('Windows', 'ARM64', 'windows-arm64'), ('Windows', 'i686', 'windows-x86'),
                ('Linux', 'aarch64', 'linux-aarch64'), ('Darwin', 'aarch64', 'darwin-arm64')]:
            self.assertEqual(module.platform_key(system, machine), expected)
        with self.assertRaisesRegex(ValueError, 'unsupported_platform'):
            module.platform_key('Linux', 'mips')

    def test_lock_blocks_other_process_and_releases_after_owner_exit(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as directory:
            lock = Path(directory) / 'lock'
            code = "import importlib.util,sys;s=importlib.util.spec_from_file_location('p',sys.argv[1]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)\nwith m.exclusive_lock(sys.argv[2],timeout=0.1): print('owned')"
            with module.exclusive_lock(lock):
                result = subprocess.run([sys.executable, '-I', '-B', '-c', code, str(SCRIPT), str(lock)], capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('owned', result.stdout)
            result = subprocess.run([sys.executable, '-I', '-B', '-c', code, str(SCRIPT), str(lock)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_pipe_reader_handles_partial_lines_eof_and_timeout(self):
        module = self.module()
        child = subprocess.Popen([sys.executable, '-u', '-c', "import sys,time;sys.stdout.write('ab');sys.stdout.flush();time.sleep(.1);print('cd');time.sleep(.3)"], stdout=subprocess.PIPE)
        try:
            reader = module.PipeReader(child.stdout)
            self.assertEqual(reader.readline(2), b'abcd\n')
            with self.assertRaises(TimeoutError):
                reader.readline(.01)
            child.wait(timeout=3)
            with self.assertRaises(EOFError):
                reader.readline(2)
        finally:
            if child.poll() is None:
                child.kill(); child.wait()
            child.stdout.close()

    def test_lock_rejects_symlink_without_changing_target(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)/'user'; target.write_text('keep')
            link = Path(directory)/'lock'; link.symlink_to(target)
            with self.assertRaises((OSError, ValueError)):
                with module.exclusive_lock(link):
                    self.fail('followed lock link')
            self.assertEqual(target.read_text(), 'keep')
