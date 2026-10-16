"""Generate inspectable audit and paper artifacts; never invent missing results."""
import argparse
import collections
import html
import statistics
from pathlib import Path
from common import *

def audit_report(root):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    summary=read_json(root/'audit'/'summary.json');counts=read_csv(root/'tables'/'unvalidated_data_counts.csv')
    raw=read_json(root/'audit'/'raw_kale_summary.json') if (root/'audit'/'raw_kale_summary.json').exists() else {}
    tests=read_json(root/'reproducibility'/'test_results.json') if (root/'reproducibility'/'test_results.json').exists() else {}
    corrections=read_json(root/'audit'/'confirmed_crop_source_conflicts.json') if (root/'audit'/'confirmed_crop_source_conflicts.json').exists() else {}
    cache=read_json(root/'reproducibility'/'io_speed_cached_available.json') if (root/'reproducibility'/'io_speed_cached_available.json').exists() else {}
    reviewed=read_json(root/'audit/review_finalization.json') if (root/'audit/review_finalization.json').exists() else {}
    split_counts=read_csv(root/'tables/fixed_split_counts.csv') if (root/'tables/fixed_split_counts.csv').exists() else []
    completed=len([p for p in (root/'runs').glob('*_seed*/completed.json') if p.parent.name[0] in 'ABC'])
    stage=f'라벨·그룹 검토 및 8종 고정 분할 완료. 본실험 완료 {completed}/9회.' if split_counts else '라벨·그룹 검토 진행 중. 본실험·고정 분할·테스트 성능은 아직 없습니다.'
    split_html=''.join('<tr>'+''.join('<td>'+html.escape(str(r[k]))+'</td>' for k in ('crop','binary_label','split','images','reviewed_leakage_groups','evaluation_representatives'))+'</tr>' for r in split_counts)
    values={(r['crop'],int(r['candidate_label'])):int(r['file_entries']) for r in counts}
    fig,ax=plt.subplots(figsize=(10,5));x=list(range(8));normal=[values[c,0] for c in CROPS];abnormal=[values[c,1] for c in CROPS]
    ax.bar(x,normal,label='Folder normal (unvalidated)',color='#3296a5');ax.bar(x,abnormal,bottom=normal,label='Folder abnormal (unvalidated)',color='#d97745')
    ax.set_xticks(x,CROPS,rotation=25);ax.set_ylabel('Image entries, including derivatives');ax.set_title('Current folder distribution — label review pending');ax.legend();fig.tight_layout()
    fig.savefig(root/'figures'/'unvalidated_crop_distribution.png',dpi=180);fig.savefig(root/'figures'/'unvalidated_crop_distribution.svg');plt.close(fig)
    rows=''.join('<tr>'+''.join('<td>'+html.escape(str(r[k]))+'</td>' for k in ('crop','candidate_label','file_entries','unique_sha256','filename_candidate_families'))+'</tr>' for r in counts)
    body=f'''<!doctype html><html lang="ko"><meta charset="utf-8"><title>8종 작물 연구 구현·검증 보고서</title>
<style>body{{font:16px/1.65 sans-serif;max-width:1100px;margin:40px auto;padding:0 24px;color:#233243}}h1,h2{{line-height:1.3}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ccd4dd;padding:7px;text-align:left}}pre{{background:#eef2f5;padding:18px;white-space:pre-wrap}}img{{max-width:100%}}.gate{{padding:18px;border-left:6px solid #bf7226;background:#fff4e5}}</style>
<h1>8종 작물 연구 구현·검증 보고서</h1><p>실험 ID: {root.name}<br>생성 시각: {utc()}</p>
<p class="gate"><b>8종 모두 필수.</b> {stage} 합성 입력 검사와 시간 시나리오는 연구 분류 성능이 아닙니다.</p>
<h2>검토 후 학습 대상과 고정 분할</h2><p>사용자가 모든 판단을 Codex에 위임한 지시에 따라 출처 검증과 실제 이미지 검토를 새 manifest에 기록했습니다. 케일은 WUR 원본의 10일차·20일차를 직접 검토해 정상 외관 또는 눈에 보이는 잎 조직 소실로 새 주석을 만들었습니다. 같은 개체의 모든 날짜는 한 분할에 묶었습니다. 빈 라벨이나 폴더명으로 정답을 추정하지 않았습니다.</p>
<p><b>케일 주석은 단일 AI 육안 검토이며 식물병리 전문가나 병원균 검사로 검증된 정답이 아닙니다.</b> 손상 원인·병명을 확정하지 않습니다. 품종·생육 시기·촬영 단계와 상태가 연관된 한계를 결과 해석에 반영해야 합니다. 공개 이미지의 서로 다른 촬영 그룹은 서로 다른 생물학적 개체임을 완전히 증명하지 못하므로 표의 그룹 수를 독립 개체 수로 단정하지 않습니다.</p>
<pre>{html.escape(json.dumps(reviewed,ensure_ascii=False,indent=2))}</pre>
<table><tr><th>작물</th><th>상태</th><th>분할</th><th>이미지</th><th>검토한 누출 방지 그룹</th><th>평가 대표 수</th></tr>{split_html}</table>
<p><a href="review/visual_annotation_ledger.csv">새 육안 주석과 실제 이미지 근거</a> · <a href="review/decisions.csv">전체 포함·제외 판정</a> · <a href="manifests/fixed_split.csv">고정 분할 manifest</a></p>
<h2>현재 processed 재점검</h2><p>이미지 항목 {summary['file_entries']:,}개, 고유 SHA-256 {summary['unique_sha256']:,}개, 디코딩 실패 {summary['decode_errors']}개. 고유 SHA 수는 독립 촬영 표본 수가 아닙니다.</p>
<table><tr><th>작물</th><th>현재 상태 후보(0/1)</th><th>파일 항목</th><th>고유 SHA</th><th>파일명 후보 계열</th></tr>{rows}</table>
<img src="figures/unvalidated_crop_distribution.png" alt="검증 전 작물별 데이터 분포">
<h2>raw 확인 결과와 연구 성립 조건</h2>
<p class="gate">케일 v5 흰가루병 129장은 저자 제공 PlantVillage의 Squash___Powdery_mildew 사진과 일대일로 대응하여 호박으로 확인됐습니다. 새 manifest의 교정 사항이며 기존 이미지는 수정하지 않았습니다. 해당 이미지 ID·SHA-256은 케일 학습 포함을 차단합니다. 케일을 제외한 7종 본실험으로 대체하지 않습니다.</p>
<p><a href="https://github.com/spMohanty/PlantVillage-Dataset/tree/master/raw/color/Squash___Powdery_mildew">PlantVillage 원 출처</a> · <a href="review/confirmed_crop_source_conflicts.csv">129장별 대응·교정 근거</a> · <a href="manifests/provisional_review_manifest.csv">정답 확정 전 전체 검토 manifest</a></p>
<pre>{html.escape(json.dumps(corrections,ensure_ascii=False,indent=2))}</pre>
<p>Roboflow raw ZIP에서도 케일 v3 클래스 정의가 비어 있고 115개 라벨이 비어 있습니다. v4에는 빈 라벨 57개가 있습니다. v2의 객체 클래스 이름은 59이며, 이 문자열만으로 정상 의미를 확정할 수 없습니다.</p>
<p>별도 raw 케일 자료의 출처 설명은 320개체의 20일 반복 촬영, 총 6,400장입니다. 정상·질병 라벨 데이터셋은 아닙니다. 로컬 ZIP의 디렉터리 검증은 실패했고, 기존 추출본을 따로 검사했습니다. 실제 사진을 검토한 항목만 새 주석 근거를 남겨 포함했습니다.</p>
<p><a href="https://research.wur.nl/en/datasets/top-view-images-of-kale-brassica-oleracea/">Wageningen University 원출처</a> · <a href="review/index.html">케일·청경채 충돌 및 라벨 검토 이미지</a> · <a href="review/raw_kale_examples.jpg">raw 케일 대표 이미지</a></p>
<pre>{html.escape(json.dumps(raw,ensure_ascii=False,indent=2))}</pre>
<p>불명확한 기존 케일 폴더는 제외하고 검토된 raw 사진으로 대체했습니다. 로즈마리·청경채 정상 후보는 검토표의 실제 사진을 확인했고, 충돌·모호한 항목은 제외했습니다. 16개 그룹 모두 학습에 존재하고 검증·테스트 각각 10개 이상 누출 방지 그룹을 확보하는 검사를 적용했습니다.</p>
<h2>구현과 검증</h2><p>고정 그룹 분할, A/B/C 이미지별 가중 CE, 이미지→2로짓 EfficientNet-B0, 재개 체크포인트, 0.5 임계값 평가, 결과 집계, 원본 보호 검사, 해시 검증 전송 코드를 구현했습니다.</p>
<p>18시간은 완료 목표이며 자동 중단 제한이 아닙니다. 시간이 지나도 미완료 작업을 계속합니다. 반복 JPEG 디코딩 비용을 줄이기 위해 실험 디렉터리에 EXIF 방향 반영·짧은 변 320픽셀 PNG 캐시를 생성했습니다. 이는 손실 없는 PNG 저장이라는 뜻이며, 320픽셀 리사이즈 자체는 새 공통 전처리입니다. 병변·크롭 품질 검사 결과는 reproducibility의 전처리 점검 기록에 남겼습니다.</p>
<pre>{html.escape(json.dumps(cache,ensure_ascii=False,indent=2))}</pre>
<pre>{html.escape(json.dumps(tests,ensure_ascii=False,indent=2))}</pre>
<p><a href="reproducibility/preflight.json">본실험 준비 상태</a> · <a href="reproducibility/test_results.txt">테스트 상세</a> · <a href="reproducibility/environment.json">전용 환경</a> · <a href="reproducibility/synthetic_gpu_smoke.json">합성 GPU 동작 검사</a> · <a href="README.txt">실행·재현 절차</a></p>
<h2>실행 순서</h2><p>근거 검토 → 새 manifest 교정 → 그룹 분할 검증 → 실제 데이터 소수 배치·처리량 검사 → 공통 설정 확정 → A/B/C×3시드 → 고정 테스트·논문 결과. 각 실행의 실제 상태는 runs와 evaluation의 완료 기록을 확인합니다.</p>
<h2>원본 보호와 결과 보관</h2><p>입력 파일은 읽기 전용입니다. 제외·재라벨링은 실험 manifest로만 표현합니다. 서버 실험 파일은 자동 삭제하지 않습니다. 결과는 노트북 Desktop/ComputerVision-ai의 고유 실험 폴더에 보관하고, 전송 목록·크기·SHA-256을 검증합니다.</p></html>'''
    (root/'REPORT.html').write_text(body,encoding='utf-8')
    text='''논문 결과·논의 초안 — 측정 전 상태

연구 질문: 정상·이상 비율만 보정하는 것보다 작물×상태까지 보정하는 것이 작물별 성능을 개선하는가?
설계: ImageNet EfficientNet-B0의 이미지 입력·2로짓 출력. 8종 필수. 동일한 검증된 학습 목록, 전처리, 최적화, 30 epoch와 시드 17/42/2026.
손실: A=1, B=N/(2n_y), C=N/(16n_c,y); reduction='none' CE에 곱한 뒤 배치 이미지 수로 평균.
분할: 검토된 촬영 그룹 기준 60/20/20. 같은 원본·파생본은 분할 간 분리 금지. 검증·테스트 대표 이미지 평가.
주지표: 각 작물에서 normal/abnormal macro-F1을 구한 후 8종 동일 비중 평균. 전체 pooled binary macro-F1과 구분.
검증 주지표 최고 epoch 선택(동률이면 이른 epoch), 테스트 임계값 0.5 고정. 평균±표본 SD 및 paired C-B, B-A, C-A.

현재 실제 확인 결과: audit/summary.json 및 tables/unvalidated_data_counts.csv 참조. 이는 기존 폴더 라벨의 집계이며 확정 정답/학습 수가 아니다.
현재 모델 결과: 미측정. 합성 GPU 검사 수치·손실은 논문 성능 표에 사용하지 않는다.
케일: WUR 기존 raw의 작물 정체성을 원출처로 확인했다. 10일차·20일차 실제 사진을 단일 AI가 육안 주석했으며, 정상 외관과 뚜렷한 잎 조직 소실을 구분했다. 병명·손상 원인을 진단하지 않았고 임상·식물병리 전문가 검증 정답이라고 주장하지 않는다.
같은 개체의 서로 다른 상태·날짜는 같은 분할에 유지한다. 품종·생육 시기·촬영 단계와 상태의 상관 및 단일 주석자 오류가 주요 한계다. 별도 전문가 확인이 없는 결과는 해당 주석 기준에 조건부인 탐색적 실증 결과로 해석한다.

결과 절 작성 예정:
1. 라벨·원본 그룹 검토 전후 수와 제외/교정 사유.
2. 전체 주지표와 pooled 지표의 A/B/C 평균±SD.
3. 8종별 성능과 C-B 변화. 학습 수 하위 2종은 사전 정의.
4. 정상 오판·이상 누락 사례를 고정 규칙으로 제시.

논의 절 작성 예정:
보정이 개선·악화·무변화일 가능성을 모두 열어 둔다. 촬영 부위, 출처, 배경, 이상 유형이 작물 수와 함께 달라지는 교란 가능성을 기술한다.
3시드만으로 통계적 유의성을 주장하지 않는다. 내부 테스트를 새 촬영 환경/미지 이상 일반화의 증명으로 표현하지 않는다.
새 알고리즘/최초 연구라는 주장 없이 해당 데이터 조건의 통제 비교를 기여로 둔다.
미측정 정확도·F1·신뢰구간을 채워 넣지 않는다.

참고 1차 출처:
Atila et al. 2021 https://doi.org/10.1016/j.ecoinf.2020.101182 — EfficientNet 식물 이미지 전이학습 참고; 본 연구 8종 이진/16그룹 실험은 별도 설계.
Shahoveisi et al. 2023 https://www.nature.com/articles/s41598-023-31942-9 — 여러 작물의 정상·녹병 이미지 연구 참고; 데이터셋 간 정확도 우열 비교 금지.
Tong-Le & Doan 2026 https://www.jait.us/articles/2026/JAIT-V17N8-1456.pdf — 조건을 통제한 손실 비교 참고; 본 연구의 그룹 분할/3시드는 별도 설계.
'''
    (root/'paper'/'results_discussion_draft.txt').write_text(text,encoding='utf-8')

