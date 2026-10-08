"""命令升级差异必须离线、确定性且不能继承过期验收。"""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'skills/effectcraft-use/scripts/command_catalog.py'

class CommandCatalogDiffTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SCRIPT.is_file(),'offline command diff implementation missing')
        spec=importlib.util.spec_from_file_location('command_catalog_test',SCRIPT)
        self.module=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.module)
        self.before={'schema':'craft-command-coverage/v1','pluginId':'effectcraft','runtimeSha256':'a'*64,
            'nativeTools':['execute_command'],'nativeToolSchemas':{'execute_command':{'type':'object'}},
            'commands':[{'id':'text.set','label':'设置文字','params':'value:string','ownerSkill':'effectcraft-cli-layers',
                         'workflowMapped':True,'executionAcceptance':'PASS','runModes':{'headless':{'acceptance':'NOT_RUN'}}}]}
        self.after=copy.deepcopy(self.before)

    def test_identical_does_not_import_acceptance(self):
        original=copy.deepcopy(self.before);r=self.module.compare(self.before,self.after)
        self.assertEqual(r['commands']['unchanged'],['text.set']);self.assertEqual(r['executionAcceptance'],'NOT_RUN')
        self.assertEqual(self.before,original);self.assertEqual(r['commands']['changed'],[])

    def test_added_and_removed_preserve_contracts_but_new_acceptance_is_not_run(self):
        self.after['commands'][0]['id']='text.new';r=self.module.compare(self.before,self.after)
        self.assertEqual(r['commands']['added'][0]['params'],'value:string')
        self.assertEqual(r['commands']['added'][0]['executionAcceptance'],'NOT_RUN')
        self.assertEqual(r['commands']['removed'],['text.set'])

    def test_parameter_owner_mode_and_mapping_changes_are_visible(self):
        self.after['commands'][0].update(params='value:number',ownerSkill='effectcraft-cli',workflowMapped=False,runModes={})
        r=self.module.compare(self.before,self.after);row=r['commands']['changed'][0]
        self.assertEqual(row['changedFields'],['ownerSkill','params','runModes','workflowMapped'])
        self.assertEqual(row['executionAcceptance'],'NOT_RUN')
        self.assertEqual(row['before']['params'],'value:string');self.assertEqual(row['after']['params'],'value:number')

    def test_mode_acceptance_claims_are_never_inherited(self):
        self.after['commands'][0]['runModes']['headless']['acceptance']='PASS'
        self.after['commands'][0]['params']='new value'
        r=self.module.compare(self.before,self.after)
        self.assertEqual(r['commands']['changed'][0]['after']['runModes']['headless']['acceptance'],'NOT_RUN')

    def test_generator_rejects_missing_and_duplicate_native_commands_before_writing(self):
        spec=importlib.util.spec_from_file_location('coverage_diff_test',ROOT/'scripts/build_command_coverage.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);base=root/'skill';(base/'references').mkdir(parents=True);(base/'scripts').mkdir()
            (root/'skill-suite.json').write_text(json.dumps({'skills':[]}),encoding='utf-8')
            (base/'scripts/workflow.py').write_text('ALLOWED = set()\n',encoding='utf-8')
            (base/'references/commands.json').write_text(json.dumps({'commands':[{'id':'text.set','label':'Text','params':None}]}),encoding='utf-8')
            module.ROOT=root;module.BASE=base
            for rows in [[{'id':'text.set'},{'id':'new.command'}],[{'id':'text.set'},{'id':'text.set'}],[]]:
                (base/'references/native-command-snapshot.json').write_text(json.dumps({'commands':rows,'tools':[],'runtimeSha256':'a'*64}),encoding='utf-8')
                with self.subTest(rows=rows),self.assertRaisesRegex(ValueError,'native_registry_drift'):
                    module.build()
                self.assertFalse((base/'references/command-coverage.json').exists())

    def test_runtime_change_invalidates_even_identical_contracts(self):
        self.after['runtimeSha256']='b'*64;r=self.module.compare(self.before,self.after)
        self.assertTrue(r['runtimeChanged']);self.assertEqual(r['requiresRevalidation'],['text.set'])

    def test_tool_added_removed_and_schema_change(self):
        self.after['nativeTools']+=['render_frame'];self.after['nativeToolSchemas']['render_frame']={}
        self.after['nativeToolSchemas']['execute_command']={'type':'object','required':['command']}
        r=self.module.compare(self.before,self.after)
        self.assertEqual(r['tools']['added'],['render_frame']);self.assertEqual(r['tools']['schemaChanged'],['execute_command'])
        self.after['nativeTools']=['render_frame'];del self.after['nativeToolSchemas']['execute_command']
        self.assertEqual(self.module.compare(self.before,self.after)['tools']['removed'],['execute_command'])

    def test_legacy_tool_schema_is_unavailable_not_unchanged(self):
        del self.before['nativeToolSchemas'];r=self.module.compare(self.before,self.after)
        self.assertEqual(r['tools']['schemaComparison'],'NOT_RUN');self.assertIsNone(r['tools']['schemaChanged'])

    def test_duplicate_command_ids_fail(self):
        self.before['commands']*=2
        with self.assertRaisesRegex(ValueError,'command_catalog_invalid'):self.module.compare(self.before,self.after)

    def test_wrong_domain_schema_and_missing_fields_fail(self):
        for field,value in [('pluginId','filmcraft'),('schema','future/v9'),('runtimeSha256','invalid')]:
            bad=copy.deepcopy(self.before);bad[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):self.module.compare(bad,self.after)
        del self.before['commands'][0]['params']
        with self.assertRaisesRegex(ValueError,'command_catalog_invalid'):self.module.compare(self.before,self.after)

    def test_duplicate_tools_and_schema_inventory_fail(self):
        for change in [{'nativeTools':['execute_command','execute_command']},{'nativeToolSchemas':{}}]:
            bad={**self.before,**change}
            with self.subTest(change=change),self.assertRaisesRegex(ValueError,'command_catalog_invalid'):self.module.compare(bad,self.after)

    def test_order_does_not_change_report(self):
        extra={**self.before['commands'][0],'id':'comp.create'}
        self.before['commands'].append(extra);self.after=copy.deepcopy(self.before)
        first=self.module.compare(self.before,self.after);self.after['commands'].reverse()
        self.assertEqual(first,self.module.compare(self.before,self.after))

    def test_generated_current_catalog_has_modes_and_native_schemas(self):
        current=json.loads((ROOT/'skills/effectcraft-use/references/command-coverage.json').read_text(encoding='utf-8'))
        self.assertEqual(set(current['nativeToolSchemas']),set(current['nativeTools']))
        for row in current['commands']:
            self.assertEqual(set(row['runModes']),{'headless','desktop'})
            self.assertTrue(all(v['acceptance']=='NOT_RUN' for v in row['runModes'].values()))
        self.module.compare(current,current)

    def test_public_diff_without_runtime_does_not_write_or_install(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);baseline=root/'baseline.json'
            baseline.write_text(json.dumps(self.before,ensure_ascii=False),encoding='utf-8')
            before=baseline.read_bytes()
            result=subprocess.run([sys.executable,'-I','-B',str(ROOT/'skills/effectcraft-use/scripts/commands.py'),'diff',str(baseline)],capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr.decode('utf-8',errors='replace'))
            self.assertEqual(json.loads(result.stdout)['executionAcceptance'],'NOT_RUN')
            self.assertEqual(sorted(p.name for p in root.iterdir()),['baseline.json']);self.assertEqual(baseline.read_bytes(),before)

    def test_public_diff_rejects_ambiguous_json(self):
        with tempfile.TemporaryDirectory() as name:
            path=Path(name)/'baseline.json';path.write_text('{"schema":1,"schema":2}',encoding='utf-8')
            result=subprocess.run([sys.executable,'-I','-B',str(ROOT/'skills/effectcraft-use/scripts/commands.py'),'diff',str(path)],capture_output=True)
            self.assertEqual(result.returncode,1);self.assertEqual(json.loads(result.stdout)['result'],'FAIL')

if __name__=='__main__':unittest.main()
