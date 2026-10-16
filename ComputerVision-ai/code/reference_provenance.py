"""Check suspected source-label conflicts against the authors' public archive.

Reference pixels are read into memory only and never saved or added to any
training source. Saved evidence contains URLs, source classes, content hashes,
and image correspondence diagnostics. pHash alone never confirms a match.
"""
from __future__ import annotations
import argparse
import concurrent.futures
import hashlib
import io
import json
import urllib.request
import urllib.parse
from pathlib import Path
from common import *

REPO='spMohanty/PlantVillage-Dataset'

def get(url,limit=8*1024*1024):
    if not url.startswith(('https://api.github.com/repos/'+REPO+'/',
                           'https://raw.githubusercontent.com/'+REPO+'/')):raise ValueError('Unregistered reference URL')
    request=urllib.request.Request(url,headers={'User-Agent':'Crop8-source-provenance-check','Accept':'application/vnd.github+json'})
    with urllib.request.urlopen(request,timeout=45) as r:data=r.read(limit+1)
    if len(data)>limit:raise ValueError('Reference exceeds allowed response size')
    return data

def run(root):
    root=initialize(root)
    import numpy as np
    from PIL import Image
    from scipy.fft import dctn
    rows=[r for r in read_csv(root/'audit'/'image_inventory.csv') if r['crop']=='kale' and r['source']=='roboflow_v5']
    phashes=np.array([int(r['phash'],16) for r in rows],dtype=np.uint64)
    local={}
    for r in rows:
        with Image.open(input_path(r['processed_relpath'])) as im:local[r['image_id']]=np.asarray(im.convert('RGB').resize((256,256)),dtype=float)/255
    index=json.loads(get('https://api.github.com/repos/'+REPO+'/contents/raw/color?ref=master'))
    source=next(x for x in index if x['name']=='Squash___Powdery_mildew')
    tree=json.loads(get('https://api.github.com/repos/'+REPO+'/git/trees/'+source['sha']))
    items=[x for x in tree['tree'] if x['type']=='blob' and x['path'].lower().endswith(('.jpg','.jpeg','.png'))]
    write_json(root/'audit'/'reference_source_index.json',{'fetched_at':utc(),'repository':REPO,'class':source['name'],
        'tree_sha':source['sha'],'entries':len(items),'reference_images_used_for_training':0,
        'items':items},root)
    def compare(item):
        path='raw/color/'+source['name']+'/'+item['path'];url='https://raw.githubusercontent.com/'+REPO+'/master/'+urllib.parse.quote(path)
        try:
            data=get(url,2*1024*1024)
            blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
            if blob!=item['sha']:raise ValueError('Git content hash mismatch')
            with Image.open(io.BytesIO(data)) as im:
                a=np.asarray(im.convert('L').resize((32,32)),dtype=float);d=dctn(a,norm='ortho')[:8,:8].ravel();bits=d>np.median(d[1:])
                ph=int(''.join('1' if b else '0' for b in bits),2)
                distances=[(int(h)^ph).bit_count() for h in phashes]
                candidates=[i for i,dist in enumerate(distances) if dist<=8]
                if not candidates:return []
                ref=np.asarray(im.convert('RGB').resize((256,256)),dtype=float)/255
            found=[]
            for i in candidates:
                r=rows[i];a=local[r['image_id']]
                found.append({'local_image_id':r['image_id'],'processed_relpath':r['processed_relpath'],
                    'local_sha256':r['sha256'],'reference_url':url,
                    'reference_github_url':'https://github.com/'+REPO+'/blob/master/'+urllib.parse.quote(path),
                    'reference_class':source['name'],'reference_sha256':hashlib.sha256(data).hexdigest(),
                    'reference_git_blob_sha':blob,'phash_distance':distances[i],
                    'pixel_mae_after_resize':float(np.abs(a-ref).mean()),
                    'pixel_correlation':float(np.corrcoef(a.ravel(),ref.ravel())[0,1]),
                    'status':'correspondence_candidate_requires_visual_review','reference_pixels_saved':False})
            return found
        except Exception as e:return [{'reference_url':url,'error':f'{type(e).__name__}: {e}'}]
    matches=[];errors=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        for i,result in enumerate(pool.map(compare,items)):
            for row in result:
                (errors if 'error' in row else matches).append(row)
            if (i+1)%200==0:print(f'Reference images checked {i+1}/{len(items)}; candidates {len(matches)}',flush=True)
    matches.sort(key=lambda r:(r['pixel_mae_after_resize'],r['phash_distance']))
    write_csv(root/'review'/'reference_correspondence_candidates.csv',matches,root)
    write_json(root/'audit'/'reference_provenance_summary.json',{'completed_at':utc(),'references_checked':len(items),
        'reference_class':source['name'],'local_images_checked':len(rows),'candidate_pairs':len(matches),
        'distinct_local_candidates':len({r['local_image_id'] for r in matches}),
        'very_close_pixel_candidates':sum(r['pixel_mae_after_resize']<.03 and r['pixel_correlation']>.98 for r in matches),
        'errors':errors,'reference_images_saved_or_admitted_to_training':0,
        'conclusion':'Inspect candidate photographs and original source class before adjudicating crop identity; no pHash-only relabeling.'},root)
    print(json.dumps({'candidate_pairs':len(matches),'distinct_local_candidates':len({r['local_image_id'] for r in matches}),'errors':len(errors),'best':matches[:3]}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);run(Path(p.parse_args().root))