def results_report(root):
    import matplotlib.pyplot as plt
    import numpy as np
    cfg=read_json(root/'configs'/'common.json');results={};predictions={}
    for c in 'ABC':
        for seed in cfg['training_seeds']:
            path=root/'evaluation'/f'{c}_seed{seed}'/'metrics.json'
            if not path.exists():return False
            results[c,seed]=read_json(path)
            predictions[c,seed]=read_csv(path.parent/'predictions.csv')
    summary=[];crop_rows=[];deltas=[]
    for c in 'ABC':
        for key in ('equal_crop_binary_macro_f1','pooled_binary_macro_f1','overall_accuracy'):
            vals=[results[c,s][key] for s in cfg['training_seeds']]
            summary.append({'condition':c,'metric':key,'mean':statistics.mean(vals),'sample_sd':statistics.stdev(vals),'seeds':3})
        for crop in CROPS:
            for key in ('binary_macro_f1','abnormal_recall','normal_false_positive_rate'):
                vals=[results[c,s]['per_crop'][crop][key] for s in cfg['training_seeds']]
                crop_rows.append({'condition':c,'crop':crop,'metric':key,'mean':statistics.mean(vals),'sample_sd':statistics.stdev(vals)})
    for newer,older in [('B','A'),('C','B'),('C','A')]:
        for crop in [*CROPS,'ALL_EQUAL_CROP']:
            vals=[results[newer,s]['equal_crop_binary_macro_f1']-results[older,s]['equal_crop_binary_macro_f1'] if crop=='ALL_EQUAL_CROP' else
                  results[newer,s]['per_crop'][crop]['binary_macro_f1']-results[older,s]['per_crop'][crop]['binary_macro_f1'] for s in cfg['training_seeds']]
            deltas.append({'comparison':newer+'-'+older,'crop':crop,'mean_percentage_points':100*statistics.mean(vals),'sample_sd_percentage_points':100*statistics.stdev(vals)})
    write_csv(root/'tables'/'abc_summary.csv',summary,root);write_csv(root/'tables'/'crop_metrics.csv',crop_rows,root);write_csv(root/'tables'/'paired_deltas.csv',deltas,root)
    fig,ax=plt.subplots(figsize=(11,5));x=np.arange(8)
    for ci,c in enumerate('ABC'):
        v=[next(r for r in crop_rows if (r['condition'],r['crop'],r['metric'])==(c,crop,'binary_macro_f1')) for crop in CROPS]
        ax.bar(x+(ci-1)*.25,[r['mean'] for r in v],width=.25,yerr=[r['sample_sd'] for r in v],label=c)
    ax.set_xticks(x,CROPS,rotation=25);ax.set_ylim(0,1);ax.set_ylabel('Binary macro-F1 (mean ± sample SD)');ax.legend();fig.tight_layout();fig.savefig(root/'figures'/'crop_f1_comparison.png',dpi=200);plt.close(fig)
    values=[next(r for r in deltas if r['comparison']=='C-B' and r['crop']==c) for c in CROPS]
    fig,ax=plt.subplots(figsize=(10,5));ax.bar(x,[r['mean_percentage_points'] for r in values],yerr=[r['sample_sd_percentage_points'] for r in values]);ax.axhline(0,color='black',linewidth=1);ax.set_xticks(x,CROPS,rotation=25);ax.set_ylabel('C − B, F1 percentage points');fig.tight_layout();fig.savefig(root/'figures'/'crop_c_minus_b.png',dpi=200);plt.close(fig)
    for c in 'ABC':
        fig,axes=plt.subplots(2,4,figsize=(12,6))
        for crop,ax in zip(CROPS,axes.ravel()):
            # Mean counts over repeated evaluations of the SAME test set;
            # summing would misleadingly triple independent sample size.
            values=np.mean([[[results[c,s]['per_crop'][crop]['tn'],results[c,s]['per_crop'][crop]['fp']],
                             [results[c,s]['per_crop'][crop]['fn'],results[c,s]['per_crop'][crop]['tp']]] for s in cfg['training_seeds']],axis=0)
            ax.imshow(values,cmap='Blues');ax.set_title(crop);ax.set_xticks([0,1],['normal','abnormal']);ax.set_yticks([0,1],['normal','abnormal'])
            for i in range(2):
                for j in range(2):ax.text(j,i,f'{values[i,j]:.1f}\n{values[i,j]/values[i].sum():.1%}',ha='center',va='center')
        fig.suptitle(c+' — mean confusion counts over seeds (not pooled independent samples)');fig.tight_layout();fig.savefig(root/'figures'/f'{c}_confusion_matrices.png',dpi=180);plt.close(fig)
    # Fixed rule: seed 17, each condition/crop/error type, first three image IDs.
    errors=[]
    for c in 'ABC':
        for crop in CROPS:
            for true in (0,1):
                wrong=sorted([r for r in predictions[c,17] if r['crop']==crop and int(r['binary_label'])==true and int(float(r['p_abnormal'])>=.5)!=true],key=lambda r:r['image_id'])[:3]
                errors.extend(dict(r,condition=c,seed=17,error_type='false_positive' if true==0 else 'false_negative') for r in wrong)
    write_csv(root/'evaluation'/'error_examples.csv',errors,root)
    write_json(root/'evaluation'/'aggregation.json',{'created_at':utc(),'runs':9,'results_measured':True,'independent_test_sample_count_not_multiplied_by_seeds':True},root)
    # Save measured results in prose as well as CSV; never leave a stale
    # "unmeasured" paragraph above final measured tables.
    def aggregate(condition,metric):
        row=next(r for r in summary if r['condition']==condition and r['metric']==metric)
        return f"{100*row['mean']:.2f} ± {100*row['sample_sd']:.2f}%"
    run_rows=[]
    for (condition,seed),metrics in results.items():
        done=read_json(root/'runs'/f'{condition}_seed{seed}'/'completed.json')
        run_rows.append(dict(condition=condition,seed=seed,selected_epoch=done['selected_epoch'],
            elapsed_seconds=done['elapsed_seconds'],updates=done['updates'],amp_skips=done['amp_skips'],
            best_checkpoint_sha256=done['best_checkpoint_sha256']))
    write_csv(root/'tables'/'run_resources.csv',run_rows,root)
    split=read_csv(root/'tables'/'fixed_split_counts.csv')
    train_counts={c:sum(int(r['images']) for r in split if r['crop']==c and r['split']=='train') for c in CROPS}
    low=read_json(root/'manifests'/'lock.json')['low_data_crops']
    lines=['논문 결과·논의 초안 — 고정 테스트 실측',
        '', '연구 질문: 상태별 보정에 작물 종류를 추가하면 작물별 이진 판별 성능이 개선되는가?',
        '방법: ImageNet EfficientNet-B0를 고정하고 A(무보정), B(상태 역빈도), C(작물×상태 역빈도)를 비교했다.',
        '동일 학습 목록·분할·증강·2+28 epoch·시드17/42/2026을 사용했다. 이미지별 가중 CE를 배치 이미지 수로 평균했다.',
        '검증 작물 평균 macro-F1 최고 체크포인트를 선택하고, 테스트는 동일 임계값0.5로 평가했다.',
        '주지표는 8종 각각의 이진 macro-F1을 동일 비중으로 평균한다. 전체 이미지를 합친 pooled binary macro-F1과 구분한다.',
        '', '데이터:', f'학습 이미지 수는 {sum(train_counts.values()):,}장이다. 작물별 학습 수: {train_counts}.',
        f'성능을 보기 전에 학습 수 하위 2종을 저자료 작물로 정했다: {", ".join(low)}.',
        '같은 원본·파생·확인 가능한 촬영 그룹은 한 분할에 묶었다. 평가는 촬영 그룹×작물×상태 대표 이미지로 계산했다.',
        'raw 케일의 새 정상 외관/잎 조직 소실 라벨은 단일 AI의 실제 이미지 검토이다. 식물병리 전문가 검증이나 병원균 진단이 아니다.',
        '폴더상 케일 v5 129장은 원출처의 호박 사진과 대응하여 제외했다. 원본은 수정하지 않았다.',
        '', '전체 결과(3시드 평균 ± 표본 SD):']
    for condition in 'ABC':
        lines.append(f"{condition}: 작물 평균 macro-F1 {aggregate(condition,'equal_crop_binary_macro_f1')}; "
            f"전체 pooled macro-F1 {aggregate(condition,'pooled_binary_macro_f1')}; 정확도 {aggregate(condition,'overall_accuracy')}.")
    lines+=['', '같은 시드끼리 계산한 차이(평균 ± 표본 SD, 퍼센트포인트):']
    for r in deltas:
        if r['crop']=='ALL_EQUAL_CROP':
            lines.append(f"{r['comparison']}: {r['mean_percentage_points']:+.2f} ± {r['sample_sd_percentage_points']:.2f} pp.")
    lines+=['', '작물별 C−B 변화:']
    for r in deltas:
        if r['comparison']=='C-B' and r['crop'] in CROPS:
            lines.append(f"{r['crop']} (train n={train_counts[r['crop']]}): {r['mean_percentage_points']:+.2f} ± {r['sample_sd_percentage_points']:.2f} pp.")
    lines+=['', '실행 자원:', f"9회 실제 학습 누적 {sum(r['elapsed_seconds'] for r in run_rows)/3600:.3f}시간. "
        '이는 데이터 점검·설치·캐시·평가·전송 시간을 포함하지 않는다.',
        '', '논의와 해석 한계:',
        'C−B의 방향과 작물별 변화를 중심으로 작물 정보를 더한 보정의 효과를 기술한다. 악화·무변화도 동일하게 보고한다.',
        '3시드 표본 SD는 통계적 유의성의 증거가 아니다. 신뢰구간이나 p값을 측정 없이 제시하지 않는다.',
        '작물 수·촬영 부위·출처·배경·이상 유형이 함께 다르다. 가중치 효과와 도메인 효과를 완전히 분리했다고 주장하지 않는다.',
        '케일은 성장 촬영 자료의 재주석이며 촬영 시기·품종·생육 단계와 상태의 연관 및 단일 주석자 오류 가능성이 있다.',
        '평가 그룹은 확인 가능한 누출 방지 묶음이며 모든 공개 이미지에서 생물학적 독립성이 증명된 것은 아니다.',
        '내부 테스트 성능은 새로운 촬영 환경이나 미지 이상 상태의 일반화를 입증하지 않는다.',
        '보정 비교의 결과는 해당 데이터·주석·분할에 조건부이며 새로운 알고리즘이나 최초 연구라는 주장을 하지 않는다.',
        '', '재생성 자료: tables/abc_summary.csv, crop_metrics.csv, paired_deltas.csv, run_resources.csv; evaluation/*/predictions.csv.',
        '오분류는 seed17, 조건×작물×오류 종류별 image_id 정렬 앞3개의 고정 규칙으로 선정했다.',
        '', '참고 1차 출처:',
        'Atila et al. 2021 https://doi.org/10.1016/j.ecoinf.2020.101182 — EfficientNet 전이학습 참고; 8종 이진/16그룹 설계는 본 연구의 결정.',
        'Shahoveisi et al. 2023 https://www.nature.com/articles/s41598-023-31942-9 — 식물 이미지 전이학습 참고. 데이터셋 간 정확도 우열 비교를 하지 않는다.',
        'Tong-Le & Doan 2026 https://www.jait.us/articles/2026/JAIT-V17N8-1456.pdf — 통제된 손실 비교 참고; 본 연구의 그룹 분할/3시드는 별도 설계.']
    (root/'paper'/'results_discussion_draft.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    header='<h2>9회 본실험과 고정 테스트 실측</h2><table><tr><th>조건</th><th>작물 평균 macro-F1</th><th>전체 pooled macro-F1</th><th>정확도</th></tr>'
    table=''.join('<tr><td>'+c+'</td>'+''.join('<td>'+aggregate(c,m)+'</td>' for m in ('equal_crop_binary_macro_f1','pooled_binary_macro_f1','overall_accuracy'))+'</tr>' for c in 'ABC')
    section=header+table+'</table><p>3시드 평균 ± 표본 SD. 통계적 유의성을 뜻하지 않습니다.</p><p><a href="paper/results_discussion_draft.txt">실측 결과·논의 초안</a></p><img src="figures/crop_f1_comparison.png"><img src="figures/crop_c_minus_b.png">'
    report=root/'REPORT.html';report.write_text(report.read_text(encoding='utf-8').replace('</html>',section+'</html>'),encoding='utf-8')
    # Illustrative copies are rendered outside the dataset; source files stay read-only.
    from PIL import Image,ImageDraw,ImageOps
    for condition in 'ABC':
        selected=[r for r in errors if r['condition']==condition]
        if not selected:continue
        columns=6;cw,ch=220,220
        sheet=Image.new('RGB',(columns*cw,((len(selected)+columns-1)//columns)*ch),'white');draw=ImageDraw.Draw(sheet)
        for i,r in enumerate(selected):
            x,y=(i%columns)*cw,(i//columns)*ch
            with Image.open(input_path(r['processed_relpath'])) as im:
                preview=ImageOps.exif_transpose(im).convert('RGB');preview.thumbnail((210,170))
            sheet.paste(preview,(x+(cw-preview.width)//2,y))
            draw.text((x+4,y+174),f"{r['crop']} {r['error_type']}\np_abnormal={float(r['p_abnormal']):.3f}\n{r['image_id'][:20]}",fill='black')
        sheet.save(root/'figures'/f'{condition}_error_examples.jpg',quality=92)
    return True

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);a=p.parse_args();root=initialize(a.root);audit_report(root);results_report(root)
