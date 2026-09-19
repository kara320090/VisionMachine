# 무엇을 커밋할 것인가

## 올릴 것
코드, 테스트, pyproject/검증한 lockfile, .gitignore, 계약 원본·생성 JSON Schema·합성 예제, DB 마이그레이션, 수집/라벨 기준, 공개자료 URL·이용조건 조사표, 데이터 검사/분할/평가 코드, 모델 설정·모델 카드·공개 가능한 집계표, 펌웨어·교정 절차, Android Gradle 설정과 wrapper, README·프롬프트·CI.

Android의 아이콘 등 검토한 UI 리소스(`apps/android/**/src/main/res/`)와 명시된 합성 이미지 시험자료(`tests/fixtures/synthetic/`)는 이미지 제외 규칙의 예외다. 실제 작물 사진을 이 경로에 넣어 제외 규칙을 우회하지 않는다.

## 올리지 않을 것
`.env`, API 토큰, Google 서비스 계정 키, Android 서명키, 실제 원본 사진/센서 로그/DB, 실제 최종시험 정답, 대량 학습 데이터, 학습 가중치, APK/AAB, 로그, 캐시, 가상환경, 개인정보·서명이 있는 학교 양식/영수증. 익명 데이터라도 재배포 권한을 확인하기 전 공개하지 않는다.

원본 자료·가중치는 팀이 접근 가능한 별도 비공개 저장공간에 두고 데이터/모델 ID·버전·해시·이용조건·재현 절차를 Git에 기록한다. 실제 경로·임시 서명 URL·키는 올리지 않는다. Git LFS는 용량 관리이며 개인정보 보호 기능이 아니다. 현재 패키지는 LFS를 자동 활성화하지 않는다.

## 검증한 작업 단위마다 바로 commit과 push

사용자의 최신 결정은 **각자 로컬 clone의 `main`에서 개발하고, 검증한 단위마다 `origin/main`에 바로 commit·push**하는 것이다. 별도 기능 브랜치를 기본으로 만들지 않는다. 다른 사람이 먼저 push했으면 내 커밋과 상대방 커밋을 병합하여 함께 반영한다. 두 사람의 기능을 보존하는 것이 기준이며, 충돌을 해결하면서 코드 배치는 달라질 수 있다.

여러 개발자·에이전트가 같은 로컬 폴더와 Git index를 동시에 사용하지 않는다. 각자 별도 clone을 열고, Git author는 기존 사용자 설정을 유지한다. 명령은 단계별로 실행하고 실패 결과를 확인한다. 오류가 난 상태에서 다음 명령을 계속 실행하지 않는다.

### 작업 시작

1. `git status --short --branch`, `git branch --show-current`, `git remote -v`로 작업 위치·브랜치·원격·기존 변경을 확인한다.
2. 작업 브랜치는 `main`이다. 다른 브랜치에 기존 작업이 있다면 커밋 또는 적절한 비공개 백업으로 먼저 보존한다. 깨끗한 상태에서 `main`으로 전환하고 기존 커밋을 검토해 병합하거나 필요한 작업 커밋을 반영한다. 새 기능 브랜치를 만들어 작업을 이어가지 않는다.
3. 깨끗한 `main`에서 `git fetch origin`, `git merge --no-edit origin/main`으로 최신 원격 변경을 반영한다. 이미 로컬 커밋과 원격이 갈라졌다면 아래 충돌 처리 절차를 따른다.
4. 미커밋 변경을 버리면서 동기화하지 않는다. 현재 작업은 관련 파일만 검토해 커밋하고, 별개 사용자 변경은 명시적으로 보존한 뒤 병합한다. 비밀키·실제 데이터는 보존을 이유로 공개 커밋에 넣지 않는다.

### 완료 단위 게시

```powershell
git status --short --branch
# 해당 작업의 테스트와 생성 계약 동기화 검사를 먼저 실행한다.
git add <이번에-검토한-파일들>
git diff --cached --check
git diff --cached --stat
git diff --cached
git commit -m "feat(server): describe the completed change"
git fetch origin
git merge --no-edit origin/main
# 병합이 성공한 뒤 최종 diff와 양쪽 기능을 확인하고 관련 검사를 다시 실행한다.
# 충돌 중이거나 검사가 실패하면 push하지 않고 먼저 해결한다.
git push origin main
```

