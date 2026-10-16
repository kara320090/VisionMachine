"""Materialize evidence-supported proposals; never silently resolve ambiguity."""
import argparse
from pathlib import Path
from common import *

def run(root):
    root=initialize(root);rows=read_csv(research_inventory(root));support={r['image_id']:r for r in read_csv(root/'review'/'source_supported_mapping.csv')}
    correction_path=root/'review'/'confirmed_crop_source_conflicts.csv'
    corrections={r['image_id']:r for r in read_csv(correction_path)} if correction_path.exists() else {}
    draft=[]
    for r in rows:
        if r['image_id'] in corrections:
            c=corrections[r['image_id']]
            draft.append({'image_id':r['image_id'],'action':'exclude','crop':c['source_crop'],
                'binary_label':c['binary_health_label_from_source'],
                'reason':'Confirmed source crop outside the eight required crops',
                'evidence':c['evidence'],'reviewer':c['reviewer'],
                'decision_status':'confirmed_source_crop_correction','does_not_sign_human_approval':True})
            continue
        s=support.get(r['image_id'],{});known=s.get('status')=='metadata_supported'
        draft.append({'image_id':r['image_id'],'action':'include' if known else 'pending',
            'crop':s.get('proposed_crop',r['crop']),'binary_label':s.get('proposed_binary_label',''),
            'reason':s.get('reason','Raw growth data has no health-state annotation'),
            'evidence':s.get('evidence',r.get('source_url','')),
            'reviewer':'Codex original metadata consistency check' if known else '',
            'decision_status':'source_supported_proposal' if known else 'unresolved',
            'does_not_sign_human_approval':True})
    write_csv(root/'review'/'decisions_evidence_draft.csv',draft,root)
    write_json(root/'review'/'decision_draft_status.json',{'created_at':utc(),'entries':len(draft),
        'source_supported_proposals':sum(r['action']=='include' for r in draft),
        'confirmed_wrong_crop_exclusions':sum(r['action']=='exclude' for r in draft),
        'unresolved_entries':sum(r['action']=='pending' for r in draft),'approval_signed':False,
        'research_training_started':False},root)
    status={r['image_id']:r for r in draft}
    provisional=[dict(r,proposed_action=status[r['image_id']]['action'],
        proposed_crop=status[r['image_id']]['crop'],proposed_binary_label=status[r['image_id']]['binary_label'],
        decision_status=status[r['image_id']]['decision_status'],
        decision_evidence=status[r['image_id']]['evidence'],final_split='not_fixed') for r in rows]
    write_csv(root/'manifests'/'provisional_review_manifest.csv',provisional,root)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);run(Path(p.parse_args().root))
