"""Label-free cache quality review; does not select a split or model setting."""
import argparse
import collections
import random
from pathlib import Path
from common import *

def run(root):
    root=initialize(root)
    import torch
    import numpy as np
    from PIL import Image,ImageDraw
    from learning import Images
    from image_cache import path_for,RECIPE_ID
    cfg=read_json(root/'configs'/'common.json');base=dict(cfg);base.pop('image_cache_root',None)
    cached=dict(base,image_cache_root={'experiment_root':str(root),'recipe_id':RECIPE_ID})
    fixed=root/'manifests'/'fixed_split.csv'
    rows=read_csv(fixed if fixed.exists() else root/'audit'/'image_inventory.csv');selected=[]
    for c in CROPS:
        for y in ('0','1'):
            # Tomato has no previous train/valid/test folders. Unsplit entries
            # here are used solely for checking deterministic cache quality.
            allowed=('train','unsplit') if c=='tomato' else ('train',)
            candidates=[r for r in rows if r['crop']==c and str(r.get('binary_label',r['candidate_label']))==y
                and (r['split']=='train' if fixed.exists() else r['original_split'] in allowed) and path_for(root,r).exists()]
            if candidates:
                candidates.sort(key=lambda r:r['image_id']);selected.append(dict(candidates[0],binary_label=int(y),candidate_label=y))
    if len(selected)!=16:raise ValueError('Wait until all 16 source groups have ready cache examples')
    old=Images(selected,base,True,24680,0);new=Images(selected,cached,True,24680,0)
    sheet=Image.new('RGB',(896,16*245),'white');draw=ImageDraw.Draw(sheet);results=[]
    mean=np.array(cfg['mean']);std=np.array(cfg['std'])
    for i,r in enumerate(selected):
        a=old[i][0].permute(1,2,0).numpy()*std+mean;b=new[i][0].permute(1,2,0).numpy()*std+mean
        a=np.clip(a,0,1);b=np.clip(b,0,1)
        sheet.paste(Image.fromarray(np.uint8(a*255)),(0,i*245));sheet.paste(Image.fromarray(np.uint8(b*255)),(224,i*245))
        draw.text((450,i*245+20),r['crop']+' / '+r['candidate_label']+'\n'+r['image_id']+'\nleft original -> RRC224\nright 320px PNG -> RRC224',fill='black')
        results.append({'image_id':r['image_id'],'crop':r['crop'],'folder_label_candidate':r['candidate_label'],
                       'processed_relpath':r['processed_relpath'],'pixel_mae_0to1':float(np.abs(a-b).mean())})
    sheet.save(root/'review'/'cache_preprocessing_comparison.jpg',quality=92)
    write_csv(root/'audit'/'cache_preprocessing_comparison.csv',results,root)
    write_json(root/'reproducibility'/'cache_visual_check.json',{'created_at':utc(),'source_groups':16,
        'source_split':'fixed reviewed training split only' if fixed.exists() else 'original train where available; tomato unsplit for label-free cache quality only',
        'does_not_define_research_split':True,'recipe_id':RECIPE_ID,'mean_pixel_mae':float(np.mean([r['pixel_mae_0to1'] for r in results])),
        'review_required':'Check lesion visibility and cropping in review/cache_preprocessing_comparison.jpg before final protocol freeze.'},root)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);run(Path(p.parse_args().root))
