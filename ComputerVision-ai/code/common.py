"""Read-only data access, experiment confinement and reproducible IO."""
from __future__ import annotations
import csv
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

CROPS = ('basil','bok_choy','cucumber','kale','lettuce','pepper','rosemary','tomato')
DATA = Path('/home/user/data/ComputerVision_data/processed')
RAW_KALE = Path('/home/user/data/ComputerVision_data/extracted/other/kale/Kale_Dataset')
PROTECTED = (Path('/home/data'), Path('/home/user/data'))

def utc():
    return datetime.now(timezone.utc).isoformat()

def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def inside(path, root):
    return path == root or root in path.parents

def safe_output(path, experiment):
    root, dest = Path(experiment).resolve(), Path(path).resolve()
    if not inside(dest, root):
        raise ValueError(f'Output escaped experiment: {dest}')
    if any(inside(root, x.resolve()) or inside(dest, x.resolve()) for x in PROTECTED):
        raise ValueError(f'Output overlaps protected dataset: {dest}')
    return dest

def input_path(relpath):
    if str(relpath).startswith('raw-kale:'):
        rel=Path(str(relpath)[len('raw-kale:'):])
        if rel.is_absolute() or '..' in rel.parts or not rel.parts:
            raise ValueError('Invalid raw source path')
        p=RAW_KALE/rel
        if not inside(p.resolve(),RAW_KALE.resolve()):raise ValueError('Raw source path escaped registered root')
        return p
    rel = Path(relpath)
    if rel.is_absolute() or '..' in rel.parts or not rel.parts or rel.parts[0] not in CROPS:
        raise ValueError(f'Invalid processed-relative path: {rel}')
    # Read through the processed entry; do not substitute its resolved target.
    return DATA / rel

def initialize(root):
    root = safe_output(root, root)
    for name in ('audit','review','manifests','configs','runs','evaluation','tables','figures',
                 'paper','reproducibility','transfer','cache','tmp'):
        safe_output(root / name, root).mkdir(parents=True, exist_ok=True)
    for key, subdir in {'TORCH_HOME':'torch','XDG_CACHE_HOME':'xdg','MPLCONFIGDIR':'matplotlib',
                        'PIP_CACHE_DIR':'pip','NUMBA_CACHE_DIR':'numba'}.items():
        value = safe_output(root / 'cache' / subdir, root)
        value.mkdir(exist_ok=True)
        os.environ[key] = str(value)
    temporary=root/'tmp'
    # Linux multiprocessing AF_UNIX socket paths are limited to 108 bytes.
    # A short alias resolves into this experiment's tmp; no data are written
    # outside the experiment and no pre-existing alias is replaced.
    if os.name=='posix' and len(str(temporary))>65:
        alias=root.parent/('t_'+hashlib.sha256(str(root).encode()).hexdigest()[:8])
        if alias.exists() or alias.is_symlink():
            if alias.resolve()!=temporary.resolve():raise ValueError('Temporary alias collision')
        else:alias.symlink_to(temporary,target_is_directory=True)
        temporary=alias
    os.environ['TMPDIR'] = str(temporary)
    os.environ['TEMP'] = str(temporary)
    os.environ['TMP'] = str(temporary)
    tempfile.tempdir = str(temporary)
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
    return root

def write_json(path, value, root):
    path = safe_output(path, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.partial')
    with temp.open('w', encoding='utf-8') as f:
        json.dump(value, f, indent=2, ensure_ascii=False, allow_nan=False)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, path)

def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def write_csv(path, rows, root, fields=None):
    path = safe_output(path, root)
    rows = list(rows)
    fields = fields or list(dict.fromkeys(k for r in rows for k in r))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='raise')
        writer.writeheader()
        writer.writerows(rows)

def read_csv(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def research_inventory(root):
    root=Path(root)
    return root/'audit'/('research_inventory.csv' if (root/'audit'/'research_inventory.csv').exists() else 'image_inventory.csv')

def code_hash():
    h = hashlib.sha256()
    for p in sorted(Path(__file__).parent.rglob('*.py')):
        h.update(str(p.relative_to(Path(__file__).parent)).encode())
        h.update(p.read_bytes())
    return h.hexdigest()

def progress(root, state):
    state = dict(state, updated_at=utc())
    write_json(root / 'audit' / 'progress.json', state, root)
    # The runner's progress file is explicitly allowed, outside source data.
    if os.environ.get('CODEX_PROGRESS_FILE'):
        p = Path(os.environ['CODEX_PROGRESS_FILE'])
        runner_root = Path('/home/user/codex_gpu_jobs/runs').resolve()
        if inside(p.resolve(), runner_root):
            write_json(p, state, runner_root)
