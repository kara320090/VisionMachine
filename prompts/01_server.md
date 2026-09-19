먼저 AGENTS.md, .agents/rules/visionmachine.md, docs/PROJECT_SCOPE.md, docs/STATUS.md, docs/OWNERSHIP.md 및 아래 파트 문서를 읽어라. 사용자 최신 결정과 현재 코드를 우선하고 기존 변경을 보존하라. 구현 계획만 설명하고 끝내지 말고 이번 범위의 실제 파일과 검증 결과를 남겨라. 실기기·자료·모델이 없으면 해당 제약을 정확히 기록하고 가능한 개발을 진행하라. 완료·미완료를 구분하여 docs/STATUS.md를 갱신하라. docs/GIT_COMMITS.md를 따라 `main`에서 작업하고, 검증된 작업 단위마다 관련 파일을 commit한 뒤 `git push origin main`을 수행한다. 다른 사람이 먼저 push했으면 내 커밋을 보존하고 `git fetch origin` 및 `git merge --no-edit origin/main`으로 양쪽 변경을 합친다. 충돌을 검토하여 내 기능과 상대방 변경을 모두 보존하고 재검증한 뒤 다시 push한다. 별도 기능 브랜치 생성, 강제 push, 상대방 변경 덮어쓰기로 해결하지 않는다. 사용자의 최신 요청에 따른 규칙이며, 실제 배포·결제는 포함하지 않는다.

# 서버 첫 구현: 실제 사진 업로드·저장

담당: 정회서·이봉헌. server/README.md, docs/API.md, docs/DATA_PROTOCOL.md와 공통 모델을 읽는다.
이번 범위는 POST /v1/inspections 및 GET /v1/inspections/{id}의 로컬 실제 저장이다.
- multipart photo + metadata JSON 문자열을 받는다. python-multipart/이미지 디코더를 의존성에 추가하고 호환 버전을 잠근다.
- 공통 계약 검증, JPEG/PNG 디코딩·크기/픽셀 상한, 실제 SHA-256 대조. 파일명으로 경로를 만들지 않는다.
- settings, repository, file storage와 migration을 실제로 연결한다. owner는 인증 인터페이스로 분리하고 로컬 개발 신원을 제품 인증처럼 설명하지 않는다.
- inspection_id 기준 동일 내용 재시도는 기존 검사, 다른 내용은409. canonical metadata·사진 해시로 비교한다. partial write/rollback/orphan 파일/재시작 복구를 고려한다.
- 모델 미탑재는 pending_model. mock 입력을 실제 결과로 바꾸지 않는다. 사진 업로드 성공과 AI 분석 완료를 분리한다.
- 임시 폴더/DB 기반 시험으로 업로드·조회·재시작·중복·충돌·잘못된 이미지·해시 불일치·파일 실패를 확인한다.
- 앱이 따라할 요청 예와 반환 구조를 갱신한다. 외부 배포·인증 완성·실모델 추론을 이번 작업 성과로 과장하지 않는다.

다음 단계는 소유자별 인증·이력·삭제·백업/복구, 실제 Predictor 연결이다. API와 스키마 변경은 앱·데이터 파트 영향까지 기록한다.
