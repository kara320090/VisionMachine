# 로컬에 보존한 자료

사용자의 최신 요청에 따라 논문 작성·모델 보관·검토에 필요한 자료를 선정했다. 아래 내용은 바탕화면의 ComputerVision-ai 원본에 그대로 남겨두었다.

- 이미지 전수 목록: research_inventory.csv, image_inventory.csv, provisional_review_manifest.csv.
- 이미지별 전체 분할 목록 fixed_split.csv. 공개본에는 분할 해시와 작물·상태별 집계만 남겼다.
- 캐시·심볼릭 링크 목록과 각 학습 이미지의 weights.csv.
- 반복된 검토 초안·전체 그룹 목록·source_supported_mapping.csv·decisions.csv 등의 대형 중간 대응표.
- 중간·pilot 모델, last.pt, epoch별 체크포인트와 중복 tar·ZIP.
- 과거 전달 스냅샷·전송 디버깅 기록·전체 원본 파일 색인.

검토 화면·썸네일·패널 이미지·최종 시각 주석 원장·출처/중복 검토 요약은 공개본에 포함했다. 이 페이지로 연결된 옛 HTML 링크는 제외한 로컬 자료를 가리키던 링크다.

동일한 이미지 단위 분할로 재학습하거나 전수 판정을 재검증하려면 로컬의 원래 목록과 원본 이미지·캐시를 사용해야 한다. 모델과 집계표만으로 그 목록을 복원할 수는 없다.
