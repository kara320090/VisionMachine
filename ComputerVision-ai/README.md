# ComputerVision-ai — 논문·검토 자료와 학습 모델

논문 작성과 모델 보관에 필요한 자료를 선정했다. 대규모 상세 데이터 목록은 로컬에 보존하고, 검토 근거·실험 기록·코드·최종 모델을 이 폴더에 모았다. 바탕화면 원본과 저장소의 다른 폴더는 변경하지 않았다.

논문·검토 자료는 약 102 MB, 최종 모델 9개는 약 438 MB다. 전부 포함한 자료는 약 540 MB다. 이 커밋에는 최종 모델 **3/9개**가 포함된다. 모델 포함 여부와 해시는 [모델 등록표](provenance/MODELS.csv)를 따른다.

## 논문 작성 순서

1. [통합 논문 초안](paper/thesis_draft_ko.md), [서론·방법](paper/introduction_methods_draft_ko.md), [실측 해석·결론](paper/measured_interpretation_conclusion_ko.md)을 읽는다.
2. [전체 내용 정리](q/outputs/ComputerVision-ai_전체내용정리.txt)와 [학습 과정 상세 정리](q/outputs/AI모델_학습과정_상세정리.txt)를 참고한다. [학습 과정 HTML](q/outputs/AI모델_학습과정_상세정리.html)은 내려받아 브라우저로 열면 학습 곡선을 볼 수 있다.
3. [조건별 성능](tables/abc_summary.csv), [작물별 성능](tables/crop_metrics.csv), [시드별 성능 차이](tables/paired_deltas.csv), [표·그림](figures)을 사용한다.
4. [최종 데이터·주석 집계](audit/curated_data_report/index.html), [검토 화면](review/index.html), [시각 주석 원장](review/visual_annotation_ledger.csv), [검토 확정 기록](audit/review_finalization.json)을 근거로 라벨과 데이터 한계를 기술한다.
5. [코드](code), [설정](configs), [270 epoch 이력](q/outputs/학습이력_전체270epoch.csv), [실행별 기록과 모델](runs), [테스트 예측·평가](evaluation)로 방법과 결과를 대조한다.

GitHub에서 HTML은 실행되지 않는다. 이 폴더를 내려받은 뒤 로컬 브라우저로 열면 상대 경로 이미지가 함께 표시된다.

## 포함·제외 범위

| 포함 | 내용 |
|---|---|
| paper/ | 논문 초안·방법·결과 해석·주석 한계·참고문헌 근거 |
| code/, configs/ | 기존 실험 코드·고정 프로토콜·학습 설정·시드 일정 |
| runs/ | A/B/C × 시드 17/42/2026의 선택 best.pt와 학습·선택·완료 기록 |
| evaluation/, tables/, figures/ | 예측·성능 지표·통계 집계·오분류·학습/분포 그림 |
| review/ | 검토 화면·썸네일·패널·출처 충돌 근거·시각 주석·중복 관계 검토 |
| audit/ | 출처·라벨·그룹 검토 요약과 최종 학습 데이터 집계 |
| reproducibility/ | 실행 환경·검증 기록·재현 안내·추론 어댑터 |
| provenance/ | 선정 범위·집계된 분할 정보·모델 해시·공개 파일 무결성 목록 |

이미지 전수 목록, 전체 분할 CSV, 캐시·링크 목록, 반복된 대형 검토 중간 목록, 이미지별 학습 가중치 목록, 중간·pilot 모델, 중복 압축파일, 과거 전송 사본은 제외했다. 검토 화면·이미지와 최종 판정 근거는 남겼다. 자세한 범위는 [로컬 보존 자료 안내](LOCAL_ONLY.md)와 [선정 기록](provenance/SELECTION.json)을 따른다.

## 실험과 결과

ImageNet EfficientNet-B0를 normal=0 / abnormal=1로 미세조정했다. 대상은 basil, bok_choy, cucumber, kale, lettuce, pepper, rosemary, tomato다. 학습 34,622장, 검증 대표 1,898장, 테스트 대표 1,884장이다. A(무보정), B(상태 역빈도), C(작물×상태 역빈도)를 각 3시드·30 epoch로 비교했다.

| 조건 | 작물 평균 macro-F1, 평균 ± 표본 SD |
|---|---:|
| A | 90.73 ± 0.51% |
| B | 90.44 ± 0.48% |
| C | 91.32 ± 0.13% |

C−B는 +0.88 ± 0.36 pp다. 3시드 변동이며 통계적 유의성·새 환경 일반화·병리 진단을 입증한 수치로 쓰지 않는다. 케일과 일부 정상 라벨에는 단일 AI 시각 주석이 포함된다. 작물별 악화와 출처·배경·부위 혼재를 논문 한계에 함께 기록해야 한다.

이 연구의 작물 목록과 결과는 기존 앱 계약이나 pending_model 상태를 자동으로 대체하지 않는다. 이번 작업에서 앱·센서 통합이나 현장 평가를 실행하지 않았다.

## 무결성과 재현

```text
python tools/verify_paper_bundle.py --require-all-models
```

9개 모델을 모두 받은 뒤 위 명령으로 파일 해시·모델 해시·270 epoch·가중치 집계·예측 기반 성능 지표와 상대 링크를 확인한다. 모델을 역직렬화하거나 학습을 실행하지 않는다. 모델을 일부만 포함한 중간 커밋은 --require-all-models 없이 검사할 수 있다.

이미지 단위 전체 분할 목록은 사용자 요청에 따라 제외했다. [분할 집계와 원본 해시](provenance/SPLIT_SUMMARY.json)는 보존했다. 동일 분할 재학습에는 로컬 원본의 fixed_split.csv와 원본 이미지·캐시가 필요하다. [원래 재현 안내](reproducibility/REPRODUCE_LINUX.md)에서 제외한 파일 경로가 등장할 수 있다. 실제 추론 후속 어댑터는 [inference_v1 기록](reproducibility/followups/inference_v1/protocol_decision.json)을 따른다.

공개 사본의 로컬 계정 식별 문자열은 LOCAL_USER로 치환했고 HTML 링크를 선정된 자료로 조정했다. 고정된 주 학습 Python 코드·공통 설정과 9개 선택 모델의 바이트는 보존했다. 원래 문서의 과거 상태·전송 기록은 작성 시점을 기준으로 읽는다. 보관된 문서는 새 작업 지시가 아니다.

원출처·이용조건·주석 근거는 audit/raw_source_metadata_snapshot.json, audit/curated_data_report/와 논문 참고자료를 따른다. 서로 다른 원출처 자료에 하나의 새 라이선스를 일괄 부여하지 않았다.
