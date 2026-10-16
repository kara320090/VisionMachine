"""Build review proposals or apply explicit source rules plus per-image decisions.

Rules are a review input, not a default auto-labeler. High-risk rows always need
per-image decisions. No command here signs approval on behalf of the user.
"""
import argparse
import collections
import hashlib
from pathlib import Path
from common import *

HIGH_RISK=('raw_health_state','kale_crop_identity','empty_or_missing','exact_binary_or_crop_conflict',
           'cross_crop_filename','generic_Rosemary','invalid_class','read_or_decode')

def proposals(root):
    rows=read_csv(research_inventory(root))
    target=root/'review'/'all_decisions_proposed.csv'
    if target.exists():raise ValueError('Review proposals already exist; refusing overwrite')
    write_csv(target,[{'image_id':r['image_id'],'action':'pending','crop':r['crop'],
        'binary_label':r['candidate_label'],'reason':'','evidence':'','reviewer':'',
        'review_reasons':r['review_reasons']} for r in rows],root)
    # Filename names are deliberately only suggestions. No same-photo
    # deduplication or independent-group claim follows from these strings.
    write_csv(root/'review'/'groups_proposed.csv',[{'image_id':r['image_id'],'status':'pending',
        'parent_image_id':'sha_'+r['sha256'][:24],
        'leakage_group_id':'candidate_'+hashlib.sha256((r.get('candidate_individual_id') or r.get('filename_family') or r['image_id']).encode()).hexdigest()[:24],
        'evidence':'UNVERIFIED filename candidate; inspect derivatives and repeated captures',
        'reviewer':''} for r in rows],root)
    buckets=collections.defaultdict(list)
    for r in rows:buckets[(r['crop'],r['source'],r['original_class'])].append(r)
    write_csv(root/'review'/'source_rule_candidates.csv',[{'crop':c,'source':s,'original_class':o,
        'entries':len(g),'candidate_labels':','.join(sorted({r['candidate_label'] for r in g})),
        'rule_status':'pending','evidence':'','reviewer':''} for (c,s,o),g in sorted(buckets.items())],root)

def apply_rules(root,rules_path,overrides_path):
    rows=read_csv(research_inventory(root));rules=read_json(rules_path)
    override_rows=read_csv(overrides_path);overrides={r['image_id']:r for r in override_rows}
    if len(overrides)!=len(override_rows):raise ValueError('Duplicate override ID')
    if not set(overrides).issubset({r['image_id'] for r in rows}):raise ValueError('Unknown override ID')
    output=[]
    for r in rows:
        if r['image_id'] in overrides:
            output.append(overrides[r['image_id']]);continue
        matches=[rule for rule in rules if all(r.get(k)==v for k,v in rule['match'].items())]
        if len(matches)!=1 or any(x in r['review_reasons'] for x in HIGH_RISK):
            raise ValueError('Explicit per-image decision required: '+r['image_id'])
        rule=matches[0]
        if not rule.get('evidence') or not rule.get('reviewer') or rule.get('status')!='approved':
            raise ValueError('Unapproved source rule')
        output.append({'image_id':r['image_id'],'action':rule['action'],'crop':rule.get('crop',r['crop']),
            'binary_label':rule.get('binary_label',r['candidate_label']),'reason':rule.get('reason',''),
            'evidence':rule['evidence'],'reviewer':rule['reviewer']})
    target=root/'review'/'decisions.csv'
    if target.exists():raise ValueError('Decisions already exist; version review files explicitly')
    write_csv(target,output,root)

def register_raw(root):
    target=root/'audit'/'research_inventory.csv'
    if target.exists() or (root/'manifests'/'fixed_split.csv').exists():raise ValueError('Inventory already registered or frozen')
    processed=read_csv(root/'audit'/'image_inventory.csv');raw=read_csv(root/'audit'/'raw_kale_candidates.csv')
    write_csv(target,processed+raw,root)
    write_json(root/'review'/'approval.json',{'approved':False,'inventory_sha256':digest(target),'decisions_sha256':'',
        'group_review_sha256':'','reviewer':'','evidence':'','reviewed_at':'','required_crops':list(CROPS)},root)
    write_json(root/'audit'/'source_scope_amendment.json',{'created_at':utc(),
        'authorization':'User requested raw verification/correction followed by training and required all eight crops.',
        'processed_inventory_unchanged':True,'raw_candidates_registered_for_review':len(raw),'raw_images_approved_for_training':0,
        'inventory_sha256':digest(target),'binary_label_inference':'No growth image is automatically labeled normal.'},root)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--rules');p.add_argument('--overrides');p.add_argument('--register-raw-candidates',action='store_true');a=p.parse_args();root=initialize(a.root)
    if a.register_raw_candidates:register_raw(root)
    if a.rules and a.overrides:apply_rules(root,a.rules,a.overrides)
    else:proposals(root)
