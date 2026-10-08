"""局部修订不得扩大对象范围或隐藏非目标关键帧变化。"""
import copy
import importlib.util
from pathlib import Path
import unittest

SCRIPT=Path(__file__).resolve().parents[1]/'skills/effectcraft-use/scripts/revision.py'


class RevisionScopeTests(unittest.TestCase):
    def module(self):
        self.assertTrue(SCRIPT.exists(),'bounded revision validator is missing')
        spec=importlib.util.spec_from_file_location('revision_test',SCRIPT)
        m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

    def test_native_gateway_cannot_bypass_local_revision_scope(self):
        m=self.module()
        with self.assertRaisesRegex(ValueError,'revision_command_not_allowed'):
            m.validate_revision({'operations':[{'command':'native.command','params':{'command':'file.newProject','params':{}}}]}, {'bindings':{'title':{'layer':4}}}, [{'layer':'title','properties':['text/sourceText']}])

    def test_unapproved_property_rejected_before_execution(self):
        m=self.module();manifest={'bindings':{'title':{'layer':4}}}
        operation={'command':'prop.set','params':{'layer':{'$ref':'title.layer'},'path':'transform/position','value':[1,2]}}
        with self.assertRaisesRegex(ValueError,'revision_scope_exceeded'):
            m.validate_revision({'operations':[operation]},manifest,[{'layer':'title','properties':['text/sourceText']}])

    def test_permitted_text_change_preserves_keyframes_and_other_objects(self):
        m=self.module()
        before={'composition':{'layers':[4]},'layers':{'4':{'properties':{'children':[{'path':'text/sourceText','value':'old'},{'path':'transform/opacity','value':100,'keys':[0,1]}]}}}}
        after=copy.deepcopy(before);after['layers']['4']['properties']['children'][0]['value']='new'
        m.assert_preserved(before,after,{('4','text/sourceText')})
        after['layers']['4']['properties']['children'][1]['keys']=[0,2]
        with self.assertRaisesRegex(ValueError,'non_target_changed'):
            m.assert_preserved(before,after,{('4','text/sourceText')})
