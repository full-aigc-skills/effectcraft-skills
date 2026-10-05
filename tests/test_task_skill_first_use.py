"""EffectCraft 场景技能首次安装及真实操作；摄像机必须包含可执行前置步骤。"""
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

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class CameraSkillContractTests(unittest.TestCase):
    def test_camera_skill_carries_creation_view_and_layer_prerequisites(self):
        catalog = json.loads((ROOT / 'skills/effectcraft-cli-camera/references/commands.json').read_text())
        required = {'layer.newCamera', 'layer.newLight', 'layer.setSwitch',
                    'view.set3DView', 'view.get3D', 'camera.dolly'}
        self.assertTrue(required.issubset({command['id'] for command in catalog['commands']}))


    def test_masks_skill_carries_editable_mask_commands_and_example(self):
        catalog=json.loads((ROOT/'skills/effectcraft-cli-masks/references/commands.json').read_text())
        self.assertTrue({'mask.new','mask.setVertex','mask.remove'}.issubset({entry['id'] for entry in catalog['commands']}))
        plan=json.loads((ROOT/'skills/effectcraft-cli-masks/examples/layer-mask.json').read_text())
        self.assertIn('mask.new',{entry['command'] for entry in plan['operations']})


@unittest.skipUnless(os.environ.get('CRAFT_TASK_FIRST_USE') == '1',
                     'requires macOS arm64, public archives, ffprobe and Pillow')
class TaskSkillFirstUseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture_directory = tempfile.TemporaryDirectory(prefix='effectcraft-task-fixture-')
        cls.fixture = Path(cls.fixture_directory.name)
        source = ROOT / 'skills/effectcraft-use'
        spec = importlib.util.spec_from_file_location('effect_task_fixture', source / 'scripts/workflow.py')
        workflow = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(workflow)
        cls.base = cls.fixture / 'base'
        delivered = workflow.execute(json.loads((source / 'examples/brand-intro.json').read_text()),
                                     cls.base, runtime_home=cls.fixture / 'fixture-runtime')
        cls.project = cls.base / 'project.ecproj'
        cls.project_sha = digest(cls.project)
        cls.comp = delivered['bindings']['composition']['comp']
        cls.badge = delivered['bindings']['badge']['layer']
        cls.title = delivered['bindings']['title']['layer']

    @classmethod
    def tearDownClass(cls):
        cls.fixture_directory.cleanup()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='effectcraft-task-single-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.runtime = self.root / 'fresh-runtime'
        self.environment = dict(os.environ, PATH='/usr/bin:/bin')
        self.addCleanup(lambda: self.assertEqual(digest(self.project), self.project_sha))

    def install_only(self, task):
        self.skill_name = 'effectcraft-cli-' + task
        self.skill = self.root / 'single-skill'
        shutil.copytree(ROOT / 'skills' / self.skill_name, self.skill,
                        ignore=shutil.ignore_patterns('__pycache__'))
        self.assertFalse(self.runtime.exists())

    def cli(self, *arguments, success=True):
        result = subprocess.run([sys.executable, '-I', '-B', str(self.skill / 'scripts/cli.py'),
                                 '--runtime-home', str(self.runtime), '--', *map(str, arguments), '--json'],
                                env=self.environment, capture_output=True, text=True, timeout=240)
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue((self.runtime / 'effectcraft/0.2.0/effectcraft-cli').is_file())
        else:
            self.assertNotEqual(result.returncode, 0)
        return result

    def execute(self, command, params, target, project=None):
        return json.loads(self.cli('exec', command, '--params', json.dumps(params),
                                   '--project', project or self.project, '--save-as', target).stdout)['result']

    def info(self, project):
        return json.loads(self.cli('info', '--project', project).stdout)

    def prop(self, project, layer, path, time=0):
        return json.loads(self.cli('get', self.comp, layer, path, '--time', time, '--project', project).stdout)

    def props(self, project, layer):
        properties = json.loads(self.cli('props', self.comp, layer, '--project', project).stdout)
        # 插入新图层会改变栈索引，不代表旧图层属性被编辑；稳定 ID 和其余数据仍逐项比较。
        properties.pop('index', None)
        return properties

    def render(self, project, name='frame.png', time=0, transparent=False):
        output = self.root / name
        if transparent:
            # 0.2.0 render-frame 是 RGB 预览。透明交付使用 RGBA PNG 原生序列导出。
            # render 的 --comp 要求名称；props/get/render-frame 则接受数字 ID。
            composition = self.info(project)['activeComp']
            result = json.loads(self.cli('render', '--comp', composition['name'], '--start', time,
                                         '--end', time + 1 / composition['frameRate'],
                                         '--fps', composition['frameRate'], '--out', output,
                                         '--format', 'png', '--channels', 'rgba', '--project', project).stdout)
            output = Path(result['rendered'][0]['output'])
            self.assertTrue(output.is_relative_to(self.root))
        else:
            self.cli('render-frame', '--comp', self.comp, '--time', time, '--out', output, '--project', project)
        return output

    def test_project_creates_and_reopens_native_composition(self):
        self.install_only('project')
        target = self.root / 'new.ecproj'
        result = self.cli('run', 'file.newProject', '{}', 'comp.new',
                          json.dumps({'name': 'Main', 'width': 320, 'height': 180, 'frameRate': 12, 'duration': 1}),
                          '--empty', '--save-as', target)
        self.assertEqual(len(json.loads(result.stdout)['result']), 2)
        reopened = self.info(target)
        self.assertEqual(reopened['activeComp']['name'], 'Main')
        self.assertEqual((reopened['activeComp']['width'], reopened['activeComp']['height']), (320, 180))
        self.assertEqual(reopened['activeComp']['layers'], [])

    def test_footage_imports_and_places_image_without_changing_existing_layers(self):
        from PIL import Image
        self.install_only('footage')
        image, imported, target = self.root / 'product.png', self.root / 'imported.ecproj', self.root / 'placed.ecproj'
        Image.new('RGBA', (320, 180), (20, 210, 50, 255)).save(image)
        old_layers = self.info(self.project)['activeComp']['layers']
        result = self.execute('file.import', {'paths': [str(image)]}, imported)
        item = result['items'][0]
        placed = self.execute('layer.addItem', {'item': item, 'time': 0, 'duration': 1}, target, imported)
        layers = self.info(target)['activeComp']['layers']
        self.assertEqual(len(layers), len(old_layers) + 1)
        for old in old_layers:
            current = next(layer for layer in layers if layer['id'] == old['id'])
            self.assertEqual({k: v for k, v in current.items() if k != 'index'},
                             {k: v for k, v in old.items() if k != 'index'})
        self.assertIn(placed['layer'], {layer['id'] for layer in layers})
        with Image.open(self.render(target)) as frame:
            self.assertGreater(frame.getpixel((20, 20))[1], 180)

    def test_composition_settings_reopen_and_render_at_new_dimensions(self):
        from PIL import Image
        self.install_only('composition')
        target = self.root / 'resized.ecproj'
        self.execute('comp.settings', {'comp': self.comp, 'name': 'Resized', 'width': 160,
                                      'height': 90, 'frameRate': 24, 'duration': .5}, target)
        composition = self.info(target)['activeComp']
        self.assertEqual((composition['name'], composition['width'], composition['height'],
                          composition['frameRate'], composition['duration']), ('Resized', 160, 90, 24, .5))
        with Image.open(self.render(target)) as image:
            self.assertEqual(image.size, (160, 90))

    def test_layers_add_editable_solid_and_preserve_title_properties(self):
        from PIL import Image
        self.install_only('layers')
        target = self.root / 'layers.ecproj'
        original = self.props(self.project, self.title)
        result = self.execute('layer.newSolid', {'name': 'Green solid', 'color': '#20d030',
                                               'width': 40, 'height': 40}, target)
        layer = next(value for value in self.info(target)['activeComp']['layers'] if value['id'] == result['layer'])
        self.assertEqual((layer['name'], layer['type']), ('Green solid', 'Solid'))
        self.assertEqual(self.props(target, self.title), original)
        with Image.open(self.render(target)) as image:
            self.assertGreater(image.getpixel((160, 90))[1], 180)

    def test_animation_changes_property_keys_and_rendered_alpha(self):
        from PIL import Image
        self.install_only('animation')
        target = self.root / 'animation.ecproj'
        self.cli('run', 'prop.addKey', json.dumps({'layer': self.badge, 'path': 'transform/opacity', 'time': 0, 'value': 0}),
                 'prop.addKey', json.dumps({'layer': self.badge, 'path': 'transform/opacity', 'time': .5, 'value': 100}),
                 '--project', self.project, '--save-as', target)
        keys = self.prop(target, self.badge, 'transform/opacity')['keys']
        self.assertEqual([(key['time'], key['value']) for key in keys], [(0, 0), (.5, 100)])
        with Image.open(self.render(target, 'invisible.png', 0, transparent=True)) as image:
            self.assertEqual(image.getchannel('A').getextrema(), (0, 0))
        with Image.open(self.render(target, 'visible.png', .5, transparent=True)) as image:
            self.assertEqual(image.getchannel('A').getextrema(), (0, 255))

    def test_effects_modify_blur_and_preserve_other_layer(self):
        from PIL import Image, ImageChops
        self.install_only('effects')
        target = self.root / 'blur.ecproj'
        original = self.props(self.project, self.title)
        self.cli('set', self.comp, self.badge, 'effects/#1/blurriness', '12',
                 '--project', self.project, '--save-as', target)
        self.assertEqual(self.prop(target, self.badge, 'effects/#1/blurriness')['value'], 12)
        self.assertEqual(self.props(target, self.title), original)
        before_path, after_path = self.render(self.project, 'before.png'), self.render(target, 'after.png')
        with Image.open(before_path) as before, Image.open(after_path) as after:
            self.assertIsNotNone(ImageChops.difference(before.convert('RGB'), after.convert('RGB')).getbbox())

    def test_masks_clip_alpha_and_preserve_other_layer(self):
        from PIL import Image
        self.install_only('masks')
        target = self.root / 'masked.ecproj'
        original = self.props(self.project, self.title)
        result = self.execute('mask.new', {'layer': self.badge, 'vertices': [[0, -50], [50, -50], [50, 50], [0, 50]],
                                           'closed': True, 'mode': 'Add'}, target)
        self.assertIn('mask', result)
        self.assertEqual(self.props(target, self.title), original)
        with Image.open(self.base / 'frame-0000.png') as before, Image.open(self.render(target, transparent=True)) as after:
            alpha_before = sum(before.getchannel('A').getdata())
            alpha_after = sum(after.getchannel('A').getdata())
            self.assertGreater(alpha_after, .25 * alpha_before)
            self.assertLess(alpha_after, .75 * alpha_before)

    def test_expressions_evaluate_at_two_times_and_report_errors(self):
        self.install_only('expressions')
        target = self.root / 'expression.ecproj'
        self.execute('prop.setExpression', {'layer': self.badge, 'path': 'transform/opacity',
                                            'expression': '25 + time * 50', 'enabled': True}, target)
        self.assertEqual(self.prop(target, self.badge, 'transform/opacity', 0)['evaluated'], 25)
        self.assertEqual(self.prop(target, self.badge, 'transform/opacity', .5)['evaluated'], 50)
        report = json.loads(self.cli('exec', 'expr.errors', '--params', json.dumps({'comp': self.comp, 'time': .5}),
                                     '--project', target).stdout)
        self.assertEqual(report['count'], 0)
        self.assertEqual(report['errors'], [])

    def test_camera_creates_view_dollies_and_reopens_transform(self):
        self.install_only('camera')
        target = self.root / 'camera.ecproj'
        result = json.loads(self.cli('run', 'layer.newCamera',
                                    json.dumps({'name': 'Primary camera', 'position': [160, 90, -400], 'poi': [160, 90, 0]}),
                                    'view.set3DView', json.dumps({'view': 'activeCamera', 'comp': self.comp}),
                                    'camera.dolly', json.dumps({'amount': 50}),
                                    '--project', self.project, '--save-as', target).stdout)['result']
        camera = result[0]['result']['layer']
        self.assertEqual(self.prop(target, camera, 'transform/position')['value'], [160, 90, -350])
        layers = self.info(target)['activeComp']['layers']
        self.assertEqual(next(layer['type'] for layer in layers if layer['id'] == camera), 'Camera')
        # 默认二维视角不能直接从视图创建摄像机；失败不产生新工程。
        rejected = self.root / 'invalid-view.ecproj'
        self.cli('exec', 'camera.fromView', '--params', '{}', '--project', self.project,
                 '--save-as', rejected, success=False)
        self.assertFalse(rejected.exists())

    def test_masks_remain_editable_and_change_actual_alpha(self):
        from PIL import Image
        self.install_only('masks')
        sample=self.root/'sample';revision=self.root/'sample-revision'
        def workflow(plan,output,source=None):
            path=self.root/(output.name+'-plan.json');path.write_text(json.dumps(plan))
            command=[sys.executable,'-I','-B',str(self.skill/'scripts/workflow.py'),str(path),'--output',str(output),'--runtime-home',str(self.runtime)]
            if source:command+=['--source',str(source)]
            result=subprocess.run(command,env=self.environment,capture_output=True,text=True,timeout=240)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            return json.loads(result.stdout)
        delivered=workflow(json.loads((self.skill/'examples/layer-mask.json').read_text()),sample)
        original_sha=digest(sample/'project.ecproj')
        modified=workflow({'expectedProjectSha256':original_sha,'operations':[
            {'command':'mask.setVertex','params':{'layer':{'$ref':'product.layer'},'mask':{'$ref':'crop.mask'},'index':1,'point':[240,0]}},
            {'command':'mask.setVertex','params':{'layer':{'$ref':'product.layer'},'mask':{'$ref':'crop.mask'},'index':2,'point':[240,180]}}],
            'frames':[.5]},revision,sample)
        self.assertEqual(digest(sample/'project.ecproj'),original_sha)
        with Image.open(sample/'frame-0001.png') as image:self.assertEqual(image.getpixel((220,90))[3],0)
        with Image.open(revision/'frame-0000.png') as image:self.assertGreater(image.getpixel((220,90))[1],180)
        self.assertEqual(delivered['bindings'],modified['bindings'])
        original=self.props(self.project,self.title)
        solid=self.root/'solid.ecproj';masked=self.root/'masked.ecproj'
        layer=self.execute('layer.newSolid',{'name':'Masked product','color':'#20d030','width':320,'height':180},solid)['layer']
        mask=self.execute('mask.new',{'layer':layer,'vertices':[[0,0],[160,0],[160,180],[0,180]],'closed':True,'mode':'add'},masked,solid)['mask']
        self.assertEqual(self.props(masked,self.title),original)
        with Image.open(self.render(masked,'masked.png',.5,transparent=True)) as image:
            self.assertGreater(image.getpixel((80,90))[1],180)
            self.assertEqual(image.getpixel((240,90))[3],0)
        revised=self.root/'mask-revised.ecproj'
        self.cli('run','mask.setVertex',json.dumps({'layer':layer,'mask':mask,'index':1,'point':[240,0]}),
                 'mask.setVertex',json.dumps({'layer':layer,'mask':mask,'index':2,'point':[240,180]}),
                 '--project',masked,'--save-as',revised)
        self.assertEqual(self.props(revised,self.title),original)
        with Image.open(self.render(revised,'expanded.png',.5,transparent=True)) as image:
            self.assertGreater(image.getpixel((220,90))[1],180)
            self.assertEqual(image.getpixel((280,90))[3],0)
        unmasked=self.root/'unmasked.ecproj'
        self.execute('mask.remove',{'layer':layer,'mask':mask},unmasked,revised)
        with Image.open(self.render(unmasked,'unmasked.png',.5,transparent=True)) as image:
            self.assertGreater(image.getpixel((280,90))[1],180)
        self.assertEqual(self.props(unmasked,self.title),original)

    def test_export_transparent_frame_and_decoded_native_video(self):
        from PIL import Image
        self.install_only('export')
        frame, video = self.render(self.project, time=.5, transparent=True), self.root / 'intro.mp4'
        with Image.open(frame) as image:
            self.assertEqual(image.size, (320, 180))
            self.assertEqual(image.getchannel('A').getextrema(), (0, 255))
        self.cli('render', '--comp', self.info(self.project)['activeComp']['name'], '--out', video, '--format', 'h264',
                 '--channels', 'rgb', '--project', self.project)
        streams = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-count_frames',
                                                      '-show_streams', '-of', 'json', str(video)]))['streams']
        self.assertEqual(len(streams), 1)
        self.assertEqual((streams[0]['width'], streams[0]['height'], streams[0]['nb_read_frames']), (320, 180, '12'))


if __name__ == '__main__':
    unittest.main()
