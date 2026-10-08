"""受管理桌面会话版本保护：原子检查已知命令，未知变更不自动归属。"""
import importlib.util
import json
from pathlib import Path
import uuid

TOKEN_FUNCTION='''function token(){var p=app.project.__info();return {project:[p.revision,p.path,p.active,p.selection,p.items,p.dirty],editor:app.run("editor.state",{})};}'''
STABLE_FUNCTION='''function stable(v){if(v===null||typeof v!=="object")return JSON.stringify(v);if(Array.isArray(v))return "["+v.map(stable).join(",")+"]";return "{"+Object.keys(v).sort().map(function(k){return JSON.stringify(k)+":"+stable(v[k]);}).join(",")+"}";}'''

READ_ONLY_TOOLS={'list_commands','describe_command','list_effects','list_fonts','get_project','get_comp','get_layer','render_frame','ui_inspect','screenshot'}


def load(name):
    spec=importlib.util.spec_from_file_location('desktop_guard_'+name,Path(__file__).with_name(name+'.py'))
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


def literal(value):
    return json.dumps(value,ensure_ascii=True,allow_nan=False,separators=(',',':'))


def validate_token(value):
    """版本与编辑上下文必须来自完整原生查询，不接受缺字段或非有限数据。"""
    if not isinstance(value,dict) or set(value)!={'project','editor'}:raise ValueError('desktop_native_token_invalid')
    project=value['project']
    if (not isinstance(project,list) or len(project)!=6 or type(project[0]) is not int or project[0]<0
            or project[1] is not None and not isinstance(project[1],str)
            or project[2] is not None and type(project[2]) is not int
            or any(not isinstance(project[n],list) or any(type(item) is not int for item in project[n]) for n in (3,4))
            or type(project[5]) is not bool or not isinstance(value['editor'],dict)):
        raise ValueError('desktop_native_token_invalid')
    if len(literal(value))>1024*1024:raise ValueError('desktop_native_token_invalid')
    return value


def atomic_body(name,arguments):
    """只映射已核对的原生工具；其余保留原调用，不推断修改归属。"""
    if not isinstance(arguments,dict):raise ValueError('desktop_tool_arguments_invalid')
    if name=='execute_command':
        command=arguments.get('command',arguments.get('id'))
        if not isinstance(command,str) or not command:raise ValueError('desktop_tool_arguments_invalid')
        params=arguments.get('params')
        if params is None:params={}
        if isinstance(params,str):params=load('commands').reply_json(params)
        return 'return app.run('+literal(command)+','+literal(params)+');'
    if name=='open_project':
        path=arguments.get('path');demo=arguments.get('demo') is True
        if path is None and not demo and arguments.get('new') is not True:raise ValueError('desktop_tool_arguments_invalid')
        operation='app.run("file.open",'+literal({'path':path})+')' if path is not None else ('app.run("file.openDemoProject",{})' if demo else 'app.run("file.newProject",{})')
        return operation+';return app.run("project.summary",{});'
    if name=='save_project':
        path=arguments.get('path')
        operation='app.run("file.saveAs",'+literal({'path':path})+')' if path is not None else 'app.run("file.save",{})'
        return operation+';var s=app.run("project.summary",{});return {path:s.path,dirty:s.dirty};'
    if name=='run_script':
        code=arguments.get('code')
        if not isinstance(code,str):raise ValueError('desktop_tool_arguments_invalid')
        return 'return eval('+literal(code)+');'
    if name=='batch':
        if arguments.get('steps') is None:raise ValueError('desktop_tool_arguments_invalid')
        values={key:arguments[key] for key in ('steps','label','atomic') if arguments.get(key) is not None}
        if isinstance(values['steps'],str):values['steps']=load('commands').reply_json(values['steps'])
        return 'return app.run("engine.batch",'+literal(values)+');'
    return None


