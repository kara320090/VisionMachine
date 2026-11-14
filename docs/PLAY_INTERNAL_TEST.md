# Google Play 내부 시험 빌드

## 2026-11-15 Android 0.6.0 자동 연결 업데이트 후보 — 출시 전

기존 `org.visionmachine.agriclinic`의 versionCode 6 / versionName 0.6.0 후보다. 설치 후 주소·키 입력 없이 4090 서버에 연결하고 설치별 인증을 자동 등록·갱신한다. [AUTOMATIC_SERVER](AUTOMATIC_SERVER.md)의 실제 서버 적용과 기본 설치 흐름을 확인한 뒤 기존 내부 테스트 트랙에 업데이트한다. 아직 이 후보를 Play에 업로드하지 않았다.

출시 노트 초안:

```text
별도 주소·인증키 설정 없이 4090 서버에 자동 연결합니다.
새 설치와 앱 업데이트 후 기기 인증을 자동으로 준비하고 갱신합니다.
사진 분석 시 서버 연결을 다시 확인하고 일시적인 인증 만료를 자동 복구합니다.
서버 연결 상태와 오류를 표시하며 기기 내 분석도 선택할 수 있습니다.
```

## 2026-11-15 Android 0.5.0 업데이트 — 기존 내부 테스트 트랙 배포 완료

기존 앱 ID `org.visionmachine.agriclinic`을 유지하고 `versionCode 5` / `versionName 0.5.0`으로 빌드했다. 사진 화면에 서버 주소·기기별 API 키 입력을 추가했다. 사용자가 설정하지 않으면 기기 내 RGB 분석을 유지한다.

- JDK 21.0.13에서 `bundleRelease`, `assembleRelease`, `lintRelease`, `assembleDebug`, `assembleDebugAndroidTest` 성공. lint 오류 0 / 경고 25. JVM 테스트 4건과 `scripts/check.py`의 Python 89건·계약/OpenAPI·manifest·localhost HTTP 검사가 통과했다. Android 계측 테스트는 이번 Windows 환경에서 실행하지 않았다.
- 새 release AAB의 서명 유효성과 기존 로컬 signed AAB와 같은 인증서 지문을 확인했다. APK의 패키지/versionCode/versionName을 확인했고 AAB의 ONNX 모델 해시는 원본과 일치한다. 업로드 전 Play Console의 최고 versionCode 4를 확인했고, 5(0.5.0) AAB가 서명·호환성 검사를 통과해 등록됐다.
- 현재 4090 임시 HTTPS 주소의 `/health/ready`는 `ready`를 반환하고 CUDA/CPU provider를 표시했다. 임시 TryCloudflare 주소라 만료될 수 있다. health check만으로 실제 앱 업로드 왕복을 확인한 것은 아니다.
- 2026-11-15 01:08(KST)에 기존 내부 테스트 트랙으로 출시했고 Console의 최신 출시 버전 0.5.0 및 ‘내부 테스터에게 제공됨/검토되지 않음’을 확인했다. 기존 테스터 구성은 변경하지 않았다. 휴대폰의 Play 업데이트 표시는 보통 1시간 이내에 반영되지만 더 걸릴 수 있다. 실제 휴대폰 설치·인증된 사진 분석·결과 화면 왕복은 아직 확인하지 않았다.
- 출시 검토에서 가독화 파일 및 네이티브 디버그 기호 누락 경고 2건을 확인했다. 차단 오류나 지원 기기 감소는 없었다.
- API 키는 앱 설정에서 직접 입력하며 APK/AAB에 넣지 않는다. 현재 주소는 임시이므로 안정적인 HTTPS 또는 사용자의 tailnet 주소로 교체한 뒤 연결한다.

0.5.0에 게시한 출시 노트:

```text
사진 분석 화면에 4090 서버 연결 설정을 추가했습니다.
서버 분석을 선택하면 사진과 같은 검사에 연결된 센서 기록을 전송하고 결과를 표시합니다.
서버 주소와 기기별 인증키를 앱에서 설정할 수 있습니다.
서버 연결 및 분석 오류를 사진별로 표시하고, 기기 내 분석 모드도 선택할 수 있습니다.
```

## 2026-11-13 이전 업데이트 — 0.4.0/versionCode 4

0.4.0은 바로 촬영·8장 추가/일괄·사진별 센서 기준/종합 지수를 추가한 이전 업데이트 후보 기록이다. 범위·계산식은 [ANDROID_PHOTO_SENSOR_INDEX](ANDROID_PHOTO_SENSOR_INDEX.md)를 따른다. 아래 0.3.0 출시 준비와 함께 이 기록도 0.5.0 서버 연결 업데이트로 대체됐다.

