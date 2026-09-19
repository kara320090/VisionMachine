먼저 AGENTS.md, .agents/rules/visionmachine.md, docs/PROJECT_SCOPE.md, docs/STATUS.md, docs/OWNERSHIP.md 및 아래 파트 문서를 읽어라. 사용자 최신 결정과 현재 코드를 우선하고 기존 변경을 보존하라. 구현 계획만 설명하고 끝내지 말고 이번 범위의 실제 파일과 검증 결과를 남겨라. 실기기·자료·모델이 없으면 해당 제약을 정확히 기록하고 가능한 개발을 진행하라. 완료·미완료를 구분하여 docs/STATUS.md를 갱신하라. docs/GIT_COMMITS.md를 따라 `main`에서 작업하고, 검증된 작업 단위마다 관련 파일을 commit한 뒤 `git push origin main`을 수행한다. 다른 사람이 먼저 push했으면 내 커밋을 보존하고 `git fetch origin` 및 `git merge --no-edit origin/main`으로 양쪽 변경을 합친다. 충돌을 검토하여 내 기능과 상대방 변경을 모두 보존하고 재검증한 뒤 다시 push한다. 별도 기능 브랜치 생성, 강제 push, 상대방 변경 덮어쓰기로 해결하지 않는다. 사용자의 최신 요청에 따른 규칙이며, 실제 배포·결제는 포함하지 않는다.

# Android 첫 구현: 촬영·원본 저장 APK

담당: 이봉헌·유재윤. apps/android/README.md, docs/API.md, docs/DATA_PROTOCOL.md를 읽는다.
- apps/android의 기존 상태 및 SDK·JDK·AGP/Gradle 호환성을 확인한다. 없다면 호환되는 Kotlin/Compose 프로젝트를 생성하고 버전·Gradle wrapper를 기록한다. 설치되지 않은 도구로 빌드 성공했다고 하지 않는다.
- 기존 카메라 앱을 호출하고 TakePicture/output URI로 원본을 앱 저장공간에 저장한다. 취소·Activity 복귀·프로세스 복원·URI 권한을 처리한다. thumbnail 저장으로 대체하지 않는다.
- 새 inspection_id와 subject_id/crop_code를 연결하는 저장 모델, 촬영 화면과 이력의 기초를 만든다. 서버/센서 준비 전에도 실제 촬영과 저장은 동작해야 한다.
- 다음 작업을 위한 API DTO와 USB JSONL 파서를 공통 스키마에 맞춰 둔다. mock 화면/패킷은 debug에서 명시하며 sensor 미연결·pending_model을 정상 진단으로 표시하지 않는다.
- 테스트에는 촬영 취소, 파일 없음, 중복 요청, 이전 USB 응답·부분 줄·다중 줄·권한 거부 상태를 포함한다. 실제 기기 시험은 수행한 것만 기록한다.
- 가능한 경우 debug APK를 생성하되 Git에는 포함하지 않는다. 서명키/Google 키/local.properties도 제외한다.

1주차 촬영저장, 2주차 실제 업로드, 3주차 실측 수신, 4주차 RGB 결과, 5주차 기본 왕복 앱, 7주차 베타를 유지한다. 이번에 구현한 범위를 명확히 기록한다.
