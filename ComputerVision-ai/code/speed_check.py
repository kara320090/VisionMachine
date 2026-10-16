"""Hardware-only model selection diagnostic, not a research experiment."""
import argparse
import gc
import statistics
import time
from pathlib import Path
from common import *

def run(root):
    root=initialize(root)
    import torch
    from torch import nn
    from torchvision import models
    from learning import seed_everything
    torch.set_num_threads(4);seed_everything(24680)
    rows=[]
    for name in ['efficientnet_b0','mobilenet_v3_large','resnet18','mobilenet_v3_small','shufflenet_v2_x1_0']:
        net=getattr(models,name)(weights=None)
        if name=='efficientnet_b0':net.classifier[1]=nn.Linear(net.classifier[1].in_features,2)
        elif name.startswith('mobilenet_v3'):net.classifier[-1]=nn.Linear(net.classifier[-1].in_features,2)
        else:net.fc=nn.Linear(net.fc.in_features,2)
        net=net.cuda().train();opt=torch.optim.AdamW(net.parameters(),lr=1e-4);scaler=torch.amp.GradScaler('cuda',init_scale=1024)
        x=torch.randn(64,3,224,224,device='cuda');y=torch.arange(64,device='cuda')%2
        torch.cuda.reset_peak_memory_stats();times=[];skips=0
        for step in range(45):
            torch.cuda.synchronize();start=time.perf_counter();opt.zero_grad(set_to_none=True)
            with torch.autocast('cuda',dtype=torch.float16):loss=nn.functional.cross_entropy(net(x),y)
            scaler.scale(loss).backward();scaler.unscale_(opt);torch.nn.utils.clip_grad_norm_(net.parameters(),1.)
            scale=scaler.get_scale();scaler.step(opt);scaler.update();skips+=int(scaler.get_scale()<scale)
            torch.cuda.synchronize()
            if step>=15:times.append(time.perf_counter()-start)
        result={'model':name,'batch_size':64,'warmup_steps':15,'measured_steps':30,'median_step_seconds':statistics.median(times),
            'mean_step_seconds':statistics.mean(times),'synthetic_images_per_second':64/statistics.mean(times),
            'max_memory_bytes':torch.cuda.max_memory_allocated(),'amp_skips_including_warmup':skips}
        net.eval();inference=[];single=[]
        with torch.inference_mode():
            for step in range(45):
                torch.cuda.synchronize();start=time.perf_counter()
                with torch.autocast('cuda',dtype=torch.float16):net(x)
                torch.cuda.synchronize()
                if step>=15:inference.append(time.perf_counter()-start)
            for step in range(45):
                torch.cuda.synchronize();start=time.perf_counter()
                with torch.autocast('cuda',dtype=torch.float16):net(x[:1])
                torch.cuda.synchronize()
                if step>=15:single.append(time.perf_counter()-start)
        result['inference_batch64_seconds']=statistics.median(inference)
        result['inference_single_image_seconds']=statistics.median(single)
        rows.append(result);print(json.dumps(result),flush=True)
        del net,opt,scaler,x,y,loss;gc.collect();torch.cuda.empty_cache()
    write_json(root/'reproducibility'/'model_speed_comparison_v2.json',{'created_at':utc(),'results':rows,
        'input':'random GPU-resident tensors, 64 x 3 x 224 x 224','weights':'random initialization, 2-class heads',
        'optimizer':'AdamW, full fine-tuning, AMP, deterministic algorithms, clip norm 1',
        'limitations':'Excludes file IO, decoding, augmentation, transfer, validation and checkpointing. One short measurement per model; not an epoch estimate or accuracy comparison.',
        'research_model_changed':False},root)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);run(Path(p.parse_args().root))