0.4.0 출시 노트:

```text
첫 화면에서 바로 촬영하거나 최대 8장을 추가해 한 번에 분석할 수 있습니다.
사진별 작물·진행 상태·결과와 개별 실패 처리를 추가했습니다.
동일 사진에 USB 센서 실측을 연결하고 작물별 기준/허용편차로 센서 이탈 점수를 계산합니다.
사진 AI와 센서의 개별 점수 및 사용자 가중 종합 지수를 함께 표시하고 CSV에 기록합니다.
종합 지수는 참고값이며 병해 확률·학습된 융합 AI 결과가 아닙니다. 센서 기준은 조건·출처를 확인한 후 적용해 주세요.
```

현재 Android 앱은 기존 촬영·로컬 기록과 기기 내 RGB 사진 점검을 제공하는 내부 시험용이다. 2026-11-13 소스 0.3.0에는 [USB 센서 연결·측정·사진 연결·이력/CSV](ANDROID_USB.md)를 추가했다. 실제 휴대폰 USB 시험과 운영 서버 통합 진단은 별도로 구분한다. 모델 준비·제한·시험은 [ANDROID_RGB](ANDROID_RGB.md)를 따른다.

## 2026-11-13 업데이트 준비 — Play 업로드 전

- 대상은 기존 앱 `org.visionmachine.agriclinic`의 **내부 테스트** 트랙이다. 새 앱 생성·새 테스터 지정·공개 프로덕션 출시는 하지 않는다.
- `0.3.0(versionCode 3)`의 서명된 `bundleRelease`·`assembleRelease`·`lintRelease`가 성공했다. 기존 0.2.0과 업로드 인증서 SHA-256이 같으며 패키지·기존 모델 해시도 유지했다. APK 서명 검증·16KB ZIP 정렬을 통과했다. lint 오류 0/경고 17이다.
- API 37.1 에뮬레이터의 계측시험은 27건 통과/skip 0이고 JVM 전처리 비교 1건도 통과했다. 저장된 실제 보드 패킷 재생이 포함되며 실제 휴대폰 UsbManager 연결 성공을 뜻하지 않는다. 사용자가 현재 보드를 PC에 다시 연결할 수 없어 라이브 PC 브리지 시험은 재수행하지 않았다.
- **Play Console 업로드·출시 확인은 수행하지 않았다.** 이 세션에는 사용자 Chrome을 제어하는 도구나 Play Developer API 게시 인증이 없다. 기존 활성 릴리스는 아래 0.2.0 기록이며 로컬 빌드를 Play 배포 완료로 기록하지 않는다.

접근 가능한 Console에서 기존 VisionMachine → 테스트 → 내부 테스트 → 새 버전 만들기 → versionCode 3 AAB 업로드 → 출시 노트 → 검토 → 기존 내부 테스터에게 출시 순으로 진행한다. 콘솔에 더 큰 versionCode가 이미 있다면 덮어쓰거나 다른 앱을 만들지 말고 버전부터 다시 정한다. 업로드 뒤 콘솔의 활성 버전과 Play 업데이트 버튼을 확인하고 이 문서의 상태를 갱신한다.

출시 노트:

```text
USB-C로 UNO R4 Minima를 연결해 토양 원시값·온습도·광학·표면온도를 측정하고 저장할 수 있습니다.
촬영 사진 연결, 측정 이력과 CSV 내보내기, USB·센서 오류 안내를 추가했습니다.
기존 사진 분석·기록 기능을 유지했습니다. 센서값은 기기에 저장되며 사진 분석과 별도로 표시됩니다.
내부 시험용 버전입니다. 실제 휴대폰 USB 연결·전원·분리/재연결을 확인해 주세요.
```

## 빌드

- JDK 17 또는 21, Android SDK 36 사용. Gradle Wrapper 8.11.1 및 Android Gradle Plugin 8.10.1을 사용한다.
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

아래는 2026-11-05 배포 시점의 촬영·서버 경로와 통합 작업 기록이다. 0.3.0에서 추가한 센서 로컬 기록은 위 내용을 따른다.

- 기존 휴대폰 카메라 앱으로 촬영해 앱 전용 저장소에 저장·목록 표시.
- 디버그 빌드에만 있는 loopback 서버 시험 경로는 Play용 릴리스 빌드에서 사용자에게 제공되지 않는다.
- 실제 Android 기종의 촬영·재진입·권한 동작은 아직 검증되지 않았다.
- USB 센서, HTTPS 운영 서버, AI 진단 결과, 이력·오류 복구는 미완료다. 내부 테스트 링크를 공개 배포 링크로 취급하지 않는다.
