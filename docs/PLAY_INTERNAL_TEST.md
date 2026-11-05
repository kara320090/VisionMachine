# Google Play 내부 시험 빌드

현재 Android 앱은 기존 촬영·로컬 기록 경로와 기기 내 RGB 사진 점검 경로를 제공하는 내부 시험용이다. 2026-11-05에 사용자 요청으로 기존 캡스톤 모델을 이용한 개별/최대 8장 일괄 분석·기록·CSV 화면을 추가했다. USB 센서 실측·운영 서버 통합 진단은 미구현이며 현장 정확도 검증 완료를 뜻하지 않는다. 내부 테스터에게도 이 범위를 출시 노트에 표시한다. 모델 준비·제한·시험은 [ANDROID_RGB](ANDROID_RGB.md)를 따른다.

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

2026-11-05 13:38 KST, 버전 **0.2.0(versionCode 2)** ‘사진 분석·기록 UI’를 기존 VisionMachine 내부 테스트 트랙에 출시했다. 콘솔에서 ‘활성’, ‘내부 테스터에게 제공됨’을 확인했다. 기존 본인 시험 계정 1명의 설정을 유지했다. 공개 프로덕션 출시는 하지 않았다. 저장소 구현 커밋은 `f90191e`이며 Android/Python GitHub Actions 모두 통과했다. 배포 AAB/APK는 공개 Git에 넣지 않았다.

서명된 `bundleRelease`, `assembleRelease`, `lintRelease`가 통과했다(오류 0, 의존성·기존 스타일 경고 14). Android 계측시험 18개/skip 0, 별도 실제 화면 렌더 시험 1개, 합성 5개 크기 전처리 비교가 통과했다. Play의 크기 증가·난독화 매핑 없음·외부 네이티브 라이브러리 디버그 기호 없음 경고 3개는 내부 출시를 막지 않았다. 기기별 Play 신규 설치 표시는 약 34MB, 업데이트 표시는 약 28.8MB였다. 실제 휴대전화의 촬영·권한·성능은 별도 확인한다.

아래는 기존 촬영·서버 경로의 범위와 남은 통합 작업이다.

- 기존 휴대폰 카메라 앱으로 촬영해 앱 전용 저장소에 저장·목록 표시.
- 디버그 빌드에만 있는 loopback 서버 시험 경로는 Play용 릴리스 빌드에서 사용자에게 제공되지 않는다.
- 실제 Android 기종의 촬영·재진입·권한 동작은 아직 검증되지 않았다.
- USB 센서, HTTPS 운영 서버, AI 진단 결과, 이력·오류 복구는 미완료다. 내부 테스트 링크를 공개 배포 링크로 취급하지 않는다.
