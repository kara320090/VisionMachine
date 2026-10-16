"""Conservative leakage boundaries for review, without declaring duplicates.

Exact SHA relations are confirmed same-file relations. Name/pHash relations are
unconfirmed and only join a conservative split boundary. Parent photos are not
collapsed based on an unconfirmed relation. These are NOT independent plant
counts and this script never writes fixed_split.csv or approval=true.
"""
import argparse
import collections
import hashlib
import re
from pathlib import Path
from common import *

class Union:
    def __init__(self,ids):self.parent={i:i for i in ids}
    def find(self,x):
        while self.parent[x]!=x:self.parent[x]=self.parent[self.parent[x]];x=self.parent[x]
        return x
    def join(self,a,b):
        a,b=self.find(a),self.find(b)
        if a!=b:self.parent[max(a,b)]=min(a,b)

def run(root):
    root=initialize(root);rows=read_csv(research_inventory(root));byid={r['image_id']:r for r in rows}
    support={r['image_id']:r for r in read_csv(root/'review'/'source_supported_mapping.csv')}
    uf=Union(byid);buckets=collections.defaultdict(list);relations=[]
    for r in rows:
        buckets['exact_sha',r['sha256']].append(r['image_id'])
        if r.get('filename_family'):buckets['unconfirmed_filename',r['filename_family']].append(r['image_id'])
        if r.get('candidate_individual_id'):buckets['raw_plant_hypothesis',r['candidate_individual_id']].append(r['image_id'])
        s=support.get(r['image_id'],{})
        if s.get('capture_group_candidate'):buckets['source_session_date',s['capture_group_candidate']].append(r['image_id'])
    for (kind,key),ids in buckets.items():
        if len(ids)<2:continue
        for other in ids[1:]:uf.join(ids[0],other)
        relations.append({'kind':kind,'key':key,'images':len(ids),'crop_count':len({byid[i]['crop'] for i in ids}),
                          'relationship_confirmed':kind=='exact_sha','purpose':'conservative_split_boundary'})
    p=root/'review'/'perceptual_candidates.csv'
    if p.exists():
        for edge in read_csv(p):uf.join(edge['image_id_a'],edge['image_id_b'])
    components=collections.defaultdict(list)
    for r in rows:components[uf.find(r['image_id'])].append(r)
    groups=[];stats=[]
    for key,items in components.items():
        gid='boundary_'+hashlib.sha256(','.join(sorted(r['image_id'] for r in items)).encode()).hexdigest()[:24]
        for r in items:
            groups.append({'image_id':r['image_id'],'status':'pending','parent_image_id':'sha_'+r['sha256'][:24],
                'leakage_group_id':gid,'evidence':'Exact SHA plus conservative filename/perceptual/source-session boundary; candidate relations are not deduplication evidence.',
                'reviewer':'','independence_status':'not_certified'})
        stats.append({'leakage_boundary':gid,'image_entries':len(items),'unique_sha256':len({r['sha256'] for r in items}),
            'crops':'|'.join(sorted({r['crop'] for r in items})),'crop_count':len({r['crop'] for r in items}),
            'binary_labels_current_folder':'|'.join(sorted({r.get('candidate_label','') for r in items})),
            'relationship_status':'conservative_candidate_boundary'})
    write_csv(root/'review'/'groups_conservative_proposed.csv',groups,root)
    write_csv(root/'review'/'grouping_relations.csv',relations,root)
    write_csv(root/'review'/'conservative_group_summary.csv',stats,root)
    gid_by_image={r['image_id']:r['leakage_group_id'] for r in groups}
    counts=[]
    for c in CROPS:
        for y in (0,1):
            sub=[r for r in rows if r['crop']==c and r.get('candidate_label')==str(y)]
            metadata=[r for r in sub if support.get(r['image_id'],{}).get('status')=='metadata_supported']
            counts.append({'crop':c,'candidate_label':y,'folder_entries':len(sub),
                'source_supported_label_entries':len(metadata),'unconfirmed_leakage_boundaries':len({gid_by_image[r['image_id']] for r in sub}),
                'confirmed_independent_plant_count':'UNKNOWN','final_approved_training_count':'NOT_READY'})
    write_csv(root/'tables'/'source_and_group_review_counts.csv',counts,root)
    summary={'created_at':utc(),'candidate_entries':len(rows),'conservative_boundaries':len(components),
        'cross_crop_boundaries':sum(s['crop_count']>1 for s in stats),'label_approval_changed':False,
        'fixed_split_created':False,'independent_original_count':None,
        'note':'Grouping similar images together is a precaution against leakage, not proof they are duplicates. Source/pair adjudication is still required.'}
    write_json(root/'audit'/'group_review_summary.json',summary,root);print(json.dumps(summary),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);run(Path(p.parse_args().root))
