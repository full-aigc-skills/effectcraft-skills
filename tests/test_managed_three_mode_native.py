"""公开受管理三模式与真实适配器的组合验收；显式启用后才启动原生桌面。"""
import hashlib
import json
import os
import platform
import sys
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def inventory(root):
    return {p.relative_to(root).as_posix():sha(p) for p in root.rglob('*')
            if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}

@unittest.skipUnless(os.environ.get('CRAFT_MANAGED_THREE_MODE_LIVE')=='1','explicit native desktop opt-in')
@unittest.skipUnless(sys.platform=='darwin' and platform.machine()=='arm64','macOS arm64 native acceptance case')
class ManagedThreeModeNativeTests(unittest.TestCase):
    def test_workflow_public_composition(self):self.exercise('workflow')
    def test_commands_public_composition(self):self.exercise('commands')
    def test_desktop_public_composition(self):self.exercise('desktop')
    def exercise(self, selected_mode):
        base=Path(os.environ.get('CRAFT_MANAGED_COMPOSITION_ROOT') or tempfile.mkdtemp(prefix='effectcraft three modes '))
        root=base/selected_mode
        root.mkdir(parents=True,exist_ok=True)
        self.assertFalse(any(root.iterdir()),'preserve previous acceptance tasks; use a fresh test root')
        skill=root/'only readonly skill'
        shutil.copytree(ROOT/'skills/effectcraft-use',skill,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        for p in skill.rglob('*'):p.chmod(0o555 if p.is_dir() else 0o444)
        skill.chmod(0o555);original=inventory(skill)
        runtime=Path(os.environ.get('CRAFT_MANAGED_COMPOSITION_RUNTIME_HOME') or base/'native runtime');env=dict(os.environ,CRAFT_RUNTIME_HOME=str(runtime),PATH='/opt/homebrew/bin:/usr/bin:/bin')
        self.native_before=runtime.exists()
        self.assertIn('CRAFT_PYTHON_HOME',env,'verified isolated interpreter cache required')
        criteria=root/'criteria.json';criteria.write_text(json.dumps({'goal':'Technical interface composition; no creative acceptance claim'}))
        logs=[]
        def invoke(mode,action,*args,ok=True):
            argv=['/bin/sh',str(skill/'scripts/launch.sh'),'--state-root',str(root/mode/'state'),action,*map(str,args)]
            r=subprocess.run(argv,cwd=root,env=env,capture_output=True,timeout=420)
            label=f'{mode}-{len(logs):03d}-{action}';logs.append(label)
            (root/(label+'.stdout')).write_bytes(r.stdout);(root/(label+'.stderr')).write_bytes(r.stderr)
            if ok:self.assertEqual(r.returncode,0,r.stdout.decode(errors='replace')+r.stderr.decode(errors='replace'))
            else:self.assertNotEqual(r.returncode,0,r.stdout.decode(errors='replace'))
            return json.loads(r.stdout)
        command={'schema':'craft-command-plan/v1','operations':[
            {'command':'comp.new','params':{'name':'Actual adapter','width':96,'height':64,'duration':1,'frameRate':12},'as':'comp'},
            {'command':'layer.newShape','params':{'kind':'rect','name':'Subject','size':[40,40],'position':[32,32],'fill':'#ff0000'},'as':'subject'},
            {'tool':'get_layer','params':{'layer':{'$ref':'subject.layer'}},'as':'actualLayer'},
            {'tool':'save_project','params':{'path':{'$output':'project.ecproj'}}},
            {'tool':'render_frame','params':{'time':0.5,'max_side':96,'transparent':True,'inline':False,'path':{'$output':'preview.png'}}},
            {'tool':'open_project','params':{'path':{'$output':'project.ecproj'}}},
            {'tool':'get_comp','params':{}}]}
        cases=[]
        for mode in (selected_mode,):
            case=root/mode;case.mkdir();plan=json.loads((skill/'examples/brand-intro.json').read_text()) if mode=='workflow' else json.loads(json.dumps(command))
            if mode=='desktop':plan['operations'].append({'tool':'ui_inspect','params':{}})
            planfile=case/'plan.json';planfile.write_text(json.dumps(plan));out=case/'delivery';state=case/'state'
            checked=invoke(mode,'plan','--mode',mode,'--plan',planfile,'--output',out)
            self.assertEqual(checked['result'],'VALID');self.assertFalse(state.exists());self.assertFalse(out.exists())
            task='successful';run=invoke(mode,'run','--mode',mode,'--task',task,'--plan',planfile,'--output',out)
            self.assertEqual(run['state'],'review_ready',run);self.assertEqual(run['identity']['planHash'],checked['planHash'])
            self.assertEqual(run['identity']['mode'],mode);self.assertTrue(run['steps']);self.assertTrue(all(s['state']=='succeeded' for s in run['steps']))
            taskdir=state/'tasks'/task;receipts=taskdir/'receipts';self.assertEqual(len(list(receipts.glob('*.json'))),len(run['steps']))
            for step in run['steps']:
                receipt=json.loads((receipts/(step['id']+'.json')).read_text())
                self.assertEqual(receipt['taskId'],task);self.assertEqual(receipt['argumentsHash'],step['argumentsHash']);self.assertEqual(receipt['schema'],'effectcraft-step-result/v1')
            before=inventory(taskdir);delivery=inventory(out)
            for action in ('inspect','reconcile','resume'):
                result=invoke(mode,action,'--task',task);self.assertEqual(result['identityHash'],run['identityHash'])
            self.assertEqual(inventory(taskdir),before);self.assertEqual(inventory(out),delivery)
            review=invoke(mode,'review','--task',task,'--criteria',criteria)
            self.assertEqual(review['report']['engineering']['status'],'PASS',review)
            self.assertEqual(review['report']['technical']['status'],'PASS',review)
            self.assertEqual(review['report']['creative']['status'],'NOT_RUN')
            native_receipt=None;desktop=None
            if mode!='workflow':
                native_receipt=json.loads((out/'success.json').read_text());self.assertEqual(native_receipt['result'],'PASS')
                actual=native_receipt['steps'][2]['result'];self.assertIsInstance(actual,dict);self.assertEqual(actual['name'],'Subject')
                reopened=native_receipt['steps'][6]['result'];self.assertEqual(reopened['width'],96);self.assertEqual(reopened['height'],64)
                if mode=='desktop':
                    desktop=json.loads((out/'desktop-session.json').read_text());self.assertTrue(desktop['ownedProcessesStopped']);self.assertTrue(desktop['listenerOwnedByPID']);self.assertEqual(desktop['sessionsStarted'],1)
                    self.assertIsInstance(native_receipt['steps'][-1]['result'],dict)
                # 保存后真实适配器返回错误：原编辑保持未知，reconcile/resume不得重新发送。
                bad=json.loads(json.dumps(plan));bad['operations'].append({'tool':'get_layer','params':{'layer':2147483647}})
                badfile=case/'invalid-native-object.json';badfile.write_text(json.dumps(bad));failedout=case/'failed delivery'
                failed=invoke(mode,'run','--mode',mode,'--task','unknown','--plan',badfile,'--output',failedout,ok=False)
                self.assertEqual(failed['state'],'reconciling',failed);self.assertTrue((failedout/'project.ecproj').is_file())
                failedtask=state/'tasks/unknown';unknownsteps=json.loads((failedtask/'state.json').read_text())['steps']
                self.assertTrue(any(s['state']=='attempted' for s in unknownsteps))
                originals=inventory(failedout);originalreceipts=inventory(failedtask/'receipts')
                for action in ('reconcile','resume'):
                    recovered=invoke(mode,action,'--task','unknown',ok=False);self.assertEqual(recovered['state'],'reconciling')
                    self.assertEqual(recovered['steps'],unknownsteps)
                self.assertEqual(inventory(failedout),originals);self.assertEqual(inventory(failedtask/'receipts'),originalreceipts)
                refused=invoke(mode,'run','--mode',mode,'--task','bypass','--plan',badfile,'--output',case/'new output',ok=False)
                self.assertIn('reconciliation_required',refused['error']);self.assertFalse((case/'new output').exists())
            cases.append({'mode':mode,'status':'PASS','taskIdentityHash':run['identityHash'],'operations':len(run['steps']),'projectSha256':sha(out/'project.ecproj'),'engineering':'PASS','technical':'PASS','creative':'NOT_RUN','publicRecoveryNoReplay':True,'adapter':native_receipt,'desktop':desktop,'unknownNativeErrorNoReplay':mode!='workflow'})
            self.assertEqual(inventory(skill),original)
        raw=subprocess.run([os.environ['CRAFT_TEST_ISOLATED_PYTHON'],'-I','-B',str(skill/'scripts/cli.py'),'--runtime-home',str(runtime),'--','--version'],env=env,capture_output=True,timeout=60)
        self.assertEqual(raw.returncode,0,raw.stdout+raw.stderr);self.assertIn(b'0.4.0',raw.stdout)
        report={'schema':'effectcraft-managed-three-mode-native/v1','status':'PASS','platform':'darwin-arm64','installedFiles':original,'cases':cases,'rawCLICompatible':True,'installedFilesUnchanged':inventory(skill)==original,'pythonPreparation':'verified isolated cache reused','nativePreparation':'official pinned installer; per-case cold/reuse recorded by shared acceptance cache','desktopPreparation':'signed official pinned installer','testSha256':sha(Path(__file__)),'fullV1':'NOT_RUN','hostDispatch':'NOT_RUN'}
        report['nativeCacheBeforeCase']=getattr(self,'native_before',None)
        (root/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
