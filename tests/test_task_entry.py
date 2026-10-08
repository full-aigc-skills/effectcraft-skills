"""已有任务须在当前Python准备失败时从公开入口继续使用原组合。"""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'skills/effectcraft-use'
def load(name):
    spec=importlib.util.spec_from_file_location('entry_test_'+name,BASE/'scripts'/(name+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

class TaskEntryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='bound entry 中文 space ');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.m=load('runtime_binding');self.store=load('task_store').Store(self.root/'task states');self.source=self.root/'original skill'
        shutil.copytree(BASE,self.source,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        (self.source/'scripts/managed.py').write_text('import json,sys,os\nprint(json.dumps({"controller":"original", "argv":sys.argv, "python":sys.executable, "pid":os.getpid()}))\nif "--judge" in sys.argv:sys.exit(125)\n',encoding='utf-8')
        self.home=self.root/'original native';self.binding,self.manifest=self.m.prepare(self.source,self.home)
        lock=json.loads((self.source/'scripts/runtime.lock.json').read_text(encoding='utf-8'))
        self.store.create('held',plan={},output=str(self.root/'delivery'),runtime_sha=lock['artifacts'][self.binding['platform']]['binarySha256'],inputs={},source=None,mode='workflow',authorization={},runtime_binding=self.binding)
        self.m.freeze(self.store,'held',self.source,self.manifest)
        self.front=self.root/'current skill';shutil.copytree(BASE,self.front,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        self.bad=self.root/'bad archive';self.bad.write_bytes(b'broken archive')
        self.env={**os.environ,'CRAFT_PYTHON_HOME':str(self.root/'empty current python'),'CRAFT_PYTHON_ARCHIVE':str(self.bad),'CRAFT_STATE_HOME':str(self.store.root)}
        self.frozen=self.store.path('held').parent/'execution';self.before={p.relative_to(self.store.root).as_posix():p.read_bytes() for p in self.store.root.rglob('*') if p.is_file()}

    def entry(self,action='resume',extra=()):
        argv=(['powershell.exe','-NoProfile','-NonInteractive','ExecutionPolicy','Bypass','-File',str(self.front/'scripts/launch.ps1')] if os.name=='nt' else ['/bin/sh',str(self.front/'scripts/launch.sh')])
        if os.name=='nt':argv[3]='-ExecutionPolicy'
        if action=='review':extra=(*extra,'--criteria',str(self.source/'references/criteria.json'))
        return subprocess.run([*argv,'--runtime-home',str(self.root/'incorrect current native'),action,'--task','held',*extra],env=self.env,capture_output=True,text=True,timeout=60)

    def unchanged(self):
        for name,data in self.before.items():self.assertEqual((self.store.root/name).read_bytes(),data,name)
        self.assertFalse((self.root/'empty current python').exists());self.assertFalse((self.root/'incorrect current native').exists())

    def test_bound_task_dispatches_original_before_current_python_install(self):
        for action in ('resume','reconcile','review','inspect','cancel'):
            with self.subTest(action=action):
                r=self.entry(action);self.assertEqual(r.returncode,0,r.stdout+r.stderr);value=json.loads(r.stdout)
                self.assertEqual(value['controller'],'original');self.assertEqual(Path(value['python']).resolve(),Path(sys.executable).resolve())
                self.assertEqual(value['argv'][value['argv'].index('--runtime-home')+1],str(self.home));self.unchanged()

    def test_original_exit_125_never_falls_back_to_current_install(self):
        r=self.entry('review',('--judge',str(self.root/'judge.json')))
        self.assertEqual(r.returncode,125,r.stdout+r.stderr);self.unchanged()

    @unittest.skipIf(os.name=='nt','Windows uses owned controller Job rather than POSIX exec identity')
    def test_posix_replaces_launcher_instead_of_leaving_an_orphan_controller(self):
        child=subprocess.Popen(['/bin/sh',str(self.front/'scripts/launch.sh'),'resume','--task','held'],env=self.env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        out,err=child.communicate(timeout=60);self.assertEqual(child.returncode,0,out+err)
        self.assertEqual(json.loads(out)['pid'],child.pid);self.unchanged()

    def test_freeze_emits_versioned_bound_entry_atomically(self):
        self.assertEqual(self.binding['schema'],'effectcraft-execution-binding/v2')
        self.assertTrue((self.frozen/'entry.tsv').is_file());self.assertTrue((self.frozen/'identity.json').is_file())
        self.assertEqual(self.m.file_sha(self.frozen/'entry.tsv'),self.binding['entrySha256'])
        self.assertEqual(json.loads((self.frozen/'identity.json').read_text(encoding='utf-8')),self.store.read('held')['identity'])

    def test_tampered_snapshot_or_entry_is_preserved_without_current_bootstrap(self):
        for name in ('entry.tsv','identity.json','skill/scripts/managed.py','skill/scripts/python.lock.json'):
            with self.subTest(name=name):
                file=self.frozen/name
                if not file.exists():self.fail('trusted startup material missing: '+name)
                original=file.read_bytes();file.write_bytes(original+b'\nchanged')
                r=self.entry();self.assertNotEqual(r.returncode,0);self.assertNotIn('"controller": "original"',r.stdout)
                self.assertEqual(file.read_bytes(),original+b'\nchanged');self.assertFalse((self.root/'empty current python').exists());file.write_bytes(original)

    def test_missing_entry_never_rebuilds_or_bootstraps_current(self):
        file=self.frozen/'entry.tsv';file.unlink(missing_ok=True);r=self.entry();self.assertNotEqual(r.returncode,0)
        self.assertIn('bound_entry',r.stderr+r.stdout);self.assertFalse(file.exists());self.assertFalse((self.root/'empty current python').exists())

    def test_corrupt_state_does_not_execute_original_or_repair(self):
        file=self.store.path('held');file.write_text('{broken',encoding='utf-8');r=self.entry();self.assertNotEqual(r.returncode,0)
        self.assertNotIn('"controller": "original"',r.stdout);self.assertEqual(file.read_text(encoding='utf-8'),'{broken');self.assertFalse((self.root/'empty current python').exists())

    def test_legacy_unbound_record_never_acquires_launch_materials(self):
        state=self.store.read('held');state['identity'].pop('runtimeBinding');state['identityHash']=self.m.digest(state['identity']);self.store.save(state)
        before=self.store.path('held').read_bytes();r=self.entry();self.assertNotEqual(r.returncode,0)
        self.assertEqual(self.store.path('held').read_bytes(),before);self.assertFalse((self.root/'empty current python').exists())

    def test_bound_descriptor_symlink_does_not_execute_or_modify_target(self):
        target=self.root/'outside descriptor';file=self.frozen/'entry.tsv';file.rename(target)
        try:file.symlink_to(target)
        except OSError as error:self.skipTest(str(error))
        before=target.read_bytes();r=self.entry();self.assertNotEqual(r.returncode,0)
        self.assertEqual(target.read_bytes(),before);self.assertTrue(file.is_symlink());self.assertFalse((self.root/'empty current python').exists())

    def test_duplicate_task_or_path_escape_rejected_without_execution(self):
        for extra in (('--task','held'),('--task','../escape')):
            r=self.entry(extra=extra);self.assertNotEqual(r.returncode,0);self.assertNotIn('"controller": "original"',r.stdout)
            self.assertFalse((self.root/'empty current python').exists())

    def test_already_bound_handoff_restores_original_native_home(self):
        from types import SimpleNamespace
        args=SimpleNamespace(action='resume',task='held',runtime_home=self.root/'wrong home')
        self.m.handoff(self.store,args,self.frozen/'skill/scripts/managed.py');self.assertEqual(args.runtime_home,self.home)

if __name__=='__main__':unittest.main()
