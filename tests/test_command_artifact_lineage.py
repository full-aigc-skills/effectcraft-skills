"""命令／自有桌面的多工程血缘不替代实际媒体和原生重开验证。"""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import test_managed_command_delivery as fixtures

ROOT=Path(__file__).resolve().parents[1]
class CommandArtifactLineageTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.CommandDeliveryTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.delivery=self.fixture.module;self.store=self.fixture.store;self.output=self.fixture.output;self.tasks=self.fixture.tasks
    def finish(self):
        proof=self.fixture.finish();data=self.delivery.document(self.store,'case')
        self.assertIn('artifactMap',data,'managed command public artifact mapping missing')
        return proof,data,data['artifactMap']
    def test_actual_project_and_matching_png_are_public_objects_without_output_rewrite(self):
        self.fixture.save('nested/scene.ecproj');self.fixture.frame();before=fixtures.json.loads((self.output/'success.json').read_text()) if (self.output/'success.json').exists() else None
        raw={p.relative_to(self.output).as_posix():p.read_bytes() for p in self.output.rglob('*') if p.is_file()}
        proof,data,mapping=self.finish();a=mapping['artifacts'][0]
        self.assertEqual(a['protocolVersion'],'craft-artifact/v1');self.assertEqual(a['producerTaskId'],'case')
        self.assertEqual(a['sha256'],self.delivery.sha(self.output/'nested/scene.ecproj'));self.assertEqual(a['bytes'],(self.output/'nested/scene.ecproj').stat().st_size)
        self.assertEqual(a['nativeProjectRef']['location'],'nested/scene.ecproj');self.assertEqual([x['location'] for x in a['renditions']],['preview.png'])
        self.assertEqual(a['evidenceRefs'][0]['location'],'success.json');self.assertIsNone(a['lossReportRef']);self.assertEqual(a['sourceRefs'],[])
        self.assertEqual(proof['commandArtifacts']['artifacts'],mapping['artifacts'])
        report=self.delivery.inspect(self.store,'case',None);self.assertEqual(report['commandArtifacts'],mapping)
        self.assertEqual(report['engineering']['status'],'NOT_RUN');self.assertEqual(report['technical']['status'],'PASS')
        self.assertEqual(report['creative']['status'],'NOT_RUN')
        for name,value in raw.items():self.assertEqual((self.output/name).read_bytes(),value)
        self.assertFalse((self.output/'manifest.json').exists())
    def test_many_projects_and_compositions_keep_separate_contexts(self):
        self.fixture.save('early.ecproj');self.fixture.frame('early.png')
        self.fixture.session.comps[2]=dict(self.fixture.session.comps[1],id=2,name='B',width=7,layers=[])
        self.fixture.save('late.ecproj');self.fixture.frame('late.png');_,_,m=self.finish()
        artifacts={a['location']:a for a in m['artifacts']};self.assertEqual(set(artifacts),{'early.ecproj','late.ecproj'})
        self.assertNotEqual(artifacts['early.ecproj']['assetId'],artifacts['late.ecproj']['assetId'])
        self.assertEqual([x['location'] for x in artifacts['early.ecproj']['renditions']],['early.png'])
        self.assertEqual([x['location'] for x in artifacts['late.ecproj']['renditions']],['late.png'])
        self.assertEqual(artifacts['early.ecproj']['technicalMetadata']['width'],2)
        self.assertNotIn('width',artifacts['late.ecproj']['technicalMetadata'])
        self.assertEqual(len(m['contexts']['projects'][1]['snapshot']['compositions']),2)
    def test_unsaved_frame_is_not_attached_to_a_later_saved_project(self):
        self.fixture.frame();self.fixture.session.comps[1]['name']='later';self.fixture.save();(self.output/'unobserved.mp4').write_bytes(b'not reviewed')
        _,_,m=self.finish();self.assertEqual(m['unmatchedFrames'],['preview.png']);self.assertEqual(m['unreviewed'],['unobserved.mp4'])
        self.assertEqual(m['artifacts'][0]['renditions'],[]);self.assertEqual(self.delivery.inspect(self.store,'case',None)['technical']['status'],'NOT_RUN')
    def test_project_media_dependencies_are_content_bound(self):
        asset=self.output/'input.png';asset.write_bytes(fixtures.png());self.fixture.session.footage[9]=asset
        self.fixture.save();self.fixture.frame();_,_,m=self.finish();a=m['artifacts'][0]
        self.assertEqual(len(a['dependencies']),1);self.assertEqual(a['dependencies'][0]['kind'],'media');self.assertTrue(a['dependencies'][0]['packaged'])
        self.assertEqual(a['dependencies'][0]['assetRef']['sha256'],self.delivery.sha(asset))
    def test_portable_map_revalidates_whole_moved_package_and_rejects_replacement(self):
        self.fixture.save();self.fixture.frame();_,_,m=self.finish();adapter=self.delivery.load('command_artifact')
        moved=self.fixture.root/'moved package';shutil.copytree(self.output,moved)
        self.assertEqual(adapter.validate(moved,m),m['artifacts'])
        (moved/'preview.png').write_bytes(fixtures.png(1,1))
        with self.assertRaisesRegex(ValueError,'command_artifact'):adapter.validate(moved,m)
    def test_fresh_file_table_does_not_allow_old_version_or_wrong_references(self):
        self.fixture.save();self.fixture.frame();proof,data,m=self.finish();adapter=self.delivery.load('command_artifact')
        for target in ('version','producerTaskId','rendition','native','unmatched'):
            with self.subTest(target=target):
                changed=copy.deepcopy(m)
                if target in ('version','producerTaskId'):changed['artifacts'][0][target]='forged'
                elif target=='rendition':changed['artifacts'][0]['renditions'][0]['location']='scene.ecproj'
                elif target=='native':changed['artifacts'][0]['nativeProjectRef']['sha256']='0'*64
                else:changed['unmatchedFrames']=['preview.png']
                with self.assertRaisesRegex(ValueError,'command_artifact'):adapter.validate(self.output,changed)
        (self.output/'scene.ecproj').write_text(json.dumps({'schema':1,'items':{},'extra':True}))
        m['files']['scene.ecproj']=self.delivery.sha(self.output/'scene.ecproj')
        m['binding']['filesHash']=self.tasks.digest(m['files'])
        with self.assertRaisesRegex(ValueError,'command_artifact'):adapter.validate(self.output,m)
    def test_legacy_delivery_remains_readable_without_auto_creating_mapping(self):
        self.fixture.save();self.fixture.frame();proof,data,m=self.finish();data.pop('artifactMap');proof.pop('commandArtifacts')
        path=self.store.path('case').parent/'command-delivery/delivery.json';self.tasks.atomic_json(path,data);proof['commandDeliverySha256']=self.delivery.sha(path)
        state=self.store.read('case');state['delivery']=proof;self.store.save(state);before=path.read_bytes()
        report=self.delivery.inspect(self.store,'case',None);self.assertEqual(report['technical']['status'],'PASS');self.assertNotIn('commandArtifacts',report)
        self.assertEqual(path.read_bytes(),before)
    def test_child_projects_preserve_parent_ids_and_versions(self):
        self.fixture.save();self.fixture.frame();_,_,m=self.finish();parent=m['artifacts'][0]
        child_output=self.fixture.root/'child output';shutil.copytree(self.output,child_output)
        parent_binding=self.delivery.inspect(self.store,'case',None)['binding'];request={'inputs':{},'source':None,'commandRevision':{'sourceTask':'case','sourceBinding':parent_binding}}
        child=self.store.create('child',plan={'schema':'craft-command-plan/v1','operations':[]},output=str(child_output),runtime_sha=self.store.read('case')['identity']['runtimeSha256'],inputs={},source=None,mode='commands',authorization={'requestHash':self.tasks.digest(request)},parent='case')
        self.tasks.atomic_json(self.store.path('child').parent/'request.json',request)
        adapter=self.delivery.load('command_artifact');source=self.delivery.document(self.store,'case');changed=copy.deepcopy(source);changed['taskId']='child';changed['identityHash']=child['identityHash']
        mapped=adapter.build(self.store,child,changed)
        self.assertEqual(mapped['artifacts'][0]['assetId'],parent['assetId'])
        self.assertEqual(mapped['artifacts'][0]['sourceRefs'],[{k:parent[k] for k in ('assetId','version','sha256')}])
        self.assertNotEqual(mapped['artifacts'][0]['version'],parent['version'])
    def test_owner_schema_validates_actual_generated_objects(self):
        self.fixture.save();self.fixture.frame();_,_,m=self.finish()
        try:import jsonschema
        except ImportError:self.skipTest('owner-schema validation requires optional test jsonschema')
        import hashlib
        raw=(ROOT/'tests/fixtures/craft-artifact-v1.schema.json').read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),'c3385db540db71fccfdb049f79f05a9adba55ec008958579eab6fac46dd6ea5d')

        for artifact in m['artifacts']:jsonschema.Draft202012Validator(json.loads(raw)).validate(artifact)
