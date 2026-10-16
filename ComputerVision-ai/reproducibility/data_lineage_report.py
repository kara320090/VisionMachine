"""Additional descriptive report; never changes the frozen training protocol."""
import argparse
import collections
import html
import json
import sys
from pathlib import Path


def run(root):
    root = Path(root).resolve()
    sys.path.insert(0, str(root / 'code'))
    from common import (CROPS, initialize, read_csv, read_json, write_csv,
                        write_json, digest, utc, code_hash, research_inventory)
    from train import load_protocol
    root = initialize(root)
    cfg, fixed, lock = load_protocol(root, main=True)
    destination = root / 'audit' / 'curated_data_report'
    if destination.exists():
        raise ValueError('Data report already exists; preserve the previous result')
    destination.mkdir()
    inventory = read_csv(research_inventory(root))
    decisions = {r['image_id']: r for r in read_csv(root / 'review/decisions.csv')}
    groups = {r['image_id']: r for r in read_csv(root / 'review/groups.csv')}
    included = []
    for r in inventory:
        d = decisions[r['image_id']]
        if d['action'] in ('include', 'relabel'):
            g = groups[r['image_id']]
            included.append(dict(r, crop=d['crop'], binary_label=d['binary_label'],
                parent_image_id=g['parent_image_id'], leakage_group_id=g['leakage_group_id'],
                label_provenance=d.get('label_provenance', 'not_recorded')))
    processed = [r for r in inventory if not r['processed_relpath'].startswith('raw-kale:')]
    raw = [r for r in inventory if r['processed_relpath'].startswith('raw-kale:')]
    def counts(name, records, reviewed=False):
        return dict(stage=name, image_entries=len(records),
            unique_sha256=len({r['sha256'] for r in records}),
            confirmed_photo_components=len({r['parent_image_id'] for r in records}) if reviewed else '',
            conservative_leakage_groups=len({r['leakage_group_id'] for r in records}) if reviewed else '',
            independently_verified_plant_count='UNKNOWN outside publisher plant-ID raw kale subset')
    stages = [counts('processed_original_entries', processed), counts('registered_raw_kale_candidates', raw),
        counts('included_before_same_photo_deduplication', included, True),
        counts('fixed_split_distinct_photo_representatives', fixed, True)]
    for split in ('train', 'validation', 'test'):
        subset = [r for r in fixed if r['split'] == split]
        stages.append(counts(split + '_image_list', subset, True))
        if split != 'train':
            stages.append(counts(split + '_evaluation_representatives', [r for r in subset
                if str(r['evaluation_representative']).lower() == 'true'], True))
    write_csv(destination / 'data_lineage_counts.csv', stages, root)
    total = len(fixed)
    state_counts = []
    for crop in CROPS:
        crop_total = sum(r['crop'] == crop for r in fixed)
        for y in (0, 1):
            records = [r for r in fixed if r['crop'] == crop and int(r['binary_label']) == y]
            row = dict(crop=crop, binary_label=y, image_entries=len(records),
                unique_sha256=len({r['sha256'] for r in records}),
                confirmed_photo_components=len({r['parent_image_id'] for r in records}),
                conservative_leakage_groups=len({r['leakage_group_id'] for r in records}),
                percent_of_crop=100 * len(records) / crop_total,
                percent_of_all_cleaned_images=100 * len(records) / total)
            for split in ('train', 'validation', 'test'):
                subset = [r for r in records if r['split'] == split]
                row[split + '_images'] = len(subset)
                row[split + '_leakage_groups'] = len({r['leakage_group_id'] for r in subset})
                row[split + '_evaluation_representatives'] = sum(str(r['evaluation_representative']).lower() == 'true' for r in subset)
            state_counts.append(row)
    write_csv(destination / 'crop_state_distribution.csv', state_counts, root)
    train = [r for r in fixed if r['split'] == 'train']
    n = len(train)
    by_y = collections.Counter(int(r['binary_label']) for r in train)
    by_group = collections.Counter((r['crop'], int(r['binary_label'])) for r in train)
    weights = []
    for crop in CROPS:
        for y in (0, 1):
            count = by_group[crop, y]
            if count == 0:
                raise ValueError('Missing crop/state training group')
            weights.append(dict(crop=crop, binary_label=y, train_images=count, A_weight=1,
                B_weight=n/(2*by_y[y]), C_weight=n/(16*count),
                A_group_mass=count, B_group_mass=count*n/(2*by_y[y]), C_group_mass=n/16))
    write_csv(destination / 'actual_training_weights.csv', weights, root)
    provenance = []
    for fields in [('crop','label_provenance'), ('crop','binary_label','source','split'),
                   ('crop','binary_label','day','species','stage','split')]:
        buckets = collections.defaultdict(list)
        for r in fixed:
            if 'day' in fields and r['crop'] != 'kale':
                continue
            buckets[tuple(str(r.get(k, '')) for k in fields)].append(r)
        output = []
        for keys, records in sorted(buckets.items()):
            output.append(dict(zip(fields,keys)) | dict(images=len(records),
                leakage_groups=len({r['leakage_group_id'] for r in records}),
                evaluation_representatives=sum(str(r['evaluation_representative']).lower() == 'true' for r in records)))
        name = ('label_provenance' if 'label_provenance' in fields else
                'kale_acquisition_confounding' if 'day' in fields else 'source_split_distribution')
        write_csv(destination / (name+'.csv'), output, root)
        if name == 'label_provenance':
            provenance = output
    exclusions = collections.Counter(d.get('reason','') for d in decisions.values() if d['action'] == 'exclude')
    write_csv(destination / 'exclusion_reasons.csv', [{'reason': k, 'image_entries': v}
        for k,v in exclusions.most_common()], root)
    totals = {c:sum(r['crop'] == c for r in fixed) for c in CROPS}
    train_totals = {c:sum(r['crop'] == c for r in train) for c in CROPS}
    summary = dict(created_at=utc(), frozen_split_sha256=lock['split_sha256'],
        frozen_code_sha256=code_hash(), config_sha256=digest(root/'configs/common.json'),
        all_eight_crops_present=all(totals.values()), train_images=n,
        dataset_crops_max_min_ratio=max(totals.values())/min(totals.values()),
        training_crops_max_min_ratio=max(train_totals.values())/min(train_totals.values()),
        training_images_per_crop=train_totals, low_data_crops=lock['low_data_crops'],
        stages=stages, biological_independence_fully_established=False,
        synthetic_metrics_used=False, model_or_split_modified=False,
        new_visual_labels_are_single_AI_annotations=True,
        script_sha256=digest(Path(__file__)))
    write_json(destination/'summary.json',summary,root)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    x=np.arange(8); normal=[next(r['image_entries'] for r in state_counts if (r['crop'],r['binary_label'])==(c,0)) for c in CROPS]
    abnormal=[next(r['image_entries'] for r in state_counts if (r['crop'],r['binary_label'])==(c,1)) for c in CROPS]
    fig,ax=plt.subplots(figsize=(11,5));ax.bar(x-.2,normal,.4,label='Normal');ax.bar(x+.2,abnormal,.4,label='Abnormal')
    ax.set_xticks(x,CROPS,rotation=25);ax.set_ylabel('Distinct reviewed photo representatives');ax.legend();fig.tight_layout()
    for suffix in ('png','svg'):fig.savefig(destination/f'curated_crop_state_distribution.{suffix}',dpi=180)
    plt.close(fig)
    def table(rows,fields):
        return '<table><tr>'+''.join('<th>'+html.escape(f)+'</th>' for f in fields)+'</tr>'+''.join('<tr>'+''.join('<td>'+html.escape(str(r.get(f,'')))+'</td>' for f in fields)+'</tr>' for r in rows)+'</table>'
    body='''<!doctype html><html lang="ko"><meta charset="utf-8"><title>정리 후 데이터와 분할</title>
<style>body{font:16px/1.65 sans-serif;margin:35px auto;max-width:1250px;padding:0 20px;color:#20313c}table{border-collapse:collapse;margin:18px 0;width:100%;font-size:13px}th,td{border:1px solid #ccd3da;padding:6px}img{max-width:100%}.note{background:#fff3df;padding:16px}</style>
<h1>8종 작물 데이터 교정·분할 보고서</h1>'''
    body+=f'<p>실험 {html.escape(root.name)} · {utc()}</p>'
    body+='<p class="note">파일 항목, 고유 SHA, 확인된 사진 계열, 누출 방지 촬영 그룹은 서로 다른 수입니다. 전체 공개 이미지의 독립 개체 수는 확인할 수 없습니다. 새 케일·일부 정상 주석은 단일 AI 육안 판정이며 식물병리 전문가 정답이 아닙니다. 모델 성능을 보고 판정을 바꾸지 않았습니다.</p>'
    body+='<h2>정리 단계별 수</h2>'+table(stages,['stage','image_entries','unique_sha256','confirmed_photo_components','conservative_leakage_groups'])
    body+='<h2>정리 후 16개 그룹</h2>'+table(state_counts,['crop','binary_label','image_entries','percent_of_crop','train_images','validation_images','test_images','validation_evaluation_representatives','test_evaluation_representatives'])
    body+='<img src="curated_crop_state_distribution.png" alt="정리 후 작물 상태별 이미지 수">'
    body+=f'<p>정리 후 작물별 이미지 수 최대/최소 비율 {summary["dataset_crops_max_min_ratio"]:.2f}배, 학습 목록의 비율 {summary["training_crops_max_min_ratio"]:.2f}배입니다. 학습 수 하위 2종은 {html.escape(", ".join(lock["low_data_crops"]))}로 성능 확인 전에 고정했습니다.</p>'
    body+='<h2>주석 근거</h2>'+table(provenance,['crop','label_provenance','images','leakage_groups'])
    body+='<p>원출처 JSON·클래스 정의와 연결된 라벨은 원출처 근거로 유지했습니다. 육안 의심만으로 병명을 새로 확정하지 않았습니다. 케일의 정상 외관/뚜렷한 잎 조직 소실 판정 기준은 visual_annotation_ledger와 visual_adjudications에 기록했습니다. 촬영 시기·품종·촬영 단계와 상태의 연관은 kale_acquisition_confounding.csv에서 확인할 수 있습니다.</p>'
    body+='<h2>학습 가중치</h2>'+table(weights,['crop','binary_label','train_images','A_weight','B_weight','C_weight','C_group_mass'])
    body+='<p>N은 학습 이미지 수만 사용합니다. B와 C 모두 전체 가중치 합 N, 상태별 N/2이며 C의 각 그룹 질량은 N/16입니다. 배치 손실 분모는 이미지 수입니다. 테스트·검증 수를 가중치에 사용하지 않습니다.</p>'
    body+='<h2>제외 사유</h2>'+table([{'reason':k,'image_entries':v} for k,v in exclusions.most_common()],['reason','image_entries'])
    body+='<p>모든 제외는 새 manifest에만 표시했습니다. 기존 파일·심볼릭 링크는 유지했습니다. 촬영 부위·출처·배경·이상 유형의 차이는 표본 수와 함께 변하므로 불균형 보정 효과의 해석 한계로 보고합니다.</p></html>'
    (destination/'index.html').write_text(body,encoding='utf-8')
    write_json(destination/'generation_receipt.json',dict(created_at=utc(),
        files=[dict(path=p.name,bytes=p.stat().st_size,sha256=digest(p)) for p in sorted(destination.iterdir()) if p.is_file()],
        protocol_unchanged=code_hash()==read_json(root/'configs/protocol_lock.json')['code_sha256']),root)
    print(json.dumps(summary,ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',required=True)
    run(parser.parse_args().root)
