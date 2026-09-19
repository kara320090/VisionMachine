# VisionMachine / AgriClinic

기존 Android 휴대폰의 정지사진과 USB-C 센서 실측을 연결하여 서버에서 저장·AI 분석하고 결과·근거·이력을 앱에 반환하는 캡스톤 프로젝트.

대상 저장소: https://github.com/kara320090/VisionMachine

**현재 상태: 개발 시작 패키지. 실제 진단 제품·완성 APK가 아니다.**

- 실행 가능: 최소 FastAPI 서버의 상태·지원범위 조회와 검사 메타데이터 검증, JSON Schema 생성, CSV manifest 및 개체/과실/구매묶음/중복 누수 검사, 계약·누수 회귀시험.
- 구현 대기: 사진 업로드·영속 저장·인증·이력·삭제·실제 AI 추론, Android 프로젝트/APK, 실측 펌웨어, 실제 데이터 수집·학습·성능평가.
- 학습 모델이 없으면 `pending_model`을 반환한다. 임의 정상 판정·정확도·가상 성능을 만들지 않는다.

먼저 [START_HERE.md](START_HERE.md), 이후 [구조](docs/ARCHITECTURE.md), [커밋 기준](docs/GIT_COMMITS.md)을 읽는다.

## Python 빠른 실행 (Windows PowerShell, Python 3.12)

```powershell
python -m venv .venv
& ./.venv/Scripts/python.exe -m pip install -r requirements.lock.txt
& ./.venv/Scripts/python.exe -m pip install --no-deps -e .
& ./.venv/Scripts/python.exe -m pytest -q
& ./.venv/Scripts/python.exe -m uvicorn vm_server.main:app --host 127.0.0.1 --port 8000
```

`http://127.0.0.1:8000/docs`에서 실제 구현된 API만 확인한다. 앱에서 접속하는 LAN 서버·HTTPS·사용자 인증은 아직 구성하지 않았다.

```powershell
& ./.venv/Scripts/python.exe scripts/export_contracts.py --check
& ./.venv/Scripts/python.exe -m vm_data.validate_manifest data/examples/manifest.synthetic.csv --allow-synthetic
```

공개 저장소에는 코드·규격·익명화한 공개 가능 메타데이터만 올린다. 원본 사진, 시험 정답, 비밀키, 서명·학번·연락처가 있는 학교 서류는 올리지 않는다.
