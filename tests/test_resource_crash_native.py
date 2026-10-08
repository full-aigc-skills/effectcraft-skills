"""真实预览写出后强杀worker，公开核对必须计量残留且不重发编辑。"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]


def load(path):
    spec=importlib.util.spec_from_file_location('crash_resource_managed',path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


@unittest.skipUnless(os.environ.get('CRAFT_RESOURCE_CRASH_LIVE')=='1','requires actual native engine')
class ResourceCrashNativeTests(unittest.TestCase):
    def test_preview_response_loss_accounts_owned_stage_without_replay(self):
        with tempfile.TemporaryDirectory(prefix='resource preview crash ') as temporary:
            root=Path(temporary).resolve();skill=root/'single skill'
            shutil.copytree(ROOT/'skills/effectcraft-use',skill,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
            before={p.relative_to(skill).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in skill.rglob('*') if p.is_file()}
            managed=load(skill/'scripts/managed.py');tasks=managed.load('task_store');store=tasks.Store(root/'state')
            plan=managed.read(skill/'examples/brand-intro.json');key=managed.load('platform_support').platform_key()
            lock=managed.read(skill/'scripts/runtime.lock.json');request={'inputs':{},'source':None}
            store.create('preview-crash',plan=plan,output=str(root/'delivery'),runtime_sha=lock['artifacts'][key]['binarySha256'],
                inputs={},source=None,mode='workflow',authorization={'requestHash':tasks.digest(request)})
            tasks.atomic_json(store.path('preview-crash').parent/'request.json',request)
            driver=root/'interrupt_preview.py'
            driver.write_text('import importlib.util,sys,os,signal\nfrom pathlib import Path\n'
                's=importlib.util.spec_from_file_location("managed",sys.argv[1]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)\n'
                'session=m.load("mcp_session");native=session.Session.request\n'
                'def lost(self,method,params,*args,**kwargs):\n'
                '    result=native(self,method,params,*args,**kwargs)\n'
                '    if method=="tools/call" and params.get("name")=="render_frame" and not result.get("isError"):\n'
                '        os.kill(os.getpid(),signal.SIGKILL)\n'
                '    return result\n'
                'session.Session.request=lost;original=m.load;m.load=lambda name:session if name=="mcp_session" else original(name)\n'
                'm.worker(m.load("task_store").Store(Path(sys.argv[2])),"preview-crash",Path(sys.argv[3]))\n')
            process=subprocess.Popen([sys.executable,'-I','-B',str(skill/'scripts/process_guard.py'),
                '--receipt',str(store.path('preview-crash').parent/'lifecycle.json'),
                '--lease',str(store.root/'leases/preview-crash.lifecycle.lock'),'--',sys.executable,'-I','-B',str(driver),
                str(skill/'scripts/managed.py'),str(store.root),str(root/'runtime')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            try:process.wait(timeout=240)
            finally:
                if process.poll() is None:process.kill();process.wait()
                process.stdin.close();out=process.stdout.read();err=process.stderr.read()
                process.stdout.close();process.stderr.close()
            self.assertNotEqual(process.returncode,0,(out,err))
            state=store.read('preview-crash');self.assertEqual(state['steps'][-1]['operation'],'render_frame')
            self.assertEqual(state['steps'][-1]['state'],'attempted');self.assertIn('resourceLocations',state)
            location=Path(state['resourceLocations']['locations'][0]['path']);frame=location/'frame-0000.png'
            self.assertTrue(frame.is_file());size=frame.stat().st_size;project=tasks.file_sha(location/'project.ecproj')
            base=[sys.executable,'-I','-B',str(skill/'scripts/managed.py'),'--state-root',str(store.root),
                '--runtime-home',str(root/'runtime')]
            result=subprocess.run([*base,'reconcile','--task','preview-crash'],capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,1,result.stdout+result.stderr)
            checked=json.loads(result.stdout);self.assertEqual(checked['state'],'reconciling')
            self.assertEqual(checked['resourceObservation']['status'],'PASS')
            self.assertEqual(checked['resources']['entries']['preview-crash']['encodedBytes'],size)
            self.assertEqual(checked['steps'],state['steps']);self.assertEqual(tasks.file_sha(location/'project.ecproj'),project)
            resumed=subprocess.run([*base,'resume','--task','preview-crash'],capture_output=True,text=True,timeout=30)
            self.assertEqual(resumed.returncode,1,resumed.stdout+resumed.stderr)
            self.assertEqual(json.loads(resumed.stdout)['steps'],state['steps'])
            after={p.relative_to(skill).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in skill.rglob('*') if p.is_file()}
            self.assertEqual(before,after)
            if os.environ.get('CRAFT_RESOURCE_CRASH_EVIDENCE'):
                proof={'schema':'effectcraft-preview-crash-resource/v1','result':'PASS','candidateOnly':True,'platform':key,
                    'scope':'actual native preview completed, worker SIGKILL before editing receipt; public reconcile accounts original owned stage; resume does not replay',
                    'skillFiles':before,'testSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    'driverSha256':hashlib.sha256(driver.read_bytes()).hexdigest(),'observedMediaBytes':size,
                    'projectSha256':project,'resourceObservation':checked['resourceObservation'],'resources':checked['resources'],
                    'originalStepsPreserved':True,'originalProjectPreserved':True,'unknownEditNotReplayed':True,
                    'excluded':['SIGKILL while native is writing a partial frame','orphan segment automatic recovery','other platforms','CPU/memory','host dispatch','fixed release','complete V1']}
                Path(os.environ['CRAFT_RESOURCE_CRASH_EVIDENCE']).write_text(json.dumps(proof,indent=2)+'\n')
