"""Resumable, paired-seed EfficientNet-B0 experiments (no test access)."""
from __future__ import annotations
import argparse
import math
import os
import signal
import sys
import time
from pathlib import Path
from common import *

def load_protocol(root,main=False):
    from prepare import validate_split
    from source_guard import validate_source_corrections, correction_digest
    split=root/'manifests'/'fixed_split.csv';lock=read_json(root/'manifests'/'lock.json')
    if digest(split)!=lock['split_sha256']:raise ValueError('Fixed split changed')
    if digest(root/'review'/'approval.json')!=lock['approval_sha256']:raise ValueError('Approval changed')
    approval=read_json(root/'review'/'approval.json')
    if not approval.get('approved'):raise ValueError('Labels/group approval missing')
    for key,name in [('decisions_sha256','decisions.csv'),('group_review_sha256','groups.csv')]:
        if approval[key]!=digest(root/'review'/name):raise ValueError('Review changed')
    if approval['inventory_sha256']!=digest(research_inventory(root)):raise ValueError('Audit changed')
    cfg=read_json(root/'configs'/'common.json');rows=read_csv(split)
    validate_source_corrections(root,rows)
    if lock.get('source_corrections_sha256')!=correction_digest(root):
        raise ValueError('Source correction evidence changed after split freeze')
    validate_split(rows,cfg['minimum_eval_groups_per_crop_label'])
    if cfg['required_crops']!=list(CROPS):raise ValueError('All eight crops required')
    if main:
        freeze=read_json(root/'configs'/'protocol_lock.json')
        if freeze['config_sha256']!=digest(root/'configs'/'common.json') or freeze['split_sha256']!=lock['split_sha256']:
            raise ValueError('Protocol lock mismatch')
        if freeze['code_sha256']!=code_hash():raise ValueError('Code changed since protocol freeze')
    return cfg,rows,lock

def rng_state():
    import random,numpy as np,torch
    return {'python':random.getstate(),'numpy':np.random.get_state(),'torch':torch.get_rng_state(),
            'cuda':torch.cuda.get_rng_state_all() if torch.cuda.is_available() else []}

def restore_rng(state):
    import random,numpy as np,torch
    random.setstate(state['python']);np.random.set_state(state['numpy']);torch.set_rng_state(state['torch'].cpu())
    if state['cuda']:torch.cuda.set_rng_state_all([x.cpu() for x in state['cuda']])

def save_checkpoint(path,state,root):
    import torch
    path=safe_output(path,root);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix('.partial')
    with temp.open('wb') as f:
        torch.save(state,f);f.flush();os.fsync(f.fileno())
    os.replace(temp,path)

def predict(net,rows,cfg,seed,device):
    import torch
    from learning import loader
    net.eval();records=[]
    with torch.inference_mode():
        for x,y,w,indices in loader(rows,cfg,False,seed):
            logits=net(x.to(device,non_blocking=True));p=logits.softmax(1)[:,1].cpu().tolist()
            for i,prob in zip(indices.tolist(),p):
                r=rows[i]
                records.append({k:r[k] for k in ('image_id','processed_relpath','crop','binary_label','parent_image_id','leakage_group_id')}|{'p_abnormal':prob})
    return records

