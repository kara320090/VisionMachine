# 시작 패키지 검증 기록

검증일: 2026-09-19. Windows, Python 3.12.14, 저장소 안의 .venv(Python 3.12.14)를 새로 만들고 잠금 의존성과 로컬 패키지를 설치하여 다시 실행했다. 정확한 라이브러리 버전은 `requirements.lock.txt`에 기록했다.

| 검사 | 실제 결과 |
|---|---|
| `python -m pytest -q` | **52 passed**, 외부 라이브러리 deprecation 경고 2개 |
| `python scripts/export_contracts.py --check` | Python 계약과 생성 JSON Schema 일치 |
| `python scripts/export_openapi.py --check` | 실제 구현 API와 OpenAPI 일치 |
| `python scripts/smoke_server.py` | 실제 localhost HTTP 상태·지원범위·합성 검사 요청 성공, 생성한 프로세스 종료 |
| 설치 패키지 재현 | wheel에 SQL 포함, 소스 폴더 밖에서 설치 패키지로 init-db 성공 |
| 로컬 DB setup | 재실행/재오픈 후 데이터 보존, 외래키, 미지원 DB 거부, SQL 실패 롤백 시험 통과 |
| 합성 manifest + `--allow-synthetic` | 합성 3행의 형식 검사 통과 |
| 합성 manifest, 허용 옵션 없음 | 실패 종료 확인; 실제 자료로 자동 수용하지 않음 |
| `firmware/simulate_packet.py --request-id ...` | JSONL 출력·요청 ID 유지·`mode=mock` 확인 |
| `python -m pip check` | 의존성 충돌 없음 |
| Git ignore 점검 | 개인정보/비밀/실데이터/산출물 경로 예 13개 제외, 소스/설정/Android 리소스 경로 예 10개 유지 |
| Markdown 상대 링크 | 작성한 문서 내 링크 대상 존재 확인 |

52개 시험은 다음의 구현을 검증한다.
- ADC 범위·유한수·결측 오류·교정 없는 지수·검사 ID 연결·시간대·모의 표시 검증.
- 미탑재 모델이 진단/정확도를 만들어내지 않는 응답, API 입력 오류와 미구현 업로드 경로의 구분.
- 개체·원식물·묶음·중복·해시의 직접/연쇄 누수, 경로 이탈, 중복 ID, 잘못된 CSV, 최종 자료 검사 조건.
- SQLite 초기 구조 재적용, 외래키 거부와 삭제 연결, 초기화 CLI·알 수 없는 DB 보존·트랜잭션 롤백. 실제 HTTP 사진 저장 기능을 시험한 것은 아님.

두 경고는 Starlette TestClient의 httpx 사용과 anyio BlockingPortal alias에 관한 향후 변경 안내다. 테스트는 통과했으며 경고를 숨기지 않았다. 의존성을 변경할 때 호환성을 다시 확인한다.

## 아직 검증하지 않은 것
Android SDK/Gradle 빌드·실제 APK, 카메라/USB 실휴대폰 시험, 실센서 보정·펌웨어 업로드, 사진 저장 서버, 사용자 인증·HTTPS·외부 배포, 실제 데이터 수집·학습·AI 성능, Play Console 등록/심사.

원격 검증: 첫 커밋 `6b327f8`의 [GitHub Actions](https://github.com/kara320090/VisionMachine/actions/runs/35430048327) 통과. 이후 Windows/Linux 두 환경에서 같은 `scripts/check.py`를 실행하도록 구성했다. 최신 커밋의 실행 결과는 Actions에서 구분해 확인한다.

JSON/CSV와 테스트에 등장하는 측정값·ID·시각·해시는 합성 시험용이다. 통과한 테스트 수는 작물 표본 수나 진단 성능이 아니다. CSV 검사기는 사진 실재·실제 해시·라벨 정답·이용허락의 진위를 확인하지 않는다. 실제 자료 검사는 다음 구현 과제다.

사용자는 검증한 단위마다 GitHub commit/push를 요청했다. 게시 이력은 git log와 원격 Actions에서 확인한다. 계정 변경·유료 서비스 결제·제품 외부 배포는 수행하지 않는다.

일회용 `_ANTIGRAVITY_START_HERE.md`의 준비 작업을 완료하고 결과를 STATUS/VALIDATION/NEXT_STEPS에 남긴 뒤 해당 파일만 삭제했다. 상시 AGENTS/rules/prompts는 보존한다.
