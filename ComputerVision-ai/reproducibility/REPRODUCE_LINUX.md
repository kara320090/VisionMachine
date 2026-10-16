# Linux 재현·검증 안내

최종 보관 경로는 사용자 최신 지시에 따라 `/home/user/ComputerVision_ai/`이다. 현재 세션 정책에서 이 경로는 읽기 전용이며, 원본 실험 폴더에 모든 산출물을 보존 중이다. Windows 전송은 완료 조건에서 제외됐다. `transfer/delivery_target_linux.json`을 우선 적용한다.

## 실행 환경과 고정 프로토콜

실행 환경은 전용 `.venv`, Python 3.10.12, PyTorch 2.9.0+cu128, torchvision 0.24.0+cu128, CUDA runtime 12.8, RTX 4090이다. 전체 버전은 `environment.json`, `requirements.lock.txt`에 보관했다. 환경 점검 당시 `code_sha256`은 설치 시점의 코드 해시이고, 본실험의 고정 코드 해시는 `configs/protocol_lock.json` 및 각 `completed.json` 값이다. 두 기록의 시점을 구분한다.

본실험: EfficientNet-B0 IMAGENET1K_V1, 8종, normal=0/abnormal=1, A/B/C × seeds 17/42/2026, 30 epochs, 검증 작물 평균 이진 macro-F1 최고(동률이면 이른 epoch), 테스트 임계값 0.5. 프로토콜·분할·검토 판정은 덮어쓰지 않는다.

## 현재 산출물 검증

아래 명령은 원본 실험 루트에서 실행하며 새 학습을 시작하지 않는다.

```bash
.venv/bin/python -B reproducibility/verify_completed_runs_linux.py
.venv/bin/python -B reproducibility/plot_frozen_training_distribution.py
```

첫 명령은 완료 실행의 코드·설정·분할·체크포인트 SHA, 30 epoch 이력, 선택 규칙, 실제 업데이트·AMP skip, 초기 모델 대응, 저장 가중치를 확인한다. 고정 테스트 예측이 있으면 평가 대표 ID·정답 메타데이터·0.5 임계값·체크포인트 대응과 주지표·pooled 지표·정확도를 독립 재계산한다. 원본 보존·그림·논문·최종 복사 검증은 별도 항목이다.

집계 표 검증 근거는 `final_aggregation_audit_linux.json`이다. `tables/abc_summary.csv`, `crop_metrics.csv`, `paired_deltas.csv`는 각 `evaluation/*/metrics.json`에서 평균과 표본 SD로 재생성할 수 있다. 서로 다른 시드의 동일 테스트 평가를 독립 표본 수로 합산하지 않는다.

## 추론

기존 `code/infer.py`는 고정 캐시가 필요한 SHA 정보를 전달하지 않아 실패하는 문제가 확인됐다. 원본 코드는 보존했다. `followups/inference_v1/protocol_decision.json`에 근거와 범위를 기록하고 별도 어댑터를 검증했다.

```bash
.venv/bin/python -B reproducibility/followups/inference_v1/infer_registered.py \
  --checkpoint "$PWD/runs/A_seed17/checkpoints/best.pt" \
  --processed-relpath 'cucumber/normal/aihub/train/V006_77_0_00_08_01_13_0_c21_20201117_0047_S01_1.JPG'
```

등록된 manifest 이미지 경로와 사용자가 명시한 완료 실행의 validation-selected best.pt를 사용한다. crop 인자는 없고 모델은 이미지 텐서만 받는다. 경로 예시는 학습 이미지이며 스모크 검사 결과를 연구 성능으로 제시하지 않는다. 캐시·원본 경로가 보존된 원래 서버 위치에서 실행해야 한다. 보관 사본만으로 원본 데이터 접근 없이 재학습할 수 있다는 뜻은 아니다.

## 재학습·재평가 원칙

현재 suite와 결과를 덮어쓰거나 같은 위치에서 중복 학습하지 않는다. 재현 학습은 별도 고유 실험과 명시적 프로토콜 버전으로 수행해야 한다. 장기 학습·평가는 기존 jobctl과 execution.lock/flock으로 관리한다. 현 설정은 절대 경로를 포함하므로 위치 변경 시 새 실험에서 경로·캐시·프로토콜 잠금을 재검증하고 기존 고정 파일을 몰래 수정하지 않는다.

이미 완료한 테스트를 같은 경로에서 다시 실행하지 않는다. 고정 `code/evaluate.py`는 기존 출력이 있으면 차단한다. 표·그림 재생성은 `code/report.py`가 제공하나 기존 REPORT.html·결과 초안을 덮어쓰므로 보존된 결과를 검증하거나 별도 분석 사본에서 실행한다. 해당 고정 리포터의 보관 문구는 과거 Windows 경로이므로 최신 Linux 보관 지시와 후속 문서를 함께 유지해야 한다.

## 논문·원본 보존·최종 복사

서론·방법: `paper/introduction_methods_draft_ko.md`. 실측 표 기반 초안: `paper/results_discussion_draft.txt`. 해석·오분류·결론: `paper/measured_interpretation_conclusion_ko.md`. 주석 범위와 참고문헌 확인 한계는 각각 `annotation_scope_notes.txt`, `reference_evidence.txt`. 모든 결과는 단일 AI 신규 주석과 출처·촬영 부위·배경 혼재의 한계를 포함한다.

원본 최종 전체 SHA 검사는 suite가 수행하며, 종료 후의 `audit/preservation_*.json`에 issues=[] 및 passed=true가 있어야 한다. `runs/suite_completed.json` 없이 전체 suite 완료로 판단하지 않는다.

최종 보관은 지정 Linux 경로의 고유 스냅샷에서 상대 파일 목록·크기·SHA-256을 확인하고 영수증을 생성해야 한다. 서버의 `bundle_*.receipt.json`은 묶음 생성 영수증이며 목적지 복사 성공을 증명하지 않는다. `*_archive_verified_linux.json`도 서버 묶음 내부 검증이다. 원본 실험·전송 묶음은 자동 삭제하지 않는다.
