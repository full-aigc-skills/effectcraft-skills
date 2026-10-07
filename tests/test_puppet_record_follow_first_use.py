"""木偶录制与跟随须保存真实动画、按范围返工并保全其他对象。"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tree(folder):
    return {str(path.relative_to(folder)): digest(path)
            for path in folder.rglob('*') if path.is_file()}


def group(properties, uid):
    """按实际返回 UID 查找属性组，不猜测原生组名或属性索引。"""
    if isinstance(properties, dict):
        if properties.get('uid') == uid:
            return properties
        for value in properties.values():
            found = group(value, uid)
            if found is not None:
                return found
    elif isinstance(properties, list):
        for value in properties:
            found = group(value, uid)
            if found is not None:
                return found
    return None


@unittest.skipUnless(os.environ.get('CRAFT_PUPPET_FIRST_USE') == '1',
                     'requires declared macOS arm64 runtime and public locked archive')
class PuppetRecordFollowFirstUseTests(unittest.TestCase):
    def test_record_follow_reopen_targeted_revision_and_rejected_calls(self):
        from PIL import Image, ImageChops
        selected = Path(os.environ.get('CRAFT_INSTALLED_SKILL_ROOT',
                                      str(ROOT/'skills/effectcraft-cli-puppet')))
        if os.environ.get('CRAFT_PUPPET_OUTPUT_ROOT'):
            work = Path(os.environ['CRAFT_PUPPET_OUTPUT_ROOT'])
            work.mkdir(parents=True, exist_ok=False)
        else:
            temporary = tempfile.TemporaryDirectory(prefix='puppet-record-follow-')
            self.addCleanup(temporary.cleanup)
            work = Path(temporary.name)
        skill = work/'项目 空格/.agents/skills/effectcraft-cli-puppet'
        shutil.copytree(selected, skill, ignore=shutil.ignore_patterns('__pycache__'))
        before = tree(skill)
        source_before = tree(selected)
        self.assertEqual({p.name for p in skill.parent.iterdir()}, {skill.name})
        runtime = work/'runtime 空缓存'
        self.assertFalse(runtime.exists())
        spec = importlib.util.spec_from_file_location('puppet_commands', skill/'scripts/commands.py')
        commands = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(commands)
        from unittest.mock import patch
        environment = {key: value for key, value in os.environ.items() if not key.startswith('CRAFT_')}
        environment['PATH'] = '/usr/bin:/bin'
        plans = {}
        receipts = {}

        def execute(name, project=None):
            plan = json.loads((skill/'examples'/('puppet-record-follow-'+name+'.json')).read_text())
            inputs = {} if project is None else {'project': str(project)}
            commands.validate(plan, inputs)
            with patch.dict(os.environ, environment, clear=True):
                result = commands.execute(plan, work/name, runtime_home=runtime, inputs=inputs)
            self.assertEqual(result['result'], 'PASS', result.get('error'))
            self.assertTrue(all(step['state'] == 'succeeded' for step in result['steps']))
            plans[name], receipts[name] = plan, result
            return {step['as']: actual['result'] for step, actual in zip(plan['operations'], result['steps'])
                    if 'as' in step}

        def pins(info):
            self.assertEqual(len(info['meshes']), 1)
            return {item['pin']: item for item in info['meshes'][0]['pins']}

        def property_child(info, uid, name):
            item = group(info['properties'], uid)
            self.assertIsNotNone(item)
            return next(child for child in item['children'] if child.get('match') == name)

        def state(info):
            # 查询的当前时间不属于非目标图层的保存属性。
            return {key: value for key, value in info.items() if key != 'time'}

        made = execute('create')
        anchor, leader, follower, scratch = [made[name]['pin'] for name in
                                            ('anchor', 'leader', 'follower', 'scratch')]
        self.assertEqual(made['removed']['removed'], 1)
        self.assertEqual(made['selected']['pins'], [leader, follower])
        self.assertEqual(made['recordOptions'], {'speed': 100.0, 'smoothing': 0.0,
                         'useDraftDeformation': False, 'showMesh': False})
        self.assertEqual(made['recorded'], {'start': 0.0, 'end': .5, 'frames': 7, 'keys': 7})
        self.assertEqual(made['followed']['leader'], leader)
        self.assertEqual(made['followed']['pins'][0]['pin'], follower)
        self.assertAlmostEqual(made['followed']['pins'][0]['delay'], 1/12)
        self.assertEqual(pins(made['movedInfo'])[leader]['position'], [48.0, 16.0])
        self.assertEqual(pins(made['recordedInfo'])[leader]['position'], [48.0, 12.0])
        self.assertEqual(pins(made['finalInfo'])[follower]['position'], [32.0, 18.0])
        self.assertEqual(pins(made['finalInfo'])[anchor]['position'], [16.0, 24.0])
        self.assertNotIn(scratch, pins(made['finalInfo']))
        lead_property = property_child(made['subjectProperties'], leader, 'position')
        self.assertEqual(len(lead_property['keys']), 7)
        for key, time in zip(lead_property['keys'], [n/12 for n in range(7)]):
            self.assertAlmostEqual(key['time'], time)
        self.assertEqual(property_child(made['subjectProperties'], follower, 'scale')['value'], 110.0)
        self.assertEqual(property_child(made['subjectProperties'], follower, 'rotation')['value'], 5.0)
        with Image.open(work/'create/before-follow.png') as before_image, \
                Image.open(work/'create/followed.png') as followed:
            self.assertEqual(followed.size, (96, 64))
            self.assertIsNotNone(ImageChops.difference(before_image.convert('RGB'),
                                                      followed.convert('RGB')).getbbox())
            self.assertEqual(followed.convert('RGB').getpixel((88, 8)), (0, 255, 0))
        original = work/'create/project.ecproj'
        original_sha = digest(original)
        opened = execute('reopen', original)
        self.assertEqual(opened['finalInfo'], made['finalInfo'])
        self.assertEqual(state(opened['controlProperties']), state(made['controlProperties']))
        self.assertEqual(opened['subjectProperties']['properties'], made['subjectProperties']['properties'])
        with Image.open(work/'create/followed.png') as a, Image.open(work/'reopen/reopened.png') as b:
            self.assertEqual(a.convert('RGBA').tobytes(), b.convert('RGBA').tobytes())
        revised = execute('revise', original)
        self.assertEqual(revised['recorded'], made['recorded'])
        self.assertEqual(pins(revised['finalInfo'])[follower]['position'], [32.0, 21.0])
        self.assertEqual(pins(revised['finalInfo'])[anchor], pins(made['finalInfo'])[anchor])
        self.assertEqual(group(revised['subjectProperties'], anchor), group(made['subjectProperties'], anchor))
        self.assertEqual(group(revised['subjectProperties'], follower), group(made['subjectProperties'], follower))
        self.assertEqual(state(revised['controlProperties']), state(made['controlProperties']))
        revised_plan = plans['reopen']
        with patch.dict(os.environ, environment, clear=True):
            second = commands.execute(revised_plan, work/'revised-reopened', runtime_home=runtime,
                                      inputs={'project': str(work/'revise/project.ecproj')})
        self.assertEqual(second['result'], 'PASS', second.get('error'))
        info = second['steps'][1]['result']
        self.assertEqual(info, revised['finalInfo'])
        with Image.open(work/'create/followed.png') as a, Image.open(work/'revise/revised.png') as b, \
                Image.open(work/'revised-reopened/reopened.png') as c:
            self.assertIsNotNone(ImageChops.difference(a.convert('RGB'), b.convert('RGB')).getbbox())
            self.assertEqual(a.convert('RGBA').crop((85, 5, 91, 11)).tobytes(),
                             b.convert('RGBA').crop((85, 5, 91, 11)).tobytes())
            self.assertEqual(b.convert('RGBA').tobytes(), c.convert('RGBA').tobytes())
        failures = []
        for name, source, command, params in [
            ('empty', None, 'puppet.recordPin', {'pin': 1, 'samples': [[0, 0, 0]]}),
            ('nonmoving', work/'create/rigged.ecproj', 'puppet.recordPin',
             {'layer': 'Deform subject', 'pin': scratch, 'samples': [[0, 32, 16], [.5, 32, 12]]}),
            ('missing', original, 'puppet.removePin', {'layer': 'Deform subject', 'pin': 999999})]:
            steps = [] if source is None else [{'tool': 'open_project', 'params': {'path': {'$ref': 'project.path'}}}]
            steps += [{'command': command, 'params': params},
                      {'tool': 'save_project', 'params': {'path': {'$output': 'forbidden.ecproj'}}}]
            plan = {'schema': 'craft-command-plan/v1', 'operations': steps}
            inputs = {} if source is None else {'project': str(source)}
            source_sha = None if source is None else digest(source)
            with patch.dict(os.environ, environment, clear=True):
                failed = commands.execute(plan, work/name, runtime_home=runtime, inputs=inputs)
            self.assertEqual(failed['result'], 'FAIL', failed)
            self.assertFalse((work/name/'forbidden.ecproj').exists())
            self.assertFalse(any(step.get('tool') == 'save_project' for step in failed['steps']))
            if source is not None:
                self.assertEqual(digest(source), source_sha)
            failures.append({'case': name, 'result': failed['result'], 'error': failed['error']})
        self.assertEqual(digest(original), original_sha)
        self.assertEqual(tree(skill), before)
        self.assertEqual(tree(selected), source_before)
        family = {step['command'] for step in receipts['create']['steps']
                  if (step.get('command') or '').startswith('puppet.')}
        self.assertEqual(len(family), 10)
        if os.environ.get('CRAFT_PUPPET_EVIDENCE_FILE'):
            evidence = {'schema': 'craft-puppet-record-follow-first-use/v1', 'result': 'PASS',
                        'skill': selected.name, 'runtimeSha256': receipts['create']['runtimeSha256'],
                        'commands': sorted(family), 'recordedFrames': 7, 'frameRate': 12,
                        'followDelaySeconds': 1/12, 'followAmountPercent': 50,
                        'followerAtOneThird': [32, 18], 'revisedFollowerAtOneThird': [32, 21],
                        'originalProjectSha256': original_sha, 'revisedProjectSha256': digest(work/'revise/project.ecproj'),
                        'createPlanSha256': digest(skill/'examples/puppet-record-follow-create.json'),
                        'failures': failures, 'checks': ['single skill, public cold runtime install',
                        'returned pin and mesh identities', 'ten representative puppet commands',
                        'seven frame-aligned recording keys', 'follow expression evaluated by native renderer',
                        'native reopen and identical rendered pixels', 'targeted amplitude revision',
                        'anchor, follower expression and control layer preserved',
                        'source projects and skill trees preserved'],
                        'unverified': ['all pin kinds and parameter contexts', 'GUI pointer gestures', 'creative quality'],
                        'scope': 'headless position/advanced recording and follow fixture; not full CM-001'}
            Path(os.environ['CRAFT_PUPPET_EVIDENCE_FILE']).write_text(json.dumps(evidence, indent=2)+'\n')


if __name__ == '__main__':
    unittest.main()
