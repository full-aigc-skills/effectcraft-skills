"""文件创建代际的平台读取、失败关闭和旧认领兼容测试。"""
import importlib.util
import os
from pathlib import Path
import struct
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch,Mock

HERE=Path(__file__).resolve().parents[1]/'skills/effectcraft-use/scripts'
def load():
 spec=importlib.util.spec_from_file_location('creation_claims',HERE/'project_claims.py');value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value

class ProjectCreationIdentityTests(unittest.TestCase):
 def setUp(self):self.claims=load()
 def test_native_integer_birth_time_preserves_nanoseconds(self):
  self.assertEqual(self.claims.creation_identity('unused',SimpleNamespace(st_birthtime_ns=3000000007)),{'seconds':3,'nanoseconds':7})
 def test_native_float_birth_time_is_stable(self):
  self.assertEqual(self.claims.creation_identity('unused',SimpleNamespace(st_birthtime=3.25)),{'seconds':3,'nanoseconds':250000000})
 def buffer(self,mask=0x900,inode=123,nanos=7):
  data=bytearray(256);struct.pack_into('=I',data,0,mask);struct.pack_into('=Q',data,32,inode);struct.pack_into('=qI',data,80,3,nanos);struct.pack_into('=II',data,136,8,1);return bytes(data)
 def info(self):return SimpleNamespace(st_ino=123,st_dev=2049)
 def test_linux_statx_layout_and_mask(self):
  with patch.object(os,'major',return_value=8,create=True),patch.object(os,'minor',return_value=1,create=True):
   self.assertEqual(self.claims.parse_statx(self.buffer(),self.info()),{'seconds':3,'nanoseconds':7})
 def test_linux_missing_birth_time_wrong_inode_device_and_nanos_fail_closed(self):
  with patch.object(os,'major',return_value=8,create=True),patch.object(os,'minor',return_value=1,create=True):
   for data in [self.buffer(mask=0x100),self.buffer(inode=124),self.buffer(nanos=1000000000),b'short']:
    with self.subTest(data=data[:40]),self.assertRaisesRegex(ValueError,'project_creation_identity_unavailable'):self.claims.parse_statx(data,self.info())
  with patch.object(os,'major',return_value=9,create=True),patch.object(os,'minor',return_value=1,create=True),self.assertRaises(ValueError):self.claims.parse_statx(self.buffer(),self.info())
 def test_unsupported_platform_never_uses_ctime(self):
  with patch('sys.platform','unsupported'),self.assertRaisesRegex(ValueError,'project_creation_identity_unavailable'):
   self.claims.creation_identity('unused',SimpleNamespace(st_ctime_ns=123))
 def test_linux_call_is_bound_to_verified_fd_and_always_closes_it(self):
  import ctypes
  seen=[]
  def invoke(fd,path,flags,mask,buffer):
   seen.append((fd,path,flags,mask));ctypes.memmove(buffer,self.buffer(),256);return 0
  function=Mock(side_effect=invoke);lib=SimpleNamespace(statx=function)
  with patch('sys.platform','linux'),patch('ctypes.CDLL',return_value=lib),patch.object(os,'open',return_value=42),patch.object(os,'fstat',return_value=self.info()),patch.object(os,'close') as close,patch.object(os,'major',return_value=8,create=True),patch.object(os,'minor',return_value=1,create=True):
   self.assertEqual(self.claims.creation_identity('source',self.info()),{'seconds':3,'nanoseconds':7});close.assert_called_once_with(42)
  self.assertEqual(seen,[(42,b'',0x1000,0x900)])
 def test_linux_replaced_fd_and_error_never_fabricate_identity(self):
  for changed,code in [(True,0),(False,-1)]:
   function=Mock(return_value=code)
   info=SimpleNamespace(st_ino=124 if changed else 123,st_dev=2049)
   with patch('sys.platform','linux'),patch('ctypes.CDLL',return_value=SimpleNamespace(statx=function)),patch.object(os,'open',return_value=42),patch.object(os,'fstat',return_value=info),patch.object(os,'close') as close,self.assertRaisesRegex(ValueError,'project_source_identity_changed|project_creation_identity_unavailable'):
    self.claims.creation_identity('source',self.info())
   close.assert_called_once_with(42)
   if changed:function.assert_not_called()
 def test_real_file_creation_identity_survives_edit_and_hardlink(self):
  with tempfile.TemporaryDirectory() as root:
   path=Path(root)/'source';path.write_bytes(b'original');first=self.claims.creation_identity(path,path.stat())
   path.write_bytes(b'user edited');self.assertEqual(first,self.claims.creation_identity(path,path.stat()))
   alias=Path(root)/'alias'
   try:os.link(path,alias)
   except OSError:self.skipTest('hardlink unavailable')
   self.assertEqual(first,self.claims.creation_identity(alias,alias.stat()))
