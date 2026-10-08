#!/usr/bin/env python3
"""EffectCraft 单技能的受管理入口：诊断、执行、核对、评估与局部修订。"""
import argparse
import importlib.util
import json
import math
from fractions import Fraction
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent


def load(name):
    spec=importlib.util.spec_from_file_location('managed_'+name,HERE/(name+'.py'))
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value)
    return value


def read(path):
    return load('commands').reply_json(Path(path).read_text(encoding='utf-8'))


def doctor(runtime_home):
    key=load('platform_support').platform_key(); lock=read(HERE/'runtime.lock.json')
    expected=lock['artifacts'].get(key)
    result={'platform':key,'python':sys.version.split()[0],
            'runtime':{'version':lock['resolvedVersion'],'supported':bool(expected),'installed':False},
            'managedCommands':['doctor','plan','run','inspect','reconcile','resume','cancel','review','revise'],
            'acceptance':{'nativePlatform':'NOT_RUN','hostDispatch':'NOT_RUN'},
            'recovery':'run a validated plan to install pinned dependencies'}
    directory=Path(runtime_home)/'effectcraft'/lock['resolvedVersion']
    if expected and directory.exists():
        try:
            result['runtime'].update(load('bootstrap').inspect_install(directory,lock['artifact'],expected),installed=True)
        except (ValueError,OSError) as error:
            result['runtime']['error']=str(error)
    if expected:
        result['runtime']['minimumSystem']=expected.get('minimumSystem',{})
        try:load('platform_support').check_minimum(expected.get('minimumSystem',{}))
        except ValueError as error:result['runtime']['platformError']=str(error)
    return result


def preflight(plan, output, mode, inputs=None, source=None):
    inputs=inputs or {}
    if mode=='workflow':
        load('workflow').validate(plan)
    else:
        load('commands').validate(plan,inputs,'bridge' if mode=='desktop' else 'headless')
    output=Path(output).absolute()
    if output.exists() or output.is_symlink():
        raise ValueError('output_exists')
    hashes={k:load('task_store').file_sha(v) for k,v in inputs.items()}
    for name,item in plan.get('assets',{}).items():
        actual=load('task_store').file_sha(item['path'])
        if actual!=item['sha256']:raise ValueError('asset_digest_mismatch')
        hashes[name]=actual
    if source:
        manifest=read(Path(source)/'manifest.json'); project=Path(source)/'project.ecproj'
        if load('task_store').file_sha(project)!=manifest['files']['project.ecproj'] or plan.get('expectedProjectSha256')!=manifest['files']['project.ecproj']:
            raise ValueError('revision_conflict')
    return {'result':'VALID','planHash':load('task_store').digest(plan),'inputHashes':hashes,
            'mode':mode,'output':str(output),'source':str(source) if source else None}


