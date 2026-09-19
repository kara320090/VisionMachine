먼저 AGENTS.md, .agents/rules/visionmachine.md, docs/PROJECT_SCOPE.md, docs/STATUS.md, docs/OWNERSHIP.md 및 아래 파트 문서를 읽어라. 사용자 최신 결정과 현재 코드를 우선하고 기존 변경을 보존하라. 구현 계획만 설명하고 끝내지 말고 이번 범위의 실제 파일과 검증 결과를 남겨라. 실기기·자료·모델이 없으면 해당 제약을 정확히 기록하고 가능한 개발을 진행하라. 완료·미완료를 구분하여 docs/STATUS.md를 갱신하라. 검증된 작업 단위마다 관련 파일을 commit하고 origin의 현재 작업 branch에 push한다. 사용자의 최신 요청에 따른 규칙이며, 실제 배포·결제는 포함하지 않는다.

# 커밋 전 검토

git status와 diff/staged diff를 확인해 이번 작업만 검토하라.
- docs/GIT_COMMITS.md 기준으로 코드·계약·시험·문서가 같은 변경 단위를 이루는가?
- 원본 사진/DB/정답/모델/APK/비밀키/학교 개인정보가 추적되는가? .gitignore뿐 아니라 이미 tracked인 파일도 확인한다.
- pytest와 contracts export --check 및 변경 파트 빌드를 실행했는가? 실기기 미검증은 명시되어 있는가?
- 앱·서버·펌웨어 간 계약 변경과 버전·예제가 함께 갱신되었는가?
- 모델 없음/센서 없음/모의 상태를 실제 정상 판정으로 바꾸지 않았는가?
- 독립시험·교정·데이터 누수 원칙이 깨지지 않았는가?

문제는 먼저 수정하고 변경 이유·검증·남은 한계를 정리하라. 검토된 파일만 명시적으로 stage하고 작은 commit을 만든 뒤 현재 branch를 origin에 push하라. Git author를 임의 설정하거나 force push하지 않는다.
