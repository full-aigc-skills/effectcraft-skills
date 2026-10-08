"""命令修订必须先验证范围/源版本，保全非目标原生字段。"""
import copy
import importlib.util
from pathlib import Path
import unittest

SCRIPT=Path(__file__).resolve().parents[1]/'skills/effectcraft-use/scripts/command_revision.py'


class CommandRevisionTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SCRIPT.exists(),'managed command/desktop bounded revision is missing')
        spec=importlib.util.spec_from_file_location('command_revision_test',SCRIPT);self.m=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.m)
        self.plan={'schema':'craft-command-plan/v1','operations':[{'command':'comp.new','params':{},'as':'main'},{'command':'layer.newText','params':{},'as':'title'},{'tool':'save_project','params':{'path':{'$output':'scene.ecproj'}}}]}
        self.scope=[{'project':'scene.ecproj','comp':'main','layer':'title','properties':['text/sourceText']}]
        self.project={'path':'scene.ecproj','snapshot':{'compositions':{'1':{'composition':{'id':1},'layers':{'2':{'properties':{'children':[{'uid':9,'path':'text/sourceText','value':'too long'},{'uid':10,'path':'transform/opacity','value':100,'keys':[{'time':0,'value':0}]}]}}}}}}}
        self.allowed=[{'project':'scene.ecproj','comp':1,'layer':2,'properties':['text/sourceText']}]
        self.request={'schema':'effectcraft-command-revision/v1','binding':{'commandDeliverySha256':'a'*64},'project':'scene.ecproj','operations':[{'comp':1,'command':'layer.setText','params':{'layer':2,'text':'Short'}}]}
        self.raw={'schema':1,'settings':{'depth':8},'items':{'1':{'kind':{'type':'Comp','layers':[{'id':2,'name':'Title','props':{'uid':3,'children':[{'uid':9,'value':{'t':'Text','v':'old'}},{'uid':10,'value':100,'keys':[{'time':0,'value':0}]}]}}]}}},'next_id':11}

    def test_scope_is_validated_without_changing_public_plan(self):
        before=copy.deepcopy(self.plan);self.assertEqual(self.m.validate_scope(self.plan,self.scope),self.scope);self.assertEqual(before,self.plan)

    def test_scope_cannot_reference_uncreated_alias(self):
        self.scope[0]['layer']='missing'
        with self.assertRaisesRegex(ValueError,'revision_scope'):self.m.validate_scope(self.plan,self.scope)

    def test_scope_cannot_bind_an_undeclared_project_path(self):
        self.scope[0]['project']='../other.ecproj'
        with self.assertRaisesRegex(ValueError,'revision_scope|invalid_output_path'):self.m.validate_scope(self.plan,self.scope)

    def test_scope_rejects_empty_wildcard_and_duplicate_addresses(self):
        for props in [[],['*'],['text/sourceText','text/sourceText']]:
            bad=copy.deepcopy(self.scope);bad[0]['properties']=props
            with self.assertRaisesRegex(ValueError,'revision_scope'):self.m.validate_scope(self.plan,bad)

    def test_authorized_text_is_resolved_to_native_uid(self):
        targets=self.m.validate_plan(self.request,self.project,self.allowed)
        self.assertEqual(targets,[{'comp':1,'layer':2,'path':'text/sourceText','uid':9}])

    def test_native_gateway_cannot_bypass_scope(self):
        self.request['operations'][0]['command']='native.command'
        with self.assertRaisesRegex(ValueError,'revision_command_not_allowed'):self.m.validate_plan(self.request,self.project,self.allowed)

    def test_text_style_parameters_cannot_expand_text_only_request(self):
        self.request['operations'][0]['params']['size']=80
        with self.assertRaisesRegex(ValueError,'revision_parameters'):self.m.validate_plan(self.request,self.project,self.allowed)

    def test_other_composition_cannot_use_same_layer_number(self):
        self.request['operations'][0]['comp']=7
        with self.assertRaisesRegex(ValueError,'revision_scope'):self.m.validate_plan(self.request,self.project,self.allowed)

    def test_other_property_cannot_use_authorized_layer(self):
        self.request['operations'][0].update(command='prop.set',params={'layer':2,'path':'transform/opacity','value':10})
        with self.assertRaisesRegex(ValueError,'revision_scope'):self.m.validate_plan(self.request,self.project,self.allowed)

    def test_animated_property_requires_explicit_future_time_scope(self):
        self.allowed[0]['properties']=['transform/opacity'];self.request['operations'][0].update(command='prop.set',params={'layer':2,'path':'transform/opacity','value':10})
        with self.assertRaisesRegex(ValueError,'animated_property'):self.m.validate_plan(self.request,self.project,self.allowed)

    def test_same_property_from_duplicate_operations_is_rejected(self):
        self.request['operations'].append(copy.deepcopy(self.request['operations'][0]))
        with self.assertRaisesRegex(ValueError,'revision_duplicate'):self.m.validate_plan(self.request,self.project,self.allowed)

    def test_only_authorized_value_is_excluded_from_native_comparison(self):
        after=copy.deepcopy(self.raw);after['items']['1']['kind']['layers'][0]['props']['children'][0]['value']['v']='new'
        self.m.assert_preserved(self.raw,after,{9},{},{})

    def test_non_target_keyframes_are_preserved(self):
        after=copy.deepcopy(self.raw);after['items']['1']['kind']['layers'][0]['props']['children'][1]['keys'][0]['time']=1
        with self.assertRaisesRegex(ValueError,'non_target_changed'):self.m.assert_preserved(self.raw,after,{9},{},{})

    def test_target_keyframes_cannot_hide_inside_allowed_value_change(self):
        after=copy.deepcopy(self.raw);after['items']['1']['kind']['layers'][0]['props']['children'][0]['keys']=[{'time':1,'value':'new'}]
        with self.assertRaisesRegex(ValueError,'non_target_changed'):self.m.assert_preserved(self.raw,after,{9},{},{})

    def test_other_native_fields_cannot_change(self):
        after=copy.deepcopy(self.raw);after['settings']['depth']=32
        with self.assertRaisesRegex(ValueError,'non_target_changed'):self.m.assert_preserved(self.raw,after,{9},{},{})

    def test_asset_relocation_preserves_actual_digest_identity(self):
        before=copy.deepcopy(self.raw);before['items']['5']={'kind':{'type':'Footage','path':'/original/a.png'}}
        after=copy.deepcopy(before);after['items']['5']['kind']['path']='/new/inputs/a.png'
        self.m.assert_preserved(before,after,set(),{'5':{'sha256':'a'*64}},{'5':{'sha256':'a'*64}})
        with self.assertRaisesRegex(ValueError,'non_target_changed'):self.m.assert_preserved(before,after,set(),{'5':{'sha256':'a'*64}},{'5':{'sha256':'b'*64}})

class CommandRevisionFlowTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SCRIPT.exists());spec=importlib.util.spec_from_file_location('command_revision_flow',SCRIPT);self.m=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.m)
        self.assertTrue(hasattr(self.m,'revise'),'command revision must connect validated scope to durable child execution')
        import test_managed_command_delivery as fixture
        from unittest.mock import patch
        self.f=fixture.CommandDeliveryTests('runTest');self.f.setUp();self.addCleanup(self.f.doCleanups)
        f=self.f;self.store=f.store;self.output=f.output
        scope=[{'project':'scene.ecproj','comp':'main','layer':'title','properties':['text/sourceText']}]
        plan={'schema':'craft-command-plan/v1','operations':[{'command':'comp.new','params':{},'as':'main'},{'command':'layer.newText','params':{},'as':'title'},{'tool':'save_project','params':{'path':{'$output':'scene.ecproj'}}},{'tool':'render_frame','params':{'path':{'$output':'preview.png'}}}]}
        state=self.store.read('case');state['plan']=plan;state['identity']['planHash']=f.tasks.digest(plan);state['identity']['authorization']['revisionScope']=scope
        state['identityHash']=f.tasks.digest(state['identity']);state['workKey']=f.tasks.digest({k:v for k,v in state['identity'].items() if k not in ('authorization','runtimeSha256')});state['resources']['entries']['case']['bindingHash']=state['identity']['planHash'];state['resourceReservation']['bindingHash']=state['identity']['planHash'];self.store.save(state)
        f.session.comps[1].update(frameRate=1,duration=1);f.session.layers['3']['properties'][0]['uid']=9
        f.steps=[{'index':0,'command':'comp.new','tool':None,'params':{},'state':'succeeded','result':{'comp':1}},{'index':1,'command':'layer.newText','tool':None,'params':{},'state':'succeeded','result':{'layer':3}}]
        raw={'savedBy':'0.4.0','schema':1,'settings':{},'items':{'1':{'id':1,'kind':{'type':'Comp','layers':[{'id':3,'props':{'uid':4,'children':[{'node':'Prop','uid':9,'value':{'t':'Text','v':'before'}}]}}]}}},'next_id':10}
        rec={'index':2,'command':None,'tool':'save_project','params':{'path':str(f.output/'scene.ecproj')},'state':'started'}
        f.observer(f.session,rec,'before');(f.output/'scene.ecproj').write_text(__import__('json').dumps(raw));rec.update(state='succeeded',result={});f.observer(f.session,rec,'after');f.steps.append(rec)
        f.frame();f.finish();self.criteria={'goal':'short readable title'}
        delivery=f.module;original_inspect=delivery.inspect
        self.engineering='PASS'
        def inspected(*args,**kwargs):
            report=original_inspect(*args,**kwargs);report['engineering']={'status':self.engineering,'fresh':self.engineering=='PASS'};return report
        native=patch.object(delivery,'inspect',side_effect=inspected);native.start();self.addCleanup(native.stop)
        ledger=delivery.load('review_ledger');quality=delivery.load('command_judge').Quality(self.store,'case');quality.inspect_delivery=lambda output,home=None:delivery.inspect(self.store,'case',home)
        qpatch=patch.object(ledger,'quality_adapter',return_value=quality);qpatch.start();self.addCleanup(qpatch.stop)
        request=ledger.review(self.store,'case',self.criteria,runtime_home='prepared')['judgeRequest']
        response={k:request[k] for k in ('taskId','requestId','binding','criteriaHash','scopeHash')};response.update(schema='effectcraft-judge-receipt/v2',status='FAIL',score=.4,passed=False,issues=[{'description':'title too long'}],capabilities={'visual':True,'temporal':True},temporalReviewed=True,
            observations=[{'path':x['path'],'sha256':x['sha256'],'frameIndices':x['frameIndices'],'method':'unit PNG observation','description':'title too long'} for x in request['scope']['media']])
        response_path=f.root/'response.json';f.tasks.atomic_json(response_path,response);ledger.review(self.store,'case',self.criteria,response_path,'prepared')
        self.request={'schema':'effectcraft-command-revision/v1','binding':request['binding'],'project':'scene.ecproj','operations':[{'comp':1,'command':'layer.setText','params':{'layer':3,'text':'Short'}}]}
        real_load=self.m.load;managed=real_load('managed');managed.supervise=lambda store,task,home:store.read(task)
        loader=patch.object(self.m,'load',side_effect=lambda name:delivery if name=='command_delivery' else managed if name=='managed' else real_load(name));loader.start();self.addCleanup(loader.stop)

    def revise(self):return self.m.revise(self.store,'case',self.request,self.f.root/'revised','prepared')

    def test_child_uses_original_mode_runtime_deadline_and_shared_attempt(self):
        before=(self.output/'scene.ecproj').read_bytes();root=self.store.read('case');child=self.revise();latest=self.store.read('case')
        self.assertEqual(child['identity']['mode'],'commands');self.assertEqual(child['identity']['runtimeSha256'],root['identity']['runtimeSha256']);self.assertLessEqual(child['deadline'],root['deadline'])
        self.assertEqual(child['parent'],'case');self.assertEqual(latest['budget']['revisions'],1);self.assertEqual(latest['activeRevision'],child['taskId'])
        self.assertEqual(before,(self.output/'scene.ecproj').read_bytes());self.assertFalse((self.f.root/'revised').exists())
        self.m.validate_prepared(self.store,child['taskId'])

    def test_wrong_binding_rejects_before_budget_or_child_creation(self):
        self.request['binding']['filesHash']='0'*64;before=self.store.path('case').read_bytes()
        with self.assertRaisesRegex(ValueError,'revision_conflict|artifact_changed'):self.revise()
        self.assertEqual(before,self.store.path('case').read_bytes());self.assertFalse((self.f.root/'revised').exists())

    def test_missing_runtime_rejects_before_budget(self):
        self.engineering='NOT_RUN';before=self.store.path('case').read_bytes()
        with self.assertRaisesRegex(ValueError,'engineering_gate'):self.revise()
        self.assertEqual(before,self.store.path('case').read_bytes())

    def test_two_round_budget_rejects_before_native_attempt(self):
        root=self.store.read('case');root['budget']['revisions']=2;self.store.save(root);before=self.store.path('case').read_bytes()
        with self.assertRaisesRegex(ValueError,'revision_budget_exhausted'):self.revise()
        self.assertEqual(before,self.store.path('case').read_bytes())

    def test_forged_stagnant_counter_rejects_without_charging_or_child(self):
        root=self.store.read('case');root['budget']['stagnant']=2;self.store.save(root);before=self.store.path('case').read_bytes()
        with self.assertRaisesRegex(ValueError,'review_selection_changed'):self.revise()
        self.assertEqual(before,self.store.path('case').read_bytes());self.assertFalse((self.f.root/'revised').exists())

    def test_cancel_intent_rejects_without_charging_or_child(self):
        root=self.store.read('case');root['cancellationRequestedAt']=root['createdAt'];self.store.save(root);before=self.store.path('case').read_bytes()
        with self.assertRaisesRegex(ValueError,'cancel_requested'):self.revise()
        self.assertEqual(before,self.store.path('case').read_bytes());self.assertFalse((self.f.root/'revised').exists())

    def test_expired_deadline_rejects_without_charging_or_child(self):
        from unittest.mock import patch
        root=self.store.read('case');before=self.store.path('case').read_bytes()
        with patch.object(self.f.tasks.time,'time',return_value=root['deadline']+1):
            with self.assertRaisesRegex(ValueError,'deadline_exceeded'):self.revise()
        self.assertEqual(before,self.store.path('case').read_bytes());self.assertFalse((self.f.root/'revised').exists())

    def test_legacy_root_without_initial_frame_accounting_is_read_only(self):
        root=self.store.read('case');root['resources']['entries']['case'].pop('commandFrames',None);self.store.save(root);before=self.store.path('case').read_bytes()
        with self.assertRaisesRegex(ValueError,'legacy_command_resource_read_only'):self.revise()
        self.assertEqual(before,self.store.path('case').read_bytes());self.assertFalse((self.f.root/'revised').exists())

    def test_partial_child_cannot_be_bypassed_by_a_new_revision(self):
        self.revise();before=self.store.path('case').read_bytes()
        with self.assertRaisesRegex(ValueError,'revision_in_progress'):self.revise()
        self.assertEqual(before,self.store.path('case').read_bytes())

    def test_changed_source_keeps_original_budget_and_artifact(self):
        p=self.output/'preview.png';p.write_bytes(b'changed');before=self.store.path('case').read_bytes()
        with self.assertRaises(ValueError):self.revise()
        self.assertEqual(before,self.store.path('case').read_bytes());self.assertEqual(p.read_bytes(),b'changed')

    def test_seed_corruption_is_detected_before_public_command_execution(self):
        import json
        child=self.revise();request=json.loads((self.store.path(child['taskId']).parent/'request.json').read_text());seed=Path(next(iter(request['commandRevision']['seeds'])));seed.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'revision_seed_changed'):self.m.validate_prepared(self.store,child['taskId'])

    def test_prepared_validation_does_not_reset_existing_partial_output(self):
        child=self.revise();out=Path(child['output']);out.mkdir();(out/'partial.txt').write_bytes(b'keep')
        self.m.validate_prepared(self.store,child['taskId'])
        self.assertEqual((out/'partial.txt').read_bytes(),b'keep')

    def test_command_preparation_reserves_parent_resource_budget_once(self):
        child=self.revise();out=Path(child['output']);out.mkdir()
        hooks=self.m.load('managed').Hooks(self.store,child['taskId'])
        hooks.prepare_command_output(out)
        first=self.store.path('case').read_bytes();hooks.prepare_command_output(out)
        self.assertEqual(first,self.store.path('case').read_bytes())
        resources=self.store.read('case')['resources']
        self.assertTrue(resources)


    def executed_child(self):
        import json,hashlib
        import test_managed_command_delivery as fixture
        child=self.revise();out=Path(child['output']);out.mkdir();self.store.start(child['taskId'])
        self.m.load('managed').Hooks(self.store,child['taskId']).prepare_command_output(out)
        module=self.f.module;session=copy.deepcopy(self.f.session)
        session.layers['3']['properties'][0]['value']='Short'
        observer=module.Observer(self.store,child['taskId']);steps=[]
        native=json.loads((self.output/'scene.ecproj').read_text());native['items']['1']['kind']['layers'][0]['props']['children'][0]['value']['v']='Short'
        for index,op in enumerate(child['plan']['operations']):
            params=copy.deepcopy(op['params'])
            if isinstance(params.get('path'),dict):params['path']=str(out/params['path']['$output'])
            record={'index':index,'tool':op.get('tool'),'command':op.get('command'),'params':params,'state':'started'}
            observer(session,record,'before')
            if op.get('tool')=='save_project':Path(params['path']).write_text(json.dumps(native))
            if op.get('tool')=='render_frame':Path(params['path']).write_bytes(fixture.png())
            record.update(state='succeeded',result={});observer(session,record,'after');steps.append(record)
        receipt={'schema':'craft-command-receipt/v1','pluginId':'effectcraft','mode':'headless','result':'PASS','runtimeSha256':'a'*64,'steps':steps,
          'planSha256':hashlib.sha256(json.dumps(child['plan'],ensure_ascii=False,sort_keys=True,allow_nan=False).encode()).hexdigest()}
        self.f.tasks.atomic_json(out/'success.json',receipt);proof=module.finalize(self.store,child['taskId'])
        return child,proof

    def test_preservation_receipt_precedes_delivery_and_is_idempotent(self):
        child,proof=self.executed_child();root_bytes=self.store.path('case').read_bytes()
        result=self.m.validate_result(self.store,child['taskId'],proof)
        self.assertEqual(result['status'],'PASS');self.assertIsNone(self.store.read(child['taskId'])['delivery'])
        path=self.store.path(child['taskId']).parent/'preservation.json';before=path.read_bytes()
        self.m.validate_result(self.store,child['taskId'],proof)
        self.assertEqual(before,path.read_bytes());self.assertEqual(root_bytes,self.store.path('case').read_bytes())

    def test_valid_new_observations_do_not_hide_unauthorized_native_fields(self):
        child,proof=self.executed_child();out=Path(child['output']);p=out/'scene.ecproj'
        import json
        value=json.loads(p.read_text());value['settings']['unexpected']=True;p.write_text(json.dumps(value))
        # Re-finalizing a changed artifact must already fail at the immutable observation boundary.
        with self.assertRaisesRegex(ValueError,'command_artifact_changed'):
            self.f.module.finalize(self.store,child['taskId'])
        self.assertIsNone(self.store.read(child['taskId'])['delivery'])
        self.assertEqual(self.store.read('case')['activeRevision'],child['taskId'])


    def test_recovery_clears_only_verified_completed_child(self):
        child,proof=self.executed_child();self.m.validate_result(self.store,child['taskId'],proof);self.store.delivered(child['taskId'],proof)
        self.f.tasks.atomic_json(self.store.lifecycle_path(self.store.read(child['taskId'])),{'schema':'effectcraft-process-lifecycle/v1','status':'stopped'})
        self.m.settle_completed(self.store,child['taskId'])
        self.assertIsNone(self.store.read('case')['activeRevision']);before=self.store.path('case').read_bytes()
        self.m.settle_completed(self.store,child['taskId']);self.assertEqual(before,self.store.path('case').read_bytes())

    def test_recovery_missing_preservation_cannot_rebuild_baseline(self):
        child,proof=self.executed_child();self.store.delivered(child['taskId'],proof)
        self.f.tasks.atomic_json(self.store.lifecycle_path(self.store.read(child['taskId'])),{'schema':'effectcraft-process-lifecycle/v1','status':'stopped'})
        before=self.store.path('case').read_bytes()
        with self.assertRaisesRegex(ValueError,'preservation_receipt_missing'):self.m.settle_completed(self.store,child['taskId'])
        self.assertEqual(before,self.store.path('case').read_bytes())

    def test_recovery_live_or_unconfirmed_process_keeps_revision_occupied(self):
        child,proof=self.executed_child();self.m.validate_result(self.store,child['taskId'],proof);self.store.delivered(child['taskId'],proof)
        before=self.store.path('case').read_bytes()
        with self.assertRaisesRegex(ValueError,'process_termination_unconfirmed'):self.m.settle_completed(self.store,child['taskId'])
        self.assertEqual(before,self.store.path('case').read_bytes())


    def test_generated_edit_selects_exact_authorized_layer_first(self):
        child=self.revise();ops=child['plan']['operations'];i=next(i for i,x in enumerate(ops) if x.get('command')=='layer.setText')
        self.assertEqual(ops[i-1],{'command':'layer.select','params':{'layers':[3]}})

    def blocked_child(self):
        child=self.revise();out=Path(child['output']);out.mkdir();self.store.start(child['taskId']);self.m.load('managed').Hooks(self.store,child['taskId']).prepare_command_output(out);steps=[]
        tasks=self.f.tasks;commands=self.m.load('commands');catalog=commands.ROUTES['effectcraft'][0]
        def call(name,args):
            identity=self.store.begin_step(child['taskId'],name,{'name':name,'arguments':args});self.store.finish_step(child['taskId'],identity,{})
        call(catalog,{})
        for index,op in enumerate(child['plan']['operations']):
            params=copy.deepcopy(op['params']);row={'index':index,'command':op.get('command'),'tool':op.get('tool'),'params':params}
            if op.get('command'):call(catalog,{'filter':op['command']})
            if op.get('command')=='layer.setText':
                row.update(state='blocked',reason='select a layer first');steps.append(row);break
            tool,args=commands.native_call(op['command'],params) if op.get('command') else (op['tool'],params)
            call(tool,args);row.update(state='succeeded',result={});steps.append(row)
        import hashlib,json
        error='precondition_failed: layer.setText: select a layer first'
        receipt={'schema':'craft-command-receipt/v1','pluginId':'effectcraft','mode':'headless','result':'FAIL','runtimeSha256':'a'*64,'steps':steps,'error':error,
          'planSha256':hashlib.sha256(json.dumps(child['plan'],ensure_ascii=False,sort_keys=True,allow_nan=False).encode()).hexdigest()}
        tasks.atomic_json(out/'failure.json',receipt);tasks.atomic_json(out/'journal.json',receipt)
        self.store.fail(child['taskId'],error,unknown=True)
        tasks.atomic_json(self.store.lifecycle_path(self.store.read(child['taskId'])),{'schema':'effectcraft-process-lifecycle/v1','status':'stopped'})
        return child

    def test_blocked_recovery_proves_no_edit_without_refunding_attempt(self):
        child=self.blocked_child();result=self.m.prove_not_executed(self.store,child['taskId'])
        self.assertEqual(result['state'],'failed');self.assertEqual(result['reconciliation']['result'],'revision_not_executed')
        root=self.store.read('case');self.assertEqual(root['budget']['revisions'],1);self.assertIsNone(root['activeRevision'])
        self.assertFalse((Path(child['output'])/'scene.ecproj').exists())

    def test_blocked_recovery_rejects_any_unresolved_native_call(self):
        child=self.blocked_child();state=self.store.read(child['taskId']);state['steps'][-1]['state']='attempted';self.store.save(state)
        before=self.store.path('case').read_bytes()
        with self.assertRaisesRegex(ValueError,'revision_outcome_unknown'):self.m.prove_not_executed(self.store,child['taskId'])
        self.assertEqual(before,self.store.path('case').read_bytes())

    def test_missing_failure_receipt_keeps_unknown_with_stable_diagnostic(self):
        child=self.blocked_child();(Path(child['output'])/'failure.json').unlink()
        before=self.store.path('case').read_bytes();state=self.store.path(child['taskId']).read_bytes()
        with self.assertRaisesRegex(ValueError,'revision_outcome_unknown'):
            self.m.prove_not_executed(self.store,child['taskId'])
        self.assertEqual(before,self.store.path('case').read_bytes());self.assertEqual(state,self.store.path(child['taskId']).read_bytes())

    def interrupted_settlement(self):
        from unittest.mock import patch
        child=self.blocked_child();original=self.store.save
        def save(state):
            if state['taskId']=='case' and state.get('activeRevision') is None:raise OSError('simulated root settlement crash')
            return original(state)
        with patch.object(self.store,'save',side_effect=save):
            with self.assertRaisesRegex(OSError,'simulated root settlement crash'):self.m.prove_not_executed(self.store,child['taskId'])
        self.assertEqual(self.store.read(child['taskId'])['state'],'failed')
        self.assertEqual(self.store.read('case')['activeRevision'],child['taskId'])
        return child

    def test_public_reconcile_finishes_interrupted_not_executed_settlement(self):
        child=self.interrupted_settlement();proof=self.store.path(child['taskId']).parent/'not-executed.json';before=proof.read_bytes()
        managed=self.m.load('managed');original=managed.load
        from unittest.mock import patch
        with patch.object(managed,'load',side_effect=lambda name:self.m if name=='command_revision' else original(name)):
            result=managed.reconcile(self.store,child['taskId'])
        self.assertEqual(result['reconciliation']['result'],'revision_not_executed')
        self.assertIsNone(self.store.read('case')['activeRevision']);self.assertEqual(self.store.read('case')['budget']['revisions'],1)
        self.assertEqual(before,proof.read_bytes())

    def test_interrupted_settlement_changed_proof_keeps_root_occupied(self):
        child=self.interrupted_settlement();proof=self.store.path(child['taskId']).parent/'not-executed.json';proof.write_text('{}')
        before=self.store.path('case').read_bytes()
        with self.assertRaisesRegex(ValueError,'revision_not_executed_proof_changed'):
            self.m.prove_not_executed(self.store,child['taskId'])
        self.assertEqual(before,self.store.path('case').read_bytes())

    def test_not_executed_settlement_after_expiry_does_not_schedule_work(self):
        from unittest.mock import patch
        child=self.interrupted_settlement();state=self.store.read(child['taskId']);steps=copy.deepcopy(state['steps']);root=self.store.read('case')
        with patch.object(self.f.tasks.time,'time',return_value=root['deadline']+1):
            result=self.m.prove_not_executed(self.store,child['taskId'])
        self.assertEqual(result['steps'],steps);self.assertIsNone(self.store.read('case')['activeRevision']);self.assertEqual(self.store.read('case')['budget']['revisions'],1)

    def test_not_executed_settlement_after_cancel_retains_cancel_intent(self):
        child=self.interrupted_settlement();root=self.store.read('case');root['cancellationRequestedAt']=root['createdAt'];self.store.save(root)
        result=self.m.prove_not_executed(self.store,child['taskId'])
        self.assertEqual(result['state'],'failed');latest=self.store.read('case');self.assertIsNone(latest['activeRevision']);self.assertEqual(latest['cancellationRequestedAt'],root['createdAt'])
        with self.assertRaisesRegex(ValueError,'cancel_requested'):self.store.allowed(latest)

    def test_completed_settlement_after_expiry_rechecks_existing_preservation_only(self):
        from unittest.mock import patch
        child,proof=self.executed_child();self.m.validate_result(self.store,child['taskId'],proof);self.store.delivered(child['taskId'],proof)
        self.f.tasks.atomic_json(self.store.lifecycle_path(self.store.read(child['taskId'])),{'schema':'effectcraft-process-lifecycle/v1','status':'stopped'})
        root=self.store.read('case');saved=self.store.path(child['taskId']).parent/'preservation.json';before=saved.read_bytes()
        with patch.object(self.f.tasks.time,'time',return_value=root['deadline']+1):self.m.settle_completed(self.store,child['taskId'])
        self.assertEqual(before,saved.read_bytes());self.assertIsNone(self.store.read('case')['activeRevision'])