class Hooks:
    """在真实 MCP 副作用前登记操作；合法返回后才能结算。"""
    def __init__(self, store, task):
        self.store=store;self.task=task

    def before(self, name, arguments):
        return self.store.begin_step(self.task,name,arguments)

    def after(self, identifier, result):
        self.store.finish_step(self.task,identifier,result)

    def checkpoint_export(self, identifier, context):
        load('render_recovery').capture(self.store,self.task,identifier,context)

    def allowed(self):
        with self.store.lock():self.store.allowed(self.store.read(self.task))

    def reserve_render(self, composition, plan):
        count=len(plan.get('frames',[0]))
        if plan.get('exports'):count+=math.ceil(Fraction(str(composition['frameRate']))*Fraction(str(composition['duration'])))
        binding={'composition':composition,'frames':plan.get('frames',[0]),'exports':plan.get('exports',[])}
        self.store.reserve_resources(self.task,{'frames':count,'decodedBytes':count*composition['width']*composition['height']*4},load('task_store').digest(binding))

    def observe_render(self, context):
        load('resource_meter').sample(self.store,self.task)

    def watch_render(self, stage, output):
        load('resource_meter').watch(self.store,self.task,stage,output,'workflow')

    def watch_segment(self, stage, output, part, composition):
        identity=stage.stat()
        attempt=load('task_store').digest({'path':str(stage.resolve()),'identity':[identity.st_dev,identity.st_ino]})
        count=part['frameCount']
        load('resource_budget').reserve_segment(self.store,self.task,output.name,attempt,count,
            count*composition['width']*composition['height']*4)
        load('resource_meter').watch(self.store,self.task,stage,output,'segment')

    def finish_segment(self, stage):
        load('resource_meter').sample(self.store,self.task)
        load('resource_meter').retire(self.store,self.task,stage)

    def session(self, argv):
        owner=self
        state=self.store.read(self.task)
        timeout=max(.1,min(120,state['deadline']-time.time()))
        underlying=load('mcp_session').Session(argv,timeout=timeout)
        class Wrapped:
            def __enter__(self):return self
            def __exit__(self,*args):underlying.close()
            def request(self,method,params):
                if method!='tools/call':return underlying.request(method,params)
                identifier=owner.before(params.get('name',method),params)
                result=underlying.request(method,params)
                # 使用真实返回解析器；畸形/错误回复保持 attempted，不误记成功。
                parsed=load('commands').parse_reply(result)
                owner.after(identifier,parsed)
                return result
        return Wrapped()


def worker(store, task, runtime_home):
    state=store.read(task)
    with load('platform_support').exclusive_lock(store.root/'leases'/(task+'.lock'),timeout=0):
        recovering=state['state']=='resuming'
        store.start(task); hooks=Hooks(store,task)
        try:
            request=read(store.path(task).parent/'request.json')
            if load('task_store').digest(request)!=state['identity']['authorization'].get('requestHash'):
                raise ValueError('request_changed')
            plan=state['plan'];output=Path(state['output'])
            if recovering:
                context=load('render_recovery').validate(store,store.read(task))
                load('workflow').validate(plan)
                hashes={name:load('task_store').file_sha(path) for name,path in request['inputs'].items()}
                hashes.update({name:load('task_store').file_sha(asset['path']) for name,asset in plan.get('assets',{}).items()})
                current={'inputHashes':hashes}
            else:
                current=preflight(plan,output,state['identity']['mode'],request['inputs'],request.get('source'))
            if current['inputHashes']!=state['identity']['inputHashes']:
                raise ValueError('input_changed')
            key=load('platform_support').platform_key()
            if read(HERE/'runtime.lock.json')['artifacts'][key]['binarySha256']!=state['identity']['runtimeSha256']:
                raise ValueError('runtime_changed; original task must keep its locked runtime')
            output.parent.mkdir(parents=True,exist_ok=True)
            if state['identity']['mode']=='workflow':
                if recovering:
                    with load('output_guard').resume_claim(output,context['executionIdentity'],context['outputIdentity']):
                        load('render_recovery').archive_failure(store,task,context)
                        result=load('workflow').finish_export(context,hooks,state['renderRecovery']['operationId'])
                else:
                    result=load('workflow').execute(plan,output,runtime_home,request.get('source'),task_hooks=hooks)
                proof={'manifestSha256':load('task_store').file_sha(output/'manifest.json'),
                       'projectSha256':load('task_store').file_sha(output/'project.ecproj'),'engineeringReopen':'PASS'}
            elif state['identity']['mode']=='commands':
                result=load('commands').execute(plan,output,runtime_home,session_factory=hooks.session,inputs=request['inputs'])
                if result['result']!='PASS':raise RuntimeError(result.get('error','native_command_failed'))
                proof={'receiptSha256':load('task_store').file_sha(output/'success.json'),'engineeringReopen':'NOT_RUN'}
            else:
                result=load('desktop_session').run(plan,output,runtime_home,request['inputs'],task_hooks=hooks)
                if result['result']!='PASS':raise RuntimeError(result.get('error','desktop_command_failed'))
                proof={'receiptSha256':load('task_store').file_sha(output/'success.json'),'engineeringReopen':'NOT_RUN'}
            store.delivered(task,proof)
        except BaseException as error:
            store.fail(task,str(error),unknown=bool(store.read(task)['steps']))
            raise


