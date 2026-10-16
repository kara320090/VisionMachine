"""Reconcile source annotations, not processed folder names, into evidence rows.

This produces supported mapping candidates and explicit unresolved rows. It does
not sign human review or admit unresolved images to a research training split.
"""
from __future__ import annotations
import argparse
import collections
import concurrent.futures
import hashlib
import json
import re
import zipfile
from pathlib import Path
from common import *

CLASS_MAP={'healthy':0,'fresh':0,'fresh cucumber':0,'fresh leaf':0,'good':0,'f_tomato':0,
           'segar':0,'fusarium':1,'powdery':1,'mildew':1,'wilted':1,'rotten':1,'bad':1,
           's_tomato':1,'busuk':1,'bacterial':1,'fungal':1,'powdery_mildew_on_lettuce':1,
           'wilt_and_leaf_blight_on_lettuce':1,'anthracnose':1,'bacterial wilt':1,'belly rot':1,
           'downy mildew':1,'pythium fruit rot':1}

def aihub_check(item):
    r,meta=item;out={'image_id':r['image_id'],'crop':r['crop'],'processed_relpath':r['processed_relpath'],
        'source':'aihub','status':'review_needed','proposed_binary_label':'','proposed_crop':r['crop'],
        'evidence':'','reason':'','capture_group_candidate':''}
    try:
        p=Path(meta['json_path']);data=read_json(p);ann=data['annotations'];desc=data['description']
        expected={'pepper':2,'cucumber':8,'lettuce':5}[r['crop']]
        if int(ann['crop'])!=expected or str(ann['crop'])!=meta['crop_code']:raise ValueError('crop code mismatch')
        if int(ann['disease'])!=int(meta['disease_code']):raise ValueError('disease code mismatch')
        if desc['image']!=Path(r['resolved_path']).name:raise ValueError('image JSON binding mismatch')
        label=int(int(ann['disease'])!=0)
        if int(ann['risk'])!=int(meta['risk']):raise ValueError('risk mismatch')
        if label==0 and int(ann['risk'])!=0:raise ValueError('normal disease code with nonzero risk')
        out.update(status='metadata_supported',proposed_binary_label=label,
            evidence=f'{p}; sha256={digest(p)}; annotations.crop={ann["crop"]},disease={ann["disease"]},risk={ann["risk"]}; image filename matched',
            reason='image-bound original JSON crop/disease codes')
        # Group conservatively by source session token and date. Filename fields
        # alone cannot certify independent plants, so this is a leakage boundary
        # proposal, never an independent plant count.
        parts=Path(desc['image']).stem.split('_');date=next((i for i,s in enumerate(parts) if re.fullmatch(r'20\d{6}',s)),None)
        if date is not None:out['capture_group_candidate']='aihub_'+r['crop']+'_'+'_'.join(parts[max(0,date-1):date+1])
        out['source_area_code']=ann.get('area','');out['source_date']=desc.get('date','')
    except Exception as e:out['reason']=f'{type(e).__name__}: {e}'
    return out

