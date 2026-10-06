"""计划边界和对象引用测试，不需要安装原生 CLI。"""
import importlib.util
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'skills/effectcraft-use/scripts/workflow.py'

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('workflow', SOURCE)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def test_effect_mask_parameter_failures_have_domain_identity(self):
        for command in ('effect.apply','effect.remove','effect.toggle','mask.new','mask.setVertex','mask.remove'):
            text=f"invalid parameters for `{command}`: unknown parameter(s) `invented`"
            error=self.module.command_error('execute_command',{'command':command},[{'type':'text','text':text}])
            self.assertIsInstance(error,ValueError)
            self.assertIn('unsupported_mapping: '+command,str(error))
            self.assertIn('invented',str(error))

    def test_other_native_failures_are_not_misclassified(self):
        for name,args,text in [('render_frame',{},'invalid parameters for `mask.new`: unknown parameter(s)'),('execute_command',{'command':'mask.new'},'asset unavailable'),('execute_command',{'command':'mask.new'},'invalid parameters for `effect.apply`: unknown parameter(s)'),('execute_command',{'command':'layer.newShape'},'invalid parameters for `layer.newShape`: unknown parameter(s)')]:
            error=self.module.command_error(name,args,[{'type':'text','text':text}])
            self.assertIsInstance(error,RuntimeError)
            self.assertIn('command_failed',str(error))

    def test_resolve_only_explicit_references(self):
        value = {'ids': [{'$ref': 'logo.id'}], 'text': 'logo.id'}
        self.assertEqual(self.module.resolve(value, {'logo': {'id': 12}}), {'ids': [12], 'text': 'logo.id'})

    def test_unknown_reference_is_an_error(self):
        with self.assertRaisesRegex(ValueError, 'unresolved_reference'):
            self.module.resolve({'$ref': 'missing.id'}, {})

    def test_file_side_effect_commands_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'unsupported_command'):
            self.module.validate({'operations': [{'command': 'document.save', 'params': {'path': '/outside'}}]})

    def test_duplicate_alias_rejected(self):
        with self.assertRaisesRegex(ValueError, 'duplicate_alias'):
            self.module.validate({'operations': [{'command': 'layer.newShape', 'as': 'logo'}, {'command': 'layer.newText', 'as': 'logo'}]})

    def test_export_range_and_format_rejected(self):
        for output in [{'format': 'exe', 'artboard': 0}, {'format': 'png', 'artboard': -1}]:
            with self.assertRaises(ValueError):
                self.module.validate({'operations': [], 'exports': [output]})

if __name__ == '__main__':
    unittest.main()
