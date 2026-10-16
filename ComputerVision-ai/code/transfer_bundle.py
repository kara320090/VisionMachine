"""Immutable tar bundle + per-file SHA256 for laptop verification."""
import argparse
import tarfile
from pathlib import Path
from common import *

def bundle(root,run=None):
    root=initialize(root);stamp=utc().replace(':','').replace('+','_');name=f'bundle_{run or "project"}_{stamp}'
    selected=[root/'runs'/run] if run else [root/d for d in ('code','configs','audit','review','manifests','runs','evaluation','tables','figures','paper','reproducibility')]
    files=sorted({p for d in selected if d.exists() for p in d.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.partial'
                  and p.name not in ('progress.json','suite_progress.json')})
    if not run:files+=sorted(p for p in (root/'REPORT.html',root/'README.txt',root/'LINUX_CLI_HANDOFF.txt') if p.is_file())
    if run and not (root/'runs'/run/'completed.json').exists():raise ValueError('Run transfer requires completed marker')
    for p in files:
        safe_output(p,root)
        if p.is_symlink():raise ValueError('Artifacts must not symlink to external files')
    inventory=[{'path':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,'sha256':digest(p)} for p in files]
    manifest=root/'transfer'/(name+'.json')
    write_json(manifest,{'created_at':utc(),'experiment_id':root.name,'files':inventory},root)
    tarpath=root/'transfer'/(name+'.tar')
    with tarfile.open(tarpath,'w') as tar:
        for p in files:tar.add(p,arcname=p.relative_to(root).as_posix(),recursive=False)
        tar.add(manifest,arcname='transfer/'+manifest.name,recursive=False)
    # Detect changes during transfer snapshot generation.
    for entry in inventory:
        p=root/entry['path']
        if p.stat().st_size!=entry['bytes'] or digest(p)!=entry['sha256']:raise ValueError('Artifact changed during bundle creation')
    result={'bundle':str(tarpath),'inventory':str(manifest),'bundle_sha256':digest(tarpath),
            'bytes':tarpath.stat().st_size,'files':len(files)}
    write_json(root/'transfer'/(name+'.receipt.json'),result,root);print(json.dumps(result))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--run');a=p.parse_args();bundle(Path(a.root),a.run)
