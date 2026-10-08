"""命令/桌面交付不能靠最后工程或命令成功冒充当前质量验收。"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zlib
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'skills/effectcraft-use/scripts/command_delivery.py'


def png(width=2,height=2,alpha=True):
    def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data))
    channels=4 if alpha else 3
    row=b'\0'+bytes([255,0,0,128][:channels])*width
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,6 if alpha else 2,0,0,0))+chunk(b'IDAT',zlib.compress(row*height))+chunk(b'IEND',b'')


class Session:
    def __init__(self):
        self.comps={1:{'id':1,'name':'A','width':2,'height':2,'frameRate':2,'duration':1,'layers':[{'id':3}]}}
        self.layers={'3':{'id':3,'properties':[{'path':'text/sourceText','value':'before'}]}}
        self.calls=[];self.footage={};self.version_bump=0
    def request(self,method,params):
        name=params['name'];args=params['arguments'];self.calls.append((name,args))
        if name=='get_project':value={'activeComp':1,'path':'','items':[{'id':n,'type':'Composition'} for n in self.comps]+[{'id':n,'type':'Image'} for n in self.footage]}
        elif name=='run_script':value={'ok':True,'result':{'revision':int(hashlib.sha256(json.dumps({'comps':self.comps,'layers':self.layers},sort_keys=True).encode()).hexdigest()[:10],16)+self.version_bump,'footage':[{'id':n,'path':str(path)} for n,path in self.footage.items()]},'error':None}
        elif name=='get_comp':
            key=args.get('comp',1);value=next(c for c in self.comps.values() if c['id']==key or c['name']==key)
        elif name=='get_layer':value=self.layers[str(args['layer'])]
        elif name=='open_project':value={'opened':args['path']}
        elif name=='execute_command' and args['command']=='footage.check':value={'checked':0,'missing':0}
        else:raise AssertionError((name,args))
        return {'content':[{'type':'text','text':json.dumps(copy.deepcopy(value))}]}
    def __enter__(self):return self
    def __exit__(self,*args):pass


class CommandDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SCRIPT.exists(),'command/desktop quality observation is missing')
        spec=importlib.util.spec_from_file_location('command_delivery_test',SCRIPT);self.module=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.module)
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.output=self.root/'output';self.output.mkdir()
        self.tasks=self.module.load('task_store');self.store=self.tasks.Store(self.root/'state')
        self.store.create('case',plan={'schema':'craft-command-plan/v1','operations':[{'tool':'save_project','params':{}}]},output=str(self.output),runtime_sha='a'*64,inputs={},source=None,mode='commands',authorization={})
        self.store.start('case')
        self.store.reserve_resources('case',{'frames':0,'decodedBytes':0},self.store.read('case')['identity']['planHash'])
        self.module.load('resource_meter').watch(self.store,'case',self.output,self.output,'commands')
        self.observer=self.module.Observer(self.store,'case');self.session=Session();self.steps=[]

    def save(self,name='scene.ecproj'):
        record={'index':len(self.steps),'tool':'save_project','command':None,'params':{'path':str(self.output/name)},'state':'started'}
        self.observer(self.session,record,'before')
        (self.output/name).parent.mkdir(parents=True,exist_ok=True)
        (self.output/name).write_text(json.dumps({'schema':1,'settings':{},'items':{str(n):{'id':n,'kind':{'type':'Footage','path':str(path)}} for n,path in self.session.footage.items()}}),encoding='utf-8')
        record.update(state='succeeded',result={'path':str(self.output/name)})
        self.observer(self.session,record,'after');self.steps.append(record);return record

    def frame(self,name='preview.png',alpha=True):
        record={'index':len(self.steps),'tool':'render_frame','command':None,'params':{'path':str(self.output/name),'inline':False,'transparent':True,'time':.5,'max_side':0},'state':'started'}
        self.observer(self.session,record,'before');(self.output/name).write_bytes(png(alpha=alpha))
        record.update(state='succeeded',result={'path':str(self.output/name)})
        self.observer(self.session,record,'after');self.steps.append(record)

    def finish(self,mode='headless'):
        receipt={'schema':'craft-command-receipt/v1','pluginId':'effectcraft','mode':mode,'result':'PASS','runtimeSha256':'a'*64,'steps':self.steps,'planSha256':hashlib.sha256(json.dumps(self.store.read('case')['plan'],ensure_ascii=False,sort_keys=True,allow_nan=False).encode()).hexdigest()}
        self.tasks.atomic_json(self.output/'success.json',receipt)
        proof=self.module.finalize(self.store,'case');self.store.delivered('case',proof);return proof

    def test_no_user_manifest_is_written_and_public_receipt_unchanged(self):
        self.save('nested/a.ecproj');self.frame();before=(self.output/'nested/a.ecproj').read_bytes();self.finish()
        self.assertFalse((self.output/'manifest.json').exists());self.assertFalse((self.output/'native.json').exists())
        self.assertEqual((self.output/'nested/a.ecproj').read_bytes(),before)
        self.assertEqual(json.loads((self.output/'success.json').read_text())['schema'],'craft-command-receipt/v1')
        self.assertEqual(self.module.inspect(self.store,'case',None)['technical']['status'],'PASS')

    def test_frame_before_edit_keeps_its_own_context(self):
        self.save('early.ecproj');self.frame();self.session.comps[1]['width']=7;self.save('late.ecproj');self.finish()
        report=self.module.inspect(self.store,'case',None)
        self.assertEqual(report['technical']['status'],'PASS',report)
        self.assertEqual(report['technical']['media'][0]['composition']['width'],2)
        self.assertEqual(report['engineering']['status'],'NOT_RUN')
        self.assertEqual(report['technical']['media'][0]['sourceProjects'],['early.ecproj'])

    def test_unsaved_render_version_is_not_assigned_to_later_project(self):
        self.frame();self.session.comps[1]['name']='later';self.save();self.finish()
        report=self.module.inspect(self.store,'case',None)
        self.assertEqual(report['technical']['status'],'NOT_RUN')
        self.assertEqual(report['technical']['unmatchedFrames'],['preview.png'])
        self.assertEqual(report['technical']['media'][0]['sourceProjects'],[])

    def test_multiple_projects_and_compositions_are_not_collapsed(self):
        self.save('one.ecproj');self.session.comps[2]=dict(self.session.comps[1],id=2,name='B',layers=[])
        self.save('two.ecproj');self.frame();self.finish()
        document=self.module.document(self.store,'case')
        self.assertEqual(len(document['projects']),2)
        self.assertEqual(len(document['projects'][0]['snapshot']['compositions']),1)
        self.assertEqual(len(document['projects'][1]['snapshot']['compositions']),2)

    def test_current_frame_change_cannot_use_old_success(self):
        self.save();self.frame();self.finish();(self.output/'preview.png').write_bytes(png(1,1))
        report=self.module.inspect(self.store,'case',None)
        self.assertEqual(report['technical']['status'],'FAIL');self.assertEqual(report['creative']['status'],'NOT_RUN')
        self.assertFalse(report['accepted'])

    def test_matching_new_hash_does_not_hide_wrong_alpha(self):
        self.save();self.frame(alpha=False);self.finish()
        self.assertEqual(self.module.inspect(self.store,'case',None)['technical']['status'],'FAIL')

    def test_unknown_media_is_not_silently_accepted(self):
        self.save();self.frame();(self.output/'unobserved.mp4').write_bytes(b'unknown');self.finish()
        report=self.module.inspect(self.store,'case',None)
        self.assertEqual(report['technical']['status'],'NOT_RUN');self.assertIn('unobserved.mp4',report['technical']['unreviewed'])

    def test_corrupt_observation_cannot_be_regenerated(self):
        self.save();self.frame();self.finish()
        p=self.store.path('case').parent/'command-delivery/delivery.json';p.write_text('{}')
        self.assertEqual(self.module.inspect(self.store,'case',None)['technical']['status'],'FAIL')
        self.assertEqual(p.read_text(),'{}')

    def test_missing_observation_does_not_create_new_baseline(self):
        self.save();self.frame();self.finish()
        p=self.store.path('case').parent/'command-delivery/delivery.json';p.unlink()
        self.assertEqual(self.module.inspect(self.store,'case',None)['technical']['status'],'FAIL');self.assertFalse(p.exists())

    def test_resolved_output_escape_is_rejected_before_observation(self):
        record={'index':0,'tool':'save_project','params':{'path':str(self.root/'escape.ecproj')},'state':'started'}
        with self.assertRaisesRegex(ValueError,'command_artifact_outside_output'):self.observer(self.session,record,'before')
        self.assertFalse((self.root/'escape.ecproj').exists())

    def test_native_project_reopen_compares_all_saved_compositions(self):
        self.save();self.frame();self.finish();doc=self.module.document(self.store,'case')
        before=(self.output/'scene.ecproj').read_bytes()
        result=self.module.verify_projects(self.output,doc['projects'],'native',session_factory=lambda argv,**kw:self.session)
        self.assertEqual(result['status'],'PASS',result);self.assertEqual((self.output/'scene.ecproj').read_bytes(),before)
        self.session.comps[1]['name']='changed'
        self.assertEqual(self.module.verify_projects(self.output,doc['projects'],'native',session_factory=lambda argv,**kw:self.session)['status'],'FAIL')
        self.assertEqual([name for name,_ in self.session.calls if name in ('save_project','set_property')],[])

    def test_legacy_task_is_diagnostic_only_without_install(self):
        report=self.module.inspect(self.store,'case',None)
        self.assertEqual(report['engineering']['status'],'NOT_RUN');self.assertEqual(report['creative']['status'],'NOT_RUN')
        self.assertFalse((self.store.path('case').parent/'command-delivery').exists())

    def test_repeated_explicit_save_keeps_current_version_and_prior_observation(self):
        self.save();self.session.comps[1]['name']='later';self.save();self.frame();self.finish()
        data=self.module.document(self.store,'case')
        self.assertEqual(len(data['projects']),1)
        self.assertEqual(data['projects'][0]['snapshot']['compositions']['1']['composition']['name'],'later')
        self.assertEqual(len(data['observations']),3)
        self.assertTrue((self.store.path('case').parent/'command-delivery/observations/0.json').exists())

    def test_wrong_dimension_is_not_accepted_with_matching_hashes(self):
        self.save();self.session.comps[1]['width']=3;self.frame();self.finish()
        report=self.module.inspect(self.store,'case',None)
        self.assertEqual(report['technical']['status'],'FAIL');self.assertIn('preview_dimensions_mismatch',report['technical']['reason'])

    def test_corrupt_png_is_decoded_even_with_matching_hashes(self):
        self.save();record={'index':len(self.steps),'tool':'render_frame','command':None,'params':{'path':str(self.output/'bad.png'),'max_side':0},'state':'started'}
        self.observer(self.session,record,'before');(self.output/'bad.png').write_bytes(b'not PNG');record.update(state='succeeded',result={});self.observer(self.session,record,'after');self.steps.append(record);self.finish()
        self.assertEqual(self.module.inspect(self.store,'case',None)['technical']['status'],'FAIL')

    def test_receipt_change_refuses_current_acceptance(self):
        self.save();self.frame();self.finish();p=self.output/'success.json';d=json.loads(p.read_text());d['mode']='bridge';p.write_text(json.dumps(d))
        report=self.module.inspect(self.store,'case',None)
        self.assertEqual(report['technical']['status'],'FAIL');self.assertIn('command_receipt_changed',report['technical']['reason'])

    def test_wrong_plan_receipt_is_not_blessed_by_finalization(self):
        self.save();self.frame();self.finish();p=self.output/'success.json';d=json.loads(p.read_text());d['planSha256']='f'*64;p.write_text(json.dumps(d))
        with self.assertRaisesRegex(ValueError,'command_receipt_mismatch'):self.module.finalize(self.store,'case')

    def test_native_engine_writing_its_snapshot_fails_and_preserves_original(self):
        self.save();self.frame();self.finish();document=self.module.document(self.store,'case');before=(self.output/'scene.ecproj').read_bytes();request=self.session.request
        def changed(method,params):
            if params['name']=='open_project':Path(params['arguments']['path']).write_text('native saved unexpectedly')
            return request(method,params)
        self.session.request=changed
        result=self.module.verify_projects(self.output,document['projects'],'native',session_factory=lambda *args,**kw:self.session)
        self.assertEqual(result['status'],'FAIL');self.assertIn('command_snapshot_changed',result['reason'])
        self.assertEqual((self.output/'scene.ecproj').read_bytes(),before)

    def test_native_timeout_is_not_run(self):
        self.save();self.frame();self.finish();data=self.module.document(self.store,'case')
        result=self.module.verify_projects(self.output,data['projects'],'native',timeout=-1,session_factory=lambda *args,**kw:self.fail('started expired native session'))
        self.assertEqual(result['status'],'NOT_RUN');self.assertFalse(result['fresh'])

    def test_public_managed_review_routes_command_and_desktop_without_replaying(self):
        self.save();self.frame();self.finish()
        managed=self.module.load('managed');original=managed.load
        with patch.object(managed,'load',side_effect=lambda name:self.module if name=='command_delivery' else original(name)):
            result=managed.review(self.store,'case',{'goal':'red'},runtime_home=None)
        self.assertEqual(result['report']['technical']['status'],'PASS');self.assertEqual(result['requiredAction'],'engineering_verification')
        self.assertIsNone(result['judgeRequest']);self.assertEqual(result['report']['creative']['status'],'NOT_RUN')
        with self.store.lock():
            state=self.store.read('case');state['identity']['mode']='desktop'
            # 修改identity应由Store拒绝，不能把旧命令身份迁移成桌面任务。
            self.store.save(state)
            with self.assertRaisesRegex(ValueError,'identity'):self.store.read('case')


    def test_render_before_save_binds_actual_footage_bytes_not_just_native_structure(self):
        asset=self.output/'logo.png';asset.write_bytes(png());self.session.footage[4]=asset
        self.frame();asset.write_bytes(png()+b'changed source bytes');self.save();self.finish()
        report=self.module.inspect(self.store,'case',None)
        self.assertEqual(report['technical']['status'],'NOT_RUN',report)
        self.assertEqual(report['technical']['unmatchedFrames'],['preview.png'])

    def test_same_footage_render_before_first_save_can_match_its_later_saved_version(self):
        asset=self.output/'logo.png';asset.write_bytes(png());self.session.footage[4]=asset
        self.frame();self.save();self.finish()
        report=self.module.inspect(self.store,'case',None)
        self.assertEqual(report['technical']['status'],'PASS',report)
        frame=self.module.document(self.store,'case')['frames'][0]
        self.assertEqual(frame['dependencies']['4']['sha256'],hashlib.sha256(png()).hexdigest())

    def test_dependency_changed_during_render_is_retained_as_unknown_not_rebased(self):
        asset=self.output/'logo.png';asset.write_bytes(png());self.session.footage[4]=asset
        record={'index':0,'tool':'render_frame','command':None,'params':{'path':str(self.output/'preview.png'),'inline':False,'max_side':0},'state':'started'}
        self.observer(self.session,record,'before');asset.write_bytes(b'changed during render');(self.output/'preview.png').write_bytes(png());record.update(state='succeeded',result={})
        with self.assertRaisesRegex(ValueError,'command_render_dependency_changed'):self.observer(self.session,record,'after')
        self.assertTrue((self.store.path('case').parent/'command-delivery/observations/0.before.json').exists())
        self.assertFalse((self.store.path('case').parent/'command-delivery/observations/0.json').exists())


    def test_native_revision_change_with_identical_compositions_is_not_same_render_source(self):
        self.frame();self.session.version_bump+=1;self.save();self.finish()
        report=self.module.inspect(self.store,'case',None)
        self.assertEqual(report['technical']['status'],'NOT_RUN')
        self.assertEqual(report['technical']['unmatchedFrames'],['preview.png'])

    def test_malformed_native_context_is_not_guessed_or_written(self):
        original=self.session.request
        def invalid(method,params):
            if params['name']=='run_script':return {'content':[{'type':'text','text':'null'}]}
            return original(method,params)
        self.session.request=invalid
        with self.assertRaisesRegex(ValueError,'command_native_context_unavailable'):self.save()
        self.assertFalse((self.output/'scene.ecproj').exists())


class ObserverConnectionTests(unittest.TestCase):
    def test_command_entry_observer_runs_before_and_after_actual_reply_and_stops_on_loss(self):
        spec=importlib.util.spec_from_file_location('command_callback_test',SCRIPT.with_name('commands.py'));commands=importlib.util.module_from_spec(spec);spec.loader.exec_module(commands)
        events=[]
        class Native(Session):
            def request(self,method,params):
                if method=='tools/list':return {'tools':[{'name':'list_commands'},{'name':'get_project'}]}
                if params['name']=='list_commands':return {'content':[{'type':'text','text':json.dumps([dict(row,enabled=True) for row in commands.catalog()['commands']])}]}
                events.append('native');return super().request(method,params)
        plan={'schema':'craft-command-plan/v1','operations':[{'tool':'get_project','params':{}},{'tool':'get_project','params':{}}]}
        def observer(session,record,phase):
            events.append(phase)
            if phase=='after':raise ValueError('observation lost; preserve successful edit')
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'output'
            receipt=commands.execute(plan,output,installer=lambda *args:{'executable':'native','binarySha256':'a'*64},session_factory=lambda *args:Native(),observer=observer)
            self.assertEqual(receipt['result'],'FAIL');self.assertEqual(events,['before','native','after'])
            self.assertEqual([step['state'] for step in receipt['steps']],['succeeded'])
            self.assertFalse((output/'success.json').exists());self.assertTrue((output/'failure.json').exists())

    def test_owned_desktop_passes_same_optional_observer_without_changing_raw_plan(self):
        spec=importlib.util.spec_from_file_location('desktop_callback_test',SCRIPT.with_name('desktop_session.py'));desktop=importlib.util.module_from_spec(spec);spec.loader.exec_module(desktop)
        commands=desktop.load('commands');original=desktop.load;observed=[]
        def execute(plan,output,*args,**kwargs):
            observed.append(kwargs['observer']);output.mkdir();return {'schema':'craft-command-receipt/v1','result':'PASS'}
        from types import SimpleNamespace
        marker=lambda *args:None
        plan={'schema':'craft-command-plan/v1','operations':[{'tool':'get_project','params':{}}]}
        with tempfile.TemporaryDirectory() as directory,patch.object(desktop,'load',side_effect=lambda name:commands if name=='commands' else original(name)),patch.object(commands,'execute',side_effect=execute):
            result=desktop.run(plan,Path(directory)/'out',task_hooks=SimpleNamespace(command_observation=marker))
        self.assertEqual(result['schema'],'craft-command-receipt/v1');self.assertEqual(observed,[marker])

    def test_task_receipt_can_validate_inline_image_without_writing_duplicate_media(self):
        import base64
        spec=importlib.util.spec_from_file_location('inline_receipt_test',SCRIPT.with_name('commands.py'));commands=importlib.util.module_from_spec(spec);spec.loader.exec_module(commands)
        reply={'content':[{'type':'text','text':'{"width":2,"height":2}'},{'type':'image','mimeType':'image/png','data':base64.b64encode(png()).decode()}]}
        result=commands.parse_reply(reply,receipt_only=True)
        self.assertEqual(result['content'][1]['sha256'],hashlib.sha256(png()).hexdigest())
        self.assertNotIn('path',result['content'][1]);self.assertNotIn('data',result['content'][1])
        reply['content'][1]['data']='bad base64'
        with self.assertRaisesRegex(RuntimeError,'invalid_image_reply'):commands.parse_reply(reply,receipt_only=True)
