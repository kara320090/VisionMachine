"""Time image loading/transforms only. No optimizer, labels or accuracy used."""
import argparse
import random
import time
from pathlib import Path
from common import *

def run(root,use_cache=False,available=False):
    root=initialize(root)
    import torch
    from learning import loader
    cfg=read_json(root/'configs'/'common.json')
    if use_cache:
        from image_cache import RECIPE_ID
        cfg['image_cache_root']={'recipe_id':RECIPE_ID,'experiment_root':str(root)}
    rows=[r for r in read_csv(root/'audit'/'image_inventory.csv') if r['original_split']=='train' and not r['error']]
    if available:
        from image_cache import path_for
        rows=[r for r in rows if path_for(root,r).exists()]
        if len(rows)<1024:raise ValueError('At least 1024 ready cached images needed for timing')
    random.Random(24680).shuffle(rows);rows=rows[:4096]
    # Placeholder targets satisfy the data adapter but are NEVER used for loss,
    # optimizer updates, prediction or metrics. This is an IO timing diagnostic.
    rows=[dict(r,binary_label=0) for r in rows]
    torch.set_num_threads(4);results=[]
    for train in (True,False):
        data=loader(rows,cfg,train,24680)
        start=time.perf_counter();measured=None;seen=0;batch_times=[];prior=start
        for i,(x,_,_,_) in enumerate(data):
            # Include pinned-memory copy cost; no model forward or training.
            dev=x.cuda(non_blocking=True);torch.cuda.synchronize();now=time.perf_counter()
            if i==7:measured=now;seen=0
            elif i>=8:seen+=len(x);batch_times.append(now-prior)
            prior=now
        end=time.perf_counter()
        results.append({'pipeline':'training_augmentation' if train else 'evaluation_preprocessing',
            'input_entries':len(rows),'measured_images':seen,'measured_seconds':end-measured,
            'images_per_second':seen/(end-measured),'total_seconds_including_startup':end-start,
            'measured_batches':len(batch_times),'batch_size':cfg['batch_size'],'workers':cfg['workers']})
        print(json.dumps(results[-1]),flush=True)
    write_json(root/'reproducibility'/('io_speed_cached_available.json' if available else 'io_speed_cached.json' if use_cache else 'io_speed_diagnostic.json'),{'created_at':utc(),'results':results,
        'images_selected_from':'current original_split=train entries only, shuffled seed24680',
        'research_training_performed':False,'labels_used':False,'input_root':str(DATA),'ready_cache_subset':available,
        'limitations':'One 4096-image sample; filesystem cache state and final source mix may differ. No model overlaps this IO diagnostic.'},root)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--cache',action='store_true');p.add_argument('--available-cache',action='store_true');a=p.parse_args();run(Path(a.root),a.cache or a.available_cache,a.available_cache)