class Guard:
    """每个拥有的原生桌面会话单独持有基线，旧会话材料不自动接管。"""
    def __init__(self,hooks,request):
        self.hooks=hooks;self.original=request;self.path=hooks.store.path(hooks.task).parent/'desktop-revision.json';self.record=None

    def query(self):
        reply=self.original('tools/call',{'name':'run_script','arguments':{'name':'readonly managed desktop token','code':'(function(){'+TOKEN_FUNCTION+'return token();})()'}})
        result=load('commands').parse_reply(reply)
        if not isinstance(result,dict) or result.get('ok') is not True or 'result' not in result:raise ValueError('desktop_native_token_invalid')
        return validate_token(result['result'])

    def persist(self):
        load('task_store').atomic_json(self.path,self.record)

    def baseline(self):
        self.hooks.allowed();state=self.hooks.store.read(self.hooks.task)
        if self.record is None:
            if self.path.exists() or self.path.is_symlink() or state['steps']:raise ValueError('desktop_session_reconciliation_required')
            token=self.query();project=token['project']
            if project[0]!=0 or project[1] is not None or project[2] is not None or project[3] or project[4] or project[5]:raise ValueError('desktop_initial_state_conflict')
            self.record={'schema':'effectcraft-desktop-revision/v1','taskId':self.hooks.task,'identityHash':state['identityHash'],'sessionNonce':uuid.uuid4().hex,'token':token,'operationId':None}
            self.persist()
        else:
            try:
                if self.path.is_symlink() or not self.path.is_file() or self.path.stat().st_size>2*1024*1024:raise ValueError('shape')
                disk=load('commands').reply_json(self.path.read_text(encoding='utf-8'))
                if disk!=self.record or disk['identityHash']!=state['identityHash']:raise ValueError('shape')
                validate_token(disk['token'])
            except (OSError,ValueError,KeyError,TypeError):raise ValueError('desktop_revision_record_invalid') from None
        current=self.query()
        if current!=self.record['token']:raise ValueError('native_revision_conflict')
        return current

    def conflict(self,identifier,result,reason):
        """原调用已登记后出现冲突，保全实际回执，不把拒绝或未知伪装成功。"""
        load('task_store').atomic_json(self.path.parent/('desktop-conflict-'+identifier+'.json'),{
            'schema':'effectcraft-desktop-conflict/v1','taskId':self.hooks.task,'operationId':identifier,
            'sessionNonce':self.record['sessionNonce'],'expected':self.record['token'],'result':result,'reason':reason})
        raise ValueError(reason)

    def request(self,method,params):
        if method!='tools/call':return self.original(method,params)
        if not isinstance(params,dict) or not isinstance(params.get('name'),str):raise ValueError('desktop_tool_arguments_invalid')
        name=params['name'];body=atomic_body(name,params.get('arguments',{}))
        if body is None and name not in READ_ONLY_TOOLS:raise ValueError('unsupported_desktop_guard_tool: use execute_command or run_script')
        expected=self.baseline()
        identifier=self.hooks.before(name,params)
        if body is not None:
            code='(function(){'+TOKEN_FUNCTION+STABLE_FUNCTION+'var expected='+literal(expected)+';var before=token();if(stable(before)!==stable(expected))return {schema:"effectcraft-native-guard-result/v1",status:"conflict",current:before};var value=(function(){'+body+'})();if(typeof value==="undefined")value=null;return {schema:"effectcraft-native-guard-result/v1",status:"PASS",before:before,after:token(),value:value};})()'
            reply=self.original('tools/call',{'name':'run_script','arguments':{'name':'atomic managed desktop command','code':code}})
            wrapper=load('commands').parse_reply(reply)
            if not isinstance(wrapper,dict) or wrapper.get('ok') is not True:raise ValueError('desktop_native_result_invalid')
            result=wrapper.get('result')
            if not isinstance(result,dict) or result.get('schema')!='effectcraft-native-guard-result/v1':raise ValueError('desktop_native_result_invalid')
            if result.get('status')=='conflict':self.conflict(identifier,result,'native_revision_conflict')
            if result.get('status')!='PASS' or result.get('before')!=expected or 'value' not in result:raise ValueError('desktop_native_result_invalid')
            after=validate_token(result.get('after'))
            value=result['value']
            if name=='run_script':value={'ok':True,'error':None,'output':wrapper.get('output',''),'result':value}
            reply={'content':[{'type':'text','text':literal(value)}],'isError':False}
        else:
            reply=self.original(method,params);value=load('commands').parse_reply(reply,receipt_only=True);after=self.query()
            if after!=expected:self.conflict(identifier,{'actualResult':value,'current':after},'native_revision_unverified')
        self.record=dict(self.record,token=after,operationId=identifier);self.persist()
        self.hooks.after(identifier,load('commands').parse_reply(reply,receipt_only=True))
        return reply
