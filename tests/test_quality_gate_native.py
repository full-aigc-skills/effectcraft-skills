"""独立只读技能公开入口的完整技术门禁：真实素材、工程、视频与两种序列。"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import struct
import subprocess
import tempfile
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[1]


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def files(root):
    return {p.relative_to(root).as_posix(): sha(p) for p in root.rglob('*')
            if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}


def load(path):
    spec = importlib.util.spec_from_file_location('native_quality_gate', path)
    value = importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


@unittest.skipUnless(os.environ.get('CRAFT_QUALITY_GATE_LIVE') == '1', 'explicit native technical gate opt-in')
@unittest.skipUnless(platform.system() == 'Darwin' and platform.machine() == 'arm64', 'macOS arm64 native acceptance')
class NativeQualityGateTests(unittest.TestCase):
    def test_collected_asset_video_public_review(self): self.exercise('mp4')
    def test_collected_asset_transparent_sequence_public_review(self): self.exercise('png-sequence')
    def test_collected_asset_segmented_sequence_public_review(self): self.exercise('png-segmented')

    def exercise(self, format):
        base = Path(os.environ.get('CRAFT_QUALITY_GATE_ROOT') or tempfile.mkdtemp(prefix='native quality gate '))
        root = base / format;root.mkdir(parents=True, exist_ok=True)
        self.assertFalse(any(root.iterdir()), 'preserve prior evidence; select a fresh root')
        skill = root / 'single readonly skill'
        shutil.copytree(ROOT / 'skills/effectcraft-use', skill, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        for path in skill.rglob('*'): path.chmod(0o555 if path.is_dir() else 0o444)
        skill.chmod(0o555);installed = files(skill)
        runtime = Path(os.environ['CRAFT_QUALITY_GATE_RUNTIME_HOME'])
        self.assertIn('CRAFT_PYTHON_HOME', os.environ, 'prepared isolated interpreter cache required')
        env = dict(os.environ, CRAFT_RUNTIME_HOME=str(runtime), PATH='/opt/homebrew/bin:/usr/bin:/bin')
        state = root / 'state';output = root / 'delivery'
        def chunk(kind, data): return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
        asset = root / 'source fixture.png'
        asset.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 16, 16, 8, 6, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress((b'\x00' + b'\xff\x66\x00\xff' * 16) * 16)) + chunk(b'IEND', b''))
        plan = {'document': {'name': 'Current technical gate', 'width': 64, 'height': 48, 'frameRate': 4, 'duration': 1},
            'assets': {'fixture': {'path': str(asset), 'sha256': sha(asset)}},
            'operations': [{'command': 'asset.import', 'params': {'asset': 'fixture'}, 'as': 'footage'},
                {'command': 'layer.addItem', 'params': {'item': {'$ref': 'footage.item'}, 'position': [32, 24]}, 'as': 'subject'}],
            'frames': [0, .5], 'exports': [{'format': format}]}
        if format == 'png-segmented': plan['exports'][0]['chunkFrames'] = 2
        plan_path = root / 'plan.json';plan_path.write_text(json.dumps(plan))
        criteria = root / 'criteria.json';criteria.write_text(json.dumps({'goal': 'Technical gate acceptance; creative and user acceptance not evaluated'}))
        actions = []
        def public(action, *args):
            result = subprocess.run(['/bin/sh', str(skill / 'scripts/launch.sh'), '--state-root', str(state), action, *map(str, args)],
                env=env, cwd=root, capture_output=True, timeout=300)
            label = str(len(actions)) + '-' + action
            (root / (label + '.stdout')).write_bytes(result.stdout);(root / (label + '.stderr')).write_bytes(result.stderr)
            self.assertEqual(result.returncode, 0, result.stdout.decode(errors='replace') + result.stderr.decode(errors='replace'))
            data = json.loads(result.stdout);actions.append(action);return data
        check = public('plan', '--plan', plan_path, '--output', output)
        self.assertEqual(check['result'], 'VALID');self.assertFalse(state.exists());self.assertFalse(output.exists())
        run = public('run', '--task', 'quality', '--plan', plan_path, '--output', output)
        self.assertEqual(run['state'], 'review_ready');self.assertTrue(all(x['state'] == 'succeeded' for x in run['steps']))
        before = files(output)
        review = public('review', '--task', 'quality', '--criteria', criteria)
        report = review['report']
        self.assertEqual(report['engineering']['status'], 'PASS', report)
        self.assertEqual(report['technical']['status'], 'PASS', report)
        self.assertEqual(report['technical']['verifiedAssets'], 1)
        self.assertEqual(report['creative']['status'], 'NOT_RUN');self.assertEqual(report['userAcceptance']['status'], 'NOT_RUN')
        self.assertFalse(report['accepted'])
        self.assertTrue(any(x.get('verifiedFrames') == 4 for x in report['technical']['media']), report)
        managed = load(skill / 'scripts/managed.py');store = managed.load('task_store').Store(state)
        current = store.read('quality');bound = managed.load('runtime_binding').resolve(store, 'quality')
        frozen = managed.load('runtime_binding').source_files(Path(bound['script']).parent.parent)
        self.assertTrue(all(installed[k] == v for k, v in frozen.items()))
        manifest = managed.read(output / 'manifest.json')
        self.assertEqual(sha(output / manifest['assets']['fixture']['path']), sha(asset))
        for frame in manifest['frames']:
            facts = managed.load('image_sequence').rgba_facts(output / frame['path'])
            self.assertEqual([facts['width'], facts['height'], facts['alphaExtrema']], [64, 48, [0, 255]])
        if format != 'mp4':
            observed = managed.load('quality_review').inspect_sequence_contract(output, manifest['imageSequence'])
            self.assertEqual(observed['verifiedFrames'], 4)
        lifecycle = managed.read(store.lifecycle_path(current))
        self.assertEqual(lifecycle['status'], 'stopped');self.assertEqual(lifecycle['returncode'], 0)
        receipts = files(store.path('quality').parent / 'receipts')
        public('resume', '--task', 'quality')
        self.assertEqual(files(output), before);self.assertEqual(files(store.path('quality').parent / 'receipts'), receipts)
        self.assertEqual(files(skill), installed)
        # 原成功交付不受负例影响；隔离副本的清单摘要也同步，强制检验实际内容。
        negative = root / 'corrupt media copy';shutil.copytree(output, negative)
        bad_manifest = managed.read(negative / 'manifest.json')
        bad_frame = bad_manifest['frames'][0]['path'];(negative / bad_frame).write_bytes(b'not PNG')
        bad_manifest['files'][bad_frame] = sha(negative / bad_frame)
        (negative / 'manifest.json').write_text(json.dumps(bad_manifest))
        rejected = managed.load('quality_review').inspect_delivery(negative)
        self.assertEqual(rejected['technical']['status'], 'FAIL', rejected)
        self.assertEqual(rejected['creative']['status'], 'NOT_RUN');self.assertFalse(rejected['accepted'])
        self.assertEqual(files(output), before)
        proof = {'schema': 'effectcraft-native-technical-gate/v1', 'status': 'PASS_COMPONENT', 'format': format,
            'platform': 'darwin-arm64', 'report': report, 'manifestSha256': sha(output / 'manifest.json'),
            'projectSha256': sha(output / 'project.ecproj'), 'nativeOutputs': before, 'steps': len(current['steps']),
            'negativeActualDecode': {'technical': 'FAIL', 'freshManifestHash': True, 'creative': 'NOT_RUN', 'originalPreserved': True},
            'installedFiles': installed, 'frozenResources': frozen, 'testSha256': sha(Path(__file__)),
            'actions': actions, 'runtimeSha256': current['identity']['runtimeSha256'], 'python': current['identity']['runtimeBinding']['python'],
            'cacheReused': True, 'isolatedPython': True, 'hostDispatch': 'NOT_RUN', 'fullV1': 'NOT_RUN'}
        (root / 'result.json').write_text(json.dumps(proof, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__': unittest.main()
