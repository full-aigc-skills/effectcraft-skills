#!/usr/bin/env python3
"""由当前锁和绑定证据生成能力矩阵；制品存在不自动升级为原生验收。"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def build(check=False):
    base=ROOT/'skills/effectcraft-use';runtime=json.loads((base/'scripts/runtime.lock.json').read_text())
    python=json.loads((base/'scripts/python.lock.json').read_text())
    evidence_path=ROOT/'docs/evidence/managed-optimization-20261008.json'
    evidence=json.loads(evidence_path.read_text()) if evidence_path.exists() else {}
    rows=[]
    for key,artifact in runtime['artifacts'].items():
        proof=evidence.get('platforms',{}).get(key,{})
        bound=proof.get('runtimeSha256')==artifact['binarySha256']
        rows.append({'platform':key,'python':python['version'],'runtime':runtime['resolvedVersion'],
                     'pythonMinimum':python['artifacts'][key].get('minimumSystem',{}),
                     'runtimeMinimum':artifact.get('minimumSystem',{}),
                     'nativeRepresentative':proof.get('nativeRepresentative','NOT_RUN') if bound else 'NOT_RUN',
                     'completePlatformAcceptance':'NOT_RUN'})
    result={'schema':'effectcraft-capability-matrix/v1','platforms':rows,
            'web':{'installation':'PASS' if evidence.get('webInstallation')=='PASS' else 'NOT_RUN','browserTask':'NOT_RUN'},
            'freebsd':{'sourceBuild':'NOT_RUN'},'fullV1':'NOT_RUN'}
    text=json.dumps(result,ensure_ascii=False,indent=2)+'\n';path=ROOT/'docs/current-capabilities.json'
    if check:
        if not path.exists() or path.read_text()!=text:raise ValueError('capability_matrix_drift')
    else:path.write_text(text)
    print(json.dumps({'result':'PASS','scope':'generated capability matrix','platforms':len(rows)}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');build(p.parse_args().check)
