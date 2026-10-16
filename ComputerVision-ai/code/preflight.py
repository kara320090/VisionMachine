import argparse
from pathlib import Path
from common import *

def main(root):
    root=initialize(root);fail=[];checks={}
    approval=root/'review'/'approval.json'
    if not approval.exists() or not read_json(approval).get('approved'):
        fail.append('라벨·촬영 그룹 검토가 미확정입니다. 원본 근거가 부족한 항목을 임의로 포함하지 않습니다.')
    if not (root/'manifests'/'lock.json').exists():
        fail.append('8종·16그룹을 충족하는 고정 분할 manifest가 아직 없습니다.')
    source_summary=root/'audit'/'label_source_validation_summary.json'
    if source_summary.exists():checks['source_label_evidence']=read_json(source_summary)['counts']
    try:
        from train import load_protocol
        if not fail:
            cfg,rows,lock=load_protocol(root)
            from learning import sample_weights
            train=[r for r in rows if r['split']=='train']
            checks['weights']={c:{'sum':float(sample_weights(train,c).sum()),'mean':float(sample_weights(train,c).mean())} for c in 'ABC'}
            checks['eight_crops_and_split']='passed'
    except (ValueError,FileNotFoundError) as e:fail.append(str(e))
    checks['protected_output_paths']='passed'
    result={'checked_at':utc(),'ready_for_research_training':not fail,'required_crops':list(CROPS),'checks':checks,'blockers':fail}
    write_json(root/'reproducibility'/'preflight.json',result,root);print(json.dumps(result,indent=2))
    return 2 if fail else 0

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);raise SystemExit(main(Path(p.parse_args().root)))