def supervise(store, task, runtime_home, recover=False):
    """监督通道断开由独立守护器清理整个自有进程树，核实后才结算。"""
    platform=load('platform_support')
    with platform.exclusive_lock(store.root/'leases'/(task+'.supervisor.lock'),timeout=0):
        with platform.exclusive_lock(store.root/'leases'/(task+'.lifecycle.lock'),timeout=0):
            state=store.read(task)
            if recover:
                with store.lock():
                    state=store.read(task);store.allowed(state)
                    if (state['state']!='reconciling' or state.get('reconciliation',{}).get('result')!='render_resume_ready'
                            or state.get('termination',{}).get('status')=='confirmed'):
                        raise ValueError('reconciliation_required')
                    previous=store.lifecycle_path(state)
                    if read(previous).get('status')!='stopped':raise ValueError('process_termination_unconfirmed')
                    load('render_recovery').validate(store,state)
                    state=load('orphan_segments').archive_locked(store,task)
                    load('render_recovery').validate(store,state)
                    history=state.setdefault('renderResumes',[])
                    if len(history)>=9999:raise ValueError('render_resume_budget_exceeded')
                    history.append({'at':time.time(),'lifecycleReceipt':previous.name,'sha256':load('task_store').file_sha(previous)})
                    state['state']='resuming';state['lifecycleReceipt']='lifecycle-resume-'+format(len(history),'04d')+'.json'
                    store.save(state)
            elif state['state']!='planned' or state['steps']:
                raise ValueError('reconciliation_required')
        receipt=store.lifecycle_path(state)
        args=[sys.executable,'-I','-B',str(HERE/'process_guard.py'),'--receipt',str(receipt),
              '--lease',str(store.root/'leases'/(task+'.lifecycle.lock')),'--',
              sys.executable,'-I','-B',str(Path(__file__).resolve()),'--state-root',str(store.root),
              '--runtime-home',str(runtime_home),'_worker','--task',task]
        options={'start_new_session':True} if os.name!='nt' else {'creationflags':subprocess.CREATE_NEW_PROCESS_GROUP}
        with (store.path(task).parent/'worker.log').open('ab') as log:
            child=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=log,stderr=log,**options)
            cancellation=False;stop_reason=None;next_sample=0
            try:
                while child.poll() is None:
                    try:
                        with store.lock():
                            if time.monotonic()>=next_sample:
                                load('resource_meter').sample_locked(store,task,live=True);next_sample=time.monotonic()+1
                            store.allowed(store.read(task))
                    except ValueError as error:
                        # 原生调用阻塞时也检查完整祖先链；停止意图先落盘，再关闭守护通道。
                        cancellation=True;stop_reason=str(error);store.cancel(task)
                        child.stdin.close();child.wait(timeout=25);break
                    time.sleep(.1)
            except BaseException:
                store.cancel(task);child.stdin.close()
                try:child.wait(timeout=25)
                finally:store.fail(task,'supervisor interrupted; inspect lifecycle receipt',unknown=True)
                raise
            finally:
                if not child.stdin.closed:child.stdin.close()
        lifecycle=read(receipt)
        if lifecycle.get('schema')!='effectcraft-process-lifecycle/v1' or lifecycle.get('status')!='stopped':
            return store.fail(task,'owned process tree termination is unconfirmed',unknown=True)
        try:load('resource_meter').sample(store,task)
        except (ValueError,OSError) as error:return store.fail(task,'resource observation unconfirmed: '+str(error),unknown=True)
        if cancellation:store.stopped(task,'owned process tree verified stopped: '+stop_reason)
        return store.worker_exited(task,lifecycle['returncode'])


