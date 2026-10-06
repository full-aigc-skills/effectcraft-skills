"""计划边界和对象引用测试，不需要安装原生 CLI。"""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
import tempfile

SOURCE = Path(__file__).resolve().parents[1] / 'skills/effectcraft-use/scripts/workflow.py'

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('workflow', SOURCE)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def test_png_sequence_is_an_explicit_supported_export(self):
        self.module.validate({'operations': [], 'exports': [{'format': 'png-sequence'}]})

    def test_segmented_export_accepts_default_and_explicit_chunk_boundaries(self):
        for output in [{'format':'png-segmented'}, {'format':'png-segmented','chunkFrames':1}, {'format':'png-segmented','chunkFrames':10000}]:
            with self.subTest(output=output):
                self.module.validate({'operations': [], 'exports':[output]})

    def test_segmented_export_rejects_invalid_chunks_before_runtime_access(self):
        outputs = [{'format':'png-segmented','chunkFrames':value} for value in (True,0,-1,10001,1.5,'4',None)]
        outputs += [{'format':'mp4','chunkFrames':4}, {'format':'png-sequence','chunkFrames':4}, {'format':'png-segmented','path':'outside'}]
        for output in outputs:
            with self.subTest(output=output), tempfile.TemporaryDirectory() as temporary:
                root=Path(temporary)
                with patch.object(self.module,'load_module',side_effect=AssertionError('runtime must not start')):
                    with self.assertRaisesRegex(ValueError,'invalid_export'):
                        self.module.execute({'operations':[], 'exports':[output]},root/'output',runtime_home=root/'runtime')
                self.assertEqual(list(root.iterdir()),[])

    def test_exports_requires_a_list(self):
        for value in (None,{},'png-segmented'):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError,'invalid_export'):
                self.module.validate({'operations':[], 'exports':value})

    def test_export_sequence_cannot_be_requested_twice(self):
        with self.assertRaisesRegex(ValueError, 'invalid_export'):
            self.module.validate({'operations': [], 'exports': [{'format': 'png-sequence'}, {'format': 'png-sequence'}]})

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

    def test_entire_effect_mask_plan_is_preflighted_before_runtime_or_source_access(self):
        for command in ('effect.apply', 'effect.remove', 'effect.toggle', 'mask.new', 'mask.setVertex', 'mask.remove'):
            with self.subTest(command=command), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                plan = {'operations': [{'command': 'layer.newSolid', 'params': {}},
                    {'command': command, 'params': {'invented': 12}}]}
                with patch.object(self.module, 'load_module', side_effect=AssertionError('runtime must not start')):
                    with self.assertRaisesRegex(ValueError, 'unsupported_mapping: ' + command + '.*invented'):
                        self.module.execute(plan, root/'output', runtime_home=root/'runtime', source=root/'absent-source')
                self.assertEqual(list(root.iterdir()), [])

    def test_native_required_keys_are_checked_before_execution(self):
        for command in ('effect.apply', 'mask.new', 'mask.setVertex', 'mask.remove'):
            with self.subTest(command=command), self.assertRaisesRegex(ValueError, 'unsupported_mapping: ' + command + '.*missing'):
                self.module.validate({'operations': [{'command': command, 'params': {}}]})

    def test_native_target_aliases_and_unresolved_value_references_are_allowed(self):
        operations = [
            {'command': 'effect.apply', 'params': {'effect': 'Gaussian Blur', 'layer': {'$ref': 'title.layer'}, 'comp': {'$ref': 'composition.comp'}}},
            {'command': 'mask.new', 'params': {'layers': {'$ref': 'title.layer'}, 'vertices': [[0,0],[20,0],[20,20]], 'closed': True, 'merge': 'gesture'}},
            {'command': 'mask.setVertex', 'params': {'mask': {'$ref': 'mask.mask'}, 'index': 0, 'in': [0,0], 'out': [1,0]}}
        ]
        self.module.validate({'operations': operations})

    def test_runtime_reflection_drift_is_rejected(self):
        schemas = self.module.validate({'operations': [{'command': 'effect.apply', 'params': {'effect': 'Gaussian Blur'}}]})
        calls = []
        def call(name, args):
            calls.append((name, args))
            return {'id': args['command'], 'schema': {'additionalProperties': True}}
        with self.assertRaisesRegex(ValueError, 'parameter_schema_mismatch: effect.apply'):
            self.module.verify_parameter_contracts(call, schemas)
        self.assertEqual(calls, [('describe_command', {'command': 'effect.apply'})])

    def test_unrelated_operation_does_not_require_a_parameter_contract(self):
        with patch.object(self.module, 'parameter_contract', side_effect=AssertionError('unneeded contract')):
            self.module.validate({'operations': [{'command': 'layer.newText', 'params': {'text': 'Brand'}}]})

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
