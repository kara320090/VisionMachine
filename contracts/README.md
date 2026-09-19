# 공통 계약 v0.1.0 — 검토 초안

원본은 `packages/contracts/src/vm_contracts/models.py`다. `python scripts/export_contracts.py`로 schemas를 생성한다. Python 모델을 변경했으면 생성물도 함께 커밋한다. 앱·펌웨어는 같은 예제로 계약 시험을 만든다.

`examples/`의 모든 값은 **합성**이며 실제 측정·사진·성능이 아니다. 해시 a×64는 실제 파일 해시가 아니다. 실제 업로드 시험은 별도 생성한 사진 바이트의 SHA-256을 사용해야 한다.

JSON Schema는 타입/범위를 표현한다. request_id 연결, ADC 비트 범위, 결측 사유, 교정 ID, mock 경고 등 필드 간 관계는 Python validator와 docs/DATA_PROTOCOL.md의 의미 규칙도 적용해야 한다. 스키마 검사만으로 모든 의미 검증이 끝나지 않는다.
