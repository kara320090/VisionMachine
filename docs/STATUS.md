# 현재 구현 상태

## 이 패키지에 구현한 것
- 공통 계약 Python 모델과 생성 JSON Schema, 명시된 합성 예제.
- 서버 GET /healthz, GET /v1/capabilities, POST /v1/dev/validate-inspection.
- 모델 미탑재를 반환하는 ML 인터페이스(실제 추론 없음).
- CSV manifest의 필수값·경로·형식·중복 ID·그룹별 split 누수 검사.
- 로컬 SQLite 초기화 CLI, 저장 경로 설정, 설치 패키지에 포함하는 SQL. 재실행 시 데이터 보존, 외래키, 알 수 없는 DB 거부, 실패 롤백 시험. HTTP API는 아직 DB에 연결하지 않음.
- 실제 구현 API에서 생성한 OpenAPI, JSON Schema 동기화 검사, 실제 localhost HTTP smoke.
- `scripts/check.py` 단일 검사 명령, Linux/Windows GitHub Actions 구성.

## 다음에 구현할 것
1. 서버: 준비된 로컬 DB 기반 위에 실제 multipart 사진+메타데이터 업로드, 파일 검증, 비공개 저장, DB 트랜잭션, 중복/충돌, 재시작 후 조회.
2. 앱: Android 프로젝트와 Gradle wrapper 생성, 카메라 호출·원본 사진 저장 APK. 같은 시기에 API DTO 작성.
3. 계측: UNO R4 실제 센서 읽기, USB 패킷, 보정/오류/재연결 시험.
4. 데이터: 실제 자료 확보·이용조건 확인·현장 라벨 기준·개체 목록·정제·분할. 지금 예제는 모두 합성.
5. AI: 첫 실제 RGB 모델, 센서 단독·융합 학습 및 평가. 모델·성능 수치는 아직 없음.

생성된 JSON Schema와 문서의 API 설계는 앱 개발의 기준 초안이다. 실제 구현과 예정 API를 혼동하지 않도록 docs/API.md의 구분을 유지한다. 상태 확인 API나 mock 응답 통과를 제품 완성으로 보고하지 않는다.

검증 환경·결과는 docs/VALIDATION.md 참고. 실휴대폰·실센서·Android 빌드·GPU·Play 배포는 시험하지 않았다.

2026-09-19 로컬 검증: 저장소 .venv/Python 3.12.14, `scripts/check.py` 통과(52 pytest, 외부 의존성 경고 2개). `6b327f8` 최초 CI와 `e6888ee` Windows/Linux CI 통과. 후속 push의 최신 CI는 Actions에서 확인한다.

개발 인계: [NEXT_STEPS](NEXT_STEPS.md), 최신 배선/구매 범위: [HARDWARE](HARDWARE.md). 검증한 단위마다 현재 branch를 commit/push한다.