def run(store, plan, output, runtime_home, mode='workflow', inputs=None, source=None, task=None, parent=None):
    inputs=inputs or {};check=preflight(plan,output,mode,inputs,source)
    if source and not parent:
        for prior in store.all():
            if Path(prior['output']).resolve()==Path(source).resolve():
                raise ValueError('managed_source_requires_revise: '+prior['taskId'])
    key=load('platform_support').platform_key();lock=read(HERE/'runtime.lock.json')
    if key not in lock['artifacts']:raise ValueError('unsupported_platform: '+key)
    task=task or uuid.uuid4().hex
    request={'inputs':inputs,'source':str(source) if source else None}
    store.create(task,plan=plan,output=str(output),runtime_sha=lock['artifacts'][key]['binarySha256'],
                 inputs=check['inputHashes'],source=str(Path(source)/'project.ecproj') if source else None,
                 mode=mode,authorization={'writeRoot':str(Path(output).absolute()),'inputs':inputs,
                 'requestHash':load('task_store').digest(request)},parent=parent)
    load('task_store').atomic_json(store.path(task).parent/'request.json',request)
    return supervise(store,task,runtime_home)


def reconcile(store, task):
    """只核对完整已落盘交付；无法证明的部分编辑继续保持 reconciling。"""
    with load('platform_support').exclusive_lock(store.root/'leases'/(task+'.lifecycle.lock'),timeout=0), load('platform_support').exclusive_lock(store.root/'leases'/(task+'.lock'),timeout=0):
        with store.lock():
            state=store.read(task)
            if state['state'] not in ('running','resuming','reconciling','cancel_requested'):
                return state
            lifecycle_path=store.lifecycle_path(state)
            if lifecycle_path.exists():
                lifecycle=read(lifecycle_path)
                if lifecycle.get('schema')!='effectcraft-process-lifecycle/v1' or lifecycle.get('status')!='stopped':
                    raise ValueError('process_termination_unconfirmed')
            elif state.get('worker'):
                raise ValueError('legacy_process_ownership_unknown')
            state=load('orphan_segments').settle_locked(store,task)
            state=load('resource_meter').sample_locked(store,task)
            state['state']='reconciling'
            state['reconciliation']={'result':'unknown','automaticReplay':False,
                'requiredAction':'inspect original project, native process and receipts; partial edits cannot be resent'}
            if state.get('delivery') and not any(s['state']=='attempted' for s in state['steps']):
                report=load('quality_review').inspect_delivery(state['output'])
                if report['technical']['status']=='PASS' and report.get('binding',{}).get('manifestSha256')==state['delivery'].get('manifestSha256'):
                    state['state']='review_ready';state['reconciliation']['result']='verified_delivery'
            if state['state']=='reconciling' and state.get('renderRecovery'):
                load('render_recovery').validate(store,state)
                if (state['steps'][-1]['state']=='attempted' and not state.get('cancellationRequestedAt')
                        and state.get('termination',{}).get('status')!='confirmed'):
                    state['reconciliation']={'result':'render_resume_ready','automaticReplay':False,
                        'requiredAction':'resume only original segmented export; no editing calls'}
            return store.save(state)


def review(store, task, criteria, judge=None):
    quality=load('quality_review');state=store.read(task);directory=store.path(task).parent
    report=quality.inspect_delivery(state['output'])
    if state.get('delivery',{}).get('engineeringReopen')=='PASS' and report.get('binding',{}).get('manifestSha256')==state['delivery'].get('manifestSha256'):
        report['engineering']={'status':'PASS','source':'current managed workflow save/reopen'}
    if judge:
        request=read(directory/'judge-request.json')
        if request['criteriaHash']!=load('task_store').digest(criteria):raise ValueError('criteria_changed')
        report=quality.accept_judge(state['output'],report,request,read(judge))
    else:
        native=read(Path(state['output'])/'native.json')
        temporal=bool(read(Path(state['output'])/'manifest.json').get('video') or native['composition'].get('duration',0)>0)
        request=quality.judge_request(task,state['output'],report,criteria,temporal)
        load('task_store').atomic_json(directory/'judge-request.json',request)
    load('task_store').atomic_json(directory/'quality.json',report)
    with store.lock():
        state=store.read(task);state['review']={'path':'quality.json','sha256':load('task_store').file_sha(directory/'quality.json')}
        store.save(state)
        if judge:
            root=store.lineage(state)[-1]
            seen=root.setdefault('reviewedRequests',[])
            if request['requestId'] not in seen:
                seen.append(request['requestId'])
                score=report['creative']['receipt']['score']
                if score>root.get('bestScore',-1):
                    root['bestScore']=score;root['bestTask']=task;root['budget']['stagnant']=0
                else:root['budget']['stagnant']+=1
                store.save(root)
    return {'report':report,'judgeRequest':request,'requiredAction':None if judge else 'host_visual_review'}


