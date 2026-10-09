"""消费 ArtCraft 持有的 craft-artifact/v1；绑定工作流包身份，不另建公共协议。"""
import importlib.util
from fractions import Fraction
from pathlib import Path, PurePosixPath
import re

# 协议事实源：artcraft-plugin v0.1.0-dev.109 / 09d4ac5b8ff82f8fe819189e4be487b45ab2472b。
# schemas/craft-artifact-v1.json SHA256 c3385db540db71fccfdb049f79f05a9adba55ec008958579eab6fac46dd6ea5d。
HERE=Path(__file__).resolve().parent
HEX=re.compile(r'^[a-f0-9]{64}$')


def load(name):
    spec=importlib.util.spec_from_file_location('artifact_lineage_'+name,HERE/(name+'.py'))
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


def read(path):return load('commands').reply_json(Path(path).read_text(encoding='utf-8'))
def digest(value):return load('task_store').digest(value)
def sha(path):return load('task_store').file_sha(path)


def fail(reason):raise ValueError('artifact_lineage: '+reason)


def file(root,name):
    if (not isinstance(name,str) or not name or '\\' in name or ':' in name or name.startswith('/')
            or any(part in ('','.','..') for part in name.split('/'))):fail('unsafe_location')
    path=root/PurePosixPath(name)
    if any(p.is_symlink() for p in (path,*path.parents) if p==root or root in p.parents):fail('symlink')
    if not path.resolve().is_relative_to(root.resolve()) or not path.is_file():fail('missing_or_escaping_file')
    return path


def inventory(root):
    result={}
    for path in sorted(root.rglob('*')):
        if path.is_symlink():fail('symlink')
        if path.is_file() and path!=root/'manifest.json':result[path.relative_to(root).as_posix()]=sha(path)
    return result


def reference(value):
    if (not isinstance(value,dict) or set(value)!=set(('assetId','version','sha256'))
            or any(not isinstance(value[k],str) or not 1<=len(value[k])<=256 for k in ('assetId','version'))
            or not isinstance(value['sha256'],str) or not HEX.fullmatch(value['sha256'])):fail('source_reference_invalid')
    return value


def validate_source(root):
    """在安装／原生副作用前校验源包；旧包可读但不补造任务来源。"""
    root=Path(root);manifest=read(file(root,'manifest.json'))
    if 'artifact' in manifest or 'artifactBinding' in manifest:verify(root,manifest)
    else:
        files=manifest.get('files')
        if not isinstance(files,dict) or 'project.ecproj' not in files:fail('legacy_file_table_invalid')
        for name,expected in files.items():
            if sha(file(root,name))!=expected:fail('legacy_file_changed')
        for asset in manifest.get('assets',{}).values():
            if files.get(asset['path'])!=asset['sha256']:fail('legacy_dependency_mismatch')
    return manifest


def source_ref(root):
    manifest=validate_source(root)
    if 'artifact' in manifest:return reference({k:manifest['artifact'][k] for k in ('assetId','version','sha256')})
    content=manifest['files']['project.ecproj']
    return {'assetId':'legacy-project:'+content,'version':content,'sha256':content}


def source_binding(root):
    """绑定整包版本，任务登记后不能仅靠未变化的原生工程摘要放行。"""
    root=Path(root);parent=source_ref(root)
    return {'schema':'effectcraft-source-package/v1','manifestSha256':sha(file(root,'manifest.json')),'sourceRef':parent}


def standalone(context):
    identity=digest(context['executionIdentity'])
    return {'producerTaskId':'standalone:'+identity,'taskIdentityHash':identity,'mode':'standalone'}


def binding(context):
    return {'schema':'effectcraft-artifact-binding/v1','producer':context.get('artifactProducer') or standalone(context),
            'planSha256':digest(context['plan']),'runtimeSha256':context['runtimeSha256'],
            'sourceRef':context.get('sourceArtifact')}


