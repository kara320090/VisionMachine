먼저 AGENTS.md, .agents/rules/visionmachine.md, docs/PROJECT_SCOPE.md, docs/STATUS.md, docs/OWNERSHIP.md 및 아래 파트 문서를 읽어라. 사용자 최신 결정과 현재 코드를 우선하고 기존 변경을 보존하라. 구현 계획만 설명하고 끝내지 말고 이번 범위의 실제 파일과 검증 결과를 남겨라. 실기기·자료·모델이 없으면 해당 제약을 정확히 기록하고 가능한 개발을 진행하라. 완료·미완료를 구분하여 docs/STATUS.md를 갱신하라. docs/GIT_COMMITS.md를 따라 `main`에서 작업하고, 검증된 작업 단위마다 관련 파일을 commit한 뒤 `git push origin main`을 수행한다. 다른 사람이 먼저 push했으면 내 커밋을 보존하고 `git fetch origin` 및 `git merge --no-edit origin/main`으로 양쪽 변경을 합친다. 충돌을 검토하여 내 기능과 상대방 변경을 모두 보존하고 재검증한 뒤 다시 push한다. 별도 기능 브랜치 생성, 강제 push, 상대방 변경 덮어쓰기로 해결하지 않는다. 사용자의 최신 요청에 따른 규칙이며, 실제 배포·결제는 포함하지 않는다.

# 파트 연결 시험

먼저 각 파트의 STATUS와 계약 버전·실행법을 확인한다. 미구현 기능을 정상 응답으로 감추지 않는다.
1. 촬영 원본의 SHA-256과 inspection_id, 대상/작물/촬영시각을 확인한다.
2. 같은 inspection_id로 센서 요청·실측 수신, raw/calibration/mode와 수신시각을 기록한다.
3. 사진+metadata를 서버로 올리고 DB/파일 저장·재시도·중복·충돌·실패 후 재시작을 확인한다.
4. 실제 RGB 모델이 있으면 전처리·가중치 버전을 기록해 추론하고, 없으면 pending_model을 유지한다.
5. 앱 결과·근거·이력·오류/대기·mock 표시를 확인한다. 인터넷 끊김/USB 분리/오래된 센서/서버 오류를 각각 시험한다.
6. 결과는 docs의 날짜별 통합기록에 코드 commit·장치·모델·data origin·실행 명령·통과/실패/미실행으로 남긴다.

독립시험은 12주차 고정 버전으로 별도 시행하며 최종시험 정답을 개발자가 튜닝에 쓰지 않게 한다. 원본 이미지·토큰·실제 정답은 공개 결과 기록에 넣지 않는다.
