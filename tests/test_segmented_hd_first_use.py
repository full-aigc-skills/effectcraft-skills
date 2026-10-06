"""1080p 五秒透明片头：独立技能公开冷使用、全部帧核验及 Film 实际消费。"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]


def hashes(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts}


@unittest.skipUnless(os.environ.get('CRAFT_EFFECT_SEGMENT_HD_FIRST_USE') == '1',
                     'requires explicit two-domain source, public native downloads, Pillow and ffmpeg')
class SegmentedHdFirstUse(unittest.TestCase):
    def test_public_cold_hd_export_and_film_collection(self):
        from PIL import Image, ImageChops
        from fractions import Fraction
        effect_source = ROOT/'skills/effectcraft-cli-export'
        film_source = Path(os.environ['CRAFT_FILM_SEQUENCE_SKILL_ROOT']).resolve()
        source_hashes = [hashes(effect_source), hashes(film_source)]
        with tempfile.TemporaryDirectory(prefix='craft-segment-hd-') as temporary:
            root = Path(temporary).resolve()
            effect = root/'.agents/skills/effectcraft-cli-export'
            film = root/'.agents/skills/filmcraft-cli-media'
            for source, target in [(effect_source, effect), (film_source, film)]:
                shutil.copytree(source, target, ignore=shutil.ignore_patterns('__pycache__'))
            copied_hashes = [hashes(effect), hashes(film)]
            runtime = root/'empty-runtime'
            self.assertFalse(runtime.exists())
            plan = json.loads((effect/'examples/brand-intro.json').read_text())
            plan['document'].update(width=1920, height=1080, frameRate=24, duration=5)
            plan['frames'] = [0, .5]
            plan['exports'] = [{'format':'png-segmented', 'chunkFrames':32}]
            plan_path = root/'effect-plan.json'; plan_path.write_text(json.dumps(plan))
            environment = dict(os.environ, PATH='/usr/bin:/bin:/usr/sbin:/sbin')
            environment.pop('CRAFT_NATIVE_ARCHIVE_DIRECTORY', None)
            started = time.monotonic()
            print('HD Effect public cold workflow started', flush=True)
            result = subprocess.run([sys.executable,'-I','-B',str(effect/'scripts/workflow.py'),str(plan_path),
                '--output',str(root/'effect'),'--runtime-home',str(runtime)],
                capture_output=True,text=True,timeout=600,env=environment)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            delivered = json.loads(result.stdout)
            checkpoint = root/'effect'/delivered['imageSequence']['path']
            descriptor = json.loads(checkpoint.read_text())
            self.assertEqual(descriptor['frameCount'],120)
            self.assertEqual([p['firstFrame'] for p in descriptor['segments']],[0,32,64,96])
            logical = 1920*1080*4*120
            self.assertGreater(logical,512*1024*1024)
            verified = 0
            for segment in descriptor['segments']:
                child_path = checkpoint.parent/segment['location']
                self.assertEqual(hashlib.sha256(child_path.read_bytes()).hexdigest(),segment['sha256'])
                child = json.loads(child_path.read_text())
                for frame in child['frames']:
                    path = child_path.parent/frame['location']
                    self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),frame['sha256'])
                    with Image.open(path) as image:
                        self.assertEqual(image.size,(1920,1080)); self.assertEqual(image.mode,'RGBA')
                        self.assertEqual(hashlib.sha256(image.tobytes()).hexdigest(),frame['rgbaSha256'])
                        self.assertEqual(list(image.getchannel('A').getextrema()),frame['alphaExtrema'])
                    verified += 1
            self.assertEqual(verified,120)
            effect_seconds = time.monotonic()-started
            background = root/'background.png'; Image.new('RGB',(1920,1080),(0,128,0)).save(background)
            ticks = 254016000000
            film_plan = {'document':{'name':'HD segmented intro','width':1920,'height':1080,'frameRate':{'num':24,'den':1}},
                'operations':[{'command':'asset.import','params':{'asset':'background'},'as':'background'},
                    {'command':'asset.import','params':{'asset':'overlay'},'as':'overlay'},
                    {'command':'timeline.place','params':{'item':{'$ref':'background.item'},'track':'V1','duration':str(5*ticks),'insert':False}},
                    {'command':'timeline.place','params':{'item':{'$ref':'overlay.item'},'track':'V2','duration':str(5*ticks),'insert':False}}],
                'frames':['0',str(ticks//2)],'export':{'audioRequired':False}}
            film_path=root/'film-plan.json';film_path.write_text(json.dumps(film_plan))
            print('HD Effect passed; Film public cold workflow started',flush=True)
            result=subprocess.run([sys.executable,'-I','-B',str(film/'scripts/workflow.py'),str(film_path),
                '--output',str(root/'film'),'--runtime-home',str(runtime),'--asset','background='+str(background),
                '--segmented-sequence-asset','overlay='+str(checkpoint)],capture_output=True,text=True,timeout=600,env=environment)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            collected=json.loads(result.stdout)
            self.assertEqual(collected['assets']['overlay']['sourceSequenceSha256'],hashlib.sha256(checkpoint.read_bytes()).hexdigest())
            self.assertEqual(collected['assets']['overlay']['sequenceMetadata']['frameCount'],120)
            probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-select_streams','v:0',
                '-show_entries','stream=width,height,avg_frame_rate,nb_read_frames,duration','-of','json',str(root/'film/film.mp4')],text=True))['streams']
            self.assertEqual(len(probe),1)
            video=probe[0]
            self.assertEqual((video['width'],video['height'],int(video['nb_read_frames'])),(1920,1080,120))
            self.assertEqual(Fraction(video['avg_frame_rate']),24)
            self.assertLessEqual(abs(float(video['duration'])-5),1/24)
            decoded=root/'decoded.rgb'
            subprocess.run(['ffmpeg','-v','error','-i',str(root/'film/film.mp4'),'-f','rawvideo','-pix_fmt','rgb24',str(decoded)],check=True,timeout=180)
            self.assertEqual(decoded.stat().st_size,120*1920*1080*3)
            checks=0
            with decoded.open('rb') as stream:
                for index in (0,60,119):
                    overlay=checkpoint.parent/f'segment_{index//32:05d}'/f'frame_{index%32:05d}.png'
                    with Image.open(overlay) as image:
                        expected=Image.alpha_composite(Image.new('RGBA',(1920,1080),(0,128,0,255)),image).convert('RGB')
                        for x,y in ((10,10),(60,85)):
                            stream.seek((index*1920*1080+y*1920+x)*3)
                            self.assertLessEqual(max(abs(a-b) for a,b in zip(stream.read(3),expected.getpixel((x,y)))),20)
                            checks+=1
            self.assertEqual(checks,6)
            # 独立寻找 Alpha 从 0 到 255 的标题内点，静态首帧不能冒充动画成片。
            with Image.open(checkpoint.parent/'segment_00000/frame_00000.png') as first, Image.open(checkpoint.parent/'segment_00001/frame_00028.png') as middle:
                a=first.getchannel('A');b=middle.getchannel('A');box=ImageChops.subtract(b,a).getbbox()
                self.assertIsNotNone(box)
                x,y=next((x,y) for y in range(box[1],box[3]) for x in range(box[0],box[2]) if a.getpixel((x,y))==0 and b.getpixel((x,y))==255)
                with decoded.open('rb') as stream:
                    actual=[]
                    for index,image in [(0,first),(60,middle)]:
                        expected=Image.alpha_composite(Image.new('RGBA',(1920,1080),(0,128,0,255)),image).convert('RGB').getpixel((x,y))
                        stream.seek((index*1920*1080+y*1920+x)*3);pixel=tuple(stream.read(3));actual.append(pixel)
                        self.assertLessEqual(max(abs(a-b) for a,b in zip(pixel,expected)),20)
                self.assertGreater(max(abs(a-b) for a,b in zip(*actual)),40)
                checks+=2
            self.assertEqual([hashes(effect),hashes(film)],copied_hashes)
            self.assertEqual([hashes(effect_source),hashes(film_source)],source_hashes)
            proof={'schema':'effect-film-segment-hd-candidate/v1','result':'PASS','width':1920,'height':1080,'fps':24,'seconds':5,
                'segments':4,'framesIndependentlyVerified':verified,'decodedVideoFrames':120,'compositePixelChecks':checks,'animatedTitlePixelVerified':True,
                'logicalRgbaBytes':logical,'effectDurationSeconds':round(effect_seconds,3),'totalDurationSeconds':round(time.monotonic()-started,3),
                'runtimeSha256':{'effect':delivered['runtimeSha256'],'film':collected['runtimeSha256']},'independentVideoProbe':video,
                'nativeProjectSha256':{'effect':delivered['files']['project.ecproj'],'film':collected['files']['project.fcproj']},'videoSha256':collected['files']['film.mp4'],
                'driverSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'skillHashes':{'effect':copied_hashes[0],'film':copied_hashes[1]},
                'skillsPreserved':True,'scope':'two copied-alone current source skills; public workflow; empty shared runtime; default downloads',
                'excluded':['immutable new releases','installed Art HD workflow','HD text revision and recovery','model/GUI/creative acceptance','full V1']}
            if os.environ.get('CRAFT_EFFECT_SEGMENT_HD_EVIDENCE'):
                Path(os.environ['CRAFT_EFFECT_SEGMENT_HD_EVIDENCE']).write_text(json.dumps(proof,indent=2)+'\n')


if __name__=='__main__':
    unittest.main()
