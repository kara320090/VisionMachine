# VisionMachine / AgriClinic

기존 Android 휴대폰의 정지사진과 USB-C 센서 실측을 연결하여 서버에서 저장·AI 분석하고 결과·근거·이력을 앱에 반환하는 캡스톤 프로젝트.

대상 저장소: https://github.com/kara320090/VisionMachine

**현재 상태: 개발 중. 기능별 구현·실물 검증 범위는 [STATUS](docs/STATUS.md)를 따른다.**

Android 0.6.0 업데이트 후보는 설치 후 주소·키 입력 없이 [4090 자동 연결](docs/AUTOMATIC_SERVER.md)을 준비한다. 기기별 인증은 앱이 자동 발급받으며 기존 Play 앱의 업데이트로 배포한다. 현재 배포/검증 상태는 아래 0.5.0 기록과 구분한다.

4090 서버 연결 경로는 [SERVER_GPU](docs/SERVER_GPU.md)를 따른다. 기존 C_seed42 가중치에서 앱과 SHA-256이 같은 ONNX를 복원하고 CUDA 추론·Android 에뮬레이터의 8장 성공 결과를 확인했다. 사진별 센서 스냅샷 전송·인증·중복 방지·기존 결과 화면 연결을 제공하며 실휴대폰 접속 검증은 별도다.

Android 0.5.0 내부 테스트 배포: [바로 촬영·최대 8장 분석·사진별 센서/종합 지수](docs/ANDROID_PHOTO_SENSOR_INDEX.md)에 4090 서버 RGB 분석 연결 설정을 추가했다. 배포된 앱은 새 버전이 설치되기 전까지 이 기능을 갖지 않는다. 종합 지수는 사용자 가중평균 참고값이며 학습된 융합 모델 결과와 구분한다. 작물별 기준은 출처와 측정 조건을 확인해 적용한다.

- 실행 가능: 최소 FastAPI 서버의 상태·지원범위 조회와 검사 메타데이터 검증, 로컬 전용 실제 JPEG/PNG 업로드·SQLite 저장·단건 조회, Android 원본 사진 촬영·로컬 저장·디버그 loopback 전송과 수동 재시도·USB JSONL 패킷 파서, JSON Schema/OpenAPI 생성, CSV manifest 및 개체/과실/구매묶음/중복 누수 검사, 계약·누수 회귀시험.
- 추가 구현: Android의 [RGB 사진 분석 동반 화면](docs/ANDROID_RGB.md), [USB 연결·4종 센서 측정·사진 연결·이력/CSV](docs/ANDROID_USB.md), 4090 서버 RGB 연결 설정, UNO R4의 [센서 USB 실측](firmware/README.md). 서버 주소와 인증키는 앱에서 기기별로 입력한다. 0.5.0은 2026-11-15 기존 Play 내부 테스트 트랙에 출시됐다. 실제 휴대폰의 인증된 사진 분석 왕복은 아직 확인하지 않았다.
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

각 파트의 첫 구현 단위와 인계 조건은 [NEXT_STEPS](docs/NEXT_STEPS.md)에 있다. 폴더별 README는 앞으로 만들 파일과 실제 구현을 구분한다. 공개 정상·병해 이미지 후보와 내려받기 방법은 [DATASET_REVIEW](docs/DATASET_REVIEW.md), 센서 전기 구성은 [HARDWARE](docs/HARDWARE.md), 실제 제품 치수와 장착 통과 조건은 [HARDWARE_FIT_CHECK](docs/HARDWARE_FIT_CHECK.md), 공구 없는 조립 순서는 [HARDWARE_ASSEMBLY_GUIDE](docs/HARDWARE_ASSEMBLY_GUIDE.md), 2026-10-07 전자부품 통합 구매안과 AI 구매 제외 후 미배정액은 [PURCHASE_PLAN](docs/PURCHASE_PLAN.md)에서 확인한다. 이전 구매 의사결정 PDF는 2026-09-20 당시 비교 기록이며 최신 예산으로 사용하지 않는다.

## Python 빠른 실행 (Windows PowerShell, Python 3.12)

```powershell
python -m venv .venv
& ./.venv/Scripts/python.exe -m pip install -r requirements.lock.txt
& ./.venv/Scripts/python.exe -m pip install --no-deps -e .
& ./.venv/Scripts/python.exe scripts/check.py
& ./.venv/Scripts/python.exe -m vm_server init-db
& ./.venv/Scripts/python.exe -m uvicorn vm_server.main:app --host 127.0.0.1 --port 8000
```

`http://127.0.0.1:8000/docs`에서 실제 구현된 API만 확인한다. Android 디버그 앱은 USB 디버깅 연결 뒤 `adb reverse tcp:8000 tcp:8000`으로 PC loopback 서버에 접속한다. LAN 서버·HTTPS·사용자 인증은 아직 구성하지 않았다.

`init-db`는 `storage/visionmachine.db`와 빈 `storage/uploads/`를 준비한다. 로컬 HTTP 업로드·조회는 구현했으나 인증과 외부 접속은 아직 없다. 유료 DB/클라우드 계약은 필요하지 않으며 실제 서비스를 운영할 PC와 외부 연결은 별도 결정한다. `VM_STORAGE_DIR` 환경변수로 위치를 바꿀 수 있고 `.env`는 자동으로 읽지 않는다.

`scripts/check.py`는 의존성·pytest·계약/OpenAPI 동기화·합성 manifest·실제 localhost HTTP 기동을 점검한다. HTTP 점검 프로세스는 스크립트가 종료한다. Android 빌드·lint는 `apps/android/gradlew`로 별도 확인하며 실기기/센서/AI 성능 시험은 포함하지 않는다.

Google Play 내부 시험 빌드와 서명키 취급은 [PLAY_INTERNAL_TEST](docs/PLAY_INTERNAL_TEST.md)를 따른다. 서버 연결용 0.5.0 signed AAB를 2026-11-15 01:08(KST)에 기존 내부 테스트 트랙에 출시했다. Console의 ‘내부 테스터에게 제공됨’을 확인했으며 실제 휴대폰 왕복 시험은 별도다. 앱 연결과 서버 준비 상태는 [STATUS](docs/STATUS.md)를 따른다.

```powershell
& ./.venv/Scripts/python.exe scripts/export_contracts.py --check
& ./.venv/Scripts/python.exe -m vm_data.validate_manifest data/examples/manifest.synthetic.csv --allow-synthetic
```

공개 저장소에는 코드·규격·익명화한 공개 가능 메타데이터만 올린다. 원본 사진, 시험 정답, 비밀키, 서명·학번·연락처가 있는 학교 서류는 올리지 않는다.
