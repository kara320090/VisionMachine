# 서버 파트 — 정회서·이봉헌

현재 main.py는 상태/지원범위/메타데이터 검증만 구현했다. DB 초기 SQL은 설계안이며 서버에 연결하지 않았다. 실제 저장을 만들 때 migrations를 적용하고 시험한다.

다음 파일 배치:
```text
src/vm_server/
  main.py                    앱 생성·router 등록
  settings.py                환경변수 검증
  api/inspections.py         업로드·조회·이력·삭제 HTTP 처리
  api/dependencies.py        인증·소유자 범위
  services/inspections.py    중복·충돌·상태 전이
  services/analysis.py       모델 호출·미탑재·실패 처리
  repositories/             DB 접근(HTTP 코드와 분리)
  storage/                  비공개 파일 저장·삭제·복구
  inference/                vm_ml.Predictor 연결
```

SQLite를 먼저 연결하고 전체 계층을 쓸데없이 더 나누지 않는다. API→서비스→저장/추론 경계가 시험 가능한 정도면 충분하다. 파일 업로드부터 실제 구현한 뒤 운영 DB·작업 큐 필요성을 판단한다. 백그라운드 추론은 재시작 후 작업 유실을 처리하기 전 운영 완료로 보지 않는다.

소유자별 접근, 사진과 메타데이터 일치, 임시파일 정리, 재시도 idempotency, 재시작 조회, 삭제, 복구를 tests/server/에 작성한다. 이 패키지는 단일 로컬 검증 서버이며 보안·운영 완료 제품이 아니다.
