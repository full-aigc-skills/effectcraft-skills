#!/usr/bin/env python3
"""持续 MCP 会话中的原生合成、动画与渲染计划。"""
import argparse
import sys
sys.dont_write_bytecode = True
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

def exchange_report(root,outputs,warnings):
    spec=importlib.util.spec_from_file_location('craft_exchange_loss',Path(__file__).with_name('exchange_loss.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.write_report(root,outputs,warnings)

ALLOWED = {'asset.import', 'asset.replace', 'layer.addItem', 'layer.newText', 'layer.newShape', 'layer.newSolid', 'layer.setText',
           'layer.select', 'layer.setParent', 'prop.set', 'prop.addKey',
           'keys.select', 'keys.easyEase', 'keys.interpolation', 'mask.new',
           'effect.apply', 'effect.remove', 'effect.toggle', 'comp.settings'}

def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def resolve(value, bindings):
    if isinstance(value, dict):
        if set(value) == {'$ref'}:
            try:
                parts = value['$ref'].split('.')
                result = bindings[parts[0]]
                for field in parts[1:]:
                    result = result[int(field)] if isinstance(result, list) else result[field]
                return result
            except (KeyError, IndexError, TypeError, ValueError, AttributeError):
                raise ValueError('unresolved_reference: ' + str(value['$ref'])) from None
        return {key: resolve(item, bindings) for key, item in value.items()}
    if isinstance(value, list):
        return [resolve(item, bindings) for item in value]
    return value


def load_module(name):
    spec = importlib.util.spec_from_file_location('craft_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate(plan):
    if not isinstance(plan, dict) or not isinstance(plan.get('operations'), list):
        raise ValueError('operations_required')
    aliases = set()
    for item in plan['operations']:
        if item.get('command') not in ALLOWED:
            raise ValueError('unsupported_command')
        alias = item.get('as')
        if alias is not None:
            if alias in aliases:
                raise ValueError('duplicate_alias')
            if not isinstance(alias, str) or not re.fullmatch(r'[a-zA-Z][\w-]*', alias):
                raise ValueError('invalid_alias')
            aliases.add(alias)
        if not isinstance(item.get('params', {}), dict):
            raise ValueError('invalid_params')
    if any(set(x) != {'format'} or x['format'] != 'mp4' for x in plan.get('exports', [])) or len(plan.get('exports', [])) > 1:
        raise ValueError('invalid_export')
    for value in plan.get('frames', [0]):
        if type(value) not in (int, float) or not 0 <= value <= 3600:
            raise ValueError('invalid_frame_time')
    if 'document' in plan:
        doc = plan['document']
        if set(doc) - {'name', 'width', 'height', 'frameRate', 'duration', 'background'}:
            raise ValueError('unsupported_document_setting')
        for field in ('width', 'height'):
            if type(doc.get(field)) is not int or not 0 < doc[field] <= 16384:
                raise ValueError('invalid_document_size')
        for field, limit in [('frameRate', 240), ('duration', 3600)]:
            if type(doc.get(field)) not in (int, float) or not 0 < doc[field] <= limit:
                raise ValueError('invalid_document_timing')


def execute(plan, output, runtime_home=None, source=None):
    owned = {'output': False}
    try:
        return _execute(plan, output, runtime_home, source, owned)
    except BaseException as error:
        directory = Path(output).absolute()
        if owned['output'] and directory.is_dir():
            (directory / 'failure.json').write_text(json.dumps({'status': 'failed', 'error': str(error)}, ensure_ascii=False) + '\n')
        raise


def _execute(plan, output, runtime_home, source, owned):
    validate(plan)
    output = Path(output).absolute()
    if output.exists() or output.is_symlink():
        raise ValueError('output_exists')
    source_project, source_hash = None, None
    bindings = {}
    inherited = {}
    if source:
        source = Path(source).resolve()
        source_project = source / 'project.ecproj'
        if source_project.is_symlink():
            raise ValueError('invalid_source')
        prior = json.loads((source / 'manifest.json').read_text())
        source_hash = sha(source_project)
        if source_hash != prior['files']['project.ecproj'] or source_hash != plan.get('expectedProjectSha256'):
            raise ValueError('revision_conflict')
        if 'document' in plan:
            raise ValueError('revision_cannot_recreate_document')
        bindings = prior['bindings']
        inherited = prior.get('assets', {})
    elif 'document' not in plan:
        raise ValueError('document_required')
    installed = load_module('bootstrap').install(json.loads(Path(__file__).with_name('runtime.lock.json').read_text()),
        runtime_home or os.environ.get('CRAFT_RUNTIME_HOME', str(Path.home() / '.local/share/craft-runtimes')))
    cli = installed['executable']
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.effectcraft-', dir=output.parent) as temporary:
        stage = Path(temporary)
        project = stage / 'project.ecproj'
        working = stage
        assets = {}
        def copy_asset(alias, path, digest):
            if not re.fullmatch(r'[a-zA-Z][\w-]*', alias) or not re.fullmatch(r'[a-f0-9]{64}', digest):
                raise ValueError('invalid_asset')
            path = Path(path)
            if path.is_symlink() or not path.is_file() or sha(path) != digest:
                raise ValueError('asset_digest_mismatch: ' + alias)
            destination = working / 'assets' / (alias + path.suffix.lower())
            destination.parent.mkdir(exist_ok=True)
            if destination.exists():
                raise ValueError('duplicate_asset')
            shutil.copyfile(path, destination)
            if sha(destination) != digest:
                raise ValueError('asset_changed_during_copy')
            return destination
        for alias, asset in inherited.items():
            path = (source / asset['path']).resolve()
            if not path.is_relative_to(source):
                raise ValueError('invalid_asset_path')
            assets[alias] = dict(asset, staging=str(copy_asset(alias, path, asset['sha256'])))
        for alias, asset in plan.get('assets', {}).items():
            if alias in assets:
                raise ValueError('asset_alias_exists')
            assets[alias] = {'sha256': asset['sha256'], 'staging': str(copy_asset(alias, asset['path'], asset['sha256']))}
        receipts = []
        with load_module('mcp_session').Session([cli, '--empty', 'mcp']) as session:
            def call(name, args):
                result = session.request('tools/call', {'name': name, 'arguments': args})
                if result.get('isError'):
                    raise RuntimeError('command_failed: ' + name + ': ' + json.dumps(result['content']))
                text = [x['text'] for x in result.get('content', []) if x.get('type') == 'text']
                if len(text) != 1:
                    raise RuntimeError('unexpected_result')
                value = json.loads(text[0])
                receipts.append({'tool': name, 'arguments': args, 'result': value})
                return value
            if source_project:
                call('open_project', {'path': str(source_project)})
                for asset in assets.values():
                    if 'item' in asset:
                        call('execute_command', {'command': 'file.replaceFootage', 'params': {'item': asset['item'], 'path': asset['staging']}})
            else:
                bindings['composition'] = call('execute_command', {'command': 'comp.new', 'params': plan['document']})
            for operation in plan['operations']:
                params = resolve(operation.get('params', {}), bindings)
                if operation['command'] == 'asset.import':
                    asset = assets[params['asset']]
                    if 'item' in asset:
                        raise ValueError('asset_already_imported')
                    imported = call('execute_command', {'command': 'file.import', 'params': {'paths': [asset['staging']]}})
                    if imported['errors'] or len(imported['items']) != 1:
                        raise ValueError('asset_import_failed')
                    asset['item'] = imported['items'][0]
                    result = {'item': asset['item']}
                elif operation['command'] == 'asset.replace':
                    alias, replacement = params['asset'], params['replacement']
                    if alias == replacement or 'item' not in assets[alias] or 'item' in assets[replacement]:
                        raise ValueError('invalid_asset_replacement')
                    updated = assets.pop(replacement)
                    updated['item'] = assets[alias]['item']
                    call('execute_command', {'command': 'file.replaceFootage', 'params': {'item': updated['item'], 'path': updated['staging']}})
                    assets[alias] = updated
                    result = {'item': updated['item']}
                else:
                    if operation['command'] == 'layer.addItem' and params.get('item') not in {asset.get('item') for asset in assets.values()}:
                        raise ValueError('registered_asset_required')
                    result = call('execute_command', {'command': operation['command'], 'params': params})
                if operation.get('as'):
                    if operation['as'] in bindings:
                        raise ValueError('alias_already_exists')
                    bindings[operation['as']] = result
            comp = call('get_comp', {'comp': bindings['composition']['comp']})
            if plan.get('exports'):
                overview = call('get_project', {})
                if sum(item.get('name') == comp['name'] for item in overview['items']) != 1:
                    raise ValueError('ambiguous_composition_name')
            for time in plan.get('frames', [0]):
                if time >= comp['duration']:
                    raise ValueError('frame_out_of_range')
            overview = call('get_project', {})
            for item in overview['items']:
                if item['type'] not in ('Composition', 'Folder', 'Solid') and item['id'] not in {asset.get('item') for asset in assets.values()}:
                    raise ValueError('unregistered_dependency')
            call('save_project', {'path': str(project)})
            if assets:
                if any('item' not in asset for asset in assets.values()):
                    raise ValueError('asset_not_imported')
                output.mkdir(mode=0o700)
                owned['output'] = True
                collected = call('execute_command', {'command': 'file.collectFiles', 'params': {'folder': str(output)}})
                if collected['errors']:
                    raise ValueError('asset_collection_failed')
                project = Path(collected['project'])
                if project != output / 'project.ecproj':
                    raise ValueError('unexpected_collected_project')
                for asset in assets.values():
                    target = output / '(Footage)' / Path(asset['staging']).name
                    if not target.is_file() or sha(target) != asset['sha256']:
                        raise ValueError('collected_asset_mismatch')
                    asset['path'] = str(target.relative_to(output))
                stage = output
            call('open_project', {'path': str(project)})
            comp = call('get_comp', {'comp': bindings['composition']['comp']})
            layers = {str(layer['id']): call('get_layer', {'comp': comp['id'], 'layer': layer['id']}) for layer in comp['layers']}
            frames = []
            for index, time in enumerate(plan.get('frames', [0])):
                filename = f'frame-{index:04d}.png'
                call('render_frame', {'comp': comp['id'], 'time': time, 'max_side': 0, 'path': str(stage / filename), 'inline': False, 'transparent': True})
                if not (stage / filename).is_file():
                    raise ValueError('frame_missing')
                frames.append({'path': filename, 'seconds': time, 'requestedAlpha': True})
        if plan.get('exports'):
            # 0.2.0 CLI 将 --comp 字符串解释为名称，数字 ID 只用于 MCP。
            rendered = subprocess.run([cli, '--project', str(project), 'render', '--comp', comp['name'], '--out', str(stage / 'intro.mp4'), '--format', 'h264', '--start', '0', '--end', str(comp['duration']), '--fps', str(comp['frameRate']), '--audio', 'off'], capture_output=True, text=True, timeout=180)
            if rendered.returncode or not (stage / 'intro.mp4').is_file():
                raise RuntimeError('render_failed: ' + rendered.stdout[-1000:] + rendered.stderr[-1000:])
        if source_project and sha(source_project) != source_hash:
            raise ValueError('revision_conflict')
        # 交付记录使用包内路径；原生文件自身仍是引擎保存的格式。
        serialized = json.dumps(receipts, ensure_ascii=False, indent=2)
        for asset in assets.values():
            serialized = serialized.replace(asset['staging'], asset['path'])
            del asset['staging']
        serialized = serialized.replace(str(working), '.').replace(str(stage), '.').replace(str(source_project) if source_project else '\x00', 'source/project.ecproj')
        (stage / 'operations.json').write_text(serialized + '\n')
        for name, value in [('native.json', {'composition': comp, 'layers': layers}), ('plan.json', plan)]:
            (stage / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
        exchange_report(stage,[frame['path'] for frame in frames]+(['intro.mp4'] if plan.get('exports') else []),{})
        manifest = {'schema': 'effectcraft-delivery/v1', 'sourceProjectSha256': source_hash,
                    'runtimeSha256': installed['binarySha256'], 'bindings': bindings, 'frames': frames, 'assets': assets,
                    'video': {'path': 'intro.mp4', 'alpha': False} if plan.get('exports') else None,
                    'files': {str(f.relative_to(stage)): sha(f) for f in stage.rglob('*') if f.is_file()}, 'lossReport': {'path':'exchange-loss.json','sha256':sha(stage/'exchange-loss.json')}, 'acceptance': 'requires-domain-and-visual-review'}
        (stage / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
        if stage != output:
            if output.exists() or output.is_symlink():
                raise ValueError('output_exists')
            stage.rename(output)
        return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--runtime-home', type=Path)
    parser.add_argument('--asset', action='append', default=[], help='name=/absolute/path; computes input digest')
    args = parser.parse_args()
    try:
        plan = json.loads(args.plan.read_text())
        for assignment in args.asset:
            alias, path = assignment.split('=', 1)
            plan.setdefault('assets', {})[alias] = {'path': path, 'sha256': sha(path)}
        print(json.dumps(execute(plan, args.output, args.runtime_home, args.source), ensure_ascii=False))
    except (ValueError, RuntimeError, OSError, subprocess.SubprocessError) as error:
        print(json.dumps({'error': str(error)}, ensure_ascii=False))
        raise SystemExit(1)

if __name__ == '__main__':
    main()