def record(root,manifest,bound):
    """只依据实际包文件与显式生产身份构造公共对象；不推断技术／创作通过。"""
    if not isinstance(bound,dict) or set(bound)!=set(('schema','producer','planSha256','runtimeSha256','sourceRef')) or bound['schema']!='effectcraft-artifact-binding/v1':fail('binding_schema')
    producer=bound['producer']
    if (not isinstance(producer,dict) or set(producer)!=set(('producerTaskId','taskIdentityHash','mode'))
            or not isinstance(producer['producerTaskId'],str) or not 1<=len(producer['producerTaskId'])<=256
            or producer['mode'] not in ('managed','standalone')
            or not isinstance(producer['taskIdentityHash'],str) or not HEX.fullmatch(producer['taskIdentityHash'])):fail('producer_invalid')
    if producer['mode']=='standalone' and producer['producerTaskId']!='standalone:'+producer['taskIdentityHash']:fail('standalone_identity_invalid')
    for key in ('planSha256','runtimeSha256'):
        if not isinstance(bound[key],str) or not HEX.fullmatch(bound[key]):fail('binding_digest')
    if bound['runtimeSha256']!=manifest['runtimeSha256'] or bound['planSha256']!=digest(read(file(root,'plan.json'))):fail('execution_binding_changed')
    files=manifest.get('files')
    if not isinstance(files,dict) or not files or files!=inventory(root):fail('package_file_table_changed')
    for name in files:file(root,name)
    native=read(file(root,'project.ecproj'))
    if not isinstance(native,dict) or native.get('schema')!=1 or not isinstance(native.get('items'),dict):fail('native_format_invalid')
    parent=reference(bound['sourceRef']) if bound['sourceRef'] is not None else None
    if (parent['sha256'] if parent else None)!=manifest.get('sourceProjectSha256'):fail('source_project_changed')
    asset_id=parent['assetId'] if parent else 'effectcraft:'+digest(producer)
    version=digest({'binding':bound,'files':files,'sourceProjectSha256':manifest.get('sourceProjectSha256')})
    native_sha=files['project.ecproj']
    def ref(name,logical=None):
        if name not in files:fail('unlisted_reference')
        return {'assetId':logical or 'effectcraft-rendition:'+digest({'assetId':asset_id,'location':name}),
                'version':files[name],'sha256':files[name],'location':name}
    assets=manifest.get('assets',{})
    if not isinstance(assets,dict):fail('dependencies_invalid')
    dependencies=[];asset_paths=set()
    for alias,asset in sorted(assets.items()):
        if not isinstance(asset,dict) or files.get(asset.get('path'))!=asset.get('sha256'):fail('dependency_changed')
        name=asset['path'];file(root,name);asset_paths.add(name)
        dependencies.append({'assetRef':{k:v for k,v in ref(name,'effectcraft-media:'+digest({'assetId':asset_id,'alias':alias})).items() if k!='location'},
            'kind':'media','packaged':True,'missingReason':None})
    names={frame['path'] for frame in manifest.get('frames',[])}
    if manifest.get('video'):names.add(manifest['video']['path'])
    if manifest.get('imageSequence'):
        descriptor=manifest['imageSequence']['path'];names.add(descriptor)
        directory=PurePosixPath(descriptor).parent
        names.update(name for name in files if PurePosixPath(name).is_relative_to(directory) and name.endswith('.png'))
    if names & asset_paths:fail('rendition_is_dependency')
    composition=read(file(root,'native.json'))['composition']
    width=composition['width'];height=composition['height'];rate=Fraction(str(composition['frameRate']));duration=Fraction(str(composition['duration']))
    if type(width) is not int or type(height) is not int or min(width,height)<=0 or rate<=0 or duration<=0:fail('composition_invalid')
    if max(width,height,rate.numerator,rate.denominator,duration.denominator)>9007199254740991:fail('unsafe_time_or_dimension_integer')
    loss=manifest['lossReport']
    if files.get(loss['path'])!=loss['sha256']:fail('loss_report_changed')
    return {'protocolVersion':'craft-artifact/v1','assetId':asset_id,'version':version,'sha256':native_sha,
            'bytes':file(root,'project.ecproj').stat().st_size,'mediaType':'application/vnd.effectcraft.project+json',
            'producerTaskId':producer['producerTaskId'],'sourceRefs':[parent] if parent else [],
            'nativeProjectRef':{'assetId':asset_id,'version':version,'sha256':native_sha,'location':'project.ecproj'},
            'renditions':[ref(name) for name in sorted(names)],'dependencies':dependencies,
            'technicalMetadata':{'width':width,'height':height,'frameRate':{'num':rate.numerator,'den':rate.denominator},
                'durationTicks':str(duration.numerator),'timeBase':{'num':1,'den':duration.denominator},'colorSpace':'unknown'},
            'lossReportRef':ref(loss['path']),'evidenceRefs':[ref('native.json'),ref('operations.json')],'location':'project.ecproj'}


def attach(root,manifest,context):
    """生成新包记录；生产身份随导出上下文持久化，恢复不创建新任务。"""
    try:
        bound=binding(context);manifest['artifactBinding']=bound;manifest['artifact']=record(Path(root),manifest,bound)
    except (KeyError,TypeError,OSError,ValueError) as error:
        if isinstance(error,ValueError) and str(error).startswith('artifact_lineage:'):raise
        fail('invalid_package: '+type(error).__name__)
    return manifest


def verify(root,manifest):
    """重算完整内容与引用；缺失任何一半绑定都不能降级为旧包。"""
    try:
        if manifest.get('artifact')!=record(Path(root),manifest,manifest['artifactBinding']):fail('record_changed')
    except (KeyError,TypeError,OSError,ValueError) as error:
        if isinstance(error,ValueError) and str(error).startswith('artifact_lineage:'):raise
        fail('invalid_package: '+type(error).__name__)
