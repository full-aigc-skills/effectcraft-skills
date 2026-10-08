#!/usr/bin/env python3
"""由当前锁与完整载荷绑定的技术样例证据生成矩阵；不提升其他验收门禁。"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath

ROOT=Path(__file__).resolve().parents[1]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def payload(base):
    """完整单技能文件清单；缓存不属于发布载荷，链接不允许借用包外证据。"""
    if base.is_symlink():raise ValueError('skill_symlink')
    files={}
    for path in sorted(base.rglob('*')):
        if '__pycache__' in path.relative_to(base).parts or path.suffix=='.pyc':continue
        if path.is_symlink():raise ValueError('skill_symlink')
        if path.is_file():files[path.relative_to(base).as_posix()]=sha(path)
    return files

def bound_evidence(base, runtime, python):
    path=ROOT/'docs/evidence/current-capability-evidence.json'
    if not path.is_file() or path.is_symlink():return {},{'current':False,'reason':'evidence_missing'}
    evidence=json.loads(path.read_text(encoding='utf-8'))
    reference={'file':path.relative_to(ROOT).as_posix(),'sha256':sha(path),'current':False}
    try:
        if evidence['schema']!='effectcraft-capability-evidence/v1':raise ValueError('evidence_schema')
        files=payload(base)
        if not files or files!=evidence['baseSkillFiles']:raise ValueError('skill_payload_changed')
        if evidence['runtimeVersion']!=runtime['resolvedVersion'] or evidence['pythonVersion']!=python['version']:
            raise ValueError('runtime_version_changed')
        name=evidence['reportFile'];relative=PurePosixPath(name)
        if relative.is_absolute() or not name.startswith('docs/evidence/') or '\\' in name or '..' in relative.parts:
            raise ValueError('report_path_invalid')
        report_path=ROOT.joinpath(*relative.parts)
        if any(p.is_symlink() for p in [report_path,*report_path.parents] if p==ROOT or ROOT in p.parents):
            raise ValueError('report_symlink')
        if sha(report_path)!=evidence['reportSha256']:raise ValueError('report_changed')
        report=json.loads(report_path.read_text(encoding='utf-8'))
        if report['schema']!='effectcraft-independent-offline15/v1' or report['status']!='PASS':raise ValueError('report_not_pass')
        key=report['platform'];proof=evidence['platforms'][key]
        if (proof['runtimeSha256']!=runtime['artifacts'][key]['binarySha256']
                or proof['pythonArchiveSha256']!=python['artifacts'][key]['archiveSha256']
                or report['pythonArchiveSha256']!=proof['pythonArchiveSha256']
                or report['nativeArchiveSha256']!=runtime['artifacts'][key]['archiveSha256']):
            raise ValueError('artifact_identity_changed')
        rows=[row for row in report['cases'] if row['skill']=='effectcraft-use']
        inventory={name:{'sha256':digest,'mode':0o444} for name,digest in files.items()}
        digest=hashlib.sha256(json.dumps(inventory,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        if (len(rows)!=1 or any(rows[0].get(x)!='PASS' for x in ('status','engineering','technical'))
                or rows[0].get('installedFilesAndModesUnchanged') is not True
                or rows[0].get('installedInventorySha256')!=digest):raise ValueError('report_payload_unbound')
        reference.update(current=True,reason='current_native_technical_sample',reportFile=name,reportSha256=evidence['reportSha256'])
        return {key:proof},reference
    except (KeyError,TypeError,ValueError,OSError) as error:
        reference['reason']=str(error) if isinstance(error,ValueError) else 'evidence_incomplete'
        return {},reference

def build(check=False):
    base=ROOT/'skills/effectcraft-use';runtime=json.loads((base/'scripts/runtime.lock.json').read_text(encoding='utf-8'))
    python=json.loads((base/'scripts/python.lock.json').read_text(encoding='utf-8'))
    evidence,binding=bound_evidence(base,runtime,python);rows=[]
    for key,artifact in runtime['artifacts'].items():
        proof=evidence.get(key,{})
        rows.append({'platform':key,'python':python['version'],'runtime':runtime['resolvedVersion'],
                     'pythonMinimum':python['artifacts'][key].get('minimumSystem',{}),
                     'runtimeMinimum':artifact.get('minimumSystem',{}),
                     'nativeRepresentative':'PASS' if proof.get('nativeRepresentative')=='PASS' else 'NOT_RUN',
                     'scope':'native technical sample only; not domain, cold-install, creative or host acceptance',
                     'completePlatformAcceptance':'NOT_RUN'})
    result={'schema':'effectcraft-capability-matrix/v2','evidenceBinding':binding,'platforms':rows,
            'web':{'installation':'NOT_RUN','browserTask':'NOT_RUN'},
            'freebsd':{'sourceBuild':'NOT_RUN'},'fullV1':'NOT_RUN'}
    text=json.dumps(result,ensure_ascii=False,indent=2)+'\n';path=ROOT/'docs/current-capabilities.json'
    if check:
        if not path.exists() or path.read_text(encoding='utf-8')!=text:raise ValueError('capability_matrix_drift')
    else:path.write_text(text,encoding='utf-8',newline='\n')
    print(json.dumps({'result':'PASS','scope':'generated capability matrix','platforms':len(rows),'currentEvidence':binding['current']}))
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');build(p.parse_args().check)
