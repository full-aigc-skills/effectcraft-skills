"""真实原生保存后的父子取消与控制器重启；不伪造状态、停止回执或业务结果。"""
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
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    spec = importlib.util.spec_from_file_location('native_cancel_family', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def files(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}


@unittest.skipUnless(os.environ.get('CRAFT_CANCEL_FAMILY_LIVE') == '1', 'explicit native family cancellation opt-in')
@unittest.skipUnless(sys.platform == 'darwin' and platform.machine() == 'arm64', 'macOS arm64 native acceptance')
class NativeCancelFamilyTests(unittest.TestCase):
    def test_commands_parent_cancel_stops_native_child(self): self.exercise('commands', False)
    def test_desktop_parent_cancel_stops_native_child(self): self.exercise('desktop', False)
    def test_commands_cancel_survives_supervisor_sigkill(self): self.exercise('commands', True)
    def test_desktop_cancel_survives_supervisor_sigkill(self): self.exercise('desktop', True)

    def exercise(self, mode, crash):
        base = Path(os.environ.get('CRAFT_CANCEL_FAMILY_ROOT') or tempfile.mkdtemp(prefix='native cancel family '))
        case = base / (mode + ('-crash' if crash else '-normal'))
        case.mkdir(parents=True, exist_ok=True)
        self.assertFalse(any(case.iterdir()), 'select a fresh root; preserve prior evidence')
        skill = case / 'single readonly skill'
        shutil.copytree(ROOT / 'skills/effectcraft-use', skill, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        for path in skill.rglob('*'): path.chmod(0o555 if path.is_dir() else 0o444)
        skill.chmod(0o555)
        installed = files(skill)
        managed = load(skill / 'scripts/managed.py')
        tasks = managed.load('task_store')
        store = tasks.Store(case / 'state')
        runtime = Path(os.environ['CRAFT_CANCEL_FAMILY_RUNTIME_HOME'])
        binding, manifest = managed.load('runtime_binding').prepare(skill, runtime)
        lock = managed.read(skill / 'scripts/runtime.lock.json')
        native = managed.load('bootstrap').inspect_install(runtime / 'effectcraft' / lock['resolvedVersion'],
            lock['artifact'], lock['artifacts'][binding['platform']], lock['resolvedVersion'], binding['platform'])
        plan = {'schema': 'craft-command-plan/v1', 'operations': [
            {'command': 'comp.new', 'params': {'name': 'Native cancellation child', 'width': 96, 'height': 64, 'duration': 1, 'frameRate': 12}},
            {'command': 'layer.newShape', 'params': {'kind': 'rect', 'name': 'Preserved child', 'size': [32, 32], 'position': [48, 32], 'fill': '#ff6600'}},
            {'tool': 'render_frame', 'params': {'time': 0, 'max_side': 0, 'transparent': True, 'inline': False, 'path': {'$output': 'preview.png'}}},
            {'tool': 'save_project', 'params': {'path': {'$output': 'project.ecproj'}}}]}
        # 父项是已登记但未调度的编排任务；不伪造一个成功的父作品或修订。
        for task, parent, selected in [('parent', None, {'schema': 'craft-command-plan/v1', 'operations': [plan['operations'][0]]}), ('child', 'parent', plan)]:
            output = case / task
            checked = managed.preflight(selected, output, mode)
            request = {'inputs': {}, 'source': None}
            state = store.create(task, plan=selected, output=str(output), runtime_sha=lock['artifacts'][binding['platform']]['binarySha256'],
                inputs=checked['inputHashes'], source=None, mode=mode, authorization={'requestHash': tasks.digest(request)},
                runtime_binding=binding, parent=parent, seconds=600)
            tasks.atomic_json(store.path(task).parent / 'request.json', request)
            managed.load('runtime_binding').freeze(store, task, skill, manifest)
        initial = {task: store.read(task) for task in ('parent', 'child')}
        bound = managed.load('runtime_binding').resolve(store, 'child')
        marker = case / 'native-save-returned.json'
        worker = case / 'paused-native-worker.py'
        worker.write_text('''import importlib.util,sys,time
from pathlib import Path
s=importlib.util.spec_from_file_location("bound_worker",BINDING);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
original=m.Hooks.after
def pause(self,identifier,result):
    state=self.store.read(self.task)
    if next(x for x in state['steps'] if x['id']==identifier)['operation']=='save_project':
        m.load('task_store').atomic_json(Path(MARKER),{'operation':identifier,'nativeReturned':True})
        while True:time.sleep(.1)
    return original(self,identifier,result)
m.Hooks.after=pause
m.worker(m.load('task_store').Store(Path(STATE)),"child",Path(RUNTIME))
'''.replace('BINDING', repr(bound['script'])).replace('MARKER', repr(str(marker))).replace('STATE', repr(str(store.root))).replace('RUNTIME', repr(bound['runtimeHome'])), encoding='utf-8')
        controller = case / 'native-supervisor.py'
        controller.write_text('''import importlib.util,json
from pathlib import Path
from types import SimpleNamespace
s=importlib.util.spec_from_file_location("bound_supervisor",BINDING);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
binding=m.load('runtime_binding');resolve=binding.resolve
def selected(*args):
    value=resolve(*args);value['script']=WORKER;return value
binding.resolve=selected;original=m.load;m.load=lambda name:binding if name=='runtime_binding' else original(name)
sleep=m.time.sleep
def parked(seconds):
    if seconds==.1 and Path(MARKER).exists():
        Path(READY).write_text('supervisor outside ledger lock')
        while not Path(RELEASE).exists():sleep(.01)
    sleep(seconds)
m.time.sleep=parked
result=m.supervise(m.load('task_store').Store(Path(STATE)),"child",Path(RUNTIME))
print(json.dumps(result))
'''.replace('BINDING', repr(bound['script'])).replace('WORKER', repr(str(worker))).replace('STATE', repr(str(store.root))).replace('RUNTIME', repr(bound['runtimeHome'])).replace('MARKER', repr(str(marker))).replace('READY', repr(str(case / 'supervisor-outside-lock'))).replace('RELEASE', repr(str(case / 'release-supervisor'))), encoding='utf-8')
        unrelated = subprocess.Popen([sys.executable, '-I', '-B', '-c', 'import time;time.sleep(240)'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.addCleanup(lambda: self.stop(unrelated))
        with (case / 'controller.log').open('wb') as log:
            process = subprocess.Popen([bound['python'], '-I', '-B', str(controller)], stdout=log, stderr=log)
            try:
                self.until(lambda: marker.exists() or process.poll() is not None, 120)
                self.assertTrue(marker.exists(), (case / 'controller.log').read_text())
                self.until(lambda: (case / 'supervisor-outside-lock').exists(), 15)
                state = store.read('child')
                self.assertEqual(state['steps'][-1]['operation'], 'save_project')
                self.assertEqual(state['steps'][-1]['state'], 'attempted')
                output = case / 'child'
                original_files = files(output)
                original_stats = {p.name: (p.stat().st_ino, p.stat().st_mtime_ns) for p in output.iterdir() if p.is_file()}
                original_receipts = files(store.path('child').parent / 'receipts')
                # 暂停真实监督进程，保证取消已持久化但尚未关闭守护通道。
                if crash: os.kill(process.pid, signal.SIGSTOP)
                cancelled = self.public(skill, store, 'cancel', 'parent', case)
                self.assertEqual(cancelled['state'], 'cancel_requested')
                self.assertIn('child', cancelled['cancellationFamily']['pendingTasks'])
                requested = {task: store.read(task) for task in ('parent', 'child')}
                self.assertEqual(requested['child']['state'], 'cancel_requested')
                if crash:
                    os.kill(process.pid, signal.SIGKILL)
                    process.wait(timeout=15)
                    self.assertEqual(process.returncode, -signal.SIGKILL)
                else:
                    (case / 'release-supervisor').touch()
                    process.wait(timeout=40)
                    self.assertEqual(process.returncode, 0, (case / 'controller.log').read_text())
                lifecycle = store.lifecycle_path(store.read('child'))
                self.until(lambda: lifecycle.exists() and managed.read(lifecycle).get('status') == 'stopped', 40)
                stop = managed.read(lifecycle)
                self.assertEqual(stop['status'], 'stopped')
                self.assertNotEqual(stop['returncode'], 0)
                self.assertEqual(stop['ownership']['schema'], 'effectcraft-posix-group-lease/v1')
                if crash:
                    self.assertEqual(store.read('child')['state'], 'cancel_requested', 'no manual settlement after killing supervisor')
                self.assertIsNone(unrelated.poll())
                actions = []
                # 父项不能仅凭自有未启动证明越过尚未核对子项。
                pending = self.public(skill, store, 'reconcile', 'parent', case)
                if crash: self.assertEqual(pending['state'], 'cancel_requested')
                for action, task in [('reconcile', 'child'), ('reconcile', 'parent'), ('resume', 'child'), ('resume', 'parent')]:
                    current = self.public(skill, store, action, task, case)
                    self.assertEqual(current['state'], 'reconciling')
                    self.assertEqual(current['cancellationFamily']['pendingTasks'], [])
                    self.assertIn('child', current['cancellationFamily']['unknownTasks'])
                    self.assertEqual(current['termination']['status'], 'confirmed')
                    self.assertEqual(current['cancellationRequestedAt'], requested[task]['cancellationRequestedAt'])
                    for key in ('identity', 'identityHash', 'deadline', 'budget', 'steps'): self.assertEqual(current[key], (state if task == 'child' else initial[task])[key])
                    actions.append({'action': action, 'task': task, 'state': current['state']})
                self.assertEqual(files(output), original_files)
                self.assertEqual(files(store.path('child').parent / 'receipts'), original_receipts)
                self.assertEqual({p.name: (p.stat().st_ino, p.stat().st_mtime_ns) for p in output.iterdir() if p.is_file()}, original_stats)
                settled_resources = store.read('parent')['resources']
                self.assertIn('child', settled_resources['entries'])
                self.assertEqual(settled_resources['entries']['child']['frames'], 1)
                # 命令媒体的解码预占记录在commandFrames；顶层decodedBytes用于workflow预占。
                self.assertEqual(sum(x['decodedBytes'] for x in settled_resources['entries']['child']['commandFrames'].values()), 96 * 64 * 4)
                for key in ('bindingHash', 'frames', 'decodedBytes', 'commandFrames'):
                    self.assertEqual(settled_resources['entries']['child'][key], requested['parent']['resources']['entries']['child'][key])
                self.assertEqual(settled_resources['entries']['child']['encodedBytes'], (output / 'preview.png').stat().st_size)
                self.public(skill, store, 'reconcile', 'parent', case)
                self.assertEqual(store.read('parent')['resources'], settled_resources)
                self.assertEqual(store.read('child')['deadline'], initial['parent']['deadline'])
                self.assertIsNone(store.read('child')['delivery'])
                self.assertFalse((case / 'parent').exists())
                self.assertNotIn('processExit', store.read('parent'))
                with self.assertRaisesRegex(ValueError, 'reconciliation_required'):
                    store.create('bypass', plan=plan, output=str(case / 'new-output'), runtime_sha=state['identity']['runtimeSha256'], inputs={}, source=None, mode=mode, authorization={})
                # 原工程存在且可重开；未知保存回执仍不补造为成功。
                before = managed.read(store.path('child').parent / 'command-delivery/observations/3.before.json')
                # 仅给验收器绑定当前保存文件；不写入缺失的产品回执或任务完成证明。
                project_check = {key: before[key] for key in ('path', 'dependencies', 'snapshot')}
                project_check['sha256'] = tasks.file_sha(output / 'project.ecproj')
                reopened = managed.load('command_delivery').verify_projects(output, [project_check], native['executable'])
                self.assertEqual(reopened['status'], 'PASS', reopened)
                pixels = managed.load('image_sequence').rgba_facts(output / 'preview.png')
                self.assertEqual([pixels['width'], pixels['height'], pixels['alphaExtrema']], [96, 64, [0, 255]])
                self.assertEqual(files(output), original_files)
                self.assertIsNone(unrelated.poll())
                self.assertEqual(files(skill), installed)
                self.assertEqual(managed.load('runtime_binding').source_files(Path(bound['script']).parent.parent), manifest)
                report = {'schema': 'effectcraft-native-family-cancellation/v1', 'status': 'PASS_COMPONENT', 'mode': mode,
                    'supervisorSIGKILL': crash, 'parentRegisteredNotStarted': True, 'nativeSaveReturnedBeforeDurableReceipt': True,
                    'ownedLifecycleStopped': True, 'lifecycle': stop, 'unknownChildPreserved': True, 'unrelatedProcessPreserved': unrelated.poll() is None,
                    'deadlineBudgetResourcesPreserved': True, 'resources': settled_resources, 'steps': len(state['steps']), 'actions': actions,
                    'engineering': 'PASS', 'actualPNGDecoded': True, 'installedFiles': installed, 'frozenResources': manifest,
                    'workerDriverSha256': tasks.file_sha(worker), 'controllerDriverSha256': tasks.file_sha(controller), 'testSha256': tasks.file_sha(Path(__file__)),
                    'runtimeSha256': state['identity']['runtimeSha256'], 'python': binding['python']['version'], 'pythonMode': binding['python']['mode'],
                    'cacheReused': True, 'hostDispatch': 'NOT_RUN', 'fullV1': 'NOT_RUN'}
                (case / 'result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
            finally:
                if process.poll() is None:
                    # 只停止本测试创建的监督进程；EOF由原守护器清理其自有树。
                    process.kill();process.wait(timeout=15)

    def public(self, skill, store, action, task, case):
        process = subprocess.run([sys.executable, '-I', '-B', str(skill / 'scripts/managed.py'), '--state-root', str(store.root), action, '--task', task], capture_output=True, timeout=60)
        count = len(list(case.glob('public-*.stdout')))
        (case / ('public-' + str(count) + '.stdout')).write_bytes(process.stdout)
        (case / ('public-' + str(count) + '.stderr')).write_bytes(process.stderr)
        result = json.loads(process.stdout)
        self.assertIn('state', result, process.stdout.decode(errors='replace') + process.stderr.decode(errors='replace'))
        self.assertEqual(process.returncode, 1)
        return result

    @staticmethod
    def until(predicate, seconds):
        end = time.monotonic() + seconds
        while not predicate():
            if time.monotonic() > end: raise AssertionError('timed out waiting for original live native process')
            time.sleep(.05)

    @staticmethod
    def stop(process):
        if process.poll() is None: process.terminate();process.wait(timeout=10)


if __name__ == '__main__': unittest.main()
