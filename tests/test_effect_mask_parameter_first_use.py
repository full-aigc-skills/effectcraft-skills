"""真实效果/蒙版参数拒绝必须使用领域错误，保留源工程及交付。"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]

def hashes(root):
 return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}

@unittest.skipUnless(os.environ.get('CRAFT_EFFECT_PARAMETER_FIRST_USE')=='1','requires public native runtime and installed/source effect skill')
class EffectMaskParameterFirstUseTests(unittest.TestCase):
 def test_unknown_effect_and_mask_fields_fail_without_mutating_delivery(self):
  records=[]
  for role,example,command,field in [('effects','brand-intro.json','effect.apply','blurriness'),('masks','layer-mask.json','mask.new','feather')]:
   with self.subTest(role=role), tempfile.TemporaryDirectory() as temporary:
    root=Path(temporary);name='effectcraft-cli-'+role;skill=root/'.agents/skills'/name
    origin=Path(os.environ.get('CRAFT_INSTALLED_EFFECT_PARAMETER_SKILLS',ROOT/'skills'))/name
    shutil.copytree(origin,skill,ignore=shutil.ignore_patterns('__pycache__'));before=hashes(skill)
    spec=importlib.util.spec_from_file_location('parameter_'+role,skill/'scripts/workflow.py');w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)
    runtime=root/'empty-runtime';self.assertFalse(runtime.exists())
    plan=json.loads((skill/'examples'/example).read_text());plan['exports']=[];plan['frames']=[0]
    bad=json.loads(json.dumps(plan));next(op for op in bad['operations'] if op['command']==command)['params'][field]=12
    with self.assertRaisesRegex(ValueError,'unsupported_mapping: '+command):w.execute(bad,root/'rejected-new',runtime_home=runtime)
    self.assertFalse((root/'rejected-new').exists())
    first=root/'v1';receipt=w.execute(plan,first,runtime_home=runtime);original=hashes(first)
    operation=next(op for op in bad['operations'] if op['command']==command)
    bad_revision={'expectedProjectSha256':receipt['files']['project.ecproj'],'operations':[operation],'frames':[0],'exports':[]}
    with self.assertRaisesRegex(ValueError,'unsupported_mapping: '+command):w.execute(bad_revision,root/'rejected-revision',runtime_home=runtime,source=first)
    self.assertFalse((root/'rejected-revision').exists());self.assertEqual(hashes(first),original)
    # 字段未被省略：合法参数对应的图层/效果或蒙版能保存在重开的原生工程中。
    native=json.loads((first/'native.json').read_text());self.assertTrue(native['layers'])
    self.assertEqual(hashes(skill),before);self.assertFalse(list(skill.rglob('*.pyc')))
    records.append({'skill':name,'command':command,'unknownField':field,'newAndRevisionRejected':True,'sourceFilesPreserved':True,'skillFilesPreserved':True,'nativeProjectSha256':receipt['files']['project.ecproj'],'runtimeSha256':receipt['runtimeSha256']})
  if os.environ.get('CRAFT_EFFECT_PARAMETER_EVIDENCE'):
   with Path(os.environ['CRAFT_EFFECT_PARAMETER_EVIDENCE']).open('x') as stream:json.dump({'schema':'effectcraft-parameter-first-use/v1','result':'passed','scope':'single role skills copied independently, public empty native runtime, valid creation/reopen and invalid new/revision parameters','records':records},stream,indent=2)

if __name__=='__main__':unittest.main()
