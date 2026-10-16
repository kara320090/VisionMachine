"""Train-only throughput and A/B/C finite-gradient checks; never opens test images."""
import argparse
import time
from pathlib import Path
from common import *

def run(root,batches=100):
    root=initialize(root)
    import torch
    from train import load_protocol
    from learning import model,loader,sample_weights,weighted_loss,seed_everything
    cfg,rows,lock=load_protocol(root);train=[r for r in rows if r['split']=='train']
    seed_everything(cfg['pilot_seed']);net=model().cuda();net.train()
    torch.cuda.reset_peak_memory_stats();opt=torch.optim.AdamW(net.parameters(),lr=cfg['backbone_lr'])
    scaler=torch.amp.GradScaler('cuda',enabled=cfg['amp'],init_scale=cfg['amp_initial_scale']);records=[]
    for condition in 'ABC':
        weights=sample_weights(train,condition)
        seen=0;wait_seconds=0.;started=None;prior=time.monotonic();finite=True
        limit=batches+10 if condition=='A' else 3
        for step,(x,y,w,_) in enumerate(loader(train,cfg,True,cfg['pilot_seed'],0,weights)):
            if step>=limit:break
            wait_seconds+=time.monotonic()-prior
            x=x.cuda(non_blocking=True);y=y.cuda(non_blocking=True);w=w.cuda().float()
            opt.zero_grad(set_to_none=True)
            with torch.autocast('cuda',enabled=cfg['amp'],dtype=torch.float16):loss=weighted_loss(net(x),y,w)
            if not torch.isfinite(loss):raise FloatingPointError('Benchmark loss is not finite')
            scaler.scale(loss).backward();scaler.unscale_(opt)
            grad=torch.nn.utils.clip_grad_norm_(net.parameters(),cfg['clip_grad_norm'])
            finite=finite and bool(torch.isfinite(grad));scaler.step(opt);scaler.update();torch.cuda.synchronize()
            if condition=='A' and step==9:started=time.monotonic();seen=0;wait_seconds=0.
            elif condition=='A' and step>=10:seen+=len(y)
            prior=time.monotonic()
        result={'condition':condition,'finite_gradient':finite,'peak_memory_bytes':torch.cuda.max_memory_allocated()}
        if started is not None:
            elapsed=time.monotonic()-started
            result.update(measured_images=seen,measured_seconds=elapsed,images_per_second=seen/elapsed,
                          dataloader_wait_seconds=wait_seconds,training_epoch_seconds=len(train)/(seen/elapsed))
        records.append(result)
    write_json(root/'reproducibility'/'benchmark.json',{'created_at':utc(),'results':records,'batch_size':cfg['batch_size'],
            'split_sha256':lock['split_sha256'],'config_sha256':digest(root/'configs'/'common.json'),
            'note':'No test data used; validation timing comes from pilot.'},root)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--batches',type=int,default=100);a=p.parse_args();run(Path(a.root),a.batches)
