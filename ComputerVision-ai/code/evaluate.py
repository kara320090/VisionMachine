"""Test once with frozen protocol, validation-selected checkpoint and threshold .5."""
import argparse
from pathlib import Path
from common import *

def run(root,condition,seed):
    root=initialize(root)
    import torch
    from learning import model,seed_everything
    from train import load_protocol,predict
    from metrics import evaluate_records
    cfg,rows,lock=load_protocol(root,main=True)
    torch.set_num_threads(cfg['cpu_threads'])
    runroot=root/'runs'/f'{condition}_seed{seed}'
    done=read_json(runroot/'completed.json')
    ckpath=runroot/'checkpoints'/'best.pt'
    if digest(ckpath)!=done['best_checkpoint_sha256']:raise ValueError('Best checkpoint changed')
    out=root/'evaluation'/f'{condition}_seed{seed}'
    if out.exists():raise ValueError('Test output exists; use explicit new analysis for revisions')
    test=[r for r in rows if r['split']=='test' and r['evaluation_representative'].lower()=='true']
    seed_everything(seed);net=model(False).cuda()
    ck=torch.load(ckpath,map_location='cpu',weights_only=False)
    for k,v in [('split_sha256',lock['split_sha256']),('code_sha256',code_hash()),('config_sha256',digest(root/'configs'/'common.json'))]:
        if ck[k]!=v:raise ValueError('Test protocol mismatch: '+k)
    net.load_state_dict(ck['model']);records=predict(net,test,cfg,seed,'cuda');metrics=evaluate_records(records,.5)
    out.mkdir();write_csv(out/'predictions.csv',records,root)
    write_json(out/'metrics.json',dict(metrics,condition=condition,seed=seed,
               selected_epoch=done['selected_epoch'],checkpoint_sha256=digest(ckpath),
               split_sha256=lock['split_sha256'],evaluated_at=utc()),root)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--condition',choices=['A','B','C'],required=True);p.add_argument('--seed',type=int,required=True)
    a=p.parse_args();run(Path(a.root),a.condition,a.seed)