명령의 `<...>`는 실제 검토한 경로로 바꾼다. 위 예시는 일괄 실행 스크립트가 아니다. 검사 범위는 변경 내용에 맞추며, 코드·계약이 바뀌면 `scripts/check.py`와 해당 파트 빌드/시험을 수행한다. 문서만 바뀌면 링크·지시문 일관성·diff를 검사한다. 학교 서류가 있는 상위 작업 폴더에서 `git add`를 실행하지 않는다.

### 다른 사람이 먼저 push했을 때

`non-fast-forward` 또는 `fetch first`로 push가 거절돼도 내 로컬 커밋은 남아 있다. 다음 순서로 처리한다.

1. `git status`와 `git log --oneline --graph --all -15`를 확인한다. 내 변경이 커밋되어 있고 다른 미커밋 작업도 보존됐는지 확인한다.
2. `git fetch origin`으로 최신 원격 이력을 가져온다. 인증·네트워크 실패나 브랜치 보호 오류는 병합으로 해결되는 문제가 아니므로 원인을 구분한다.
3. `git merge --no-edit origin/main`으로 현재 `main`에 원격 변경을 병합한다. 이 방식은 기존 로컬·원격 커밋을 다시 쓰지 않는다. 기본 재시도 절차로 rebase나 강제 push를 사용하지 않는다.
4. 충돌이 없더라도 내 기능과 상대방 기능이 함께 동작하는지 diff와 관련 검사로 확인한다. 자동 병합 성공은 동작 검증을 대신하지 않는다.
5. 충돌이 있으면 `git diff --name-only --diff-filter=U`로 파일을 확인하고 공통 조상·내 변경·상대방 변경을 비교한다. 양쪽의 의도를 보존하는 코드로 수정한다. 파일 전체에 `--ours`/`--theirs`를 일괄 적용하여 한쪽 변경을 버리지 않는다. 생성 파일은 계약 원본을 먼저 병합하고 다시 생성한다. STATUS·일정·검증 기록도 양쪽 내용을 유지한다.
6. 해결한 파일만 `git add <해결한-파일들>`로 stage한다. 미해결 파일과 충돌 표시가 없는지 확인하고 관련 검사를 실행한 뒤 `git merge --continue`로 병합을 완료한다. Git이 별도 merge commit을 요구하지 않으면 중복 커밋을 만들지 않는다.
7. 검사에 통과한 `main`을 `git push origin main`으로 다시 올린다. 그사이 다른 사람이 또 push했다면 같은 fetch → merge → 검증 → push 순서를 반복한다.
8. 원격 CI를 확인하고 실패하면 수정 커밋을 추가한다. 완료 시 커밋 ID·원격 반영·검증 결과를 보고한다.

같은 코드에 양립할 수 없는 요구가 있어 근거만으로 해결할 수 없다면 양쪽 커밋을 유지한 채 구체적인 충돌 의도를 확인받는다. 무조건 내 코드를 우선하거나 상대방 코드를 통째로 복원하여 해결했다고 하지 않는다. `reset --hard`, `clean -fd`, `push --force`, `push --force-with-lease`로 작업을 없애거나 공유 이력을 덮어쓰지 않는다. 원격 보호 규칙·권한은 임의로 변경하지 않는다.

| 작업 | 예시 커밋 | 함께 포함할 근거 |
|---|---|---|
| 사진 업로드 | feat(server): persist inspection photos and metadata | 계약·마이그레이션·중복/충돌/재시작 시험 |
| 촬영 저장 | feat(android): save full resolution camera photos | Gradle 설정·촬영 취소/복귀 시험 기록 |
| USB 실측 | feat(firmware): emit measured sensor packets | 라이브러리 버전·패킷 테스트·실물 미확인 표시 |
| 데이터 검증 | feat(data): validate collection metadata and grouped splits | 잘못된 라벨/누수 실패 사례 |
| RGB 학습 | feat(ml): add reproducible rgb training pipeline | 설정·전처리·분할 버전·공개 가능한 실제 결과 |

GitHub push는 로컬 commit과 별개다. 현재 브랜치가 `main`인지 확인한 뒤 `git push origin main`으로 게시한다. main 보호·리뷰어 계정·협업자 권한은 팀 운영에서 정한다. 무조건 `git add .`로 원본 자료까지 올리지 않는다. .gitignore를 추가해도 이미 추적 중인 비밀은 자동 삭제되지 않는다.

공식 근거: [GitHub ignore](https://docs.github.com/en/get-started/git-basics/ignoring-files), [대용량 파일](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github). GitHub 일반 Git은 100 MiB 초과 파일을 차단하므로 데이터·모델 배포 경로를 따로 정한다.
