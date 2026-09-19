# VisionMachine 개발 시작

이 저장소 루트가 작업 위치다. 기존 clone이 있으면 그 폴더를 사용하며 다시 중첩 clone하거나 ZIP을 덮어쓰지 않는다.

## 다른 PC에서 시작

```powershell
git clone https://github.com/kara320090/VisionMachine.git
cd VisionMachine
python -m venv .venv
& ./.venv/Scripts/python.exe -m pip install -r requirements.lock.txt
& ./.venv/Scripts/python.exe -m pip install --no-deps -e .
& ./.venv/Scripts/python.exe scripts/check.py
& ./.venv/Scripts/python.exe -m vm_server init-db
```

Python 3.12를 사용한다. Linux/macOS에서는 `.venv/bin/python`을 사용한다. 환경 폴더는 Git에 올리지 않는다.

## Antigravity에 넣을 프롬프트

> AGENTS.md, .agents/rules/visionmachine.md, README.md, docs/STATUS.md, docs/NEXT_STEPS.md를 먼저 읽어 줘. 맡은 분야의 prompts 문서를 읽고 다음 완료 단위 하나를 실제 구현해 줘. 기존 변경을 보존하고 모의 자료와 실측 결과를 구분해 줘. 관련 검사와 STATUS 갱신을 마친 단위마다 commit하고 origin의 현재 작업 branch에 바로 push해 줘. 다른 사람의 변경을 덮어쓰거나 force push하지 마.

Antigravity에서 저장소 루트를 연다. `.agents/rules/visionmachine.md`를 명시적으로 읽게 하므로 IDE 자동 규칙 인식에만 의존하지 않는다. `prompts/`는 일반 Markdown 지시문이다.

| 작업 | 프롬프트 |
|---|---|
| 최초 점검 | [00_bootstrap](prompts/00_bootstrap.md) |
| 서버 | [01_server](prompts/01_server.md) |
| 데이터·평가 | [02_data](prompts/02_data.md) |
| AI | [03_ai](prompts/03_ai.md) |
| Android | [04_android](prompts/04_android.md) |
| 계측·펌웨어 | [05_firmware](prompts/05_firmware.md) |
| 통합시험 | [06_integration](prompts/06_integration.md) |
| 커밋 전 검토 | [07_commit_review](prompts/07_commit_review.md) |

앱은 첫 주부터 촬영·원본 저장을 개발한다. 서버·센서·모델의 완성을 기다리지 않는다. 여러 개발자는 파트별 branch 또는 worktree에서 작업하고 공통 계약은 함께 검토한다.
