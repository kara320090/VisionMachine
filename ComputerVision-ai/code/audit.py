"""Persist fresh image/label/source evidence without editing dataset files."""
from __future__ import annotations
import argparse
import collections
import concurrent.futures
import hashlib
import html
import json
import os
import re
import subprocess
import time
import zipfile
from pathlib import Path
from common import *

EXT = {'.jpg','.jpeg','.png','.bmp','.webp','.tif','.tiff'}

def walk_entries():
    seen_dirs = set()
    # Directory aliases are each part of the logical dataset. Ancestors, not a
    # global inode set, detect cycles while retaining distinct alias entries.
    def visit(folder, ancestors):
        real = folder.resolve()
        if real in ancestors:
            raise RuntimeError(f'Symlink cycle: {folder}')
        for p in sorted(folder.iterdir()):
            if p.is_dir():
                yield ('directory_link' if p.is_symlink() else 'directory', p)
                yield from visit(p, ancestors | {real})
            else:
                yield ('broken_link' if p.is_symlink() and not p.exists() else 'file', p)
    yield from visit(DATA, set())

def family(name):
    s = re.split(r'\.rf\.', Path(name).name, flags=re.I)[0]
    s = re.sub(r'\.(jpg|jpeg|png)$', '', s, flags=re.I)
    while re.search(r'_(jpg|jpeg|png)$', s, re.I):
        s = re.sub(r'_(jpg|jpeg|png)$', '', s, flags=re.I)
    return s.casefold()

def inspect_one(item):
    from PIL import Image
    from scipy.fft import dctn
    import numpy as np
    path, prior = item
    rel = path.relative_to(DATA).as_posix()
    parts = Path(rel).parts
    coarse = parts[1]
    row = {'image_id':hashlib.sha256(rel.encode()).hexdigest()[:24], 'processed_relpath':rel,
           'crop':parts[0], 'folder_state':coarse, 'candidate_label':0 if coarse=='normal' else 1,
           'fine_class':prior.get('fine_class', parts[2] if coarse!='normal' else 'normal'),
           'source':prior.get('source','unknown'), 'original_split':prior.get('original_split','unknown'),
           'resolved_path':str(path.resolve()), 'entry_is_link':path.is_symlink(),
           'filename_family':family(path.name), 'label_status':'review_needed',
           'label_evidence':'', 'review_reasons':'', 'binary_label':'', 'include':'pending',
           'parent_image_id':'', 'leakage_group_id':'', 'error':''}
    try:
        st = path.stat()
        row.update(size_bytes=st.st_size, mtime_ns=st.st_mtime_ns, inode=st.st_ino, device=st.st_dev)
        row['sha256'] = digest(path)
        row['prior_sha_matches'] = row['sha256'] == prior.get('sha256')
        with Image.open(path) as im:
            row.update(width=im.width,height=im.height,mode=im.mode,exif_orientation=im.getexif().get(274,1))
            im.load()
            a = np.asarray(im.convert('L').resize((32,32)), dtype=float)
            d = dctn(a, norm='ortho')[:8,:8].ravel()
            bits = d > np.median(d[1:])
            row['phash'] = f'{int("".join("1" if b else "0" for b in bits),2):016x}'
        reasons = []
        actual = path.resolve()
        source_yaml = next((a/'data.yaml' for a in actual.parents if (a/'data.yaml').exists()), None)
        if source_yaml:
            import yaml
            definition = yaml.safe_load(source_yaml.read_text()) or {}
            names = definition.get('names', [])
            names = [names[k] for k in sorted(names)] if isinstance(names,dict) else names
            label = actual.parent.parent/'labels'/(actual.stem+'.txt')
            raw_label = label.read_text() if label.exists() else None
            ids = sorted({int(float(l.split()[0])) for l in (raw_label or '').splitlines() if l.strip()})
            row.update(label_path=str(label), label_sha256=digest(label) if label.exists() else '',
                       source_yaml=str(source_yaml), source_yaml_sha256=digest(source_yaml),
                       class_ids=json.dumps(ids), class_names=json.dumps(names,ensure_ascii=False),
                       original_class='|'.join(names[i] for i in ids if 0<=i<len(names)),
                       annotation_status='missing' if raw_label is None else ('empty' if not raw_label.strip() else 'nonempty'))
            row['label_evidence'] = f'{source_yaml}; {label}; {row["original_class"]}'
            if not names or not ids: reasons.append('empty_or_missing_object_annotation')
            if any(i<0 or i>=len(names) for i in ids): reasons.append('invalid_class_id')
            if coarse=='normal': reasons.append('object_annotation_does_not_prove_whole_image_normal')
            if row['crop']=='kale': reasons.append('kale_crop_identity_and_class_meaning')
            if row['crop']=='rosemary' and coarse=='normal': reasons.append('generic_Rosemary_class')
        elif row['source']=='aihub':
            row['label_evidence'] = 'AIHub CSV/JSON code mapping requires source-rule review'
            row['original_class'] = row['fine_class']
        else:
            row['original_class'] = actual.parent.name
            row['label_evidence'] = f'Classification directory: {actual.parent}'
        row['review_reasons'] = '|'.join(reasons or ['source_rule_and_capture_group_review'])
    except Exception as e:
        row['error'] = f'{type(e).__name__}: {e}'
        row['review_reasons'] = 'read_or_decode_error'
    return row

