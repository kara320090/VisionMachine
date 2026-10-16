# Google Play 내부 시험 빌드

현재 Android 앱은 사진 촬영·로컬 저장 중심의 초기 버전이다. USB 센서 실측, 운영 서버, AI 판정은 구현되지 않았으므로 공개 출시용 제품으로 설명하지 않는다. 내부 테스터에게도 이 범위를 출시 노트에 표시한다.

## 빌드

- JDK 17, Android SDK 36 사용. Gradle Wrapper 8.11.1 및 Android Gradle Plugin 8.10.1을 사용한다.
- `apps/android`에서 `gradlew.bat :app:assembleDebug :app:lintDebug`로 개발 빌드를 확인한다.
- Play용 AAB는 개인 서명키가 필요하다. 아래 네 환경변수를 설정한 뒤 `gradlew.bat :app:bundleRelease :app:lintRelease`를 실행한다.
  - `VM_UPLOAD_KEYSTORE`: 로컬 키 저장소의 절대 경로
  - `VM_UPLOAD_STORE_PASSWORD`: 저장소 암호
  - `VM_UPLOAD_KEY_ALIAS`: 업로드 키 별칭
  - `VM_UPLOAD_KEY_PASSWORD`: 키 암호
- 결과 파일: `apps/android/app/build/outputs/bundle/release/app-release.aab`. 서명값과 앱 ID, 버전 코드를 확인한 뒤 내부 테스트 트랙에 업로드한다.

키 저장소·암호·APK/AAB는 공개 Git에 넣지 않는다. 키 저장소와 복구 수단은 팀장이 별도로 안전하게 보관한다. 이미 사용한 versionCode를 재사용하지 않고, 다음 업로드 전에 올린다.

2026-10-16 기준 버전 0.1.0(versionCode 1)의 서명된 AAB는 Google Play 내부 테스트 트랙에 업로드·출시되었고, 본인 시험 계정 1명에게 제공된다. 콘솔은 아직 앱을 검토하지 않은 상태로 표시한다. APK를 별도의 '내부 앱 공유'에 올리려는 시도는 앱 게시 선행 요건 때문에 거절되었다. AAB 내부 테스트 출시와 APK 내부 공유는 서로 다른 경로다.

## 내부 테스트 범위

- 기존 휴대폰 카메라 앱으로 촬영해 앱 전용 저장소에 저장·목록 표시.
- 디버그 빌드에만 있는 loopback 서버 시험 경로는 Play용 릴리스 빌드에서 사용자에게 제공되지 않는다.
- 실제 Android 기종의 촬영·재진입·권한 동작은 아직 검증되지 않았다.
- USB 센서, HTTPS 운영 서버, AI 진단 결과, 이력·오류 복구는 미완료다. 내부 테스트 링크를 공개 배포 링크로 취급하지 않는다.
