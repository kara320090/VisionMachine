# 무엇을 커밋할 것인가

## 올릴 것
코드, 테스트, pyproject/검증한 lockfile, .gitignore, 계약 원본·생성 JSON Schema·합성 예제, DB 마이그레이션, 수집/라벨 기준, 공개자료 URL·이용조건 조사표, 데이터 검사/분할/평가 코드, 모델 설정·모델 카드·공개 가능한 집계표, 펌웨어·교정 절차, Android Gradle 설정과 wrapper, README·프롬프트·CI.

Android의 아이콘 등 검토한 UI 리소스(`apps/android/**/src/main/res/`)와 명시된 합성 이미지 시험자료(`tests/fixtures/synthetic/`)는 이미지 제외 규칙의 예외다. 실제 작물 사진을 이 경로에 넣어 제외 규칙을 우회하지 않는다.

## 올리지 않을 것
`.env`, API 토큰, Google 서비스 계정 키, Android 서명키, 실제 원본 사진/센서 로그/DB, 실제 최종시험 정답, 대량 학습 데이터, 학습 가중치, APK/AAB, 로그, 캐시, 가상환경, 개인정보·서명이 있는 학교 양식/영수증. 익명 데이터라도 재배포 권한을 확인하기 전 공개하지 않는다.

원본 자료·가중치는 팀이 접근 가능한 별도 비공개 저장공간에 두고 데이터/모델 ID·버전·해시·이용조건·재현 절차를 Git에 기록한다. 실제 경로·임시 서명 URL·키는 올리지 않는다. Git LFS는 용량 관리이며 개인정보 보호 기능이 아니다. 현재 패키지는 LFS를 자동 활성화하지 않는다.

## 검증한 작업 단위마다 바로 commit과 push

사용자가 이 저장소에 대해 매 작업 단위의 commit과 push를 요청했다. 검사를 통과하면 별도의 반복 확인 없이 현재 작업 branch를 push한다. 기본 구조는 main에 게시하고 이후 파트별 기능 branch를 사용한다. feature branch에서의 push는 main 병합을 뜻하지 않는다.

```powershell
git status --short --branch
# 해당 작업의 테스트와 생성 계약 동기화 검사를 먼저 실행한다.
git add <이번에-검토한-파일들>
git diff --cached --check
git diff --cached --stat
git diff --cached
git commit -m "feat(server): describe the completed change"
git push -u origin HEAD
```

명령의 `<...>`는 실제 검토한 경로로 바꾼다. push가 거부되면 원격 변경을 확인하고 정상 병합/재검증한다. force push, 타인의 작업 취소, 계정 설정 변경으로 해결하지 않는다. 학교 서류가 있는 상위 작업 폴더에서 `git add`를 실행하지 않는다.

파트별 branch 예: `feat/server-upload`, `feat/android-capture`, `feat/data-manifest`, `feat/firmware-usb`, `feat/rgb-baseline`. 브랜치 이름은 예시이며 자동으로 전부 생성하지 않는다.

| 작업 | 예시 커밋 | 함께 포함할 근거 |
|---|---|---|
| 사진 업로드 | feat(server): persist inspection photos and metadata | 계약·마이그레이션·중복/충돌/재시작 시험 |
| 촬영 저장 | feat(android): save full resolution camera photos | Gradle 설정·촬영 취소/복귀 시험 기록 |
| USB 실측 | feat(firmware): emit measured sensor packets | 라이브러리 버전·패킷 테스트·실물 미확인 표시 |
| 데이터 검증 | feat(data): validate collection metadata and grouped splits | 잘못된 라벨/누수 실패 사례 |
| RGB 학습 | feat(ml): add reproducible rgb training pipeline | 설정·전처리·분할 버전·공개 가능한 실제 결과 |

GitHub push는 로컬 commit과 별개다. 원격 branch를 확인한 뒤 선택한 branch만 push한다. main 보호·리뷰어 계정·협업자 권한은 팀 운영에서 정한다. 무조건 `git add .`로 원본 자료까지 올리지 않는다. .gitignore를 추가해도 이미 추적 중인 비밀은 자동 삭제되지 않는다.

공식 근거: [GitHub ignore](https://docs.github.com/en/get-started/git-basics/ignoring-files), [대용량 파일](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github). GitHub 일반 Git은 100 MiB 초과 파일을 차단하므로 데이터·모델 배포 경로를 따로 정한다.
