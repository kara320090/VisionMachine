"""Immutable lossless downscaled cache outside all source directories.

This is a deterministic decode/EXIF/resize cache, not new training data and not
an augmentation. Manifest source IDs/hashes stay authoritative. The optional
recipe must be fixed for all A/B/C conditions before the pilot/protocol lock.
"""
from __future__ import annotations
import argparse
import concurrent.futures
import hashlib
import json
import os
import random
import time
from pathlib import Path
from common import *

RECIPE={'version':1,'format':'PNG','compress_level':1,'short_side':320,
        'interpolation':'PIL_BICUBIC','orientation':'EXIF_transpose_before_resize',
        'preserve_aspect_ratio':True,'only_downscale':True,'color':'RGB'}
RECIPE_ID=hashlib.sha256(json.dumps(RECIPE,sort_keys=True).encode()).hexdigest()[:16]

def path_for(root,row):
    sha=row['sha256']
    if len(sha)!=64 or any(c not in '0123456789abcdef' for c in sha):raise ValueError('Invalid source SHA')
    return safe_output(Path(root)/'cache'/'images'/RECIPE_ID/sha[:2]/(sha+'.png'),root)

def build_one(root,row):
    from PIL import Image,ImageOps
    dest=path_for(root,row)
    if dest.exists():return {'image_id':row['image_id'],'source_sha256':row['sha256'],'cache_path':str(dest.relative_to(root)),'state':'existing','bytes':dest.stat().st_size}
    source=input_path(row['processed_relpath']);st=source.stat()
    if st.st_size!=int(row['size_bytes']) or st.st_mtime_ns!=int(row['mtime_ns']):raise ValueError('Source changed since audit: '+str(source))
    with Image.open(source) as image:
        image=ImageOps.exif_transpose(image).convert('RGB')
        w,h=image.size;scale=min(1.,RECIPE['short_side']/min(w,h));size=(max(1,round(w*scale)),max(1,round(h*scale)))
        if size!=image.size:image=image.resize(size,Image.Resampling.BICUBIC)
        dest.parent.mkdir(parents=True,exist_ok=True)
        temp=dest.with_suffix(f'.{os.getpid()}.partial')
        image.save(temp,format='PNG',compress_level=RECIPE['compress_level']);os.replace(temp,dest)
    return {'image_id':row['image_id'],'source_sha256':row['sha256'],'cache_path':str(dest.relative_to(root)),
            'state':'created','bytes':dest.stat().st_size,'width':size[0],'height':size[1]}

def build(root,limit=0):
    root=initialize(root);rows=read_csv(research_inventory(root));unique={}
    for r in rows:
        if not r.get('error'):unique.setdefault(r['sha256'],r)
    rows=list(unique.values());random.Random(24680).shuffle(rows)
    if limit:rows=rows[:limit]
    started=time.monotonic();records=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        for i,result in enumerate(pool.map(lambda r:build_one(root,r),rows)):
            records.append(result)
            if (i+1)%1000==0:
                progress(root,{'stage':'lossless_image_cache','images_done':i+1,'images_total':len(rows),'recipe_id':RECIPE_ID})
                print(f'Cached {i+1}/{len(rows)}',flush=True)
    stamp='sample' if limit else 'full'
    write_csv(root/'audit'/f'image_cache_{stamp}.csv',records,root)
    result={'completed_at':utc(),'images':len(records),'bytes':sum(r['bytes'] for r in records),'seconds':time.monotonic()-started,
            'recipe':RECIPE,'recipe_id':RECIPE_ID,'source_files_modified':False,'scope':stamp,
            'note':'Cache changes effective resolution; apply only as a fixed common preprocessing decision, after visual/pilot checks.'}
    write_json(root/'reproducibility'/f'image_cache_{stamp}.json',result,root);print(json.dumps(result),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--limit',type=int,default=0);a=p.parse_args();build(Path(a.root),a.limit)
