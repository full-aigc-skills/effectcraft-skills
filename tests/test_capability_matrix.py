"""当前能力必须绑定完整技能和原始验收报告；锁中有制品不代表验收。"""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
class CapabilityMatrixTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.base=self.root/'skills/effectcraft-use';self.scripts=self.base/'scripts';self.scripts.mkdir(parents=True);(self.root/'docs/evidence').mkdir(parents=True)
  spec=importlib.util.spec_from_file_location('cap_matrix',ROOT/'scripts/build_capability_matrix.py');self.m=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.m);self.m.ROOT=self.root
  self.runtime={'resolvedVersion':'0.4.0','artifacts':{'darwin-arm64':{'binarySha256':'a'*64,'archiveSha256':'e'*64},'linux-x86_64':{'binarySha256':'b'*64,'archiveSha256':'f'*64}}};self.python={'version':'3.13.16','artifacts':{key:{'archiveSha256':'c'*64} for key in self.runtime['artifacts']}}
  self.write(self.scripts/'runtime.lock.json',self.runtime);self.write(self.scripts/'python.lock.json',self.python);(self.scripts/'managed.py').write_text('operation = 1\n')
  self.report={'schema':'effectcraft-independent-offline15/v1','status':'PASS','platform':'darwin-arm64','pythonArchiveSha256':'c'*64,'nativeArchiveSha256':'e'*64,'cases':[{'skill':'effectcraft-use','status':'PASS','engineering':'PASS','technical':'PASS','creative':'NOT_RUN'}]};self.report_path=self.root/'docs/evidence/native-report.json';self.report['cases'][0].update(installedFilesAndModesUnchanged=True,installedInventorySha256=hashlib.sha256(json.dumps({k:{'sha256':v,'mode':0o444} for k,v in self.inventory().items()},sort_keys=True,separators=(',',':')).encode()).hexdigest());self.write(self.report_path,self.report)
  self.proof={'schema':'effectcraft-capability-evidence/v1','runtimeVersion':'0.4.0','pythonVersion':'3.13.16','baseSkillFiles':self.inventory(),'platforms':{'darwin-arm64':{'runtimeSha256':'a'*64,'pythonArchiveSha256':'c'*64,'nativeRepresentative':'PASS'}},'reportFile':'docs/evidence/native-report.json','reportSha256':self.sha(self.report_path),'webInstallation':'PASS'}
  self.persist()
 def write(self,p,value):p.write_text(json.dumps(value),encoding='utf-8')
 def sha(self,p):return hashlib.sha256(p.read_bytes()).hexdigest()
 def inventory(self):return {p.relative_to(self.base).as_posix():self.sha(p) for p in self.base.rglob('*') if p.is_file()}
 def persist(self):
  for name in ['managed-optimization-20261008.json','current-capability-evidence.json']:self.write(self.root/'docs/evidence'/name,self.proof)
 def build(self):self.m.build();return json.loads((self.root/'docs/current-capabilities.json').read_text())
 def status(self):return self.build()['platforms'][0]['nativeRepresentative']
 def test_valid_smoke_is_scoped_and_other_gates_remain_open(self):
  v=self.build();self.assertEqual(v['platforms'][0]['nativeRepresentative'],'PASS');self.assertEqual(v['platforms'][0]['completePlatformAcceptance'],'NOT_RUN');self.assertEqual(v['platforms'][1]['nativeRepresentative'],'NOT_RUN');self.assertEqual(v['web']['installation'],'NOT_RUN')
 def test_changed_execution_code_cannot_keep_pass(self):
  (self.scripts/'managed.py').write_text('operation = 2\n');self.assertEqual(self.status(),'NOT_RUN')
 def test_new_missing_or_incomplete_files_invalidate_proof(self):
  for action in ['added','missing','incomplete']:
   with self.subTest(action=action):
    if action=='added':(self.scripts/'new.py').write_text('new = True\n')
    elif action=='missing':(self.scripts/'managed.py').unlink()
    else:self.proof['baseSkillFiles'].pop('scripts/managed.py');self.persist()
    self.assertEqual(self.status(),'NOT_RUN')
    (self.scripts/'new.py').unlink(missing_ok=True);(self.scripts/'managed.py').write_text('operation = 1\n')
 def test_python_identity_must_match(self):
  self.python['version']='3.13.17';self.write(self.scripts/'python.lock.json',self.python);self.proof['baseSkillFiles']=self.inventory();self.persist();self.assertEqual(self.status(),'NOT_RUN')
 def test_python_archive_must_match_even_with_refreshed_files(self):
  self.python['artifacts']['darwin-arm64']['archiveSha256']='d'*64;self.write(self.scripts/'python.lock.json',self.python);self.proof['baseSkillFiles']=self.inventory();self.persist();self.assertEqual(self.status(),'NOT_RUN')
 def test_changed_raw_report_cannot_keep_pass(self):
  self.report['status']='FAIL';self.write(self.report_path,self.report);self.assertEqual(self.status(),'NOT_RUN')
 def test_matching_report_digest_cannot_promote_failed_report(self):
  self.report['status']='FAIL';self.write(self.report_path,self.report);self.proof['reportSha256']=self.sha(self.report_path);self.persist();self.assertEqual(self.status(),'NOT_RUN')
 def test_missing_report_cannot_keep_pass(self):
  self.report_path.unlink();self.assertEqual(self.status(),'NOT_RUN')
 def test_rebinding_manifest_cannot_borrow_unrelated_report(self):
  (self.scripts/'managed.py').write_text('operation = 2\n');self.proof['baseSkillFiles']=self.inventory();self.persist();self.assertEqual(self.status(),'NOT_RUN')
 def test_check_does_not_rewrite_drift(self):
  self.build();p=self.root/'docs/current-capabilities.json';p.write_text('{}\n');before=p.read_bytes()
  with self.assertRaisesRegex(ValueError,'capability_matrix_drift'):self.m.build(check=True)
  self.assertEqual(p.read_bytes(),before)
if __name__=='__main__':unittest.main()
