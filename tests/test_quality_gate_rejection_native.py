"""对当前公开原生交付的隔离副本注入损坏，评分不能掩盖实际技术失败。"""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.environ.get('CRAFT_QUALITY_GATE_REJECTION_LIVE') == '1', 'explicit native delivery rejection opt-in')
class NativeQualityRejectionTests(unittest.TestCase):
    def test_invalid_actual_video_rejects_high_score(self): self.exercise('video')
    def test_missing_collected_actual_asset_fails(self): self.exercise('asset')
    def test_invalid_actual_project_fails_independently_of_decodable_media(self): self.exercise('project')

    def exercise(self, kind):
        source = Path(os.environ['CRAFT_QUALITY_GATE_DELIVERY'])
        base = Path(os.environ.get('CRAFT_QUALITY_GATE_REJECTION_ROOT') or tempfile.mkdtemp(prefix='quality reject '))
        root = base / kind;root.mkdir(parents=True, exist_ok=True)
        self.assertFalse(any(root.iterdir()), 'select fresh evidence root')
        script = source.parent / 'single readonly skill/scripts/quality_review.py'
        spec = importlib.util.spec_from_file_location('current_native_quality_reject', script)
        quality = importlib.util.module_from_spec(spec);spec.loader.exec_module(quality)
        tasks = quality.load('task_store')
        def files(path): return {p.relative_to(path).as_posix(): quality.sha(p) for p in path.rglob('*') if p.is_file()}
        original = files(source)
        source_manifest = quality.read(source / 'manifest.json')
        original_review = quality.read(source.parent / '2-review.stdout')
        self.assertEqual(original_review['report']['engineering']['status'], 'PASS')
        self.assertEqual(original_review['report']['technical']['status'], 'PASS')
        delivery = root / 'isolated delivery';shutil.copytree(source, delivery)
        manifest = quality.read(delivery / 'manifest.json')
        if kind == 'video':
            location = manifest['video']['path'];(delivery / location).write_bytes(b'not a media container')
            manifest['files'][location] = quality.sha(delivery / location)
        elif kind == 'asset':
            location = manifest['assets']['fixture']['path'];(delivery / location).unlink()
            del manifest['files'][location]
        else:
            location = 'project.ecproj';(delivery / location).write_bytes(b'not a native project')
            manifest['files'][location] = quality.sha(delivery / location)
        (delivery / 'manifest.json').write_text(json.dumps(manifest))
        report = quality.inspect_delivery(delivery)
        if kind == 'project':
            self.assertEqual(report['technical']['status'], 'PASS', report)
            state = tasks.Store(source.parent / 'state').read('quality')
            engineering = quality.load('engineering_review').verify(delivery,
                Path(os.environ['CRAFT_QUALITY_GATE_RUNTIME_HOME']), state['identity']['runtimeSha256'])
            self.assertEqual(engineering['status'], 'FAIL', engineering)
            report['engineering'] = engineering
        else:
            self.assertEqual(report['technical']['status'], 'FAIL', report)
        if kind == 'video':
            self.assertIn('ffprobe', report['technical']['reason'], 'must reach actual media probe after fresh package hashing')
            request = original_review['judgeRequest']
            self.assertEqual(request['schema'], 'effectcraft-judge-request/v2')
            response = {'schema': 'effectcraft-judge-receipt/v2', 'requestId': request['requestId'], 'taskId': request['taskId'],
                'binding': request['binding'], 'criteriaHash': request['criteriaHash'], 'scopeHash': request['scopeHash'],
                'capabilities': {'visual': True, 'temporal': True}, 'score': 1.0, 'passed': True, 'issues': [],
                'temporalReviewed': True, 'status': 'PASS', 'observations': [
                    {'path': m['path'], 'sha256': m['sha256'], 'frameIndices': m['frameIndices'],
                     'method': 'synthetic hostile score for gate test', 'description': 'not actual creative acceptance'} for m in request['scope']['media']]}
            with self.assertRaisesRegex(ValueError, 'technical_gate'):
                quality.accept_judge(delivery, report, request, response)
        self.assertEqual(report['creative']['status'], 'NOT_RUN');self.assertEqual(report['userAcceptance']['status'], 'NOT_RUN')
        self.assertFalse(report['accepted']);self.assertEqual(files(source), original)
        proof = {'schema': 'effectcraft-native-technical-rejection/v1', 'status': 'PASS_COMPONENT', 'kind': kind,
            'sourceManifestSha256': quality.sha(source / 'manifest.json'), 'sourceProjectSha256': source_manifest['files']['project.ecproj'],
            'freshMutantManifest': True, 'sourcePreserved': True, 'engineering': report['engineering']['status'],
            'technical': report['technical']['status'], 'creative': 'NOT_RUN', 'userAcceptance': 'NOT_RUN', 'accepted': False,
            'highScoreRejected': kind == 'video', 'judgeEvidence': 'synthetic adversarial receipt only; no visual or host acceptance claim',
            'testSha256': quality.sha(Path(__file__)), 'qualitySha256': quality.sha(script),
            'engineeringSha256': quality.sha(script.with_name('engineering_review.py'))}
        (root / 'result.json').write_text(json.dumps(proof, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__': unittest.main()