def run(root):
    root=initialize(root);rows=read_csv(root/'audit'/'image_inventory.csv');result=[];todo=[]
    aihub={}
    for crop in ('pepper','cucumber','lettuce'):
        for r in read_csv(DATA/crop/'aihub_manifest.csv'):
            if r['status']=='included':aihub[crop,r['image']]=r
    mendeley={r['processed_path'].split('/processed/',1)[-1]:r for r in read_csv(DATA/'cucumber/mendeley_good_bad_unique_manifest.csv')}
    # Inspect ZIP metadata and label bytes directly without extracting anything.
    zip_sources={};zip_meta=[]
    raw=Path('/home/user/data/ComputerVision_data/raw')
    for p in sorted((raw/'roboflow').rglob('*.zip')):
        try:
            z=zipfile.ZipFile(p);zip_sources[p.name[:-4]]=z
            for name in ('data.yaml','README.dataset.txt','README.roboflow.txt'):
                if name in z.namelist():zip_meta.append({'archive':str(p),'member':name,'sha256':hashlib.sha256(z.read(name)).hexdigest(),'text':z.read(name).decode(errors='replace')})
        except Exception as e:zip_meta.append({'archive':str(p),'error':str(e)})
    write_json(root/'audit'/'raw_source_metadata_snapshot.json',zip_meta,root)
    for r in rows:
        if r['source']=='aihub':
            meta=aihub.get((r['crop'],Path(r['resolved_path']).name))
            if meta:todo.append((r,meta));continue
        out={'image_id':r['image_id'],'crop':r['crop'],'processed_relpath':r['processed_relpath'],
             'source':r['source'],'original_class':r['original_class'],'status':'review_needed',
             'proposed_binary_label':'','proposed_crop':r['crop'],'evidence':r['label_evidence'],'reason':'',
             'capture_group_candidate':''}
        if r['error']:out['reason']='unreadable source image'
        elif r['source']=='mendeley_good_bad_unique':
            d=mendeley.get(r['processed_relpath'])
            if d and d['sha256']==r['sha256'] and d['class'] in ('good','bad'):
                out.update(status='metadata_supported',proposed_binary_label=CLASS_MAP[d['class']],
                           evidence=f'processed/cucumber/mendeley_good_bad_unique_manifest.csv; original class={d["class"]}; exact image SHA matches; source={d["original_path"]}',
                           reason='original class and image hash agree')
        elif r.get('source_yaml'):
            try:
                yp=Path(r['source_yaml']);archive=zip_sources.get(yp.parent.name)
                label=Path(r['label_path']);member=label.relative_to(yp.parent).as_posix()
                if archive is None or archive.read(member)!=label.read_bytes():raise ValueError('raw ZIP annotation mismatch')
                if archive.read('data.yaml')!=yp.read_bytes():raise ValueError('raw ZIP class definition mismatch')
                ids=json.loads(r['class_ids']);names=json.loads(r['class_names']);classes=[names[i] for i in ids]
                out['evidence']+=f'; raw ZIP {yp.parent.name}.zip:{member} bytes identical; class definition identical'
                if r['crop']=='kale':out['reason']='raw corroborates export, but crop identity/59/empty object labels still unresolved'
                elif not ids:out['reason']='empty object annotation cannot infer image normality'
                elif r['crop']=='rosemary' and classes==['Rosemary']:out['reason']='generic species name does not define healthy state'
                elif any(c.lower() not in ('healthy','healthy-pechay','bok_choy-healthy','rosemary') for c in classes):
                    out.update(status='metadata_supported',proposed_binary_label=1,reason='source disease/damage object explicitly annotated')
                else:out['reason']='healthy object annotation requires whole-image check'
            except Exception as e:out['reason']=f'{type(e).__name__}: {e}'
        else:
            cls=r['original_class'].lower()
            # The class is taken from the original resolved classification
            # directory, not from processed's normal/disease directory.
            if cls in CLASS_MAP:
                out.update(status='metadata_supported',proposed_binary_label=CLASS_MAP[cls],
                           reason='original classification directory has explicit health/disease meaning')
            else:out['reason']='source class meaning needs review'
        if any(flag in r['review_reasons'] for flag in ('exact_binary_or_crop_conflict','cross_crop_filename_candidate')):
            out.update(status='review_needed',reason=out['reason']+'; cross-image/crop conflict requires adjudication')
        result.append(out)
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        for i,r in enumerate(pool.map(aihub_check,todo)):
            result.append(r)
            if (i+1)%5000==0:print(f'Source JSON verified {i+1}/{len(todo)}',flush=True)
    for z in zip_sources.values():z.close()
    result.sort(key=lambda r:r['image_id']);write_csv(root/'review'/'source_supported_mapping.csv',result,root)
    prior_labels={r['image_id']:int(r['candidate_label']) for r in rows}
    mismatches=[r for r in result if r['status']=='metadata_supported' and int(r['proposed_binary_label'])!=prior_labels[r['image_id']]]
    write_csv(root/'review'/'proven_folder_mapping_errors.csv',mismatches,root,
              ['image_id','crop','processed_relpath','source','original_class','status','proposed_binary_label','proposed_crop','evidence','reason','capture_group_candidate','source_area_code','source_date'])
    count=collections.Counter((r['crop'],r['status']) for r in result)
    summary={'created_at':utc(),'processed_entries_checked':len(result),'counts':[{'crop':c,'status':s,'images':n} for (c,s),n in sorted(count.items())],
        'proven_binary_folder_mapping_errors':len(mismatches),'source_files_modified':False,'unresolved_entries_not_admitted_to_training':True}
    write_json(root/'audit'/'label_source_validation_summary.json',summary,root);print(json.dumps(summary),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);run(Path(p.parse_args().root))
