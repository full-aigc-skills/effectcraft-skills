"""公共血缘贯通工作流完成、技术审阅及移动源包修订前校验。"""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
import test_managed_review as fixtures

BASE=Path(__file__).resolve().parents[1]/'skills/effectcraft-use/scripts'
def load(name):
    spec=importlib.util.spec_from_file_location('lineage_test_'+name,BASE/(name+'.py'))
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value

class WorkflowArtifactLineageTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.ManagedReviewTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.root=self.fixture.root;self.workflow=load('workflow');self.review=load('quality_review')
        (self.root/'project.ecproj').write_text(json.dumps({'schema':1,'items':{}}))
        self.fixture.manifest['files']['project.ecproj']=self.review.sha(self.root/'project.ecproj')
        (self.root/'manifest.json').write_text(json.dumps(self.fixture.manifest))
        self.context={'plan':{'document':{'name':'fixture'},'operations':[]},'output':str(self.root),'stage':str(self.root),
            'project':str(self.root/'project.ecproj'),'working':str(self.root),'sourceProject':None,'sourceHash':None,
            'comp':{'width':1,'height':1,'frameRate':4,'duration':1},'layers':{},
            'frames':[{'path':'frame.png','seconds':0,'requestedAlpha':True}],'bindings':{},'assets':{},'receipts':[],
            'cli':'unused','runtimeSha256':'a'*64,'executionIdentity':{'planHash':'b'*64,'inputHashes':{}},
            'artifactProducer':{'producerTaskId':'managed-original','taskIdentityHash':'c'*64,'mode':'managed'}}
    def finish(self,context=None):return self.workflow._finish_export(context or self.context)
    def save(self,manifest):(self.root/'manifest.json').write_text(json.dumps(manifest))

    def test_workflow_registers_public_artifact_bound_to_task_and_native(self):
        m=self.finish();self.assertIn('artifact',m,'public workflow artifact lineage missing')
        a=m['artifact'];self.assertEqual(a['protocolVersion'],'craft-artifact/v1')
        self.assertEqual(a['producerTaskId'],'managed-original');self.assertEqual(a['sha256'],self.review.sha(self.root/'project.ecproj'))
        self.assertEqual(a['bytes'],(self.root/'project.ecproj').stat().st_size)
        self.assertEqual(a['nativeProjectRef']['location'],'project.ecproj');self.assertEqual(a['location'],'project.ecproj')
        self.assertEqual(a['mediaType'],'application/vnd.effectcraft.project+json')
        self.assertEqual(a['sourceRefs'],[]);self.assertTrue(a['renditions']);self.assertTrue(a['evidenceRefs'])
        self.assertEqual(a['lossReportRef']['location'],'exchange-loss.json')
        self.assertEqual(self.review.inspect_delivery(self.root)['technical']['status'],'PASS')

    def test_fresh_file_table_cannot_reuse_old_immutable_version(self):
        m=self.finish();self.assertIn('artifact',m,'immutable package version missing')
        (self.root/'project.ecproj').write_text(json.dumps({'schema':1,'items':{},'changed':True}))
        m['files']['project.ecproj']=self.review.sha(self.root/'project.ecproj');self.save(m)
        report=self.review.inspect_delivery(self.root);self.assertEqual(report['technical']['status'],'FAIL',report)
        self.assertIn('artifact_lineage',report['technical']['reason'])

    def test_parent_reference_and_logical_identity_survive_package_move(self):
        old=self.finish();self.assertIn('artifact',old,'source version lineage missing')
        moved=self.root.parent/(self.root.name+' moved');shutil.copytree(self.root,moved);self.addCleanup(shutil.rmtree,moved)
        self.assertEqual(self.review.binding(moved)['projectSha256'],old['artifact']['sha256'])
        context=copy.deepcopy(self.context);context['sourceProject']=str(moved/'project.ecproj');context['sourceHash']=old['artifact']['sha256']
        context['sourceArtifact']={k:old['artifact'][k] for k in ('assetId','version','sha256')}
        context['artifactProducer']={'producerTaskId':'managed-revision','taskIdentityHash':'d'*64,'mode':'managed'}
        new=self.finish(context)
        self.assertEqual(new['artifact']['assetId'],old['artifact']['assetId'])
        self.assertNotEqual(new['artifact']['version'],old['artifact']['version'])
        self.assertEqual(new['artifact']['sourceRefs'],[context['sourceArtifact']])
        self.assertEqual(self.review.inspect_delivery(moved)['technical']['status'],'PASS')

    def test_opaque_native_bytes_cannot_be_registered_as_native_json(self):
        (self.root/'project.ecproj').write_bytes(b'fake native project')
        with self.assertRaisesRegex(ValueError,'artifact_lineage'):self.finish()

    def test_native_parent_and_rendition_reference_substitution_rejected(self):
        for target in ('nativeProjectRef','renditions','producerTaskId','sourceRefs'):
            with self.subTest(target=target):
                m=self.finish();self.assertIn('artifact',m,'reference binding missing')
                if target=='nativeProjectRef':m['artifact'][target]['location']='frame.png'
                elif target=='renditions':m['artifact'][target][0]['sha256']='0'*64
                elif target=='producerTaskId':m['artifact'][target]='other-task'
                else:m['artifact'][target]=[{'assetId':'forged','version':'1','sha256':'e'*64}]
                self.save(m);self.assertEqual(self.review.inspect_delivery(self.root)['technical']['status'],'FAIL')

    def test_source_preflight_rechecks_package_before_runtime_install(self):
        m=self.finish();self.assertIn('artifact',m,'source integrity gate missing')
        (self.root/'frame.png').write_bytes(b'replaced same path')
        plan={'operations':[],'expectedProjectSha256':m['files']['project.ecproj']}
        managed=load('managed')
        with patch.object(self.workflow,'load_module',side_effect=lambda name:load(name) if name=='artifact_lineage' else (_ for _ in ()).throw(AssertionError('installer must not run'))):
            with self.assertRaisesRegex(ValueError,'artifact_lineage'):self.workflow._execute(plan,self.root/'new','unused',self.root,None)
        with self.assertRaisesRegex(ValueError,'artifact_lineage'):managed.preflight(plan,self.root/'new','workflow',source=self.root)
        self.assertFalse((self.root/'new').exists())

    def test_legacy_package_stays_readable_and_standalone_never_claims_managed_task(self):
        self.assertEqual(self.review.inspect_delivery(self.root)['technical']['status'],'PASS')
        context=copy.deepcopy(self.context);context.pop('artifactProducer')
        m=self.finish(context);self.assertIn('artifactBinding',m,'explicit producer scope missing')
        self.assertEqual(m['artifactBinding']['producer']['mode'],'standalone')
        self.assertTrue(m['artifact']['producerTaskId'].startswith('standalone:'))

    def test_manifest_bound_dependency_cannot_hide_unlisted_or_escaping_payload(self):
        for corruption in ('unlisted','symlink','added'):
            with self.subTest(corruption=corruption):
                extra=self.root/'extra.bin'
                m=self.finish();self.assertIn('artifact',m,'package completeness binding missing')
                if corruption=='unlisted':del m['files']['operations.json'];self.save(m)
                elif corruption=='symlink':
                    (self.root/'operations.json').rename(extra);(self.root/'operations.json').symlink_to(extra)
                else:extra.write_bytes(b'not in package')
                self.assertEqual(self.review.inspect_delivery(self.root)['technical']['status'],'FAIL')
                if corruption=='symlink':(self.root/'operations.json').unlink();extra.rename(self.root/'operations.json')
                elif extra.exists():extra.unlink()

    def test_long_parent_logical_id_keeps_all_public_reference_ids_within_contract(self):
        context=copy.deepcopy(self.context)
        content=self.review.sha(self.root/'project.ecproj');context['sourceHash']=content
        context['sourceArtifact']={'assetId':'p'*256,'version':'parent-version','sha256':content}
        m=self.finish(context);self.assertEqual(m['artifact']['assetId'],'p'*256)
        refs=m['artifact']['renditions']+m['artifact']['evidenceRefs']+[m['artifact']['lossReportRef']]
        self.assertTrue(all(1<=len(r['assetId'])<=256 for r in refs),'public reference ID exceeds owner schema')

    def test_unsafe_json_timebase_is_rejected_instead_of_publishing_invalid_protocol(self):
        context=copy.deepcopy(self.context);context['comp']['duration']=1e-18
        with self.assertRaisesRegex(ValueError,'artifact_lineage.*time'):self.finish(context)

    def test_registered_source_package_blocks_metadata_or_dependency_change_before_edit(self):
        m=self.finish();tasks=load('task_store');managed=load('managed')
        for change in ('manifest','dependency'):
            with self.subTest(change=change),tempfile.TemporaryDirectory() as temporary:
                root=Path(temporary);source=root/'source';shutil.copytree(self.root,source)
                with patch('pathlib.Path.home',return_value=root/'isolated home'):
                    output=root/'revision';plan={'expectedProjectSha256':m['files']['project.ecproj'],'operations':[]}
                    checked=managed.preflight(plan,output,'workflow',source=source)
                    self.assertIn('sourcePackage',checked,'preflight does not bind the complete source version')
                    store=tasks.Store(root/'state')
                    store.create(change,plan=plan,output=str(output),runtime_sha='a'*64,inputs={},source=str(source/'project.ecproj'),mode='workflow',authorization={'sourcePackage':checked['sourcePackage']})
                    store.start(change);step=store.begin_step(change,'open_project',{});store.finish_step(change,step,{'ok':True})
                    if change=='manifest':
                        manifest=copy.deepcopy(m);manifest['acceptance']='changed after authorization'
                        (source/'manifest.json').write_text(json.dumps(manifest))
                    else:(source/'frame.png').write_bytes(b'changed dependency bytes')
                    before=copy.deepcopy(store.read(change))
                    with self.assertRaisesRegex(ValueError,'source_package_changed'):store.begin_step(change,'execute_command',{})
                    self.assertEqual(store.read(change),before)
                    with self.assertRaisesRegex(ValueError,'source_package_changed'):store.delivered(change,{'manifestSha256':'f'*64})
                    self.assertEqual(store.read(change),before)

    def test_native_windows_path_representation_produces_portable_public_locations(self):
        from pathlib import PureWindowsPath
        directory=self.root/'media';directory.mkdir();asset=directory/'dependency.bin';asset.write_bytes(b'collected media')
        context=copy.deepcopy(self.context);context['assets']={'fixture':{'path':'media/dependency.bin','sha256':self.review.sha(asset),'item':1,'staging':str(asset)}}
        # 保留真实临时目录I/O，只让relative_to呈现Windows实际返回对象的路径分隔行为。
        original=type(self.root).relative_to
        def windows_relative(path,*args,**kwargs):return PureWindowsPath(original(path,*args,**kwargs).as_posix())
        with patch.object(type(self.root),'relative_to',windows_relative):
            manifest=self.finish(context)
        self.assertIn('media/dependency.bin',manifest['files'])
        self.assertFalse(any('\\' in name for name in manifest['files']))
        self.assertEqual(self.review.inspect_delivery(self.root)['technical']['status'],'PASS')
