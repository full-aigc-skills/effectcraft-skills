"""真实worker在完成包后、账本交付前强杀；复制包跨账本不得重做。"""
import copy
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import tempfile
import unittest
from test_workflow_artifact_lineage_native import ROOT,load,files,sha

@unittest.skipUnless(os.environ.get('CRAFT_SOURCE_PRODUCER_LIVE')=='1','explicit source producer crash native opt-in')
@unittest.skipUnless(platform.system()=='Darwin' and platform.machine()=='arm64','macOS arm64 native acceptance')
class SourceProducerNativeTests(unittest.TestCase):
    def test_unknown_copy_is_refused_and_confirmed_cross_store_revision_succeeds(self):
        root=Path(os.environ.get('CRAFT_SOURCE_PRODUCER_ROOT') or tempfile.mkdtemp(prefix='source producer native '));root.mkdir(parents=True,exist_ok=True)
        self.assertFalse(any(root.iterdir()),'preserve prior native evidence')
        skill=root/'single readonly skill';shutil.copytree(ROOT/'skills/effectcraft-use',skill,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        for p in skill.rglob('*'):p.chmod(0o555 if p.is_dir() else 0o444)
        skill.chmod(0o555);installed=files(skill)
        env=dict(os.environ,HOME=str(root/'private user'),CRAFT_RUNTIME_HOME=os.environ['CRAFT_SOURCE_PRODUCER_RUNTIME_HOME'],PATH='/opt/homebrew/bin:/usr/bin:/bin')
        home=Path(env['HOME']);home.mkdir()
        managed=load(skill/'scripts/managed.py');tasks=managed.load('task_store');store=tasks.Store(root/'original state');output=root/'unconfirmed delivery';task='interrupted'
        runtime=Path(env['CRAFT_RUNTIME_HOME']);plan={'document':{'name':'Unknown producer','width':64,'height':48,'frameRate':2,'duration':1},
            'operations':[{'command':'layer.newShape','params':{'kind':'rect','name':'Subject','size':[24,24],'position':[32,24],'fill':'#ff6600'},'as':'subject'}],'frames':[0]}
        # 验收登记与冻结不写假运行或终态；真实worker由原guard持有。
        oldenv=dict(os.environ);os.environ.update(env)
        try:
            binding,snapshot=managed.load('runtime_binding').prepare(skill,runtime)
            key=managed.load('platform_support').platform_key();lock=managed.read(skill/'scripts/runtime.lock.json')
            request={'inputs':{},'source':None};initial=store.create(task,plan=plan,output=str(output),runtime_sha=lock['artifacts'][key]['binarySha256'],inputs={},source=None,mode='workflow',authorization={'writeRoot':str(output),'requestHash':tasks.digest(request)},runtime_binding=binding)
            tasks.atomic_json(store.path(task).parent/'request.json',request);managed.load('runtime_binding').freeze(store,task,skill,snapshot);bound=managed.load('runtime_binding').resolve(store,task)
        finally:os.environ.clear();os.environ.update(oldenv)
        driver=root/'fault worker.py';driver.write_text('''import importlib.util,os,signal,sys
from pathlib import Path
s=importlib.util.spec_from_file_location("bound_producer",sys.argv[1]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
t=m.load("task_store")
def crash(self,task,manifest):os.kill(os.getpid(),signal.SIGKILL)
t.Store.delivered=crash;original=m.load;m.load=lambda n:t if n=="task_store" else original(n)
m.worker(t.Store(sys.argv[2]),"interrupted",sys.argv[3])
''')
        lifecycle=store.lifecycle_path(initial)
        with (root/'guard.log').open('wb') as log:
            guard=subprocess.Popen([bound['python'],'-I','-B',bound['guard'],'--receipt',str(lifecycle),'--lease',str(store.root/'leases'/(task+'.lifecycle.lock')),'--',bound['python'],'-I','-B',str(driver),bound['script'],str(store.root),bound['runtimeHome']],env=env,stdin=subprocess.PIPE,stdout=log,stderr=log,start_new_session=True)
            try:guard.wait(timeout=240)
            finally:
                if guard.poll() is None:guard.stdin.close();guard.wait(timeout=25)
                if not guard.stdin.closed:guard.stdin.close()
        stopped=managed.read(lifecycle);self.assertEqual(stopped['status'],'stopped');self.assertEqual(stopped['ownership']['workerReturncode'],-signal.SIGKILL)
        original=store.read(task);self.assertEqual(original['state'],'running');self.assertIsNone(original['delivery']);self.assertTrue(original['steps']);self.assertTrue(all(x['state']=='succeeded' for x in original['steps']))
        before=files(output);receipts=files(store.path(task).parent/'receipts');unknowncopy=root/'copied unknown source';shutil.copytree(output,unknowncopy)
        self.assertNotEqual((output/'project.ecproj').stat().st_ino,(unknowncopy/'project.ecproj').stat().st_ino)
        change={'expectedProjectSha256':sha(unknowncopy/'project.ecproj'),'operations':[{'command':'prop.set','params':{'layer':{'$ref':'subject.layer'},'path':'transform/opacity','value':50}}],'frames':[0]}
        changefile=root/'change.json';changefile.write_text(json.dumps(change));actions=[]
        def public(state,action,*args,ok=True):
            result=subprocess.run(['/bin/sh',str(skill/'scripts/launch.sh'),'--state-root',str(state),action,*map(str,args)],env=env,cwd=root,capture_output=True,timeout=240)
            label=str(len(actions))+'-'+action;(root/(label+'.stdout')).write_bytes(result.stdout);(root/(label+'.stderr')).write_bytes(result.stderr)
            self.assertEqual(result.returncode==0,ok,result.stdout.decode(errors='replace')+result.stderr.decode(errors='replace'))
            value=json.loads(result.stdout);actions.append({'action':action,'returncode':result.returncode,'error':value.get('error')});return value
        other=root/'other state'
        for action in ('plan','run'):
            args=['--plan',changefile,'--source',unknowncopy,'--output',root/'forbidden new output']
            if action=='run':args+=['--task','new-id']
            rejected=public(other,action,*args,ok=False);self.assertIn('source_producer',rejected['error'])
            self.assertFalse((other/'tasks').exists());self.assertFalse((root/'forbidden new output').exists())
        for action in ('reconcile','resume'):
            state=public(store.root,action,'--task',task,ok=False);self.assertEqual(state['state'],'reconciling');self.assertEqual(state['reconciliation']['result'],'unknown')
            self.assertEqual(state['steps'],original['steps']);self.assertEqual(state['deadline'],original['deadline']);self.assertEqual(state['budget'],original['budget'])
            self.assertEqual(files(output),before);self.assertEqual(files(store.path(task).parent/'receipts'),receipts)
        engineering=managed.load('engineering_review').verify(output,runtime,original['identity']['runtimeSha256']);self.assertEqual(engineering['status'],'PASS',engineering)
        report=managed.load('quality_review').inspect_delivery(output);self.assertEqual(report['technical']['status'],'PASS')
        goodplan=copy.deepcopy(plan);goodplan['document']['name']='Confirmed producer';planfile=root/'good plan.json';planfile.write_text(json.dumps(goodplan));good=root/'confirmed delivery'
        self.assertEqual(public(other,'run','--task','confirmed','--plan',planfile,'--output',good)['state'],'review_ready')
        criteria=root/'criteria.json';criteria.write_text(json.dumps({'goal':'Technical copied-source and conflict protection'}))
        confirmed_review=public(other,'review','--task','confirmed','--criteria',criteria)['report']
        self.assertEqual(confirmed_review['engineering']['status'],'PASS');self.assertEqual(confirmed_review['technical']['status'],'PASS')
        moved=root/'moved confirmed source';good.rename(moved);change['expectedProjectSha256']=sha(moved/'project.ecproj');changefile.write_text(json.dumps(change));third=root/'third state';revised=root/'revised delivery'
        checked=public(third,'plan','--plan',changefile,'--source',moved,'--output',revised);self.assertEqual(checked['sourceProducer']['owner']['taskId'],'confirmed')
        child=public(third,'run','--task','revision','--plan',changefile,'--source',moved,'--output',revised);self.assertEqual(child['state'],'review_ready');self.assertEqual(child['identity']['authorization']['sourceProducer'],checked['sourceProducer'])
        for ledger,taskid in ((third,'revision'),):
            result=public(ledger,'review','--task',taskid,'--criteria',criteria)['report'];self.assertEqual(result['engineering']['status'],'PASS');self.assertEqual(result['technical']['status'],'PASS')
        parent=managed.read(moved/'manifest.json');current=managed.read(revised/'manifest.json')
        self.assertEqual(current['artifact']['assetId'],parent['artifact']['assetId']);self.assertEqual(current['artifact']['sourceRefs'][0]['version'],parent['artifact']['version'])
        self.assertNotEqual(sha(moved/parent['frames'][0]['path']),sha(revised/current['frames'][0]['path']))
        self.assertEqual(files(skill),installed);self.assertEqual(managed.load('runtime_binding').source_files(Path(bound['script']).parent.parent),snapshot)
        self.assertEqual(files(output),before);self.assertEqual(files(unknowncopy),before)
        proof={'schema':'effectcraft-native-source-producer-guard/v1','status':'PASS_COMPONENT','sourceSkillFiles':installed,'testSha256':sha(Path(__file__)),'driverSha256':sha(driver),'runtimeSha256':initial['identity']['runtimeSha256'],'python':binding['python']['version'],'pythonMode':binding['python']['mode'],'cacheReused':True,'platform':'darwin-arm64','originalWorkerReturncode':stopped['ownership']['workerReturncode'],'originalLifecycleSha256':sha(lifecycle),'originalLedgerNotForged':True,'completeNativeOutputs':before,'copyHasDifferentInode':True,'unknownCopyRejectedBeforeRegistration':True,'originalRemainsUnknownWithoutReplay':True,'originalOutputsAndReceiptsPreserved':True,'nativeEngineering':'PASS','nativeTechnical':'PASS','confirmedMovedCrossStoreRevision':'PASS','sourceProducerAuthorizationBound':True,'publicLineageAndPixelChangeVerified':True,'installedAndFrozenResourcesPreserved':True,'actions':actions,'hostDispatch':'NOT_RUN','fullV1':'NOT_RUN'}
        (root/'result.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
