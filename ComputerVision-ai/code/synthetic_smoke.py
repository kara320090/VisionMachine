"""GPU plumbing test using random tensors; not a dataset experiment or metric."""
import argparse
import time
from pathlib import Path
from common import *

def run(root):
    root=initialize(root)
    import torch
    from learning import model,seed_everything,weighted_loss
    seed_everything(7654);torch.set_num_threads(4)
    net=model(pretrained=True).cuda().train()
    cfg=read_json(root/'configs'/'common.json')
    opt=torch.optim.AdamW(net.parameters(),lr=1e-4);scaler=torch.amp.GradScaler('cuda',init_scale=cfg['amp_initial_scale'])
    x=torch.randn(4,3,224,224,device='cuda');y=torch.tensor([0,1,0,1],device='cuda')
    before=net.classifier[1].weight.detach().clone();torch.cuda.reset_peak_memory_stats();start=time.monotonic()
    results=[]
    for cond,weights in [('A',[1.,1.,1.,1.]),('B',[.5,1.5,.5,1.5]),('C',[.25,.75,1.,2.])]:
        opt.zero_grad(set_to_none=True)
        with torch.autocast('cuda',dtype=torch.float16):logits=net(x);loss=weighted_loss(logits,y,torch.tensor(weights,device='cuda'))
        assert logits.shape==(4,2) and torch.isfinite(loss)
        scaler.scale(loss).backward();scaler.unscale_(opt);norm=torch.nn.utils.clip_grad_norm_(net.parameters(),1.)
        assert torch.isfinite(norm);scaler.step(opt);scaler.update()
        results.append({'condition':cond,'synthetic_loss':float(loss.detach()),'gradient_norm':float(norm)})
    torch.cuda.synchronize();assert not torch.equal(before,net.classifier[1].weight)
    cache=Path(os.environ['TORCH_HOME'])/'hub'/'checkpoints'/'efficientnet_b0_rwightman-7f5810bc.pth'
    write_json(root/'reproducibility'/'synthetic_gpu_smoke.json',{'status':'passed','kind':'synthetic_random_tensor_plumbing_only',
        'research_training_performed':False,'input_shape':[4,3,224,224],'output_shape':[4,2],'seconds':time.monotonic()-start,
        'max_gpu_memory_bytes':torch.cuda.max_memory_allocated(),'results':results,
        'pretrained_weights_sha256':digest(cache),'pretrained_weights_bytes':cache.stat().st_size},root)
    print('Synthetic GPU smoke passed; no research images or research results produced.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);run(Path(p.parse_args().root))
