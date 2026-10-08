"""用户级工程认领：跨账本保留占用；缺失或未知原任务不得转交写入权。"""
from contextlib import contextmanager
import importlib.util
import os
from pathlib import Path
import re
import uuid


def load(name):
    spec=importlib.util.spec_from_file_location('project_claim_'+name,Path(__file__).with_name(name+'.py'))
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


def root():
    """工程协调位置不随state-root变化，不能靠新账本绕过已认领工程。"""
    return Path.home()/'.local/share/craft-tasks/effectcraft-project-claims'


def keys(source):
    """同时绑定规范路径和文件对象，覆盖原位替换及硬链接别名。"""
    path=Path(source).resolve();info=path.stat();tasks=load('task_store')
    if not info.st_ino:raise ValueError('project_source_identity_unavailable')
    return sorted([tasks.digest({'path':os.path.normcase(str(path))}),
                   tasks.digest({'device':info.st_dev,'inode':info.st_ino})])


def read_claim(key):
    if not isinstance(key,str) or not re.fullmatch('[a-f0-9]{64}',key):raise ValueError('project_claim_invalid')
    path=root()/(key+'.json')
    try:
        if root().is_symlink():raise ValueError('shape')
        if path.is_symlink() or not path.is_file() or path.stat().st_size>1024*1024:raise ValueError('shape')
        value=load('commands').reply_json(path.read_text(encoding='utf-8'))
        if (not isinstance(value,dict) or set(value)!={'schema','key','owner','nonce'}
                or value['schema']!='effectcraft-project-claim/v1' or value['key']!=key
                or not isinstance(value['owner'],dict) or set(value['owner'])!={'stateRoot','taskId','identityHash'}
                or not isinstance(value['owner']['stateRoot'],str) or not Path(value['owner']['stateRoot']).is_absolute()
                or not isinstance(value['owner']['identityHash'],str) or not re.fullmatch('[a-f0-9]{64}',value['owner']['identityHash'])
                or not isinstance(value['nonce'],str) or not re.fullmatch('[a-f0-9]{32}',value['nonce'])):raise ValueError('shape')
        return value
    except (OSError,ValueError,TypeError,KeyError):raise ValueError('project_claim_invalid') from None


def owner_identity(store,state):
    return {'stateRoot':str(store.root),'taskId':state['taskId'],'identityHash':state['identityHash']}


def check_previous(value):
    """只有可核对且无未决操作的终态才可让出；不以PID或超时推断结束。"""
    owner=value['owner'];tasks=load('task_store')
    try:
        previous=tasks.Store(owner['stateRoot']).read(owner['taskId'])
        if (previous['schema']!='effectcraft-managed-task/v2' or previous['identityHash']!=owner['identityHash']
                or previous['identity']['project'] is None
                or {'key':value['key'],'nonce':value['nonce']} not in previous.get('projectClaims',[])):
            raise ValueError('identity')
    except (OSError,ValueError,TypeError,KeyError):raise ValueError('project_claim_owner_unconfirmed') from None
    if previous['state'] in tasks.ACTIVE or any(step['state']=='attempted' for step in previous['steps']):
        raise ValueError('project_resource_busy: '+owner['taskId'])


@contextmanager
def reserve(store,state):
    """在共享互斥内先保留认领再落任务；中途崩溃保留未确认占用。"""
    source=state['identity']['project']
    if source is None:
        yield
        return
    directory=root()
    if directory.is_symlink():raise ValueError('project_claim_invalid')
    with load('platform_support').exclusive_lock(directory/'claims.lock'):
        resource_keys=keys(source)
        # 先完成所有原认领核对，失败不得替换另一把仍有效的认领。
        for key in resource_keys:
            path=directory/(key+'.json')
            if path.exists() or path.is_symlink():check_previous(read_claim(key))
        nonce=uuid.uuid4().hex;owner=owner_identity(store,state)
        state['projectClaims']=[{'key':key,'nonce':nonce} for key in resource_keys]
        for key in resource_keys:
            load('task_store').atomic_json(directory/(key+'.json'),
                {'schema':'effectcraft-project-claim/v1','key':key,'owner':owner,'nonce':nonce})
        yield


def verify(store,state):
    """逐操作只读核对原认领；旧无认领任务不补造跨账本证明。"""
    references=state.get('projectClaims')
    if references is None:return
    if (not isinstance(references,list) or len(references)!=2
            or any(not isinstance(row,dict) or set(row)!={'key','nonce'}
                   or not isinstance(row['key'],str) or not isinstance(row['nonce'],str) for row in references)
            or len({row['key'] for row in references})!=2):raise ValueError('project_claim_invalid')
    if sorted(row['key'] for row in references)!=keys(state['identity']['project']):raise ValueError('revision_conflict')
    owner=owner_identity(store,state)
    for row in references:
        value=read_claim(row['key'])
        if value['owner']!=owner or value['nonce']!=row['nonce']:raise ValueError('project_claim_invalid')
