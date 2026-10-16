"""Audit existing raw-derived kale files as candidates, never infer health labels.

Authorized by the user's subsequent request to check raw data if processed is
misclassified. This does not admit candidates to the training manifest.
"""
import argparse
import collections
import concurrent.futures
import hashlib
import html
import json
import re
import time
from pathlib import Path
from common import *

SOURCE='https://research.wur.nl/en/datasets/top-view-images-of-kale-brassica-oleracea/'

def inspect(p):
    from PIL import Image
    rel=p.relative_to(RAW_KALE).as_posix()
    r={'image_id':'raw_'+hashlib.sha256(rel.encode()).hexdigest()[:20],
       'processed_relpath':'raw-kale:'+rel,'input_kind':'raw_candidate','source_path':str(p),
       'resolved_path':str(p.resolve()),'crop':'kale','binary_label':'','candidate_label':'',
       'label_status':'review_needed','include':'pending','source':'wur_top_view_growth',
       'original_class':rel.split('/')[1],'source_url':SOURCE,'source_doi':'10.5281/zenodo.4315436',
       'review_reasons':'raw_health_state_not_annotated|repeated_plant_id_needs_verification',
       'parent_image_id':'','leakage_group_id':'','error':''}
    try:
        st=p.stat();r.update(size_bytes=st.st_size,mtime_ns=st.st_mtime_ns,sha256=digest(p))
        with Image.open(p) as im:im.load();r.update(width=im.width,height=im.height,mode=im.mode)
        day=re.search(r'Day (\d+)(b?)',rel);species=re.search(r'(?:Species |D\d+S)([12])',rel)
        individual=re.search(r'\((\d+)\)',p.stem)
        r['day']=int(day[1]) if day else ''
        r['stage']='b' if day and day[2] else 'a'
        r['species']=species[1] if species else ''
        r['candidate_individual_id']=f'WUR_{r["stage"]}_S{r["species"]}_{individual[1]}' if individual else ''
        r['independence_status']='filename grouping hypothesis; publisher describes 320 repeated plants'
    except Exception as e:r['error']=str(e)
    return r

def run(root):
    root=initialize(root);start=time.monotonic()
    paths=sorted(p for p in RAW_KALE.rglob('*') if p.is_file() and p.suffix.lower() in ('.jpg','.jpeg','.png'))
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(inspect,paths))
    write_csv(root/'audit'/'raw_kale_candidates.csv',rows,root)
    from PIL import Image,ImageOps,ImageDraw
    reps=[]
    for stage in ('a','b'):
        for species in ('1','2'):
            for day in (1,10,20):
                selected=[r for r in rows if (r['stage'],r['species'],r['day'])==(stage,species,day)]
                reps+=selected[:4]
    sheet=Image.new('RGB',(1200,((len(reps)+5)//6)*200),'white');draw=ImageDraw.Draw(sheet)
    for i,r in enumerate(reps):
        with Image.open(input_path(r['processed_relpath'])) as im:
            im=ImageOps.exif_transpose(im).convert('RGB');im.thumbnail((190,155))
            x=(i%6)*200;y=(i//6)*200;sheet.paste(im,(x,y));draw.text((x+3,y+157),r['candidate_individual_id']+'\nDay '+str(r['day']),fill='black')
    sheet.save(root/'review'/'raw_kale_examples.jpg',quality=90)
    summary={'candidate_images':len(rows),'unique_sha256':len({r['sha256'] for r in rows if r.get('sha256')}),
       'decode_errors':sum(bool(r['error']) for r in rows),'candidate_plant_ids':len({r['candidate_individual_id'] for r in rows if r.get('candidate_individual_id')}),
       'source_url':SOURCE,'source_doi':'10.5281/zenodo.4315436','source_describes':'320 plants, two varieties, 20 days; no binary disease labels',
       'local_archive_status':'Python ZIP directory validation fails; extracted files audited separately, archive equivalence not certified',
       'training_images_added':0,'health_labels_assigned':0,'duration_seconds':time.monotonic()-start,
       'next_requirement':'Verify plant identity across days and judge visible normal/abnormal status; do not label all growth images normal.'}
    write_json(root/'audit'/'raw_kale_summary.json',summary,root);print(json.dumps(summary),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);run(Path(p.parse_args().root))
