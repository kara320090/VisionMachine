"""Sequential single-GPU suite; launch this script using jobctl.py."""
import argparse
import subprocess
import sys
from pathlib import Path
from common import *

def freeze(root):
    from train import load_protocol
    cfg,rows,lock=load_protocol(root)
    bench=read_json(root/'reproducibility'/'benchmark.json')
    pilot=read_json(root/'runs'/f'pilot_A_seed{cfg["pilot_seed"]}'/'completed.json')
    for record in (bench,pilot):
        if record['config_sha256']!=digest(root/'configs'/'common.json') or record['split_sha256']!=lock['split_sha256']:
            raise ValueError('Repeat pilot after changing settings or split')
    if not all(r['finite_gradient'] for r in bench['results']):raise ValueError('Benchmark gradient check failed')
    path=root/'configs'/'protocol_lock.json'
    if path.exists():raise ValueError('Protocol already frozen')
    write_json(path,{'frozen_at':utc(),'config_sha256':digest(root/'configs'/'common.json'),
        'split_sha256':lock['split_sha256'],'code_sha256':code_hash(),
        'pilot_completed':pilot['completed_at'],'threshold':.5,'epochs':cfg['epochs']},root)

def suite(root,resume=False):
    from train import load_protocol
    cfg,_,_=load_protocol(root,True)
    from verify_source import verify
    verify(root,True)
    schedule=[{'condition':c,'seed':s} for s in cfg['training_seeds'] for c in 'ABC']
    write_json(root/'configs'/'run_schedule.json',schedule,root)
    for item in schedule:
        name=f'{item["condition"]}_seed{item["seed"]}';folder=root/'runs'/name
        if (folder/'completed.json').exists():continue
        args=[sys.executable,'-B','-u',str(root/'code'/'train.py'),'--root',str(root),
              '--condition',item['condition'],'--seed',str(item['seed'])]
        if folder.exists():
            if not resume:raise ValueError('Existing incomplete run needs --resume')
            args.append('--resume')
        write_json(root/'runs'/'suite_progress.json',dict(state='running',current=name,updated_at=utc()),root)
        subprocess.run(args,check=True)
        # A completed marker is polled by the laptop sync script. It does not
        # delete remote data and is recoverable after laptop disconnection.
        write_json(root/'transfer'/f'{name}.ready.json',{'run':name,'ready_at':utc()},root)
    for item in schedule:
        dest=root/'evaluation'/f'{item["condition"]}_seed{item["seed"]}'
        if (dest/'metrics.json').exists():continue
        subprocess.run([sys.executable,'-B','-u',str(root/'code'/'evaluate.py'),'--root',str(root),
                        '--condition',item['condition'],'--seed',str(item['seed'])],check=True)
    subprocess.run([sys.executable,'-B',str(root/'code'/'report.py'),'--root',str(root)],check=True)
    verify(root,True)
    write_json(root/'runs'/'suite_completed.json',{'completed_at':utc(),'runs':9},root)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--freeze',action='store_true');p.add_argument('--resume',action='store_true')
    a=p.parse_args();root=initialize(a.root)
    if a.freeze:freeze(root)
    else:suite(root,a.resume)
