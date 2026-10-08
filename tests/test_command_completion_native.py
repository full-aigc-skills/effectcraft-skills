"""完成证明前后强杀真实worker；原编辑不重发，恢复须重开原生工程及解码媒体。"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]


def load(path):
    spec=importlib.util.spec_from_file_location('native_completion_acceptance',path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


def files(root):
    return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}


@unittest.skipUnless(os.environ.get('CRAFT_COMPLETION_CRASH_LIVE')=='1','explicit real worker crash opt-in')
@unittest.skipUnless(sys.platform=='darwin' and platform.machine()=='arm64','macOS arm64 native acceptance')
class CommandCompletionNativeCrashTests(unittest.TestCase):
    def test_commands_killed_after_seal_recovers_original_delivery(self):self.exercise('commands','after')
    def test_desktop_killed_after_seal_recovers_original_delivery(self):self.exercise('desktop','after')
    def test_commands_killed_before_seal_keeps_unknown(self):self.exercise('commands','before')
    def test_desktop_killed_before_seal_keeps_unknown(self):self.exercise('desktop','before')
    def test_commands_killed_between_seal_and_reference_keeps_orphan(self):self.exercise('commands','orphan')
    def test_desktop_killed_between_seal_and_reference_keeps_orphan(self):self.exercise('desktop','orphan')

    def exercise(self,mode,point):
        base=Path(os.environ.get('CRAFT_COMPLETION_CRASH_ROOT') or tempfile.mkdtemp(prefix='effectcraft completion crash '))
        case=base/(mode+'-'+point);case.mkdir(parents=True,exist_ok=True)
        self.assertFalse(any(case.iterdir()),'preserve previous evidence; select a fresh acceptance root')
        skill=case/'only readonly skill';shutil.copytree(ROOT/'skills/effectcraft-use',skill,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        for path in skill.rglob('*'):path.chmod(0o555 if path.is_dir() else 0o444)
        skill.chmod(0o555);installed=files(skill)
        managed=load(skill/'scripts/managed.py');tasks=managed.load('task_store');store=tasks.Store(case/'state')
        runtime=Path(os.environ['CRAFT_COMPLETION_CRASH_RUNTIME_HOME']);output=case/'delivery';task='interrupted'
        key=managed.load('platform_support').platform_key();lock=managed.read(skill/'scripts/runtime.lock.json')
        native=managed.load('bootstrap').inspect_install(runtime/'effectcraft'/lock['resolvedVersion'],lock['artifact'],lock['artifacts'][key],lock['resolvedVersion'],key)
        plan={'schema':'craft-command-plan/v1','operations':[
            {'command':'comp.new','params':{'name':'Original completion','width':96,'height':64,'duration':1,'frameRate':12}},
            {'command':'layer.newShape','params':{'kind':'rect','name':'Preserved subject','size':[32,32],'position':[48,32],'fill':'#ff6600'}},
            {'tool':'save_project','params':{'path':{'$output':'project.ecproj'}}},
            {'tool':'render_frame','params':{'time':0,'max_side':0,'transparent':True,'inline':False,'path':{'$output':'preview.png'}}}]}
        checked=managed.preflight(plan,output,mode)
        request={'inputs':{},'source':None};binding,manifest=managed.load('runtime_binding').prepare(skill,runtime)
        initial=store.create(task,plan=plan,output=str(output),runtime_sha=lock['artifacts'][key]['binarySha256'],inputs=checked['inputHashes'],source=None,mode=mode,authorization={'requestHash':tasks.digest(request)},runtime_binding=binding)
        tasks.atomic_json(store.path(task).parent/'request.json',request);managed.load('runtime_binding').freeze(store,task,skill,manifest)
        bound=managed.load('runtime_binding').resolve(store,task)
        # 只改变验收进程内的完成证明调用；原冻结资源逐字节保全。
        driver=case/'fault-worker.py'
        driver.write_text('''import importlib.util,os,signal,sys
from pathlib import Path
s=importlib.util.spec_from_file_location("crash_bound_managed",sys.argv[1]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
c=m.load("command_completion");capture=c.capture
if sys.argv[4]=="orphan":
    ledger=c.load("review_ledger");persist=ledger.immutable
    def interrupt_reference(path,value):
        persist(path,value)
        if path.name=="command-completion.json":os.kill(os.getpid(),signal.SIGKILL)
    ledger.immutable=interrupt_reference;original_completion_load=c.load
    c.load=lambda name:ledger if name=="review_ledger" else original_completion_load(name)
def crash(store,task):
    if sys.argv[4]!="before":capture(store,task)
    os.kill(os.getpid(),signal.SIGKILL)
c.capture=crash;original=m.load;m.load=lambda name:c if name=="command_completion" else original(name)
m.worker(m.load("task_store").Store(Path(sys.argv[2])),"interrupted",Path(sys.argv[3]))
''',encoding='utf-8')
        lifecycle=store.lifecycle_path(initial)
        # 不在guard的进程组内；证明清理不会停止不属于该任务的进程。
        unrelated=subprocess.Popen([sys.executable,'-I','-B','-c','import time;time.sleep(240)'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        self.addCleanup(lambda:self.stop_test_child(unrelated))
        with (case/'guard.log').open('wb') as log:
            guard=subprocess.Popen([bound['python'],'-I','-B',bound['guard'],'--receipt',str(lifecycle),'--lease',str(store.root/'leases'/(task+'.lifecycle.lock')),'--',bound['python'],'-I','-B',str(driver),bound['script'],str(store.root),bound['runtimeHome'],point],stdin=subprocess.PIPE,stdout=log,stderr=log,start_new_session=True)
            try:guard.wait(timeout=240)
            finally:
                if guard.poll() is None:
                    guard.stdin.close();guard.wait(timeout=25)
                if not guard.stdin.closed:guard.stdin.close()
        self.assertNotEqual(guard.returncode,0,(case/'guard.log').read_text(encoding='utf-8'))
        stopped=managed.read(lifecycle);self.assertEqual(stopped['status'],'stopped')
        self.assertEqual(stopped['returncode'],-signal.SIGKILL)
        self.assertTrue(stopped['ownership']['workerResultVerified'])
        self.assertEqual(stopped['ownership']['workerReturncode'],-signal.SIGKILL)
        self.assertIsNone(unrelated.poll())
        state=store.read(task);self.assertEqual(state['state'],'running')
        self.assertTrue(state['steps']);self.assertTrue(all(s['state']=='succeeded' for s in state['steps']))
        self.assertIsNone(state['delivery']);self.assertEqual('commandCompletion' in state,point=='after')
        completion_path=store.path(task).parent/'command-completion.json'
        self.assertEqual(completion_path.exists(),point!='before')
        completion_bytes=completion_path.read_bytes() if completion_path.exists() else None
        self.assertEqual(managed.read(output/'success.json')['result'],'PASS')
        if mode=='desktop':
            desktop=managed.read(output/'desktop-session.json')
            self.assertTrue(desktop['ownedProcessesStopped']);self.assertTrue(desktop['listenerOwnedByPID'])
        # 此处不人工改写状态、不补造停止材料；公开控制器必须处理原running账本。
        before_files=files(output);before_receipts=files(store.path(task).parent/'receipts')
        before_stats={p.relative_to(output).as_posix():(p.stat().st_ino,p.stat().st_mtime_ns) for p in output.rglob('*') if p.is_file()}
        resources=json.loads(json.dumps(state['resources']));actions=[]
        for action in ('reconcile','resume','resume'):
            argv=[sys.executable,'-I','-B',str(skill/'scripts/managed.py'),'--state-root',str(store.root),action,'--task',task]
            result=subprocess.run(argv,capture_output=True,timeout=180)
            (case/(action+'-'+str(len(actions))+'.stdout')).write_bytes(result.stdout);(case/(action+'-'+str(len(actions))+'.stderr')).write_bytes(result.stderr)
            expected=0 if point=='after' else 1
            self.assertEqual(result.returncode,expected,result.stdout.decode(errors='replace')+result.stderr.decode(errors='replace'))
            current=json.loads(result.stdout)
            self.assertEqual(current['state'],'review_ready' if point=='after' else 'reconciling')
            self.assertEqual(current['steps'],state['steps']);self.assertEqual(current['deadline'],initial['deadline'])
            self.assertEqual(current['budget'],state['budget']);self.assertEqual(current['resources'],resources)
            self.assertEqual(files(output),before_files);self.assertEqual(files(store.path(task).parent/'receipts'),before_receipts)
            self.assertEqual({p.relative_to(output).as_posix():(p.stat().st_ino,p.stat().st_mtime_ns) for p in output.rglob('*') if p.is_file()},before_stats)
            if point=='after':
                review=current['reconciliation']['completionReview'];self.assertEqual(review['engineering']['status'],'PASS');self.assertEqual(review['technical']['status'],'PASS')
            else:
                self.assertIsNone(current['delivery']);self.assertNotIn('commandCompletion',current)
            self.assertEqual(completion_path.read_bytes() if completion_path.exists() else None,completion_bytes)
            actions.append({'action':action,'state':current['state'],'result':current['reconciliation']['result']})
        if point!='after':
            with self.assertRaisesRegex(ValueError,'reconciliation_required'):
                store.create('bypass',plan=plan,output=str(case/'new output'),runtime_sha=state['identity']['runtimeSha256'],inputs={},source=None,mode=mode,authorization={})
            self.assertFalse((case/'new output').exists())
        observation=managed.read(store.path(task).parent/'command-delivery/observations/2.json')
        reopened=managed.load('command_delivery').verify_projects(output,[observation],native['executable'])
        self.assertEqual(reopened['status'],'PASS',reopened)
        decoded=managed.load('image_sequence').rgba_facts(output/'preview.png')
        self.assertEqual([decoded['width'],decoded['height']],[96,64]);self.assertEqual(decoded['alphaExtrema'],[0,255])
        self.assertEqual(files(output),before_files);self.assertEqual(files(skill),installed)
        self.assertEqual(managed.load('runtime_binding').source_files(Path(bound['script']).parent.parent),manifest)
        report={'schema':'effectcraft-native-command-completion-crash/v1','status':'PASS_COMPONENT','mode':mode,'crashPoint':point,'workerKilledBySignal':'SIGKILL','workerReturncode':stopped['returncode'],'originalLifecycleVerified':True,'unrelatedProcessPreserved':unrelated.poll() is None,'operations':len(state['steps']),'originalOutputsReceiptsAndFileStatsPreserved':True,'budgetResourcesAndDeadlinePreserved':True,'installedFiles':installed,'frozenResources':manifest,'engineering':'PASS','actualPNGDecoded':True,'actions':actions,'runtimeSha256':state['identity']['runtimeSha256'],'python':binding['python']['version'],'pythonMode':binding['python']['mode'],'cacheReused':True,'hostDispatch':'NOT_RUN','fullV1':'NOT_RUN','driverSha256':tasks.file_sha(driver),'testSha256':tasks.file_sha(Path(__file__))}
        (case/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

    @staticmethod
    def stop_test_child(child):
        if child.poll() is None:child.terminate();child.wait(timeout=10)


if __name__=='__main__':unittest.main()
