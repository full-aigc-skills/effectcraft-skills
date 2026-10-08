"""原子冲突证明只核对对应操作，不放行其他未知编辑。"""
import importlib.util
import json
from pathlib import Path
import unittest
import os
import hashlib
import subprocess
import sys

spec=importlib.util.spec_from_file_location('desktop_conflict_fixture',Path(__file__).with_name('test_desktop_revision_guard.py'))
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)


class DesktopConflictReconcileTests(unittest.TestCase):
    setUp=fixture.DesktopRevisionGuardTests.setUp
    guard=fixture.DesktopRevisionGuardTests.guard
    call=fixture.DesktopRevisionGuardTests.call

    def conflict(self):
        guard=self.guard();self.call(guard);self.native.race=True
        with self.assertRaisesRegex(ValueError,'native_revision_conflict'):self.call(guard)
        self.store.fail('task','conflict',unknown=True)
        state=self.store.read('task');self.operation=state['steps'][-1]
        self.proof=self.store.path('task').parent/('desktop-conflict-'+self.operation['id']+'.json')
        # 单元夹具仅替代停止材料；真实原生停止在独立 opt-in 案例核验。
        self.managed.load('task_store').atomic_json(self.store.lifecycle_path(state),{'schema':'effectcraft-process-lifecycle/v1','status':'stopped'})
        self.desktop_stop=Path(state['output'])/'desktop-session.json'
        self.managed.load('task_store').atomic_json(self.desktop_stop,{'schema':'craft-owned-desktop-session/v1','domain':'effectcraft','ownedProcessesStopped':True,'listenerOwnedByPID':True,'sessionsStarted':1})
        return guard

    def test_atomic_refusal_binds_task_arguments_and_original_baseline(self):
        guard=self.conflict();value=json.loads(self.proof.read_text())
        self.assertEqual(value['schema'],'effectcraft-desktop-conflict/v2')
        self.assertEqual(value['identityHash'],self.store.read('task')['identityHash'])
        self.assertEqual(value['argumentsHash'],self.operation['argumentsHash'])
        self.assertEqual(value['operation'],self.operation['operation'])
        self.assertEqual(value['guardSha256'],self.managed.load('task_store').file_sha(guard.path))

    def test_reconcile_reports_not_executed_without_changing_receipts_or_replaying(self):
        self.conflict();before=self.store.read('task')['steps'];calls=len(self.native.calls)
        result=self.managed.reconcile(self.store,'task')
        rows=result['reconciliation'].get('desktopOperations',[])
        self.assertEqual([row['outcome'] for row in rows],['not_executed'])
        self.assertEqual(rows[0]['operationId'],self.operation['id'])
        self.assertEqual(result['state'],'reconciling');self.assertEqual(result['steps'],before)
        self.assertEqual(len(self.native.calls),calls)
        repeat=self.managed.reconcile(self.store,'task')
        self.assertEqual(repeat['reconciliation']['desktopOperations'],rows)
        with self.assertRaisesRegex(ValueError,'reconciliation_required'):
            self.store.create('replacement',plan={},output=str(self.root/'new output'),runtime_sha='a'*64,inputs={},source=None,mode='desktop',authorization={})

    def test_mismatched_proof_binding_is_preserved_and_refused(self):
        self.conflict();original=json.loads(self.proof.read_text())
        for field,value in [('identityHash','b'*64),('argumentsHash','c'*64),('operationId','d'*32),('operation','save_project'),('sessionNonce','e'*32),('guardSha256','f'*64)]:
            with self.subTest(field=field):
                changed=dict(original);changed[field]=value;self.proof.write_text(json.dumps(changed))
                before=self.store.path('task').read_bytes()
                with self.assertRaisesRegex(ValueError,'desktop_conflict_proof_invalid'):self.managed.reconcile(self.store,'task')
                self.assertEqual(self.store.path('task').read_bytes(),before)
                self.assertEqual(json.loads(self.proof.read_text()),changed)

    def test_corrupt_or_symlink_proof_is_not_ignored(self):
        self.conflict();self.proof.write_text('{broken')
        with self.assertRaisesRegex(ValueError,'desktop_conflict_proof_invalid'):self.managed.reconcile(self.store,'task')
        self.proof.write_text('[]')
        with self.assertRaisesRegex(ValueError,'desktop_conflict_proof_invalid'):self.managed.reconcile(self.store,'task')
        self.proof.unlink();target=self.root/'foreign';target.write_text('{}');self.proof.symlink_to(target)
        with self.assertRaisesRegex(ValueError,'desktop_conflict_proof_invalid'):self.managed.reconcile(self.store,'task')
        self.assertEqual(target.read_text(),'{}')

    def test_unattached_proof_is_rejected(self):
        self.conflict();self.proof.rename(self.proof.parent/('desktop-conflict-'+'f'*32+'.json'))
        with self.assertRaisesRegex(ValueError,'desktop_conflict_proof_invalid'):self.managed.reconcile(self.store,'task')

    def test_baseline_change_or_missing_record_does_not_adopt_new_session(self):
        guard=self.conflict();baseline=guard.path.read_bytes();guard.path.write_text('{}')
        with self.assertRaisesRegex(ValueError,'desktop_conflict_proof_invalid'):self.managed.reconcile(self.store,'task')
        guard.path.write_bytes(baseline);guard.path.unlink()
        with self.assertRaisesRegex(ValueError,'desktop_conflict_proof_invalid'):self.managed.reconcile(self.store,'task')

    def test_legacy_proof_is_diagnostic_unknown_without_migration(self):
        self.conflict();value=json.loads(self.proof.read_text());value['schema']='effectcraft-desktop-conflict/v1'
        for key in ('identityHash','argumentsHash','operation','guardSha256'):value.pop(key,None)
        self.proof.write_text(json.dumps(value));before=self.proof.read_bytes()
        result=self.managed.reconcile(self.store,'task')
        self.assertEqual([row['outcome'] for row in result['reconciliation'].get('desktopOperations',[])],['unknown'])
        self.assertEqual(self.proof.read_bytes(),before)

    def test_non_atomic_observation_change_remains_unknown(self):
        guard=self.guard();self.call(guard);self.native.mutate_other=True
        with self.assertRaisesRegex(ValueError,'native_revision_unverified'):self.call(guard,'get_project',{})
        self.store.fail('task','observation changed',unknown=True)
        self.managed.load('task_store').atomic_json(self.store.lifecycle_path(self.store.read('task')),{'schema':'effectcraft-process-lifecycle/v1','status':'stopped'})
        result=self.managed.reconcile(self.store,'task')
        self.assertEqual([row['outcome'] for row in result['reconciliation'].get('desktopOperations',[])],['unknown'])

    def test_stopping_process_does_not_invent_proof_after_response_loss(self):
        self.conflict();self.proof.unlink()
        result=self.managed.reconcile(self.store,'task')
        self.assertNotIn('desktopOperations',result['reconciliation'])
        self.assertEqual(result['state'],'reconciling')

    def test_live_lifecycle_cannot_settle_an_atomic_refusal(self):
        self.conflict();self.managed.load('task_store').atomic_json(self.store.lifecycle_path(self.store.read('task')),{'schema':'effectcraft-process-lifecycle/v1','status':'running'})
        with self.assertRaisesRegex(ValueError,'process_termination_unconfirmed'):self.managed.reconcile(self.store,'task')

    def test_unconfirmed_owned_desktop_stop_keeps_operation_unknown(self):
        self.conflict();self.desktop_stop.unlink()
        result=self.managed.reconcile(self.store,'task')
        self.assertEqual(result['reconciliation']['desktopOperations'][0]['outcome'],'unknown')
        self.managed.load('task_store').atomic_json(self.desktop_stop,{'schema':'craft-owned-desktop-session/v1','domain':'effectcraft','ownedProcessesStopped':False,'listenerOwnedByPID':True,'sessionsStarted':1})
        result=self.managed.reconcile(self.store,'task')
        self.assertEqual(result['reconciliation']['desktopOperations'][0]['outcome'],'unknown')

    def test_contradictory_original_success_receipt_cannot_prove_not_executed(self):
        self.conflict();tasks=self.managed.load('task_store')
        tasks.atomic_json(self.proof.parent/'receipts'/(self.operation['id']+'.json'),{'schema':'effectcraft-step-result/v1','taskId':'task','operationId':self.operation['id'],'argumentsHash':self.operation['argumentsHash'],'result':{'comp':2}})
        with self.assertRaisesRegex(ValueError,'desktop_conflict_proof_invalid'):self.managed.reconcile(self.store,'task')

    def test_unchanged_token_is_not_an_atomic_refusal_proof(self):
        self.conflict();value=json.loads(self.proof.read_text());value['result']['current']=value['expected'];self.proof.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError,'desktop_conflict_proof_invalid'):self.managed.reconcile(self.store,'task')

    def test_redirected_desktop_output_cannot_supply_stop_evidence(self):
        self.conflict();output=self.desktop_stop.parent;other=self.root/'foreign output';output.rename(other);output.symlink_to(other,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'desktop_conflict_proof_invalid'):self.managed.reconcile(self.store,'task')