def raw_evidence(root):
    out=[]
    for p in sorted(Path('/home/user/data/ComputerVision_data/raw').rglob('*.zip')):
        item={'path':str(p),'size_bytes':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns}
        try:
            with zipfile.ZipFile(p) as z:
                entries=z.infolist()
                item['entries']=len(entries)
                item['extensions']=dict(collections.Counter(Path(n.filename).suffix.lower() for n in entries))
                item['top_paths']=collections.Counter('/'.join(n.filename.split('/')[:3]) for n in entries).most_common(25)
                meta={}
                for n in entries:
                    if Path(n.filename).name in ('data.yaml','README.dataset.txt','README.roboflow.txt'):
                        meta[n.filename]=z.read(n).decode(errors='replace')
                item['metadata']=meta
                if '/kale/' in str(p) or '/rosemary/' in str(p) or '/bok_choy/' in str(p):
                    labels=[n for n in entries if '/labels/' in n.filename and n.filename.endswith('.txt')]
                    item['label_entries']=len(labels)
                    item['empty_label_entries']=sum(not z.read(n).strip() for n in labels)
                    item['label_class_counts']=dict(collections.Counter(l.split()[0] for n in labels for l in z.read(n).decode(errors='replace').splitlines() if l.strip()))
        except Exception as e:
            item['error']=f'{type(e).__name__}: {e}'
            # Listing only: no extraction, archive repair or modification.
            try:
                result=subprocess.run(['7z','l','-slt',str(p)],capture_output=True,text=True,timeout=90)
                target=root/'audit'/'raw_kale_7z_listing.txt'
                target.write_text(result.stdout+'\nSTDERR\n'+result.stderr)
                item['listing_exit_code']=result.returncode
                item['listing_report']=str(target.relative_to(root))
            except Exception as ex:
                item['listing_error']=str(ex)
        out.append(item)
    write_json(root/'audit'/'raw_archive_evidence.json',out,root)

def candidates(rows, root):
    by_sha=collections.defaultdict(list); by_name=collections.defaultdict(list)
    for r in rows:
        if r.get('sha256'): by_sha[r['sha256']].append(r)
        by_name[r['filename_family']].append(r)
    exact=[]; edges=[]
    for sha, group in by_sha.items():
        if len(group)>1:
            collision=len({(r['crop'],r['candidate_label']) for r in group})>1
            for r in group:
                exact.append({'sha256':sha,'image_id':r['image_id'],'processed_relpath':r['processed_relpath'],
                              'crop':r['crop'],'candidate_label':r['candidate_label'],
                              'original_split':r['original_split'],'label_conflict':collision})
                if collision: r['review_reasons']+='|exact_binary_or_crop_conflict'
    for fam, group in by_name.items():
        if len(group)>1 and len({r.get('sha256') for r in group})>1:
            cross=len({r['crop'] for r in group})>1
            for r in group:
                edges.append({'candidate_type':'filename_only_NOT_confirmation','candidate_id':fam,
                              'image_id':r['image_id'],'crop':r['crop'],'candidate_label':r['candidate_label'],
                              'processed_relpath':r['processed_relpath'],'cross_crop':cross})
                if cross: r['review_reasons']+='|cross_crop_filename_candidate'
    write_csv(root/'audit'/'exact_duplicate_members.csv',exact,root)
    write_csv(root/'review'/'filename_candidates.csv',edges,root)
    return by_sha,by_name

