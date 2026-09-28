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
카메라/USB 실휴대폰 시험, 실센서 보정·펌웨어 업로드, 사용자 인증·HTTPS·외부 배포, 실제 데이터 수집·학습·AI 성능, Play Console 등록/심사. Android 빌드와 사진 저장 서버는 아래 2026-09-28 추가 검증을 따른다.

원격 검증: 첫 커밋 `6b327f8`의 [GitHub Actions](https://github.com/kara320090/VisionMachine/actions/runs/35430048327) 통과. 서버 기반 추가 커밋 `e6888ee`는 [Windows/Linux 두 환경](https://github.com/kara320090/VisionMachine/actions/runs/35430338096)에서 같은 `scripts/check.py` 실행에 성공했다. 최신 커밋의 실행 결과는 Actions에서 구분해 확인한다.

CI의 Node 20 폐기 경고에 따라 공식 checkout v7.0.1/setup-python v7.0.0의 Node 24 런타임을 확인하고 커밋 SHA로 고정했다. Ubuntu는 24.04로 명시했다. 참조: [checkout release](https://github.com/actions/checkout/releases/tag/v7.0.1), [setup-python release](https://github.com/actions/setup-python/releases/tag/v7.0.0).

JSON/CSV와 테스트에 등장하는 측정값·ID·시각·해시는 합성 시험용이다. 통과한 테스트 수는 작물 표본 수나 진단 성능이 아니다. 기본 CSV 검사기는 사진을 읽지 않는다. `--image-root`를 명시하면 로컬 파일 존재·SHA-256·루트 밖 링크를 확인하지만, 사진 디코딩·라벨 정답·이용허락의 진위는 확인하지 않는다.

2026-09-22 추가 검증: `python scripts/check.py` 통과(56 pytest, 기존 외부 의존성 경고 2개). 파일 무결성 시험은 일치·변경·누락·루트 밖 링크·안전하지 않은 상대경로를 포함한다. 테스트 파일 바이트는 합성이며 실제 작물 사진이 아니다.

2026-09-23 공개 이미지 자료 문서 갱신 검증: `data/catalog/sources.csv`의 모든 행이 7열인지 확인했고 `python scripts/check.py`가 통과했다(56 pytest, 기존 외부 의존성 경고 2개). 공개 이미지 원본 자체는 내려받지 않았으므로 파일 수·손상·중복 검사는 결과에 포함되지 않는다.

사용자는 검증한 단위마다 GitHub commit/push를 요청했다. 게시 이력은 git log와 원격 Actions에서 확인한다. 계정 변경·유료 서비스 결제·제품 외부 배포는 수행하지 않는다.

2026-09-28 로컬 사진 저장 구현 검증: `scripts/check.py` 통과(61 pytest, 기존 외부 경고 2개). 합성 PNG/JPEG의 실제 디코딩·SHA-256·저장·SQLite 재시작 조회, 동일 요청 재시도, 다른 내용 409, 잘못된 이미지/미디어/메타데이터/바이트 상한, 파일 이동 실패 정리 및 비로컬 클라이언트 거부를 확인했다. OpenAPI는 실제 새 경로와 일치한다. 실제 휴대폰 사진·외부 네트워크·사용자 인증·강제 종료 후 파일 복구는 시험하지 않았다.

2026-09-28 Android 검증: JDK 17/SDK 35에서 `apps/android/gradlew.bat :app:assembleDebug :app:lintDebug :app:connectedDebugAndroidTest`를 실행했다. APK 빌드와 lint(오류 0, 호환되는 고정 의존성에 대한 업데이트 알림 5건), 합성 JPEG 저장/재로드·취소·잘못된 이미지 거부 계측 시험 3건이 통과했다. Android 17 에뮬레이터에서 화면 기동·카메라 호출·취소 시 빈 파일 삭제를 확인했다. 에뮬레이터 카메라가 출력 사진을 기록하지 않아 성공 촬영·사진 보기·실휴대폰 시험은 미완료다. APK와 시험 사진은 Git에서 제외했다.

일회용 `_ANTIGRAVITY_START_HERE.md`의 준비 작업을 완료하고 결과를 STATUS/VALIDATION/NEXT_STEPS에 남긴 뒤 해당 파일만 삭제했다. 상시 AGENTS/rules/prompts는 보존한다.

2026-09-29 Android 디버그 전송 검증: JDK 17/SDK 35에서 `:app:assembleDebug :app:lintDebug :app:connectedDebugAndroidTest` 성공. 에뮬레이터 계측 시험 6건 중 새 시험은 합성 JPEG의 multipart 전송(기기 내 loopback 가짜 서버가 검사 ID·SHA-256·센서 미취득을 확인), 실패 상태·동일 ID 재시도, 전송 중 앱 종료 후 복구를 확인한다. 이 시험은 실제 PC FastAPI 서버와 USB 장치 왕복을 뜻하지 않는다.

2026-09-29 USB 패킷 파서 검증: `:app:assembleDebug :app:lintDebug :app:connectedDebugAndroidTest` 성공. 전체 에뮬레이터 계측 시험 12건 중 새 6건은 요청 생성, 여러 read에 나뉜 줄·한 read의 복수 줄, 이전 요청 ID 거부, 4096바이트 초과 줄 뒤 복구, 잘못된 UTF-8·결측 오류코드 거부, 종료 시 미완료 줄 폐기를 확인한다. 첫 시도는 에뮬레이터 종료로 `No connected devices`였고 재기동 후 12건 모두 통과했다. USB 장치·실측값 검증은 아니다.

2026-09-29 실제 로컬 서버 왕복: 개발 PC의 FastAPI를 `127.0.0.1:8000`에서 실행하고 Android 에뮬레이터에 `adb reverse tcp:8000 tcp:8000`을 설정했다. 일회성 계측 시험에서 합성 JPEG로 `InspectionUploadClient`의 기본 주소에 POST하여 201, 같은 검사 ID GET에서 200과 `sensor_absence_reason=not_acquired`, `pending_model` 응답을 확인했다. 전체 계측 시험 13건 통과 후 일회성 시험 코드는 제거했다. 실제 휴대폰 카메라·USB 실측·외부 네트워크·AI 진단 시험은 아니다.
