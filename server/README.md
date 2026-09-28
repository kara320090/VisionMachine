# 서버 파트 — 정회서·이봉헌

현재 main.py는 상태/지원범위/메타데이터 검증과 로컬 전용 사진 업로드·단건 조회를 제공한다. JPEG/PNG 바이트·해시·디코딩·크기·픽셀 수를 확인하고 SQLite 메타데이터와 비공개 파일을 저장한다. 실제 추론·인증·외부 접속은 없다.

저장소 루트에서 `python -m vm_server init-db`를 실행한다. 기본 DB는 `storage/visionmachine.db`, 사진 폴더는 `storage/uploads/`다. `VM_STORAGE_DIR` 프로세스 환경변수를 읽고 `.env`는 자동 로딩하지 않는다. 기존 DB를 지우지 않으며 알 수 없는 버전/기존 무버전 테이블은 오류로 반환한다. SQL 원본은 `src/vm_server/migrations/` 한 곳이다.

다음 파일 배치:
```text
src/vm_server/
  main.py                    앱 생성·router 등록
  settings.py                환경변수 검증
  database.py                구현됨: DB 연결·외래키·트랜잭션 초기화
  migrations/                구현됨: 패키지에 포함하는 SQL 원본
  inspections.py             구현됨: 로컬 업로드·단건 조회·중복/충돌 처리
  api/inspections.py         후속: 인증·이력·삭제 HTTP 처리
  api/dependencies.py        인증·소유자 범위
  services/inspections.py    중복·충돌·상태 전이
  services/analysis.py       모델 호출·미탑재·실패 처리
  repositories/             DB 접근(HTTP 코드와 분리)
  storage/                  비공개 파일 저장·삭제·복구
  inference/                vm_ml.Predictor 연결
```

SQLite를 먼저 연결하고 전체 계층을 쓸데없이 더 나누지 않는다. API→서비스→저장/추론 경계가 시험 가능한 정도면 충분하다. 파일 업로드부터 실제 구현한 뒤 운영 DB·작업 큐 필요성을 판단한다. 백그라운드 추론은 재시작 후 작업 유실을 처리하기 전 운영 완료로 보지 않는다.

첫 업로드는 multipart의 `photo` 파일과 `metadata` JSON 문자열을 함께 보낸다. 첫 저장은 201, 동일 요청 재시도는 200, 같은 검사 ID의 다른 내용은 409다. 오류의 `detail.code`에 원인이 표시된다. 파일명은 무시하고 서버 생성 키로 저장한다. 모델이 없어 결과는 `pending_model`이다. DB 시험은 tests/test_database_setup.py와 tests/test_storage_schema.py, 업로드 시험은 tests/test_upload.py에 있다.

소유자별 인증·이력·삭제·백업과 충돌 후 복구는 후속 작업이다. 서버는 127.0.0.1에만 바인딩해 사용한다. 이 패키지는 단일 로컬 검증 서버이며 보안·운영 완료 제품이 아니다.
