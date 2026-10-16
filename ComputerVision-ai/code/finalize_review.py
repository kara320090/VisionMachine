"""Apply source evidence and actually inspected visual decisions under delegation.

Never equates a folder, pHash, or filename to ground truth. Unresolved entries
are explicitly excluded; approved means accepted for this documented research
protocol, not independently validated plant-pathology ground truth.
"""
import argparse
import collections
import hashlib
from pathlib import Path
from common import *
from group_evidence import Union


def run(root):
    root=initialize(root)
    if (root/'manifests/fixed_split.csv').exists():raise ValueError('Split already frozen')
    for path in ['review/decisions.csv','review/groups.csv']:
        if (root/path).exists():raise ValueError('Reviewed files exist; version explicitly instead of overwriting')
    authority=read_json(root/'review/review_authority.json')
    if authority.get('requires_separate_human_signoff') is not False:raise ValueError('Review authority not recorded')
    cfg=read_json(root/'configs/visual_adjudications.json');reviewer=cfg['reviewer']
    rows=read_csv(research_inventory(root));byid={r['image_id']:r for r in rows}
    sources={r['image_id']:r for r in read_csv(root/'review/source_supported_mapping.csv')}
    groups={r['image_id']:r for r in read_csv(root/'review/groups_conservative_proposed.csv')}
    decisions={};visual=[]
    def decide(identifier,action,crop,label,reason,evidence,provenance):
        decisions[identifier]={'image_id':identifier,'action':action,'crop':crop,'binary_label':label,
            'reason':reason,'evidence':evidence,'reviewer':reviewer,'label_provenance':provenance,
            'independent_expert_validation':False if provenance=='AI_visual_annotation' else 'not_claimed'}
    for r in rows:
        s=sources.get(r['image_id'],{})
        known=s.get('status')=='metadata_supported' and r['crop']!='kale'
        decide(r['image_id'],'include' if known else 'exclude',r['crop'],s.get('proposed_binary_label',''),
               'Verified original metadata mapping' if known else 'Unresolved source/crop/state; not eligible without evidence',
               s.get('evidence') or r.get('source_url') or 'audit/image_inventory.csv and source review',
               'original_source_metadata' if known else 'unresolved_excluded')
    panel_rows=read_csv(root/'review/visual_panels/panel_inventory.csv')
    for r in panel_rows:
        for crop in ('rosemary','bok_choy'):
            if not r['panel'].startswith(crop+'_'):continue
            index=int(r['panel'].rsplit('_',1)[1].split('.')[0])+int(r['cell'])
            include=index not in cfg[crop+'_normal_panels_exclude']
            reason='Source identity plus direct visual confirmation of healthy-appearing foliage' if include else 'Ambiguous visible state, crop composition, significant mark, or obscured foliage'
            evidence=f"review/visual_panels/{r['panel']} cell {r['cell']}; configs/visual_adjudications.json"
            decide(r['image_id'],'include' if include else 'exclude',crop,0,reason,evidence,'AI_visual_annotation')
            visual.append(dict(decisions[r['image_id']],panel=r['panel'],cell=r['cell']))
    for day in (10,20):
        entries=read_csv(root/f'review/kale_day{day}/inventory.csv')
        if len(entries)!=320:raise ValueError('Endpoint review inventory incomplete')
        abnormal=set(cfg[f'raw_day{day}_abnormal']);normal=set(cfg[f'raw_day{day}_s2_normal'])
        uncertain=set(cfg[f'raw_day{day}_s1_uncertain'])
        if abnormal&normal:raise ValueError('Visual annotation conflict')
        for r in entries:
            index=int(r['review_index'])
            if index in abnormal:label=1;reason='Conspicuous enclosed openings / tissue loss in true leaf blade; cause undiagnosed'
            elif (r['species']=='1' and index not in uncertain) or index in normal:
                label=0;reason='Direct visual inspection: no conspicuous injury or lesion; healthy-appearing only'
            else:label='';reason='Ambiguous mark, fold, margin morphology, colour or cotyledon-only view'
            evidence=f"review/kale_day{day}/{r['panel']} cell {r['cell']}; WUR DOI 10.5281/zenodo.4315436 confirms crop; configs/visual_adjudications.json defines new visual state"
            decide(r['image_id'],'include' if label!='' else 'exclude','kale',label,reason,evidence,'AI_visual_annotation')
            visual.append(dict(decisions[r['image_id']],panel=r['panel'],cell=r['cell'],day=day,
                               plant=r['candidate_individual_id'],cultivar=r['species'],acquisition_stage=r['stage']))
    # Merge original-photo IDs only where full geometric+pixel evidence supports
    # the relation. Conservative scene boundaries do not deduplicate originals.
    uf=Union(byid);bysha=collections.defaultdict(list)
    for r in rows:bysha[r['sha256']].append(r['image_id'])
    for ids in bysha.values():
        for identifier in ids[1:]:uf.join(ids[0],identifier)
    cross=set()
    for edge in read_csv(root/'review/geometric_candidate_checks.csv'):
        if edge['relation']!='same_photo_supported_by_geometry_and_pixels':continue
        a,b=edge['image_id_a'],edge['image_id_b'];uf.join(a,b)
        if edge['crop_a']!=edge['crop_b']:cross.update((a,b))
    components=collections.defaultdict(list)
    for r in rows:components[uf.find(r['image_id'])].append(r)
    for items in components.values():
        ids={r['image_id'] for r in items}
        included=[decisions[i] for i in ids if decisions[i]['action']=='include']
        conflict=len({(d['crop'],str(d['binary_label'])) for d in included})>1
        if ids&cross or conflict:
            for r in items:
                decide(r['image_id'],'exclude',r['crop'],'','Confirmed shared-photo crop/state ambiguity; no majority-vote relabeling',
                       'review/geometric_candidate_checks.csv or audit/exact_duplicate_members.csv','confirmed_conflict_exclusion')
        parent='photo_'+hashlib.sha256('|'.join(sorted(ids)).encode()).hexdigest()[:24]
        for r in items:
            g=groups[r['image_id']]
            g.update(status='reviewed',parent_image_id=parent,reviewer=reviewer,
                evidence='Exact SHA / strict geometry+aligned-pixel original-photo relations; conservative source-session, filename and perceptual leakage boundary. Different web photos are not certified independent plants.',
                independence_status='publisher plant ID' if r.get('candidate_individual_id') else 'biological_independence_unknown')
    for r in rows:
        if r['crop']=='kale' and r.get('input_kind')!='raw_candidate':
            decide(r['image_id'],'exclude','kale','','Unreliable crop/health provenance in processed kale; use crop-verified raw visual annotations instead',
                   'audit/confirmed_crop_source_conflicts.json and review source audit','unresolved_or_wrong_processed_kale')
        elif r.get('input_kind')=='raw_candidate' and r.get('day') not in ('10','20'):
            decide(r['image_id'],'exclude','kale','','Outside the two reviewed source dates; retain original file',
                   'review/kale_day10/selection.json and review/kale_day20/selection.json','unselected_raw_date')
    # The exact normal/abnormal collision remains excluded even if a selected
    # visual panel happens to contain a representative of that hash.
    collision='e64a0ed4f90df2dbafcc69e3508634a74169f5f1b095319f8c05db0f3f1c3a1a'
    for r in rows:
        if r['sha256']==collision:
            decide(r['image_id'],'exclude',r['crop'],'','Exact photograph has contradictory normal/abnormal source annotations',
                   'audit/exact_duplicate_members.csv','confirmed_conflict_exclusion')
    edits=[decisions[r['image_id']] for r in rows]
    from source_guard import validate_source_corrections
    validate_source_corrections(root,[dict(byid[d['image_id']],crop=d['crop']) for d in edits if d['action']=='include'])
    write_csv(root/'review/visual_annotation_ledger.csv',visual,root)
    write_csv(root/'review/decisions.csv',edits,root)
    write_csv(root/'review/groups.csv',[groups[r['image_id']] for r in rows],root)
    write_json(root/'review/approval.json',{'approved':True,'inventory_sha256':digest(research_inventory(root)),
        'decisions_sha256':digest(root/'review/decisions.csv'),'group_review_sha256':digest(root/'review/groups.csv'),
        'reviewer':reviewer,'evidence':'Source metadata rejoined to originals; source conflicts excluded; actual visual contact sheets reviewed; user delegation in review_authority.json',
        'reviewed_at':utc(),'required_crops':list(CROPS),'clinical_ground_truth_validation':False,
        'annotation_config_sha256':digest(root/'configs/visual_adjudications.json')},root)
    included=[dict(byid[d['image_id']],binary_label=int(d['binary_label'])) for d in edits if d['action']=='include']
    counts=[{'crop':c,'binary_label':y,'included_entries':sum(r['crop']==c and r['binary_label']==y for r in included),
        'leakage_groups':len({groups[r['image_id']]['leakage_group_id'] for r in included if r['crop']==c and r['binary_label']==y})} for c in CROPS for y in (0,1)]
    write_csv(root/'tables/reviewed_inclusion_counts.csv',counts,root)
    summary={'at':utc(),'inventory_entries':len(rows),'included_entries':len(included),
        'excluded_entries':len(rows)-len(included),'source_files_modified':0,
        'eight_crops_retained':all(any(r['crop']==c for r in included) for c in CROPS),
        'expert_health_labels_claimed':False,'counts':counts}
    write_json(root/'audit/review_finalization.json',summary,root);print(json.dumps(summary),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);run(Path(p.parse_args().root))
