# VisionMachine / AgriClinic

기존 Android 휴대폰의 정지사진과 USB-C 센서 실측을 연결하여 서버에서 저장·AI 분석하고 결과·근거·이력을 앱에 반환하는 캡스톤 프로젝트.

대상 저장소: https://github.com/kara320090/VisionMachine

**현재 상태: 개발 시작 패키지. 실제 진단 제품·완성 APK가 아니다.**

- 실행 가능: 최소 FastAPI 서버의 상태·지원범위 조회와 검사 메타데이터 검증, JSON Schema/OpenAPI 생성, 로컬 SQLite 초기화, CSV manifest 및 개체/과실/구매묶음/중복 누수 검사, 계약·누수 회귀시험.
- 구현 대기: 사진 업로드·영속 저장·인증·이력·삭제·실제 AI 추론, Android 프로젝트/APK, 실측 펌웨어, 실제 데이터 수집·학습·성능평가.
- 학습 모델이 없으면 `pending_model`을 반환한다. 임의 정상 판정·정확도·가상 성능을 만들지 않는다.

먼저 [START_HERE.md](START_HERE.md), 이후 [구조](docs/ARCHITECTURE.md), [커밋 기준](docs/GIT_COMMITS.md)을 읽는다. 개발은 각자의 로컬 clone에서 `main`으로 진행한다. 검증한 단위마다 commit·push하며, 선행 push가 있으면 내 커밋과 원격 변경을 병합·재검증하여 `origin/main`에 올린다.

| 개발 분야 | 작업 폴더 | 담당 |
|---|---|---|
| 서버·통합 | `server/` | 정회서·이봉헌 |
| Android 앱 | `apps/android/` | 이봉헌·유재윤 |
| 하드웨어·계측 | `firmware/` | 최승빈·정회서 |
| 데이터·독립평가 | `data-pipeline/`, `data/` | 한윤섭·유재윤 |
| AI | `ml/` | 한윤섭·최승빈 |
| 공통 입출력 | `packages/contracts/`, `contracts/` | 연결되는 파트 공동 검토 |

각 파트의 첫 구현 단위와 인계 조건은 [NEXT_STEPS](docs/NEXT_STEPS.md)에 있다. 폴더별 README는 앞으로 만들 파일과 실제 구현을 구분한다. 센서 전기 구성은 [HARDWARE](docs/HARDWARE.md), 실제 제품 치수와 장착 통과 조건은 [HARDWARE_FIT_CHECK](docs/HARDWARE_FIT_CHECK.md), 공구 없는 조립 순서는 [HARDWARE_ASSEMBLY_GUIDE](docs/HARDWARE_ASSEMBLY_GUIDE.md), 현재 구매 가격과 총액은 [PURCHASE_PLAN](docs/PURCHASE_PLAN.md)에서 확인한다. 팀의 완성 작물 구매 결정을 위한 비교표·회신 양식·전체 구매 URL은 [구매예산 및 식물구매 팀 의사결정 보고서](output/pdf/VisionMachine_구매예산_식물구매_팀의사결정_보고서.pdf)에 정리했다.

## Python 빠른 실행 (Windows PowerShell, Python 3.12)

```powershell
python -m venv .venv
& ./.venv/Scripts/python.exe -m pip install -r requirements.lock.txt
& ./.venv/Scripts/python.exe -m pip install --no-deps -e .
& ./.venv/Scripts/python.exe scripts/check.py
& ./.venv/Scripts/python.exe -m vm_server init-db
& ./.venv/Scripts/python.exe -m uvicorn vm_server.main:app --host 127.0.0.1 --port 8000
```

`http://127.0.0.1:8000/docs`에서 실제 구현된 API만 확인한다. 앱에서 접속하는 LAN 서버·HTTPS·사용자 인증은 아직 구성하지 않았다.

`init-db`는 `storage/visionmachine.db`와 빈 `storage/uploads/`를 준비한다. HTTP 사진 업로드·저장은 아직 구현하지 않았다. 유료 DB/클라우드 계약은 필요하지 않으며 실제 서비스를 운영할 PC와 외부 연결은 별도 결정한다. `VM_STORAGE_DIR` 환경변수로 위치를 바꿀 수 있고 `.env`는 자동으로 읽지 않는다.

`scripts/check.py`는 의존성·pytest·계약/OpenAPI 동기화·합성 manifest·실제 localhost HTTP 기동을 점검한다. HTTP 점검 프로세스는 스크립트가 종료한다. Android/센서/AI 성능 시험은 포함하지 않는다.

```powershell
& ./.venv/Scripts/python.exe scripts/export_contracts.py --check
& ./.venv/Scripts/python.exe -m vm_data.validate_manifest data/examples/manifest.synthetic.csv --allow-synthetic
```

공개 저장소에는 코드·규격·익명화한 공개 가능 메타데이터만 올린다. 원본 사진, 시험 정답, 비밀키, 서명·학번·연락처가 있는 학교 서류는 올리지 않는다.