def run(root,condition,seed,phase='main',resume=False):
    root=initialize(root)
    import torch
    from learning import model,loader,seed_everything,sample_weights,weighted_loss,optimizer_for,set_epoch_lr
    from metrics import evaluate_records
    cfg,allrows,lock=load_protocol(root,main=phase=='main')
    torch.set_num_threads(cfg['cpu_threads'])
    if phase=='main' and seed not in cfg['training_seeds']:raise ValueError('Unregistered main seed')
    if phase=='pilot' and (seed!=cfg['pilot_seed'] or condition!='A'):raise ValueError('Pilot is A, reserved pilot seed')
    if not torch.cuda.is_available():raise ValueError('Research training requires configured GPU')
    device=torch.device('cuda:0')
    rows=[r for r in allrows if r['split']=='train']
    val=[r for r in allrows if r['split']=='validation' and r['evaluation_representative'].lower()=='true']
    weights=sample_weights(rows,condition)
    name=f'{condition}_seed{seed}' if phase=='main' else f'pilot_{condition}_seed{seed}'
    runroot=root/'runs'/name
    if (runroot/'completed.json').exists():raise ValueError('Run already completed; refusing overwrite')
    if runroot.exists() and not resume:raise ValueError('Run exists; explicit --resume required')
    runroot.mkdir(exist_ok=True);(runroot/'checkpoints').mkdir(exist_ok=True)
    config_hash=digest(root/'configs'/'common.json');code_digest=code_hash()
    write_json(runroot/'invocation.json',{'command':sys.argv,'seed':seed,'condition':condition,'phase':phase,
        'code_sha256':code_digest,'config_sha256':config_hash,'split_sha256':lock['split_sha256'],
        'started_or_resumed_at':utc(),'resume':resume,'config':cfg},root)
    with (runroot/'events.jsonl').open('a',encoding='utf-8') as f:
        f.write(json.dumps({'event':'resume' if resume else 'start','time':utc(),'command':sys.argv})+'\n')
    write_csv(runroot/'weights.csv',[{'image_id':r['image_id'],'crop':r['crop'],'binary_label':r['binary_label'],'weight':float(w)} for r,w in zip(rows,weights)],root)
    seed_everything(seed)
    net=model(pretrained=not resume).to(device)
    initial_hash=hashlib.sha256(b''.join(t.detach().cpu().numpy().tobytes() for t in net.state_dict().values())).hexdigest() if not resume else None
    head_only=True;opt=optimizer_for(net,cfg,True)
    scaler=torch.amp.GradScaler('cuda',enabled=cfg['amp'],init_scale=cfg['amp_initial_scale'])
    epoch=0;next_batch=0;best=-1.0;best_epoch=None;updates=0;skips=0;clips=0;consecutive_skips=0
    elapsed=0.;epoch_sum=0.;epoch_items=0;history=[];restart_count=0
    if resume:
        # Only load checkpoints produced by this experiment, never untrusted files.
        ck=torch.load(runroot/'checkpoints'/'last.pt',map_location='cpu',weights_only=False)
        for key,wanted in [('config_sha256',config_hash),('code_sha256',code_digest),('split_sha256',lock['split_sha256']),('condition',condition),('seed',seed)]:
            if ck[key]!=wanted:raise ValueError(f'Resume {key} mismatch')
        net.load_state_dict(ck['model']);head_only=ck['head_only'];opt=optimizer_for(net,cfg,head_only)
        opt.load_state_dict(ck['optimizer']);scaler.load_state_dict(ck['scaler'])
        epoch=ck['epoch'];next_batch=ck['next_batch'];best=ck['best'];best_epoch=ck['best_epoch']
        updates=ck['updates'];skips=ck['amp_skips'];clips=ck['gradient_clips'];elapsed=ck['elapsed_seconds']
        epoch_sum=ck['epoch_loss_sum'];epoch_items=ck['epoch_items'];history=ck['history'];initial_hash=ck['initial_model_sha256']
        restart_count=ck.get('restart_count',0)+1;restore_rng(ck['rng'])
    stopped=[False]
    signal.signal(signal.SIGTERM,lambda *_:stopped.__setitem__(0,True))
    signal.signal(signal.SIGINT,lambda *_:stopped.__setitem__(0,True))
    started=time.monotonic();last_save=started
    total_epochs=cfg['epochs'] if phase=='main' else min(3,cfg['epochs'])
    torch.cuda.reset_peak_memory_stats()
    def snapshot():
        return {'model':net.state_dict(),'optimizer':opt.state_dict(),'scaler':scaler.state_dict(),
            'scheduler':{'type':'epoch_cosine','epoch':epoch,'lr':[g['lr'] for g in opt.param_groups]},
            'head_only':head_only,'epoch':epoch,'next_batch':next_batch,'best':best,'best_epoch':best_epoch,
            'updates':updates,'amp_skips':skips,'gradient_clips':clips,'rng':rng_state(),'history':history,
            'epoch_loss_sum':epoch_sum,'epoch_items':epoch_items,'condition':condition,'seed':seed,
            'elapsed_seconds':elapsed+time.monotonic()-started,'config_sha256':config_hash,'code_sha256':code_digest,
            'split_sha256':lock['split_sha256'],'initial_model_sha256':initial_hash,'restart_count':restart_count,'saved_at':utc()}
    while epoch<total_epochs:
        wanted_head=epoch<cfg['head_epochs']
        if wanted_head!=head_only:
            head_only=wanted_head;opt=optimizer_for(net,cfg,head_only)
        set_epoch_lr(opt,cfg,epoch)
        net.train()
        if head_only:net.features.eval() # Freeze pretrained BN statistics too.
        batches=math.ceil(len(rows)/cfg['batch_size']);batch_start=next_batch
        for b,(x,y,w,_) in enumerate(loader(rows,cfg,True,seed,epoch,weights,next_batch),start=batch_start):
            x=x.to(device,non_blocking=True);y=y.to(device,non_blocking=True);w=w.to(device,dtype=torch.float32,non_blocking=True)
            opt.zero_grad(set_to_none=True)
            with torch.autocast('cuda',dtype=torch.float16,enabled=cfg['amp']):
                loss=weighted_loss(net(x),y,w)
            if not torch.isfinite(loss):raise FloatingPointError('Nonfinite training loss')
            scaler.scale(loss).backward();scaler.unscale_(opt)
            norm=torch.nn.utils.clip_grad_norm_(net.parameters(),cfg['clip_grad_norm'])
            if float(norm)>cfg['clip_grad_norm']:clips+=1
            scale=scaler.get_scale();scaler.step(opt);scaler.update()
            skipped=scaler.get_scale()<scale;skips+=int(skipped);updates+=int(not skipped)
            consecutive_skips=consecutive_skips+1 if skipped else 0
            if consecutive_skips>=20:raise FloatingPointError('20 consecutive AMP skips; abort rather than report an untrained model')
            epoch_sum+=float(loss.detach())*len(y);epoch_items+=len(y);next_batch=b+1
            if b%25==0:
                state={'stage':'training','run':name,'epoch':epoch+1,'batch':next_batch,'batches':batches,'updates':updates,'amp_skips':skips}
                write_json(runroot/'progress.json',dict(state,updated_at=utc()),root);progress(root,state)
            if stopped[0] or time.monotonic()-last_save>=cfg['checkpoint_interval_seconds']:
                save_checkpoint(runroot/'checkpoints'/'last.pt',snapshot(),root);last_save=time.monotonic()
                if stopped[0]:
                    write_json(runroot/'stopped.json',{'time':utc(),'epoch':epoch,'next_batch':next_batch,'updates':updates},root)
                    return 143
        records=predict(net,val,cfg,seed,device);scores=evaluate_records(records,cfg['threshold'])
        score=scores['equal_crop_binary_macro_f1'];improved=score>best
        if improved:best=score;best_epoch=epoch+1
        epoch_record={'epoch':epoch+1,'train_weighted_loss':epoch_sum/epoch_items,'validation':scores,
                      'updates':updates,'amp_skips':skips,'gradient_clips':clips,
                      'elapsed_seconds':elapsed+time.monotonic()-started,'lr':[g['lr'] for g in opt.param_groups]}
        history.append(epoch_record)
        with (runroot/'history.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(epoch_record)+'\n')
        finished_epoch=epoch+1;epoch+=1;next_batch=0;epoch_sum=0.;epoch_items=0
        ck=snapshot()
        save_checkpoint(runroot/'checkpoints'/'last.pt',ck,root)
        save_checkpoint(runroot/'checkpoints'/f'epoch_{finished_epoch:02d}.pt',ck,root)
        if improved:
            save_checkpoint(runroot/'checkpoints'/'best.pt',ck,root)
            write_csv(runroot/'best_validation_predictions.csv',records,root)
        write_json(runroot/'history.json',history,root)
        print(json.dumps(epoch_record),flush=True)
        last_save=time.monotonic()
        if stopped[0]:return 143
    result={'run':name,'condition':condition,'seed':seed,'phase':phase,'completed_at':utc(),
        'selected_epoch':best_epoch,'best_validation_equal_crop_binary_macro_f1':best,
        'epochs':total_epochs,'updates':updates,'amp_skips':skips,'gradient_clips':clips,
        'elapsed_seconds':elapsed+time.monotonic()-started,'max_gpu_memory_bytes':torch.cuda.max_memory_allocated(),
        'best_checkpoint_sha256':digest(runroot/'checkpoints'/'best.pt'),'initial_model_sha256':initial_hash,
        'split_sha256':lock['split_sha256'],'config_sha256':config_hash,'code_sha256':code_digest,
        'restart_count':restart_count,'transfer_pending':True}
    write_json(runroot/'completed.json',result,root)
    print(json.dumps(result),flush=True);return 0

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--condition',choices=['A','B','C'],required=True)
    p.add_argument('--seed',type=int,required=True);p.add_argument('--phase',choices=['pilot','main'],default='main');p.add_argument('--resume',action='store_true')
    a=p.parse_args()
    try:raise SystemExit(run(Path(a.root),a.condition,a.seed,a.phase,a.resume))
    except (ValueError,FileNotFoundError) as e:print('BLOCKED:',str(e));raise SystemExit(2)
