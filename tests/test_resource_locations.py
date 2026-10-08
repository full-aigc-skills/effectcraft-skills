"""渲染位置先登记；崩溃核对仅统计同一身份的自有目录。"""
import importlib.util
from pathlib import Path
import unittest
import test_managed_tasks


class ResourceLocationTests(unittest.TestCase):
    setUp=test_managed_tasks.ManagedTaskTests.setUp
    create=test_managed_tasks.ManagedTaskTests.create

    def meter(self):
        spec=importlib.util.spec_from_file_location('location_meter_test',test_managed_tasks.SCRIPT.with_name('resource_meter.py'))
        value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value

    def prepare(self):
        self.create();self.store.start('first')
        self.store.reserve_resources('first',{'frames':2,'decodedBytes':8},'a'*64)
        stage=self.root/'.effectcraft-owned';stage.mkdir()
        return stage

    def test_registered_preview_bytes_survive_worker_restart(self):
        stage=self.prepare();self.meter().watch(self.store,'first',stage,self.root/'first','workflow')
        (stage/'frame-0000.png').write_bytes(b'actual-frame')
        restored=self.module.Store(self.root/'state');self.meter().sample(restored,'first')
        self.assertEqual(restored.read('first')['resources']['entries']['first']['encodedBytes'],12)
        self.assertEqual(restored.read('first')['resourceObservation']['status'],'PASS')

    def test_directory_replacement_is_preserved_and_unknown(self):
        stage=self.prepare();self.meter().watch(self.store,'first',stage,self.root/'first','workflow')
        stage.rename(self.root/'original');stage.mkdir();(stage/'personal.png').write_bytes(b'keep')
        with self.assertRaisesRegex(ValueError,'resource_location_identity_changed'):
            self.meter().sample(self.store,'first')
        self.assertEqual((stage/'personal.png').read_bytes(),b'keep')
        self.assertEqual(self.store.read('first')['resourceObservation']['status'],'UNKNOWN')

    def test_missing_active_stage_is_unknown_but_retired_stage_can_disappear(self):
        stage=self.prepare();meter=self.meter();meter.watch(self.store,'first',stage,self.root/'first','workflow')
        stage.rmdir()
        with self.assertRaisesRegex(ValueError,'resource_location_missing'):meter.sample(self.store,'first')

    def test_renamed_output_is_the_same_owned_directory(self):
        stage=self.prepare();meter=self.meter();meter.watch(self.store,'first',stage,self.root/'first','workflow')
        (stage/'frame-0000.png').write_bytes(b'bytes');stage.rename(self.root/'first')
        meter.sample(self.store,'first')
        self.assertEqual(self.store.read('first')['resources']['entries']['first']['encodedBytes'],5)

    def test_segment_alias_does_not_double_count_published_frames(self):
        stage=self.prepare();output=self.root/'first';stage.rename(output)
        meter=self.meter();meter.watch(self.store,'first',output,output,'workflow')
        temp=output/'.effect-segment-one';temp.mkdir();destination=output/'rgba-segments/segment_00000';destination.parent.mkdir()
        meter.watch(self.store,'first',temp,destination,'segment')
        (temp/'frame_00000.png').write_bytes(b'bytes');temp.rename(destination)
        meter.sample(self.store,'first');meter.retire(self.store,'first',temp)
        self.assertEqual(self.store.read('first')['resources']['entries']['first']['encodedBytes'],5)

    def test_media_symlink_is_not_followed(self):
        stage=self.prepare();meter=self.meter();meter.watch(self.store,'first',stage,self.root/'first','workflow')
        other=self.root/'personal';other.write_bytes(b'keep');(stage/'frame-0000.png').symlink_to(other)
        with self.assertRaisesRegex(ValueError,'resource_media_symlink'):meter.sample(self.store,'first')
        self.assertEqual(other.read_bytes(),b'keep')

    def test_live_rename_race_is_rechecked_after_stop(self):
        from unittest.mock import patch
        stage=self.prepare();meter=self.meter();meter.watch(self.store,'first',stage,self.root/'first','workflow')
        with patch.object(meter,'files',side_effect=FileNotFoundError('rename in progress')):
            meter.sample(self.store,'first',live=True)
            self.assertNotIn('resourceObservation',self.store.read('first'))
            with self.assertRaises(FileNotFoundError):meter.sample(self.store,'first')
        self.assertEqual(self.store.read('first')['resourceObservation']['status'],'UNKNOWN')

    def test_corrupt_observation_is_diagnosed_without_repair(self):
        self.prepare();state=self.store.read('first');state['resourceObservation']=[];self.store.save(state)
        before=self.store.path('first').read_bytes()
        with self.assertRaisesRegex(ValueError,'state_invalid'):self.store.read('first')
        self.assertEqual(before,self.store.path('first').read_bytes())
