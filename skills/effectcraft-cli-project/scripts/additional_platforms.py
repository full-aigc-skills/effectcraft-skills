"""固定 Web 分发与 FreeBSD 原生源码构建；各自保留独立验收状态。"""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile

HERE=Path(__file__).resolve().parent

def load(name):
    spec=importlib.util.spec_from_file_location('extra_'+name,HERE/(name+'.py'))
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def lock():return json.loads((HERE/'additional-platforms.lock.json').read_text(encoding='utf-8'))

def tree(directory):
    if any(p.is_symlink() for p in directory.rglob('*')):raise ValueError('payload_symlink')
    return {p.relative_to(directory).as_posix():load('bootstrap').digest(p) for p in directory.rglob('*') if p.is_file() and p.name!='receipt.json'}

def verified(destination,entry):
    if destination.is_symlink():raise ValueError('runtime_symlink')
    record=json.loads((destination/'receipt.json').read_text(encoding='utf-8'))
    if record['source']!=entry or record['files']!=tree(destination):raise ValueError('installed_payload_changed')
    return record

def fetch(entry,stage,archive):
    archive=Path(archive) if archive else stage/'archive'
    if not archive.exists():load('bootstrap').download(entry['url'],archive)
    if archive.is_symlink() or load('bootstrap').digest(archive)!=entry['archiveSha256']:raise ValueError('archive_checksum_mismatch')
    load('bootstrap').extract(archive,stage/'unpacked')
    return stage/'unpacked'/entry['payloadRoot']

def install_web(runtime_home,archive=None):
    data=lock();entry=data['web'];parent=Path(runtime_home).expanduser().resolve()/'effectcraft-web';destination=parent/data['version']
    with load('platform_support').exclusive_lock(parent/'.install.lock'):
        if destination.exists():verified(destination,entry);return destination
        with tempfile.TemporaryDirectory(dir=parent,prefix='.web-') as d:
            payload=fetch(entry,Path(d),archive)
            if not (payload/'effectcraft_web_bg.wasm').is_file() or not (payload/'index.html').is_file():raise ValueError('web_payload_invalid')
            load('task_store').atomic_json(payload/'receipt.json',{'schema':'effectcraft-web-install/v1','source':entry,'files':tree(payload),'nativeAcceptance':'NOT_RUN'})
            payload.rename(destination)
    return destination

def build_freebsd(runtime_home,archive=None):
    if platform.system()!='FreeBSD':raise ValueError('freebsd_host_required')
    data=lock();entry=data['freebsd'];missing=[n for n in entry['dependencies'] if not shutil.which(n)]
    if missing:raise ValueError('freebsd_build_dependencies_missing: '+', '.join(missing))
    parent=Path(runtime_home).expanduser().resolve()/'effectcraft-freebsd';destination=parent/entry['commit']
    with load('platform_support').exclusive_lock(parent/'.build.lock'):
        if destination.exists():return verified(destination,entry)
        # 失败保留源码、构建日志和中间状态，便于诊断；不自动删除或重新发起任务。
        stage=parent/('.build-'+entry['commit'])
        if stage.exists():raise ValueError('freebsd_build_requires_inspection: '+str(stage))
        stage.mkdir();source=fetch(entry,stage,archive)
        with (stage/'build.log').open('wb') as log:
            for argv in (['cargo','build','--locked','--release','-p','effectcraft-cli','-p','effectcraft'],['cargo','test','--locked','-p','effectcraft-engine']):
                subprocess.run(argv,cwd=source,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=18000)
        payload=stage/'payload';payload.mkdir()
        for name in ('effectcraft-cli','effectcraft'):
            shutil.copy2(source/'target/release'/name,payload/name)
        for license_path in source.glob('LICENSE*'):shutil.copy2(license_path,payload/license_path.name)
        result=subprocess.run([str(payload/'effectcraft-cli'),'--version'],capture_output=True,text=True,check=True,timeout=20)
        if result.stdout.strip()!='effectcraft-cli '+data['version']:raise ValueError('built_version_mismatch')
        record={'schema':'effectcraft-freebsd-build/v1','source':entry,'files':tree(payload),'platform':platform.platform(),'nativeTaskAcceptance':'NOT_RUN'}
        load('task_store').atomic_json(payload/'receipt.json',record);payload.rename(destination)
        return record

class Handler(SimpleHTTPRequestHandler):
    """浏览器 WASM 需要跨域隔离；服务器只绑定回环，不暴露其他目录。"""
    def end_headers(self):
        self.send_header('Cross-Origin-Opener-Policy','same-origin')
        self.send_header('Cross-Origin-Embedder-Policy','require-corp')
        super().end_headers()

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['web-install','web-serve','freebsd-build'])
    p.add_argument('--runtime-home',type=Path,default=Path.home()/'.local/share/craft-runtimes');p.add_argument('--archive',type=Path);p.add_argument('--port',type=int,default=0);args=p.parse_args()
    if args.action=='freebsd-build':print(json.dumps(build_freebsd(args.runtime_home,args.archive)));return
    directory=install_web(args.runtime_home,args.archive)
    if args.action=='web-install':print(json.dumps({'directory':str(directory),'browserAcceptance':'NOT_RUN'}));return
    with ThreadingHTTPServer(('127.0.0.1',args.port),partial(Handler,directory=str(directory))) as server:
        print(json.dumps({'url':'http://127.0.0.1:'+str(server.server_port)+'/?nosw','capabilityApi':'window.effectcraft.info()/commands()','acceptance':'NOT_RUN'}),flush=True)
        server.serve_forever()

if __name__=='__main__':main()