def main():
    # 固定重定向输出编码，Windows默认代码页也能返回中文帮助和回执。
    import sys
    for stream in (sys.stdout,sys.stderr):
        if hasattr(stream,"reconfigure"):stream.reconfigure(encoding="utf-8")
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-home',type=Path,default=Path(os.environ.get('CRAFT_RUNTIME_HOME',str(Path.home()/'.local/share/craft-runtimes'))))
    parser.add_argument('--state-root',type=Path,default=Path(os.environ.get('CRAFT_STATE_HOME',str(Path.home()/'.local/share/craft-tasks/effectcraft'))))
    sub=parser.add_subparsers(dest='action',required=True)
    sub.add_parser('doctor')
    for name in ('plan','run','revise'):
        p=sub.add_parser(name);p.add_argument('--plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
        p.add_argument('--mode',choices=['workflow','commands','desktop'],default='workflow');p.add_argument('--input',action='append',default=[])
        p.add_argument('--source',type=Path);p.add_argument('--task')
    for name in ('inspect','reconcile','resume','cancel','_worker','review'):
        p=sub.add_parser(name);p.add_argument('--task',required=True)
        if name=='review':p.add_argument('--criteria',type=Path,required=True);p.add_argument('--judge',type=Path)
    args=parser.parse_args();store=load('task_store').Store(args.state_root)
    try:
        if args.action=='doctor':result=doctor(args.runtime_home)
        elif args.action=='inspect':result=store.read(args.task)
        elif args.action=='cancel':result=store.cancel(args.task)
        elif args.action=='reconcile':result=reconcile(store,args.task)
        elif args.action=='resume':
            state=store.read(args.task)
            if state['state']=='planned' and not state['steps']:
                result=supervise(store,args.task,args.runtime_home)
            else:
                result=reconcile(store,args.task)
                if result.get('state')=='reconciling' and result.get('reconciliation',{}).get('result')=='render_resume_ready':
                    result=supervise(store,args.task,args.runtime_home,recover=True)
        elif args.action=='review':result=review(store,args.task,read(args.criteria),args.judge)
        elif args.action=='_worker':worker(store,args.task,args.runtime_home);return
        else:
            inputs={}
            for item in args.input:
                name,sep,value=item.partition('=')
                if not sep or name in inputs:raise ValueError('invalid_input')
                inputs[name]=str(Path(value).absolute())
            plan=read(args.plan)
            if args.action=='plan':result=preflight(plan,args.output,args.mode,inputs,args.source)
            elif args.action=='revise':result=load('revision').revise(store,args.task,plan,args.output,args.runtime_home)
            else:result=run(store,plan,args.output,args.runtime_home,args.mode,inputs,args.source,args.task)
        print(json.dumps(result,ensure_ascii=False,allow_nan=False))
        if result.get('state') in ('failed','reconciling','cancel_requested'):raise SystemExit(1)
    except (ValueError,OSError,KeyError,TypeError,subprocess.SubprocessError) as error:
        print(json.dumps({'result':'FAIL','error':str(error)},ensure_ascii=False));raise SystemExit(1)


if __name__=='__main__':main()