class ManagedRevisionEntryTests(unittest.TestCase):
    def setUp(self):
        spec=importlib.util.spec_from_file_location('entry_revision',SCRIPT.with_name('managed.py'));self.m=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.m)
        import tempfile
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.plan={'schema':'craft-command-plan/v1','operations':[{'command':'comp.new','params':{},'as':'main'},{'command':'layer.newText','params':{},'as':'title'},{'tool':'save_project','params':{'path':{'$output':'scene.ecproj'}}}]}
        self.scope=[{'project':'scene.ecproj','comp':'main','layer':'title','properties':['text/sourceText']}]

    def test_preflight_accepts_separate_scope_without_mutating_raw_plan(self):
        before=copy.deepcopy(self.plan)
        self.m.preflight(self.plan,self.root/'out','commands',revision_scope=self.scope)
        self.assertEqual(self.plan,before)

    def test_scope_cannot_override_workflow_scope(self):
        with self.assertRaisesRegex(ValueError,'revision_scope_mode'):
            self.m.preflight({},self.root/'out','workflow',revision_scope=self.scope)

    def test_scope_is_bound_to_task_identity_and_worker_request(self):
        from unittest.mock import patch
        store=self.m.load('task_store').Store(self.root/'state')
        with patch.object(self.m,'supervise',side_effect=lambda store,task,home:store.read(task)):
            state=self.m.run(store,self.plan,self.root/'out',self.root/'runtime',mode='commands',revision_scope=self.scope)
        self.assertEqual(state['identity']['authorization']['revisionScope'],self.scope)
        request=self.m.read(store.path(state['taskId']).parent/'request.json')
        self.assertEqual(request['revisionScope'],self.scope)
        self.assertEqual(self.m.load('task_store').digest(request),state['identity']['authorization']['requestHash'])

    def test_managed_revise_routes_command_mode_before_workflow_manifest(self):
        from unittest.mock import Mock,patch
        module=self.m.load('revision');store=Mock();store.read.return_value={'identity':{'mode':'commands'}}
        adapter=Mock();adapter.revise.return_value={'state':'planned'};original=module.load
        with patch.object(module,'load',side_effect=lambda name:adapter if name=='command_revision' else original(name)):
            self.assertEqual(module.revise(store,'t',{},self.root/'out','home'),{'state':'planned'})
        adapter.revise.assert_called_once()

    def test_non_target_media_compare_uses_decoded_pixels(self):
        import test_managed_command_delivery as fixture
        a=self.root/'a.png';b=self.root/'b.png';a.write_bytes(fixture.png());b.write_bytes(fixture.png())
        module=self.m.load('command_revision');module.assert_media_preserved(a,b)
        b.write_bytes(fixture.png(width=3))
        with self.assertRaisesRegex(ValueError,'non_target_media_changed'):module.assert_media_preserved(a,b)

    def test_text_only_revision_preserves_nested_font_style(self):
        module=self.m.load('command_revision')
        before={'items':{'1':{'kind':{'type':'Comp','props':{'uid':9,'value':{'t':'Text','v':{'text':'long','font':'Inter','size':30}}}}}}}
        after=copy.deepcopy(before);after['items']['1']['kind']['props']['value']['v']['text']='NOVA'
        module.assert_preserved(before,after,{9},{},{},text_uids={9})
        after['items']['1']['kind']['props']['value']['v']['font']='Other'
        with self.assertRaisesRegex(ValueError,'non_target_changed'):module.assert_preserved(before,after,{9},{},{},text_uids={9})

    def test_duplicate_native_property_uid_cannot_mask_another_object(self):
        module=self.m.load('command_revision')
        before={'items':{'1':{'kind':{'type':'Comp','props':[{'uid':9,'value':'a'},{'uid':9,'value':'b'}]}}}}
        with self.assertRaisesRegex(ValueError,'non_target_changed'):module.assert_preserved(before,before,{9},{},{})
