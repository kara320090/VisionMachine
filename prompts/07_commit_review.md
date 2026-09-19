먼저 AGENTS.md, .agents/rules/visionmachine.md, docs/PROJECT_SCOPE.md, docs/STATUS.md, docs/OWNERSHIP.md 및 아래 파트 문서를 읽어라. 사용자 최신 결정과 현재 코드를 우선하고 기존 변경을 보존하라. 구현 계획만 설명하고 끝내지 말고 이번 범위의 실제 파일과 검증 결과를 남겨라. 실기기·자료·모델이 없으면 해당 제약을 정확히 기록하고 가능한 개발을 진행하라. 완료·미완료를 구분하여 docs/STATUS.md를 갱신하라. docs/GIT_COMMITS.md를 따라 `main`에서 작업하고, 검증된 작업 단위마다 관련 파일을 commit한 뒤 `git push origin main`을 수행한다. 다른 사람이 먼저 push했으면 내 커밋을 보존하고 `git fetch origin` 및 `git merge --no-edit origin/main`으로 양쪽 변경을 합친다. 충돌을 검토하여 내 기능과 상대방 변경을 모두 보존하고 재검증한 뒤 다시 push한다. 별도 기능 브랜치 생성, 강제 push, 상대방 변경 덮어쓰기로 해결하지 않는다. 사용자의 최신 요청에 따른 규칙이며, 실제 배포·결제는 포함하지 않는다.

# 커밋 전 검토

git status와 diff/staged diff를 확인해 이번 작업만 검토하라.
- main에서 작업 중이며 최신 origin/main과 내 커밋을 모두 포함하는가? 병합 충돌을 한쪽 파일 전체 선택으로 처리해 상대방 기능을 없애지 않았는가?
- docs/GIT_COMMITS.md 기준으로 코드·계약·시험·문서가 같은 변경 단위를 이루는가?
- 원본 사진/DB/정답/모델/APK/비밀키/학교 개인정보가 추적되는가? .gitignore뿐 아니라 이미 tracked인 파일도 확인한다.
- 변경 범위에 맞는 검사를 실행했는가? 코드·계약 변경은 scripts/check.py와 해당 파트 빌드/시험, 문서 변경은 링크·지시문 일관성·diff를 확인한다. 실기기 미검증은 명시한다.
- 앱·서버·펌웨어 간 계약 변경과 버전·예제가 함께 갱신되었는가?
- 모델 없음/센서 없음/모의 상태를 실제 정상 판정으로 바꾸지 않았는가?
- 독립시험·교정·데이터 누수 원칙이 깨지지 않았는가?

문제는 먼저 수정하고 변경 이유·검증·남은 한계를 정리하라. 검토된 파일만 명시적으로 stage하고 작은 commit을 main에 만든 뒤 origin/main에 push하라. 원격이 앞서면 양쪽 커밋을 병합·재검증한 뒤 다시 push하라. Git author를 임의 설정하거나 force push하지 않는다.
