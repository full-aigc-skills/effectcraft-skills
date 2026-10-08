"""私有业务结果通道和组归属丢失的拒绝契约；不以持有者退出伪造业务成功。"""
import importlib.util,json,os,subprocess,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
SCRIPT=Path(__file__).resolve().parents[1]/'skills/effectcraft-use/scripts/posix_group_lease.py'
def load():
    s=importlib.util.spec_from_file_location('lease_tests',SCRIPT);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
class WorkerResultTests(unittest.TestCase):
    def test_result_requires_eof_and_matching_nonce(self):
        m=load();r=m.ResultReader(-1,'a'*32);data=json.dumps({'schema':'effectcraft-posix-worker-result/v1','nonce':'a'*32,'returncode':7}).encode()
        self.assertIsNone(r.consume(data[:20]));self.assertIsNone(r.consume(data[20:]));self.assertIsNone(r.code);self.assertEqual(r.consume(b''),7)
    def test_invalid_result_never_becomes_success(self):
        m=load();valid={'schema':'effectcraft-posix-worker-result/v1','nonce':'a'*32,'returncode':0}
        cases=[b'',b'{broken',b'\xff',json.dumps({**valid,'nonce':'b'*32}).encode(),json.dumps({**valid,'schema':'other/v1'}).encode(),json.dumps({**valid,'returncode':True}).encode(),json.dumps({**valid,'returncode':None}).encode(),json.dumps({**valid,'returncode':256}).encode(),json.dumps({**valid,'returncode':1.5}).encode(),json.dumps({**valid,'extra':0}).encode(),(json.dumps(valid)[:-1]+',"returncode":0}').encode(),json.dumps(valid).encode()+b'\n'+json.dumps(valid).encode()]
        for data in cases:
            with self.subTest(data=data),self.assertRaises(ValueError):
                r=m.ResultReader(-1,'a'*32);r.consume(data);r.consume(b'')
    def test_oversized_result_is_rejected_before_unbounded_read(self):
        m=load();r=m.ResultReader(-1,'a'*32)
        with self.assertRaises(ValueError):r.consume(b'x'*4097)
    def test_member_table_must_include_live_anchor(self):
        m=load()
        for rows,expected in [('123 123 S\n',False),('123 123 S\n124 123 S\n',True),('123 123 S\n124 123 Z\n',False)]:
            with self.subTest(rows=rows),patch.object(m.subprocess,'run',return_value=subprocess.CompletedProcess([],0,rows,'')):
                self.assertEqual(m.other_members(123),expected)
        for rows in ('','124 123 S\n','123 123 Z\n','malformed\n'):
            with self.subTest(rows=rows),patch.object(m.subprocess,'run',return_value=subprocess.CompletedProcess([],0,rows,'')),self.assertRaises(ValueError):m.other_members(123)
    @unittest.skipIf(os.name=='nt','POSIX group identity; Windows Job unchanged')
    def test_lost_anchor_never_signals_reused_or_unrelated_group(self):
        m=load()
        for returncode,pgid in [(0,123),(None,456)]:
            with self.subTest(returncode=returncode,pgid=pgid),patch.object(m.os,'getpgid',return_value=pgid),patch.object(m.os,'killpg') as kill:
                with self.assertRaises(ValueError):m.signal_owned(SimpleNamespace(pid=123,poll=lambda:returncode),15)
                kill.assert_not_called()
if __name__=='__main__':unittest.main()
