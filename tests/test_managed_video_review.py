"""真实FFmpeg媒体正反例；清单摘要匹配也不能掩盖缺帧或alpha丢失。"""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SCRIPT=Path(__file__).resolve().parents[1]/'skills/effectcraft-use/scripts/quality_review.py'

@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'actual ffmpeg/ffprobe required')
class VideoReviewTests(unittest.TestCase):
    def setUp(self):
        spec=importlib.util.spec_from_file_location('video_review_test',SCRIPT)
        self.review=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.review)
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        (self.root/'project.ecproj').write_bytes(b'fixture native identity; engineering NOT_RUN')
        self.comp={'width':32,'height':24,'frameRate':4,'duration':1}
        self.video={'path':'intro.mp4','alpha':False}
        self.encode()

    def encode(self,count=4,rate=4,width=32,offset=None):
        args=[shutil.which('ffmpeg'),'-hide_banner','-loglevel','error','-y','-f','lavfi','-i',f'color=c=red:s={width}x24:r={rate}','-frames:v',str(count)]
        if offset is not None:args+=['-vf',f'setpts=PTS+{offset}/TB','-fps_mode','passthrough']
        args+=['-c:v','libx264','-pix_fmt','yuv420p',str(self.root/'intro.mp4')]
        subprocess.run(args,check=True,capture_output=True,timeout=30);self.refresh()

    def refresh(self):
        (self.root/'native.json').write_text(json.dumps({'composition':self.comp}),encoding='utf-8')
        manifest={'schema':'effectcraft-delivery/v1','frames':[],'video':self.video,
            'files':{p.name:self.review.sha(p) for p in self.root.iterdir() if p.is_file() and p.name!='manifest.json'}}
        (self.root/'manifest.json').write_text(json.dumps(manifest),encoding='utf-8')

    def reject(self,reason=None):
        report=self.review.inspect_delivery(self.root)
        self.assertEqual(report['technical']['status'],'FAIL',report)
        self.assertEqual(report['engineering']['status'],'NOT_RUN');self.assertEqual(report['creative']['status'],'NOT_RUN')
        self.assertFalse(report['accepted'])
        if reason:self.assertIn(reason,report['technical']['reason'])
        return report

    def test_decoded_valid_video_reports_exact_frame_count(self):
        report=self.review.inspect_delivery(self.root)
        self.assertEqual(report['technical']['status'],'PASS',report)
        self.assertEqual(report['technical']['media'][0].get('verifiedFrames'),4)
        self.assertEqual(report['engineering']['status'],'NOT_RUN')

    def test_one_missing_frame_inside_old_duration_tolerance_fails(self):
        self.encode(count=3);self.reject('video_frame_count_mismatch')

    def test_alpha_declaration_cannot_promote_opaque_h264(self):
        self.video['alpha']=True;self.refresh();self.reject('video_alpha_missing')

    def test_nonzero_first_timestamp_does_not_cover_zero_based_scope(self):
        self.encode(offset=.25);self.reject('video_timeline_mismatch')

    def test_actual_argb_video_passes_alpha_gate(self):
        self.video={'path':'alpha.mov','alpha':True}
        subprocess.run([shutil.which('ffmpeg'),'-hide_banner','-loglevel','error','-y',
            '-f','lavfi','-i','color=c=red@0.5:s=32x24:r=4,format=rgba','-frames:v','4',
            '-c:v','qtrle','-pix_fmt','argb',str(self.root/'alpha.mov')],check=True,capture_output=True,timeout=30)
        self.refresh();report=self.review.inspect_delivery(self.root)
        self.assertEqual(report['technical']['status'],'PASS',report)
        self.assertTrue(report['technical']['media'][0]['alphaVerified'])

    def test_malformed_video_with_fresh_package_hash_fails(self):
        (self.root/'intro.mp4').write_bytes(b'not a video');self.refresh();self.reject()

    def test_wrong_dimensions_fails_after_actual_decode(self):
        self.encode(width=40);self.reject('video_contract_mismatch')

    def test_wrong_rate_fails_after_actual_decode(self):
        self.encode(rate=5);self.reject('video_contract_mismatch')

    def test_wrong_duration_fails_after_actual_decode(self):
        self.comp['duration']=2;self.refresh();self.reject()