def review_pages(rows, root):
    from PIL import Image,ImageOps
    review=root/'review'; thumbs=review/'thumbnails'; thumbs.mkdir(exist_ok=True)
    target=[r for r in rows if r['crop']=='kale' or 'exact_binary_or_crop_conflict' in r['review_reasons']]
    # Include all cross-crop candidates and a deterministic sample of normal
    # detection annotations. Review images are derivatives outside source data.
    target += [r for r in rows if r['crop']!='kale' and 'cross_crop_filename_candidate' in r['review_reasons']]
    for crop in ('rosemary','bok_choy'):
        target += [r for r in rows if r['crop']==crop and r['candidate_label']==0][:32]
    target=list({r['image_id']:r for r in target}.values())
    page=[]
    for r in target:
        if not r.get('error'):
            with Image.open(input_path(r['processed_relpath'])) as im:
                im=ImageOps.exif_transpose(im).convert('RGB'); im.thumbnail((240,200))
                im.save(thumbs/(r['image_id']+'.jpg'),quality=85)
        page.append('<article><img loading="lazy" src="thumbnails/'+r['image_id']+'.jpg"><pre>'+html.escape(
            json.dumps({k:r.get(k,'') for k in ('image_id','crop','candidate_label','processed_relpath','original_class','annotation_status','review_reasons','filename_family')},ensure_ascii=False,indent=2))+'</pre></article>')
    (review/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Crop8 label review</title><style>body{font:15px sans-serif;margin:30px}main{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:16px}article{border:1px solid #bbb;padding:12px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}img{max-width:100%}</style><h1>8-crop evidence review — labels are NOT approved</h1><p>Thumbnails are review copies. Original files are unchanged. Folder labels and filename families are candidates, not confirmed truth or independent groups. Review decisions must cite evidence.</p><main>'+''.join(page)+'</main>',encoding='utf-8')
    write_csv(review/'decisions_template.csv',[{'image_id':r['image_id'],'action':'pending','crop':'',
              'binary_label':'','parent_image_id':'','leakage_group_id':'','reason':'','evidence':'','reviewer':'','reviewed_at':''} for r in target],root)
    return len(target)

def run(root,workers):
    root=initialize(root); start=time.monotonic()
    historical=read_csv('/home/user/data/ComputerVision_data/manifests/all_processed_manifest.csv')
    lookup={str(Path(r['processed_path']).relative_to('/home/data/ComputerVision_data/processed')):r for r in historical}
    paths=[];links=[];metadata=[]
    for kind,p in walk_entries():
        if p.is_symlink(): links.append({'path':str(p.relative_to(DATA)),'kind':kind,'target':os.readlink(p),'resolved':str(p.resolve()),'exists':p.exists()})
        if kind=='file' and p.suffix.lower() in EXT: paths.append(p)
        elif kind=='file' and p.suffix.lower() in ('.csv','.yaml','.yml','.txt','.json'):
            metadata.append({'path':str(p.relative_to(DATA)),'sha256':digest(p),'size_bytes':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns})
    write_csv(root/'audit'/'symlinks.csv',links,root)
    write_csv(root/'audit'/'metadata_inventory.csv',metadata,root)
    progress(root,{'stage':'audit','state':'running','images_total':len(paths),'images_done':0})
    rows=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        inputs=((p,lookup.get(p.relative_to(DATA).as_posix(),{})) for p in paths)
        for i,r in enumerate(pool.map(inspect_one,inputs)):
            rows.append(r)
            if (i+1)%1000==0:
                progress(root,{'stage':'audit','state':'running','images_total':len(paths),'images_done':i+1})
                print(f'Audited {i+1}/{len(paths)}',flush=True)
    by_sha,by_name=candidates(rows,root)
    write_csv(root/'audit'/'image_inventory.csv',rows,root)
    raw_evidence(root)
    n_review=review_pages(rows,root)
    counts=[]
    for crop in CROPS:
        for label in (0,1):
            sub=[r for r in rows if r['crop']==crop and r['candidate_label']==label]
            counts.append({'crop':crop,'candidate_label':label,'file_entries':len(sub),
                           'unique_sha256':len({r.get('sha256') for r in sub if r.get('sha256')}),
                           'filename_candidate_families':len({r['filename_family'] for r in sub}),
                           'verified_independent_groups':'UNKNOWN','validated_training_count':'PENDING'})
    write_csv(root/'tables'/'unvalidated_data_counts.csv',counts,root)
    summary={'created_at':utc(),'input_root':str(DATA),'resolved_input_root':str(DATA.resolve()),
             'file_entries':len(rows),'unique_sha256':len(by_sha),'excess_exact_entries':len(rows)-len(by_sha),
             'exact_duplicate_groups':sum(len(g)>1 for g in by_sha.values()),
             'cross_old_split_exact_groups':sum(len({r['original_split'] for r in g})>1 for g in by_sha.values()),
             'binary_or_crop_conflict_groups':sum(len({(r['crop'],r['candidate_label']) for r in g})>1 for g in by_sha.values()),
             'decode_errors':sum(bool(r.get('error')) for r in rows),'prior_sha_disagreements':sum(not r.get('prior_sha_matches',False) for r in rows),
             'directory_symlinks':sum(r['kind']=='directory_link' for r in links),
             'file_symlinks':sum(r['kind']=='file' for r in links),'broken_links':sum(not r['exists'] for r in links),
             'logical_bytes':sum(r.get('size_bytes',0) for r in rows),'modes':dict(collections.Counter(r.get('mode') for r in rows)),
             'independent_original_group_count':None,'review_thumbnail_count':n_review,
             'elapsed_seconds':time.monotonic()-start,'code_sha256':code_hash(),
             'inventory_sha256':digest(root/'audit'/'image_inventory.csv'),
             'research_status':'BLOCKED_PENDING_LABEL_AND_CAPTURE_GROUP_EVIDENCE',
             'eight_crops_required':True,'source_policy':'processed images only; raw inspected for correction evidence; no raw images silently added'}
    write_json(root/'audit'/'summary.json',summary,root)
    write_json(root/'review'/'approval.json',{'approved':False,'inventory_sha256':summary['inventory_sha256'],
              'decisions_sha256':'','group_review_sha256':'','reviewer':'','evidence':'','reviewed_at':'',
              'required_crops':list(CROPS)},root)
    progress(root,dict(stage='audit',state='completed',summary=summary))
    print(json.dumps(summary,ensure_ascii=False),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--root',required=True); ap.add_argument('--workers',type=int,default=6)
    args=ap.parse_args(); run(Path(args.root),args.workers)
