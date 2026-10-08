"""对实际交付做技术检查并绑定宿主 Judge；不将文件存在当作验收。"""
import hashlib
import importlib.util
import json
import math
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import uuid


def load(name):
    spec=importlib.util.spec_from_file_location('craft_review_'+name,Path(__file__).with_name(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def read(path):
    return load('commands').reply_json(Path(path).read_text(encoding='utf-8'))


def sha(path):
    return load('task_store').file_sha(path)


def contained(root, relative):
    p=PurePosixPath(relative)
    if not isinstance(relative,str) or p.is_absolute() or '..' in p.parts or '\\' in relative or ':' in relative:
        raise ValueError('artifact_path_escape')
    result=root/p
    if result.is_symlink() or not result.resolve().is_relative_to(root.resolve()):
        raise ValueError('artifact_path_escape')
    return result


def binding(root):
    root=Path(root)
    manifest=read(root/'manifest.json')
    if not isinstance(manifest.get('files'),dict) or not manifest['files']:
        raise ValueError('artifact_manifest_invalid')
    for name,expected in manifest['files'].items():
        if sha(contained(root,name))!=expected:
            raise ValueError('artifact_changed: '+name)
    return {'manifestSha256':sha(root/'manifest.json'),
            'projectSha256':sha(root/'project.ecproj'),
            'filesHash':load('task_store').digest(manifest['files'])}


def inspect_delivery(root, timeout=120):
    """解码 PNG/视频，核验真实摘要；原生重开须单独提供当前执行证据。"""
    root=Path(root).resolve()
    result={'schema':'effectcraft-quality/v1','engineering':{'status':'NOT_RUN'},
            'technical':{'status':'NOT_RUN','media':[]},'creative':{'status':'NOT_RUN'},
            'accepted':False}
    try:
        result['binding']=binding(root)
        manifest=read(root/'manifest.json'); technical=result['technical']; media=technical['media']
        for frame in manifest.get('frames',[]):
            path=contained(root,frame['path'])
            facts=load('image_sequence').rgba_facts(path) if frame.get('requestedAlpha') else load('png_inspection').inspect_png(path)
            if (root/'native.json').is_file():
                comp=read(root/'native.json')['composition']
                if (facts['width'],facts['height'])!=(comp['width'],comp['height']):
                    raise ValueError('preview_dimensions_mismatch')
            media.append({'path':frame['path'],'facts':facts})
        sequence=manifest.get('imageSequence')
        if sequence:
            descriptor=contained(root,sequence['path']); data=read(descriptor)
            # 分段和普通序列各自保留帧摘要；递归核验本包中的全部 PNG。
            frames=sorted(descriptor.parent.rglob('*.png'))
            if len(frames)!=data.get('frameCount'):
                raise ValueError('sequence_frame_set_mismatch')
            dimensions=data.get('binding',{}).get('composition',data)
            for path in frames:
                facts=load('image_sequence').rgba_facts(path)
                if (facts['width'],facts['height'])!=(dimensions['width'],dimensions['height']):
                    raise ValueError('sequence_dimensions_mismatch')
            media.append({'path':sequence['path'],'verifiedFrames':len(frames)})
        video=manifest.get('video')
        if video:
            path=contained(root,video['path']); ffmpeg=shutil.which('ffmpeg'); ffprobe=shutil.which('ffprobe')
            if not ffmpeg or not ffprobe:
                technical.update(status='NOT_RUN',reason='media_decoder_missing')
                return result
            probe=subprocess.run([ffprobe,'-v','error','-show_streams','-show_format','-of','json',str(path)],capture_output=True,text=True,timeout=timeout,check=True)
            facts=json.loads(probe.stdout); streams=[s for s in facts.get('streams',[]) if s.get('codec_type')=='video']
            if len(streams)!=1 or float(facts['format'].get('duration',0))<=0:
                raise ValueError('video_stream_invalid')
            subprocess.run([ffmpeg,'-v','error','-xerror','-i',str(path),'-map','0:v:0','-f','null','-'],capture_output=True,timeout=timeout,check=True)
            native=read(root/'native.json')['composition']
            stream=streams[0]
            from fractions import Fraction
            actual_rate=float(Fraction(stream['avg_frame_rate']))
            if ((stream['width'],stream['height'])!=(native['width'],native['height'])
                    or abs(actual_rate-float(native['frameRate']))>.01
                    or abs(float(facts['format']['duration'])-float(native['duration']))>max(.05,1/actual_rate)):
                raise ValueError('video_contract_mismatch')
            media.append({'path':video['path'],'decoded':True,'probe':facts})
        if not media:
            raise ValueError('no_media_to_review')
        technical['status']='PASS'
    except (ValueError,TypeError,KeyError,OSError,subprocess.SubprocessError) as error:
        result['technical'].update(status='FAIL',reason=str(error))
    return result


def judge_request(task, root, report, criteria, temporal):
    """给宿主输出结构化评估请求，不在库中调用外部付费模型。"""
    current=binding(root)
    if current!=report.get('binding'):
        raise ValueError('artifact_changed')
    return {'schema':'effectcraft-judge-request/v1','requestId':uuid.uuid4().hex,
            'taskId':task,'binding':current,'criteria':criteria,
            'criteriaHash':load('task_store').digest(criteria),
            'temporalRequired':bool(temporal),'media':report['technical']['media'],
            'requiredResponse':['requestId','binding','score','passed','issues','temporalReviewed'],
            'instruction':'Inspect actual media and timing; missing visual capability is NOT_RUN, never PASS.'}


def accept_judge(root, report, request, response):
    """只接收绑定当前文件的宿主评价；技术失败和缺少时序证据不能提升。"""
    if report['technical']['status']!='PASS':
        raise ValueError('technical_gate')
    current=binding(root)
    if current!=request['binding'] or current!=report.get('binding'):
        raise ValueError('artifact_changed')
    if response.get('requestId')!=request['requestId'] or response.get('binding')!=current:
        raise ValueError('judge_binding_mismatch')
    if (type(response.get('score')) not in (float,int) or not math.isfinite(response['score'])
            or not 0<=response['score']<=1 or type(response.get('passed')) is not bool
            or not isinstance(response.get('issues'),list)):
        raise ValueError('judge_response_invalid')
    if request['temporalRequired'] and response.get('temporalReviewed') is not True:
        raise ValueError('temporal_evidence_required')
    result=dict(report)
    result['creative']={'status':'PASS' if response['passed'] else 'FAIL','receipt':response}
    # 用户接受状态不由模型评分代签；这里仅返回可交付判断。
    result['readyForAcceptance']=response['passed'] and report['engineering']['status']=='PASS'
    return result
