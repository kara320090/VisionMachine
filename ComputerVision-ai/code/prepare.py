"""Explicit evidence adjudication and immutable, eight-crop grouped splits."""
import argparse
import collections
import hashlib
from pathlib import Path
from common import *
from source_guard import validate_source_corrections, correction_digest

def approved_rows(root):
    audit=research_inventory(root)
    approval=read_json(root/'review'/'approval.json')
    if not approval.get('approved') or approval.get('inventory_sha256')!=digest(audit):
        raise ValueError('BLOCKED: current inventory needs evidence-backed label/group approval.')
    if not approval.get('reviewer') or not approval.get('evidence') or not approval.get('reviewed_at'):
        raise ValueError('Approval must record reviewer, date and evidence.')
    if approval.get('required_crops')!=list(CROPS):
        raise ValueError('All eight specified crops are mandatory.')
    decisions=root/'review'/'decisions.csv'; groups=root/'review'/'groups.csv'
    if approval.get('decisions_sha256')!=digest(decisions) or approval.get('group_review_sha256')!=digest(groups):
        raise ValueError('Review files do not match approval hashes.')
    rows=read_csv(audit); edits=read_csv(decisions); grouping=read_csv(groups)
    def unique_map(items):
        result={r['image_id']:r for r in items}
        if len(result)!=len(items): raise ValueError('Duplicate review image_id')
        return result
    edits=unique_map(edits); grouping=unique_map(grouping)
    identifiers={r['image_id'] for r in rows}
    if set(edits)!=identifiers: raise ValueError('Every inventory item needs a recorded include/exclude decision.')
    result=[]; excluded=[]
    for r in rows:
        d=edits[r['image_id']]
        if not d.get('evidence') or not d.get('reviewer'): raise ValueError('Decision lacks evidence/reviewer')
        if d['action']=='exclude':
            if not d.get('reason'): raise ValueError('Exclusion reason required')
            excluded.append(dict(r,exclusion_reason=d['reason'])); continue
        if d['action'] not in ('include','relabel'): raise ValueError('Unresolved review decision')
        if r['error']: raise ValueError('Cannot include unreadable image')
        if d['crop'] not in CROPS or d['binary_label'] not in ('0','1'): raise ValueError('Invalid reviewed label')
        g=grouping.get(r['image_id'],{})
        if g.get('status')!='reviewed' or not all(g.get(k) for k in ('parent_image_id','leakage_group_id','evidence','reviewer')):
            raise ValueError('Original/scene grouping is not reviewed')
        result.append(dict(r,crop=d['crop'],binary_label=int(d['binary_label']),label_status='approved',
                           label_evidence=d['evidence'],include=True,parent_image_id=g['parent_image_id'],
                           label_provenance=d.get('label_provenance','source_metadata'),
                           independent_expert_validation=d.get('independent_expert_validation','not_claimed'),
                           leakage_group_id=g['leakage_group_id'],group_evidence=g['evidence'],
                           biological_independence_status=g.get('independence_status','unknown')))
    validate_source_corrections(root,result)
    write_csv(root/'review'/'excluded_items.csv',excluded,root)
    return result

def deduplicate(rows):
    """Deduplicate only confirmed exact files / same-photo derivatives."""
    sha_groups=collections.defaultdict(list); parents=collections.defaultdict(list)
    for r in rows: sha_groups[r['sha256']].append(r)
    for sha,g in sha_groups.items():
        if len({(r['crop'],int(r['binary_label'])) for r in g})>1: raise ValueError(f'Exact label conflict: {sha}')
        if len({r['leakage_group_id'] for r in g})>1: raise ValueError('Exact duplicates assigned to different scene groups')
        if len({r['parent_image_id'] for r in g})>1: raise ValueError('Exact duplicates assigned to different original photos')
    for r in rows: parents[r['parent_image_id']].append(r)
    kept=[]
    for parent,g in parents.items():
        if len({(r['crop'],int(r['binary_label']),r['leakage_group_id']) for r in g})>1:
            raise ValueError(f'Original-photo conflict: {parent}')
        # Explicit evidence of an original outranks size. This flag is optional;
        # no inference that high resolution necessarily means original.
        g=sorted(g,key=lambda r:(r.get('verified_original','false')!='true',
                                -int(r['width'])*int(r['height']),r['processed_relpath']))
        kept.append(g[0])
    return sorted(kept,key=lambda r:r['image_id'])

