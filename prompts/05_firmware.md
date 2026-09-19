먼저 AGENTS.md, .agents/rules/visionmachine.md, docs/PROJECT_SCOPE.md, docs/STATUS.md, docs/OWNERSHIP.md 및 아래 파트 문서를 읽어라. 사용자 최신 결정과 현재 코드를 우선하고 기존 변경을 보존하라. 구현 계획만 설명하고 끝내지 말고 이번 범위의 실제 파일과 검증 결과를 남겨라. 실기기·자료·모델이 없으면 해당 제약을 정확히 기록하고 가능한 개발을 진행하라. 완료·미완료를 구분하여 docs/STATUS.md를 갱신하라. docs/GIT_COMMITS.md를 따라 `main`에서 작업하고, 검증된 작업 단위마다 관련 파일을 commit한 뒤 `git push origin main`을 수행한다. 다른 사람이 먼저 push했으면 내 커밋을 보존하고 `git fetch origin` 및 `git merge --no-edit origin/main`으로 양쪽 변경을 합친다. 충돌을 검토하여 내 기능과 상대방 변경을 모두 보존하고 재검증한 뒤 다시 push한다. 별도 기능 브랜치 생성, 강제 push, 상대방 변경 덮어쓰기로 해결하지 않는다. 사용자의 최신 요청에 따른 규칙이며, 실제 배포·결제는 포함하지 않는다.

# 계측 첫 구현: 실측 USB 패킷

담당: 최승빈·정회서. firmware/README.md, docs/DATA_PROTOCOL.md와 sensor schema를 읽는다.
- UNO R4 Minima 한 대, DFR0265, SEN0308 A0, SEN0334 I2C의 실제 구성·전압·추가 GND·완성 케이블·core/라이브러리 버전을 확인한다. 납땜·전선 접합을 기본 작업으로 만들지 않는다.
- 센서 읽기, 보정, USB 요청/응답을 분리한 Arduino C++ 스케치를 생성한다. 실제 ADC 해상도를 선언하고 원시값을 보존한다. 교정계수·온습도·모의 수치를 실측처럼 넣지 않는다.
- JSONL 측정 요청의 request_id를 응답에 반환한다. boot/sequence/uptime/firmware/mode/calibration/errors를 기록하고 오류는 null로 표현한다. debug 텍스트를 프로토콜에 섞지 않는다.
- 데스크톱 mock simulator는 mode=mock을 유지한다. 실제 장치가 없으면 컴파일·패킷 시험과 실물 미검증을 구분한다.
- 앱 파트와 실제 USB 인식·권한·전원·수신·분리/재연결·오래된 응답 거부를 시험한다. 반복 측정·재배치·온습도 센서 열 간섭을 기록한다.
- 광학 확장은 기본 경로 이후 센서/광원/차광/참고값 검증과 계약 확장을 별도로 진행한다. 연결만으로 당도·내부결함 검증 완료라 하지 않는다.

산출물: 펌웨어·패킷 테스트·연결/보정 절차·실제로 수행한 반복시험 기록.
