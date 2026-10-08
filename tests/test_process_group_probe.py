"""内核明确空组才放行；枚举失败、权限失败和历史unknown不得变成停止证明。"""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT=Path(__file__).resolve().parents[1]/'skills/effectcraft-use/scripts/process_guard.py'
def load():
    spec=importlib.util.spec_from_file_location('probe_guard',SCRIPT);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

@unittest.skipIf(os.name=='nt','POSIX kernel group probe; native Windows Job unchanged')
class GroupProbeTests(unittest.TestCase):
    def test_absent_owned_group_does_not_need_process_enumeration(self):
        m=load()
        with patch.object(m.os,'killpg',side_effect=ProcessLookupError) as probe,patch.object(m.subprocess,'run',side_effect=PermissionError('sandbox ps denied')) as ps:
            self.assertFalse(m.group_alive(98765));probe.assert_called_once_with(98765,0);ps.assert_not_called()

    def test_permission_denied_probe_never_claims_stopped(self):
        m=load()
        with patch.object(m.os,'killpg',side_effect=PermissionError('kernel denied')),patch.object(m.subprocess,'run',side_effect=PermissionError('ps denied')) as ps:
            with self.assertRaises(ValueError):m.group_alive(98765)
            ps.assert_called_once()

    def test_kernel_permission_error_requires_valid_member_evidence(self):
        m=load()
        for rows,expected in [('98765 S\n',True),('98765 Z\n',False)]:
            with self.subTest(rows=rows),patch.object(m.os,'killpg',side_effect=PermissionError('kernel denied')),patch.object(m.subprocess,'run',return_value=subprocess.CompletedProcess([],0,rows,'')):
                self.assertEqual(m.group_alive(98765),expected)

    def test_existing_group_with_denied_enumeration_remains_unknown(self):
        m=load()
        with patch.object(m.os,'killpg'),patch.object(m.subprocess,'run',side_effect=PermissionError('sandbox ps denied')):
            with self.assertRaises(ValueError):m.group_alive(98765)

    def test_invalid_group_cannot_probe_unrelated_processes(self):
        m=load()
        for group in (0,-1,True,'123',None):
            with self.subTest(group=group),patch.object(m.os,'killpg') as probe,patch.object(m.subprocess,'run') as ps:
                with self.assertRaises(ValueError):m.group_alive(group)
                probe.assert_not_called();ps.assert_not_called()

    def test_existing_group_retains_live_and_zombie_discrimination(self):
        m=load()
        for rows,expected in [('98765 S\n',True),('98765 Z\n',False),('98766 S\n',False)]:
            with self.subTest(rows=rows),patch.object(m.os,'killpg'),patch.object(m.subprocess,'run',return_value=subprocess.CompletedProcess([],0,rows,'')):
                self.assertEqual(m.group_alive(98765),expected)

    @unittest.skipUnless(sys.platform=='darwin' and shutil.which('sandbox-exec'),'actual macOS sandbox required')
    def test_actual_offline_sandbox_records_stopped_and_real_exit_code(self):
        with tempfile.TemporaryDirectory(prefix='offline guardian space ') as directory:
            root=Path(directory);receipt=root/'lifecycle.json'
            command=['/usr/bin/sandbox-exec','-p','(version 1)(allow default)(deny network*)',sys.executable,'-I','-B',str(SCRIPT),'--receipt',str(receipt),'--lease',str(root/'lease'),'--',sys.executable,'-c','raise SystemExit(7)']
            child=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            try:
                child.wait(timeout=15);out=child.stdout.read();err=child.stderr.read()
                self.assertEqual(child.returncode,7,(out+err).decode(errors='replace'))
                record=json.loads(receipt.read_text());self.assertEqual(record['status'],'stopped');self.assertEqual(record['returncode'],7)
            finally:
                if child.poll() is None:child.kill();child.wait()
                child.stdin.close();child.stdout.close();child.stderr.close()

if __name__=='__main__':unittest.main()