def validate_split(rows,minimum=10):
    group_splits=collections.defaultdict(set); sha_splits=collections.defaultdict(set); parent_splits=collections.defaultdict(set)
    counts=collections.defaultdict(set)
    for r in rows:
        if r['crop'] not in CROPS or int(r['binary_label']) not in (0,1): raise ValueError('Bad crop or binary label')
        if r['split'] not in ('train','validation','test'): raise ValueError('Bad split')
        group_splits[r['leakage_group_id']].add(r['split'])
        sha_splits[r['sha256']].add(r['split']); parent_splits[r['parent_image_id']].add(r['split'])
        counts[(r['crop'],int(r['binary_label']),r['split'])].add(r['leakage_group_id'])
    if any(len(s)>1 for m in (group_splits,sha_splits,parent_splits) for s in m.values()):
        raise ValueError('Data leakage across splits')
    failures=[]
    for c in CROPS:
        for y in (0,1):
            for s in ('train','validation','test'):
                n=len(counts[c,y,s]); need=1 if s=='train' else minimum
                if n<need: failures.append(f'{c}/{y}/{s}: {n} < {need}')
    if failures: raise ValueError('Eight-crop feasibility gate failed: '+'; '.join(failures))
    return counts

def split_rows(rows,seed=20261016,minimum=10):
    from sklearn.model_selection import StratifiedGroupKFold
    import numpy as np
    labels=np.array([CROPS.index(r['crop'])*2+int(r['binary_label']) for r in rows])
    groups=np.array([r['leakage_group_id'] for r in rows])
    folds=StratifiedGroupKFold(n_splits=5,shuffle=True,random_state=seed)
    assignment={}
    for fold,(_,ix) in enumerate(folds.split(np.zeros(len(rows)),labels,groups)):
        for i in ix: assignment[int(i)]='validation' if fold==0 else ('test' if fold==1 else 'train')
    result=[dict(r,split=assignment[i]) for i,r in enumerate(rows)]
    validate_split(result,minimum)
    # One fixed, label-aware but model-independent representative per scene,
    # crop and state for evaluation. Train keeps distinct original photos.
    chosen={}
    for r in result:
        if r['split']=='train': continue
        key=(r['leakage_group_id'],r['crop'],r['binary_label'])
        rank=(-int(r['width'])*int(r['height']),r['processed_relpath'])
        if key not in chosen or rank<chosen[key][0]: chosen[key]=(rank,r['image_id'])
    ids={v[1] for v in chosen.values()}
    return [dict(r,evaluation_representative=r['image_id'] in ids) for r in result]

def run(root):
    root=initialize(root); target=root/'manifests'/'fixed_split.csv'
    if target.exists(): raise ValueError('Fixed split already exists. Use a new experiment to revise it.')
    cfg=read_json(root/'configs'/'common.json')
    rows=deduplicate(approved_rows(root))
    result=split_rows(rows,cfg['split_seed'],cfg['minimum_eval_groups_per_crop_label'])
    write_csv(target,result,root)
    counts=[]
    for c in CROPS:
        for y in (0,1):
            for s in ('train','validation','test'):
                sub=[r for r in result if (r['crop'],r['binary_label'],r['split'])==(c,y,s)]
                counts.append({'crop':c,'binary_label':y,'split':s,'images':len(sub),
                    'reviewed_leakage_groups':len({r['leakage_group_id'] for r in sub}),
                    'evaluation_representatives':sum(r['evaluation_representative'] for r in sub)})
    write_csv(root/'tables'/'fixed_split_counts.csv',counts,root)
    low=sorted(CROPS,key=lambda c:(sum(r['crop']==c and r['split']=='train' for r in result),c))[:2]
    write_json(root/'manifests'/'lock.json',{'created_at':utc(),'split_sha256':digest(target),
        'approval_sha256':digest(root/'review'/'approval.json'),'code_sha256':code_hash(),
        'source_corrections_sha256':correction_digest(root),
        'ratios':[.6,.2,.2],'seed':cfg['split_seed'],'low_data_crops':low},root)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);args=p.parse_args()
    try: run(Path(args.root))
    except ValueError as e: print(str(e)); raise SystemExit(2)
