"""命令／桌面的初始帧和实际媒体必须参与父子共享预算。"""
import copy
import unittest
from pathlib import Path
import test_managed_tasks
import test_managed_command_delivery

class CommandResourceTests(unittest.TestCase):
    setUp=test_managed_tasks.ManagedTaskTests.setUp

    def prepare(self,frames=2,decoded=0):
        self.store.create('first',plan={},output=str(self.root/'first'),runtime_sha='a'*64,inputs={},source=None,mode='commands',authorization={})
        self.store.start('first');self.store.reserve_resources('first',{'frames':frames,'decodedBytes':decoded},'b'*64)
        return self.module.load('resource_budget')

    def test_native_frame_is_billed_once_across_restart(self):
        budget=self.prepare();budget.reserve_command(self.store,'first','c'*64,160*96*4)
        before=self.store.path('first').read_bytes();restored=self.module.Store(self.root/'state')
        budget.reserve_command(restored,'first','c'*64,160*96*4)
        self.assertEqual(before,self.store.path('first').read_bytes())
        self.assertEqual(budget.usage(restored.read('first')['resources']),{'frames':2,'decodedBytes':61440,'encodedBytes':0})

    def test_changed_attempt_size_cannot_overwrite_original(self):
        budget=self.prepare();budget.reserve_command(self.store,'first','c'*64,16);before=self.store.path('first').read_bytes()
        with self.assertRaisesRegex(ValueError,'resource_attempt_conflict'):budget.reserve_command(self.store,'first','c'*64,32)
        self.assertEqual(before,self.store.path('first').read_bytes())

    def test_child_preallocation_does_not_double_charge_actual_frame(self):
        budget=self.prepare(frames=1,decoded=16);budget.reserve_command(self.store,'first','c'*64,16)
        self.assertEqual(budget.usage(self.store.read('first')['resources'])['decodedBytes'],16)

    def test_actual_attempts_above_preallocation_cannot_hide_frames(self):
        budget=self.prepare(frames=1,decoded=0)
        for key in ['c','d']:budget.reserve_command(self.store,'first',key*64,16)
        self.assertEqual(budget.usage(self.store.read('first')['resources'])['frames'],2)
        self.assertEqual(budget.usage(self.store.read('first')['resources'])['decodedBytes'],32)

    def test_actual_decoded_limit_blocks_before_render_and_is_durable(self):
        budget=self.prepare()
        with self.assertRaisesRegex(ValueError,'resource_budget_exceeded'):budget.reserve_command(self.store,'first','c'*64,64*1024**3+1)
        with self.assertRaisesRegex(ValueError,'resource_budget_exceeded'):self.store.allowed(self.store.read('first'))
        self.assertGreater(budget.usage(self.store.read('first')['resources'])['decodedBytes'],64*1024**3)

    def test_invalid_attempt_record_cannot_be_used_to_reset_usage(self):
        budget=self.prepare();budget.reserve_command(self.store,'first','c'*64,16)
        state=self.store.read('first');state['resources']['entries']['first']['commandFrames']['c'*64]['decodedBytes']=-1;self.store.save(state)
        with self.assertRaisesRegex(ValueError,'state_invalid'):self.store.read('first')

    def test_owned_command_output_counts_nested_png_but_excludes_input_and_desktop_cache(self):
        self.prepare();out=self.root/'first';out.mkdir();(out/'nested').mkdir();(out/'nested/frame.png').write_bytes(b'pixels')
        for name in ['inputs','.desktop-data']:
            (out/name).mkdir();(out/name/'input.png').write_bytes(b'private cache input')
        meter=self.module.load('resource_meter');meter.watch(self.store,'first',out,out,'commands');meter.sample(self.store,'first')
        self.assertEqual(self.store.read('first')['resources']['entries']['first']['encodedBytes'],6)
        (out/'nested/frame.png').unlink();meter.sample(self.store,'first')
        self.assertEqual(self.store.read('first')['resources']['entries']['first']['encodedBytes'],6)

    def test_command_output_replacement_stays_unknown(self):
        self.prepare();out=self.root/'first';out.mkdir();meter=self.module.load('resource_meter');meter.watch(self.store,'first',out,out,'commands')
        out.rename(self.root/'original');out.mkdir();(out/'foreign.png').write_bytes(b'keep')
        with self.assertRaisesRegex(ValueError,'resource_location_identity_changed'):meter.sample(self.store,'first')
        self.assertEqual(self.store.read('first')['resourceObservation']['status'],'UNKNOWN');self.assertEqual((out/'foreign.png').read_bytes(),b'keep')

    def test_named_png_with_nonstandard_extension_is_metered(self):
        self.prepare();out=self.root/'first';out.mkdir();(out/'frame.payload').write_bytes(b'actual png')
        meter=self.module.load('resource_meter');meter.watch(self.store,'first',out,out,'commands',media=['frame.payload']);meter.sample(self.store,'first')
        self.assertEqual(self.store.read('first')['resources']['entries']['first']['encodedBytes'],10)

    def test_malformed_named_media_is_rejected_explicitly(self):
        self.prepare();out=self.root/'first';out.mkdir();meter=self.module.load('resource_meter');meter.watch(self.store,'first',out,out,'commands')
        value=self.store.read('first')['resourceLocations']
        for names in [[{}],['.']]:
            value['locations'][0]['media']=names
            with self.assertRaisesRegex(ValueError,'resource_locations_invalid'):meter.validate(value,str(out))

    def test_named_media_symlink_stays_unknown(self):
        self.prepare();out=self.root/'first';out.mkdir();external=self.root/'private';external.write_bytes(b'keep');(out/'frame.payload').symlink_to(external)
        meter=self.module.load('resource_meter');meter.watch(self.store,'first',out,out,'commands',media=['frame.payload'])
        with self.assertRaisesRegex(ValueError,'resource_media_symlink'):meter.sample(self.store,'first')
        self.assertEqual(self.store.read('first')['resourceObservation']['status'],'UNKNOWN');self.assertEqual(external.read_bytes(),b'keep')

class CommandResourceIntegrationTests(unittest.TestCase):
    setUp=test_managed_command_delivery.CommandDeliveryTests.setUp
    save=test_managed_command_delivery.CommandDeliveryTests.save
    frame=test_managed_command_delivery.CommandDeliveryTests.frame
    def test_observer_reserves_native_dimensions_before_frame_side_effect(self):
        self.save();self.frame();state=self.store.read('case');usage=self.module.load('resource_budget').usage(state['resources'])
        self.assertEqual(usage['frames'],1);self.assertEqual(usage['decodedBytes'],16)
        self.assertEqual(usage['encodedBytes'],(self.output/'preview.png').stat().st_size)

    def test_command_prepare_binds_declared_initial_frame_count(self):
        managed=self.module.load('managed');plan={'schema':'craft-command-plan/v1','operations':[{'tool':'render_frame','params':{}},{'command':'render.saveCurrentPreview','params':{}}]}
        out=self.root/'prepared';out.mkdir()
        self.store.create('prepared',plan=plan,output=str(out),runtime_sha='a'*64,inputs={},source=None,mode='commands',authorization={})
        self.store.start('prepared');self.tasks.atomic_json(self.store.path('prepared').parent/'request.json',{})
        managed.Hooks(self.store,'prepared').prepare_command_output(out)
        self.assertEqual(self.module.load('resource_budget').usage(self.store.read('prepared')['resources'])['frames'],2)
