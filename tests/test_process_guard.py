"""真实进程树必须在监督通道断开后停止，不能只等待直接子进程。"""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

SCRIPT = Path(__file__).resolve().parents[1]/'skills/effectcraft-use/scripts/process_guard.py'


@unittest.skipIf(os.name == 'nt', 'POSIX process evidence; Windows Job requires native runner')
class ProcessGuardTests(unittest.TestCase):
    def test_killed_supervisor_does_not_leave_its_native_process_running(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);receipt=root/'lifecycle.json';ready=root/'ready'
            launcher=root/'supervisor.py'
            launcher.write_text('import subprocess,sys,time\n'
                'p=subprocess.Popen(sys.argv[1:],stdin=subprocess.PIPE)\ntime.sleep(60)\n')
            native=root/'native.py'
            native.write_text('import os,sys,time\nfrom pathlib import Path\n'
                'Path(sys.argv[1]).write_text(str(os.getpid()))\ntime.sleep(60)\n')
            outer=subprocess.Popen([sys.executable,str(launcher),sys.executable,'-I','-B',str(SCRIPT),
                '--receipt',str(receipt),'--lease',str(root/'lease'),'--grace','0.2',
                '--',sys.executable,str(native),str(ready)])
            pid=None
            try:
                deadline=time.monotonic()+8
                while not ready.exists() and time.monotonic()<deadline:time.sleep(.02)
                self.assertTrue(ready.exists());pid=int(ready.read_text())
                outer.kill();outer.wait()
                deadline=time.monotonic()+8;report={}
                while time.monotonic()<deadline:
                    report=json.loads(receipt.read_text())
                    if report['status']=='stopped':break
                    time.sleep(.02)
                self.assertEqual(report['status'],'stopped')
                self.assertEqual(report['reason'],'supervisor_channel_closed')
                live=subprocess.run(['ps','-p',str(pid),'-o','stat='],capture_output=True,text=True).stdout.strip()
                self.assertTrue(not live or live.startswith('Z'),live)
            finally:
                if outer.poll() is None:outer.kill();outer.wait()
                if pid:
                    try:os.kill(pid,signal.SIGKILL)
                    except ProcessLookupError:pass

    def test_eof_stops_term_resistant_descendant_and_preserves_unrelated_process(self):
        self.assertTrue(SCRIPT.exists(), 'owned process guardian is missing')
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); ready=root/'ready';receipt=root/'lifecycle.json'
            program=root/'worker.py'
            program.write_text('import subprocess,sys,time\nfrom pathlib import Path\n'
                'p=subprocess.Popen([sys.executable,"-c","import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);time.sleep(60)"])\n'
                'Path(sys.argv[1]).write_text(str(p.pid))\ntime.sleep(60)\n')
            unrelated=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'])
            guard=subprocess.Popen([sys.executable,'-I','-B',str(SCRIPT),'--receipt',str(receipt),
                '--lease',str(root/'lease'),'--grace','0.2','--',sys.executable,str(program),str(ready)],stdin=subprocess.PIPE)
            descendant=None
            try:
                deadline=time.monotonic()+8
                while not ready.exists() and guard.poll() is None and time.monotonic()<deadline:time.sleep(.02)
                self.assertTrue(ready.exists(), 'worker was not started')
                descendant=int(ready.read_text());time.sleep(.1)
                guard.stdin.close();guard.wait(timeout=8)
                report=json.loads(receipt.read_text())
                self.assertEqual(report['status'],'stopped')
                self.assertEqual(report['reason'],'supervisor_channel_closed')
                live=subprocess.run(['ps','-p',str(descendant),'-o','stat='],capture_output=True,text=True).stdout.strip()
                self.assertTrue(not live or live.startswith('Z'),live)
                self.assertIsNone(unrelated.poll())
            finally:
                if guard.poll() is None:guard.kill();guard.wait()
                if descendant:
                    try:os.kill(descendant,signal.SIGKILL)
                    except ProcessLookupError:pass
                unrelated.kill();unrelated.wait()

    def test_normal_exit_records_actual_returncode_and_releases_lease(self):
        self.assertTrue(SCRIPT.exists(), 'owned process guardian is missing')
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);receipt=root/'lifecycle.json'
            guard=subprocess.Popen([sys.executable,'-I','-B',str(SCRIPT),'--receipt',str(receipt),
                '--lease',str(root/'lease'),'--',sys.executable,'-c','raise SystemExit(7)'],stdin=subprocess.PIPE)
            try:
                self.assertEqual(guard.wait(timeout=8),7)
                report=json.loads(receipt.read_text())
                self.assertEqual(report['status'],'stopped');self.assertEqual(report['returncode'],7)
            finally:guard.stdin.close()


if __name__=='__main__':unittest.main()
