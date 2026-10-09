"""真实POSIX守护进程只在有效停止观察后结算；瞬态查询错误有界重查。"""
import json,os,subprocess,sys,tempfile,time,unittest
from pathlib import Path
SCRIPT=Path(__file__).resolve().parents[1]/'skills/effectcraft-use/scripts'

@unittest.skipIf(os.name=='nt','POSIX observation; Windows Job semantics unchanged')
class StopObservationTests(unittest.TestCase):
 def run_case(self,mode,cancel=False):
  with tempfile.TemporaryDirectory(prefix='stop observation ') as temporary:
   root=Path(temporary);receipt=root/'lifecycle.json';attempts=root/'attempts';ready=root/'ready'
   wrapper=root/'guard.py'
   wrapper.write_text('import sys\nfrom pathlib import Path\nsys.path.insert(0,'+repr(str(SCRIPT))+')\nimport process_guard\nm=process_guard.load("posix_group_lease")\ncount=0\ndef probe(group,*,timeout=5):\n global count\n count+=1\n Path('+repr(str(attempts))+').write_text(str(count))\n if count==1 or '+repr(mode=='permanent')+':raise ValueError("process_tree_inspection_failed")\n return process_guard.group_alive(group,timeout=timeout)\nraise SystemExit(m.guard(sys.argv[1:],Path('+repr(str(receipt))+'),Path('+repr(str(root/'lease'))+'),.2,probe))\n',encoding='utf-8')
   program=('import signal,time;from pathlib import Path;signal.signal(signal.SIGTERM,signal.SIG_IGN);Path('+repr(str(ready))+').write_text("ready");time.sleep(60)' if cancel else 'raise SystemExit(7)')
   child=subprocess.Popen([sys.executable,'-I','-B',str(wrapper),sys.executable,'-c',program],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
   try:
    if cancel:
     deadline=time.monotonic()+8
     while not ready.exists() and child.poll() is None and time.monotonic()<deadline:time.sleep(.02)
     self.assertTrue(ready.exists());child.stdin.close()
    child.wait(timeout=15);record=json.loads(receipt.read_text());count=int(attempts.read_text())
    if mode=='permanent':
     self.assertEqual(record['status'],'unknown',record);self.assertEqual(record['error'],'process_tree_inspection_failed');self.assertGreater(count,1,'must exhaust a bounded re-observation window without inventing stop')
    else:
     self.assertEqual(record['status'],'stopped',record);self.assertGreater(count,1)
     if cancel:
      self.assertLess(record['returncode'],0);self.assertFalse(record['ownership']['workerResultVerified']);self.assertIsNone(record['ownership']['workerReturncode'])
     else:self.assertEqual(record['returncode'],7);self.assertTrue(record['ownership']['workerResultVerified'])
   finally:
    if child.poll() is None:child.kill();child.wait()
    if not child.stdin.closed:child.stdin.close()
    child.stdout.close();child.stderr.close()
 def test_transient_probe_failure_preserves_original_business_exit(self):self.run_case('transient')
 def test_transient_probe_failure_after_forced_cancel_requires_valid_stop_observation(self):self.run_case('transient',cancel=True)
 def test_persistent_probe_failure_keeps_unknown_instead_of_claiming_stopped(self):self.run_case('permanent')
