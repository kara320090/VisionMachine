먼저 AGENTS.md, .agents/rules/visionmachine.md, docs/PROJECT_SCOPE.md, docs/STATUS.md, docs/OWNERSHIP.md 및 아래 파트 문서를 읽어라. 사용자 최신 결정과 현재 코드를 우선하고 기존 변경을 보존하라. 구현 계획만 설명하고 끝내지 말고 이번 범위의 실제 파일과 검증 결과를 남겨라. 실기기·자료·모델이 없으면 해당 제약을 정확히 기록하고 가능한 개발을 진행하라. 완료·미완료를 구분하여 docs/STATUS.md를 갱신하라. docs/GIT_COMMITS.md를 따라 `main`에서 작업하고, 검증된 작업 단위마다 관련 파일을 commit한 뒤 `git push origin main`을 수행한다. 다른 사람이 먼저 push했으면 내 커밋을 보존하고 `git fetch origin` 및 `git merge --no-edit origin/main`으로 양쪽 변경을 합친다. 충돌을 검토하여 내 기능과 상대방 변경을 모두 보존하고 재검증한 뒤 다시 push한다. 별도 기능 브랜치 생성, 강제 push, 상대방 변경 덮어쓰기로 해결하지 않는다. 사용자의 최신 요청에 따른 규칙이며, 실제 배포·결제는 포함하지 않는다.

# 최초 실행 프롬프트

VisionMachine 저장소의 개발 기반을 점검하고 첫 주 작업을 시작할 수 있게 준비해 줘.
1. git status, 원격, 현재 branch/commit, 실제 파일 목록을 확인한다. 기존 코드가 있으면 이 패키지와 비교하여 필요한 부분만 병합한다. .git·기존 파일·사용자 변경을 제거하지 않는다.
2. START_HERE.md, README.md, docs/ARCHITECTURE.md, docs/GIT_COMMITS.md, docs/DEVELOPMENT_PLAN.md를 읽고 구현됨/예정임을 구분한다. .agents 규칙 활성화는 실제 Antigravity UI 지원 상태를 확인한다.
3. Python 3.12 가상환경에서 requirements.lock.txt와 로컬 패키지를 설치하고 pytest, 계약 동기화, 합성 manifest 검사를 실행한다. 실패가 있으면 원인을 수정하고 다시 확인한다.
4. 모델·실측이 없어도 서버 검증 API가 실행되고 결과가 pending_model/모의 표시임을 확인한다. 사진 업로드가 아직 없다는 사실을 명시한다.
5. docs/STATUS.md에 실제 실행환경·검증 결과와 다음 두 작업을 기록한다: 서버의 실제 사진 업로드·저장, Android 촬영·원본 저장 APK. 앱을 서버/모델 완료 이후로 미루지 않는다.
6. docs/GIT_COMMITS.md 순서에 맞춰 검토 가능한 커밋 묶음과 포함 파일을 제시한다. 검증된 파일만 commit하고 바로 push한다. 사용자 설정 author는 임의 변경하지 않는다.

산출물: 실행 가능한 기존 최소 서버 확인, 테스트 결과, 구현 상태표, 첫 주 구체적 작업목록. 모든 파트를 한 번에 완성했다고 쓰지 않는다.
