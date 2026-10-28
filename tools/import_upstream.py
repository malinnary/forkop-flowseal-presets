"""Reproducible, non-executing inventory of Flowseal Windows strategies.

No batch file is executed. No generated options are claimed Linux-compatible.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def parse_strategy(text):
    # Join CMD continuations, then remove CMD escaping of a literal exclamation.
    logical = re.sub(r'\^\r?\n', ' ', text).replace('^!', '!')
    start = re.search(r'^start\s.*?"%BIN%winws\.exe"\s+(.*)$', logical, re.M | re.I)
    if not start:
        raise ValueError('Unsupported batch launcher')
    # Quotes here wrap paths, not arbitrary shell expressions. Fail closed if changed.
    tokens = re.findall(r'(?:[^\s"]|"[^"]*")+', start.group(1))
    tokens = [t.replace('"', '') for t in tokens]
    if any(not t.startswith('--') for t in tokens):
        raise ValueError('Unexpected non-option token')
    capture = [t for t in tokens if t.startswith('--wf-')]
    blocks = [[]]
    for token in tokens:
        if token in capture:
            continue
        if token == '--new':
            if not blocks[-1]:
                raise ValueError('Empty filter block')
            blocks.append([])
        else:
            blocks[-1].append(token)
    if any(not b or not b[0].startswith('--filter-') for b in blocks):
        raise ValueError('Unexpected filter block')
    refs = sorted(set(re.findall(r'%(BIN|LISTS)%([^\s"]+)', start.group(1))))
    variables = sorted(set(re.findall(r'%([^%]+)%', start.group(1))) - {'BIN', 'LISTS'})
    return {'capture_options': capture, 'blocks': blocks,
            'references': refs, 'runtime_variables': variables}


def generate(source, output):
    lock = json.loads((ROOT / 'upstream.lock.json').read_text())
    actual = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    if actual != lock['commit']:
        raise ValueError('Upstream commit differs from lock')
    if subprocess.check_output(['git', '-C', str(source), 'status', '--porcelain'], text=True).strip():
        raise ValueError('Upstream checkout must be clean')
    if output.exists():
        raise ValueError('Output already exists; choose a new build directory')
    records = []
    assets = {}
    files = sorted(source.glob(lock['strategy_glob']))
    for path in files:
        data = path.read_bytes()
        parsed = parse_strategy(data.decode('utf-8-sig'))
        for kind, name in parsed['references']:
            if '/' in name or '\\' in name or name in ('.', '..'):
                raise ValueError('Unsafe referenced filename')
            relative = ('bin/' if kind == 'BIN' else 'lists/') + name
            ref = source / relative
            if kind == 'BIN' and ref.suffix != '.bin':
                raise ValueError('Executable dependency forbidden')
            if ref.is_file():
                assets[relative] = digest(ref.read_bytes())
        records.append({'name': path.stem, 'source': path.name, 'sha256': digest(data),
                        'status': 'unverified-linux', **parsed})
    output.mkdir(parents=True)
    for path in files:
        dest = output / 'upstream' / path.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dest)
    for relative in assets:
        dest = output / 'upstream' / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / relative, dest)
    shutil.copyfile(source / 'LICENSE.txt', output / 'LICENSE.flowseal.txt')
    manifest = {'upstream': lock, 'strategies': records, 'asset_sha256': assets}
    (output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(f'Inventoried {len(records)} strategies, {len(assets)} dependencies; no executable binaries copied.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    generate(args.source.resolve(), args.output.resolve())
