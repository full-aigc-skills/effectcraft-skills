"""真实POSIX后代清理和归属持有；沙箱禁用ps不允许漏掉已经成为孤儿的成员。"""
import json,os,signal,shutil,subprocess,sys,tempfile,time,unittest
from pathlib import Path
SCRIPT=Path(__file__).resolve().parents[1]/'skills/effectcraft-use/scripts/process_guard.py'
@unittest.skipUnless(sys.platform=='darwin' and shutil.which('sandbox-exec'),'actual macOS sandbox; other native targets remain open')
class GroupOwnershipTests(unittest.TestCase):
    def fixture(self,root):
        descendant=root/'descendant.py';descendant.write_text('import os,signal,sys,time\nfrom pathlib import Path\nsignal.signal(signal.SIGTERM,signal.SIG_IGN)\nPath(sys.argv[1]).write_text(str(os.getpid()))\nwhile True:time.sleep(.05)\n')
        worker=root/'worker.py';worker.write_text('import subprocess,sys,time\nfrom pathlib import Path\np=subprocess.Popen([sys.executable,sys.argv[1],sys.argv[2]],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)\nwhile not Path(sys.argv[2]).exists():time.sleep(.01)\n'+('time.sleep(60)\n' if root.name.endswith('hold') else 'raise SystemExit(7)\n'))
        return worker,descendant
    def alive(self,pid):
        r=subprocess.run(['ps','-p',str(pid),'-o','stat='],capture_output=True,text=True);s=r.stdout.strip();return bool(s and not s.startswith('Z'))
    def run_case(self,kill_guard):
        with tempfile.TemporaryDirectory(prefix='owned sandbox ') as temporary:
            root=Path(temporary)/('hold' if kill_guard else 'exit');root.mkdir();worker,descendant=self.fixture(root);ready=root/'ready';receipt=root/'lifecycle.json'
            unrelated=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'])
            args=['/usr/bin/sandbox-exec','-p','(version 1)(allow default)(deny network*)',sys.executable,'-I','-B',str(SCRIPT),'--receipt',str(receipt),'--lease',str(root/'lease'),'--grace','.2','--',sys.executable,str(worker),str(descendant),str(ready)]
            guard=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE);pid=None
            try:
                deadline=time.monotonic()+10
                while not ready.exists() and time.monotonic()<deadline and guard.poll() is None:time.sleep(.02)
                self.assertTrue(ready.exists(),'owned descendant was not started');pid=int(ready.read_text())
                if kill_guard:guard.kill()
                guard.wait(timeout=12)
                deadline=time.monotonic()+6
                while self.alive(pid) and time.monotonic()<deadline:time.sleep(.02)
                self.assertFalse(self.alive(pid),'owned descendant survived after direct worker/guardian exit')
                self.assertIsNone(unrelated.poll(),'unrelated process was terminated')
                report=json.loads(receipt.read_text())
                if not kill_guard:
                    self.assertEqual(guard.returncode,7,guard.stderr.read().decode(errors='replace'));self.assertEqual(report['status'],'stopped');self.assertEqual(report['returncode'],7)
                    self.assertEqual(report['ownership']['schema'],'effectcraft-posix-group-lease/v1');self.assertTrue(report['ownership']['workerResultVerified'])
                else:self.assertNotEqual(report['status'],'stopped','killed guardian cannot publish unobserved stopped evidence')
            finally:
                if guard.poll() is None:guard.kill();guard.wait()
                guard.stdin.close();guard.stdout.close();guard.stderr.close()
                if pid:
                    try:os.kill(pid,signal.SIGKILL)
                    except ProcessLookupError:pass
                unrelated.kill();unrelated.wait()
    def test_forced_cancel_confirms_stop_without_inventing_worker_success(self):
        with tempfile.TemporaryDirectory(prefix='owned resistant cancel ') as directory:
            root=Path(directory);ready=root/'ready';receipt=root/'lifecycle.json'
            program='import signal,time;from pathlib import Path;signal.signal(signal.SIGTERM,signal.SIG_IGN);Path('+repr(str(ready))+').write_text("ready");time.sleep(60)'
            args=['/usr/bin/sandbox-exec','-p','(version 1)(allow default)(deny network*)',sys.executable,'-I','-B',str(SCRIPT),'--receipt',str(receipt),'--lease',str(root/'lease'),'--grace','.2','--',sys.executable,'-c',program]
            child=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            try:
                deadline=time.monotonic()+8
                while not ready.exists() and child.poll() is None and time.monotonic()<deadline:time.sleep(.02)
                self.assertTrue(ready.exists());child.stdin.close();child.wait(timeout=10)
                self.assertNotEqual(child.returncode,0)
                record=json.loads(receipt.read_text());self.assertEqual(record['status'],'stopped');self.assertLess(record['returncode'],0)
                self.assertFalse(record['ownership']['workerResultVerified']);self.assertIsNone(record['ownership']['workerReturncode'])
                self.assertEqual(record['ownership']['exitCodeSource'],'group-holder-forced-stop')
            finally:
                if child.poll() is None:child.kill();child.wait()
                if not child.stdin.closed:child.stdin.close()
                child.stdout.close();child.stderr.close()

    def test_worker_exit_does_not_skip_term_resistant_orphan_under_ps_denial(self):self.run_case(False)
    def test_killed_guardian_private_channel_stops_owned_group(self):self.run_case(True)
if __name__=='__main__':unittest.main()