@unittest.skipUnless(os.environ.get('CRAFT_DESKTOP_CONFLICT_LIVE')=='1','explicit owned desktop conflict reconciliation opt-in')
class DesktopConflictNativeTests(unittest.TestCase):
    def test_owned_native_atomic_refusal_reconciles_without_replay(self):
        import socket
        load=fixture.load
        root=Path(os.environ['CRAFT_DESKTOP_CONFLICT_ROOT']);root.mkdir(parents=True,exist_ok=True)
        self.assertFalse(any(root.iterdir()),'preserve original tasks; select an empty root')
        cli=Path(os.environ['CRAFT_DESKTOP_REVISION_CLI']);home=Path(os.environ['CRAFT_DESKTOP_REVISION_RUNTIME_HOME'])
        lock=json.loads((fixture.HERE/'runtime.lock.json').read_text(encoding='utf-8'))
        self.assertEqual(hashlib.sha256(cli.read_bytes()).hexdigest(),lock['artifacts'][load('platform_support').platform_key()]['binarySha256'])
        desktop=load('desktop').install(json.loads((fixture.HERE/'desktop.lock.json').read_text(encoding='utf-8')),home)
        output=root/'output';output.mkdir();managed=load('managed');store=managed.load('task_store').Store(root/'state')
        binding,manifest=load('runtime_binding').prepare(fixture.HERE.parent,home)
        store.create('native',plan={'case':'atomic conflict reconciliation'},output=str(output),runtime_sha=hashlib.sha256(cli.read_bytes()).hexdigest(),inputs={},source=None,mode='desktop',authorization={},runtime_binding=binding)
        load('runtime_binding').freeze(store,'native',fixture.HERE.parent,manifest);store.start('native')
        with socket.socket() as probe:probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
        argv=load('commands').backend_argv(str(cli),output,'bridge','127.0.0.1:'+str(port))
        owned=load('desktop_session').OwnedSession(argv,desktop,'effectcraft',output,port);race=[False];foreign_hash=None
        with owned:
            with load('mcp_session').Session(argv) as foreign:
                raw=lambda name,args:load('commands').parse_reply(foreign.request('tools/call',{'name':name,'arguments':args}))
                def request(method,params):
                    if race[0] and params.get('name')=='run_script' and params['arguments'].get('name')=='atomic managed desktop command':
                        race[0]=False
                        raw('execute_command',{'command':'comp.new','params':{'name':'Foreign retained','width':96,'height':64,'duration':1,'frameRate':12}})
                        raw('save_project',{'path':str(output/'foreign.ecproj')})
                    return owned.request(method,params)
                guard=load('desktop_revision').Guard(managed.Hooks(store,'native'),request)
                call=lambda name,args:load('commands').parse_reply(guard.request('tools/call',{'name':name,'arguments':args}))
                call('execute_command',{'command':'comp.new','params':{'name':'Owner retained','width':96,'height':64,'duration':1,'frameRate':12}})
                call('save_project',{'path':str(output/'owner.ecproj')});owner_hash=hashlib.sha256((output/'owner.ecproj').read_bytes()).hexdigest()
                race[0]=True
                with self.assertRaisesRegex(ValueError,'native_revision_conflict'):call('execute_command',{'command':'comp.new','params':{'name':'Must never execute'}})
                current=raw('get_project',{});self.assertIn('Foreign retained',json.dumps(current));self.assertNotIn('Must never execute',json.dumps(current))
                foreign_hash=hashlib.sha256((output/'foreign.ecproj').read_bytes()).hexdigest()
        self.assertTrue(owned.stopped);self.assertTrue(owned.listener_verified);self.assertIsNotNone(owned.process.returncode)
        tasks=managed.load('task_store');store.fail('native','native_revision_conflict',unknown=True)
        # 所属桌面进程与桥接已真实关闭；组件夹具登记其实际退出事实，不声称完整监督器或宿主派发。
        tasks.atomic_json(output/'desktop-session.json',{'schema':'craft-owned-desktop-session/v1','domain':'effectcraft','result':'FAIL','ownedProcessesStopped':owned.stopped,'listenerOwnedByPID':owned.listener_verified,'sessionsStarted':1})
        tasks.atomic_json(store.lifecycle_path(store.read('native')),{'schema':'effectcraft-process-lifecycle/v1','status':'stopped','returncode':owned.process.returncode})
        original_steps=store.read('native')['steps'];original_receipts={p.name:p.read_bytes() for p in (store.path('native').parent/'receipts').iterdir()}
        reconciled=managed.reconcile(store,'native');self.assertEqual(reconciled['state'],'reconciling')
        self.assertEqual(reconciled['reconciliation']['desktopOperations'][0]['outcome'],'not_executed')
        self.assertEqual(reconciled['steps'],original_steps)
        self.assertEqual({p.name:p.read_bytes() for p in (store.path('native').parent/'receipts').iterdir()},original_receipts)
        self.assertEqual(hashlib.sha256((output/'owner.ecproj').read_bytes()).hexdigest(),owner_hash)
        self.assertEqual(hashlib.sha256((output/'foreign.ecproj').read_bytes()).hexdigest(),foreign_hash)
        repeat=managed.reconcile(store,'native');self.assertEqual(repeat['reconciliation']['desktopOperations'],reconciled['reconciliation']['desktopOperations'])
        for action in ('reconcile','resume'):
            process=subprocess.run([sys.executable,'-I','-B',str(fixture.HERE/'managed.py'),'--state-root',str(store.root),action,'--task','native'],capture_output=True,text=True,encoding='utf-8',timeout=60)
            actual=load('commands').reply_json(process.stdout)
            self.assertEqual(actual['state'],'reconciling',process.stderr+process.stdout)
            self.assertEqual(actual['reconciliation']['desktopOperations'],reconciled['reconciliation']['desktopOperations'])
            self.assertEqual(actual['steps'],original_steps)
        with self.assertRaisesRegex(ValueError,'reconciliation_required'):store.create('new',plan={'case':'atomic conflict reconciliation'},output=str(root/'replacement'),runtime_sha=hashlib.sha256(cli.read_bytes()).hexdigest(),inputs={},source=None,mode='desktop',authorization={})
        with load('mcp_session').Session([str(cli),'--empty','mcp']) as reopened:
            actual=load('commands').parse_reply(reopened.request('tools/call',{'name':'open_project','arguments':{'path':str(output/'foreign.ecproj')}}))
            self.assertIn('Foreign retained',json.dumps(actual));self.assertNotIn('Must never execute',json.dumps(actual))
        tasks.atomic_json(root/'result.json',{'schema':'effectcraft-desktop-conflict-native/v1','status':'PASS_COMPONENT','runtimeSha256':hashlib.sha256(cli.read_bytes()).hexdigest(),'desktopBinarySha256':desktop['binarySha256'],'cacheReused':desktop.get('reused'),'ownedProcessStopped':owned.stopped,'listenerVerified':owned.listener_verified,'steps':[s['state'] for s in original_steps],'reconciliation':reconciled['reconciliation'],'ownerProjectSha256':owner_hash,'foreignProjectSha256':foreign_hash,'projectReopened':True,'oldCommandAbsent':True,'newTaskBlocked':True,'publicReconcileResumeBound':True,'scope':'actual owned desktop and independent control-bridge mutation; component task with frozen execution and public CLI reconcile/resume; no full public run, host dispatch or physical GUI claim'})


if __name__=='__main__':unittest.main()
