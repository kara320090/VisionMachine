# Android 앱 — 이봉헌·유재윤

현재 Play 내부 테스트 배포는 [UI 개선 0.6.1(versionCode 7)](../../docs/ANDROID_UI.md)이다. 촬영·사진 추가, 사진별 결과, USB 센서, 분석 기록의 화면을 정리했다. 자동 서버 연결·기존 저장 데이터·모델과 점수 계산은 유지한다.

패키지는 `org.visionmachine.agriclinic`이다. 0.6.1을 2026-11-15 18:05(KST)에 기존 트랙의 업데이트로 출시했고 ‘내부 테스터에게 제공됨’을 확인했다. 설치·업데이트 후 앱을 열면 [4090 자동 연결](../../docs/AUTOMATIC_SERVER.md)을 수행하며 주소·API 키 입력이나 휴대폰 Tailscale 설치가 필요 없다.

설치별 인증은 자동 등록·암호화 보관·갱신한다. 분석 버튼을 누르면 사진과 연결 센서 기록을 서버로 보내며, 서버 장애를 로컬 점수로 자동 대체하지 않는다. 사용자가 ‘기기에서 분석하기’를 선택하면 로컬 모델로 전환한다. 점수 정의는 [ANDROID_PHOTO_SENSOR_INDEX](../../docs/ANDROID_PHOTO_SENSOR_INDEX.md), 실제 출시 상태는 [PLAY_INTERNAL_TEST](../../docs/PLAY_INTERNAL_TEST.md)를 따른다.

- 런처 `AnalysisActivity`: 실제 ONNX RGB 모델의 개별/최대 8장 일괄 분석, 사진 변경 시 현재 결과 초기화, 200건 이력·CSV. 모델 자산 준비·제한·전처리 검사는 [ANDROID_RGB](../../docs/ANDROID_RGB.md).
- `MainActivity`: 기존 카메라 앱으로 원본 JPEG 촬영, 검사·개체·묶음·작물 코드·사진 URI 저장, 취소 시 빈 파일 정리, 중단된 촬영 복구. 사진별 센서 측정으로 이동한다.
- `SensorActivity`: UNO R4 Minima USB 권한·CDC 연결, 토양/온습도/광학/표면온도 확장 요청·응답, 촬영 사진 연결, 최근 20건 표시/200건 보관·CSV, 연결·계측 오류 처리. 사용법·시험 범위는 [ANDROID_USB](../../docs/ANDROID_USB.md), 펌웨어 규격은 [ARDUINO_PHONE_HANDOFF](../../docs/ARDUINO_PHONE_HANDOFF.md).
- 실제 휴대폰의 USB 호스트 전원·권한·분리/재연결 성공은 에뮬레이터나 저장 응답 재생과 구분한다. 토양을 보정 수분 %로 표시하지 않는다. 종합 지수는 사용자가 선택한 가중평균이며 학습된 RGB/센서 융합 진단으로 표시하지 않는다.

## 빌드와 시험

SDK/target 36, Gradle Wrapper 8.11.1, AGP 8.10.1, Kotlin/Compose 2.0.21, 소스 타깃 JDK 17이다. JDK 17 또는 21을 사용한다. 이번 Windows 빌드는 JDK 21.0.13에서 확인했다. Android Studio 기본 JDK 25가 선택된 환경에서는 호환 JDK를 지정한다.

```powershell
./gradlew.bat :app:assembleDebug :app:lintDebug :app:testDebugUnitTest
# 에뮬레이터 또는 개발용 기기가 켜진 상태
./gradlew.bat :app:connectedDebugAndroidTest
```

Windows에서 로직 변경은 에뮬레이터를 띄우지 않고 `.\gradlew.bat :app:testDebugUnitTest`로 확인한다. PC 빌드의 동시 작업 수를 줄이려면 해당 명령에 `--max-workers=2`를 붙인다(프로젝트 기본값 4). 화면·Android API를 검사할 때는 이 폴더에서 GPU 가속 가상 기기를 한 번 열고 같은 기기에 검사를 모아서 실행할 수 있다.

```powershell
$serial = .\tools\Start-TestEmulator.ps1
adb -s $serial shell getconf PAGE_SIZE
```

기본 AVD는 `VisionMachine_Release_UI_Test`이며 `-AvdName`으로 선택할 수 있다. 자동 검사용 새 세션은 창·오디오 없이 `-gpu host`로 시작한다. 화면을 직접 조작할 때는 `.\tools\Start-TestEmulator.ps1 -ShowWindow`로 연다. 창 없이 실행 중인 세션에 화면을 붙이려면 재시작이 필요하므로, 이 경우 도구는 현재 세션을 알려주고 종료한다.

같은 AVD·데이터 경로·읽기 모드의 세션이 있으면 부팅과 렌더러를 확인한 뒤 해당 serial을 돌려준다. `-Port`를 지정하면 그 포트만 사용한다. 기존 시험 데이터 폴더로 일회성 검사를 할 때는 `.\tools\Start-TestEmulator.ps1 -DataDirectory $testData -ReadOnly -Port 5580`으로 실행한다. 읽기 전용 모드는 스냅샷을 끄며, 일반 실행은 AVD의 부팅 설정을 따른다. `-WhatIf`로 새로 실행할 옵션을 확인할 수 있다. 직접 시작한 세션을 종료할 때는 `adb -s $serial emu kill`을 사용한다.

Play Store 시스템 이미지의 콜드 부팅 후에는 홈 화면에서도 Play Store와 앱 최적화가 CPU를 쓸 수 있다. 한 작업에서 여러 화면을 확인할 때는 켜 둔 기기를 재사용하고, 마지막 검사를 마치면 가상 기기를 종료한다. 기기 안에서 화면을 꺼도 Android 시스템은 계속 실행된다.

`usb-serial-for-android` 3.9.0을 사용한다. 0.6.1 signed release 빌드·lint(오류 0/경고 28)·JVM 6건과 Android 계측 38건 통과/3건 조건부 skip을 확인했다. 0.6.0에서 설정 없는 자동 등록으로 실제 서버 CUDA 8장 분석과 매칭 모의 센서 스냅샷을 확인했으며, UI 작업에서는 실서버 분석 opt-in 시험을 반복하지 않았다. 비공개 사진·실보드 자료는 공개 Git 밖에 보관하며 선택 시험의 조건이 없으면 skip한다. 실제 휴대폰 USB/사진 분석 왕복은 별도다.

## 저장과 서버 경로

원본 사진은 `files/photos`, 촬영 메타데이터는 기존 SharedPreferences JSON, RGB 이력은 기존 파일에 저장한다. 새 센서 기록은 별도 `sensor_records_v1`에 저장하며 원래 촬영 ID는 `sourceCaptureId`로 보존한다. 신규 측정은 새 UUID를 사용한다. Room·WorkManager 자동 재전송은 아직 구현하지 않았다.

기본 자동 연결 모드에서 사진 바이트, SHA-256, 촬영/작물 메타데이터와 같은 사진에 연결된 센서 기록을 `POST /api/v1/inspections`로 전송한다. 서버 응답의 검사·사진 ID·해시·모델과 CUDA provider를 검증해 기존 결과/이력에 반영한다. 센서·종합 점수는 기존 앱 규칙을 유지한다.

서버 전송은 사진을 앱 전용 캐시에 기록하면서 해시를 계산하고, 같은 원본 바이트를 64KiB 단위로 읽어 전송한다. 전송이 끝나거나 실패하면 임시 파일을 정리한다. 에뮬레이터의 호스트 CPU 사용률과 실제 휴대폰의 사진 처리·전송 비용은 별도로 측정한다.

공개 `config/android-server.json`에서 HTTPS 주소를 자동 조회한다. 설치별 키는 자동으로 발급받아 Android Keystore로 암호화하며 APK에 공통 키를 넣지 않는다. 기존 VisionMachine의 임시 터널 주소가 변경되면 운영자가 manifest를 갱신한다. USB 이력은 앱에 보관하고 분석 때 동일 사진의 기록을 전송한다.

0.6.1의 Play 내부 테스트 제공 상태를 확인했다. 서버의 자동 등록·GPU 분석 성공은 이전 0.6.0 검증 기록이며, 실제 물리 휴대폰에서의 설치와 분석 왕복은 아직 별도 확인이 필요하다.

wrapper JAR/properties·빌드 설정·소스·합성 fixture만 커밋한다. `local.properties`, APK/AAB, 서명키, 암호, 실제 사진·패킷, 모델 가중치는 Git에서 제외한다. Play 앱 업데이트용 AAB 서명·업로드 절차는 [PLAY_INTERNAL_TEST](../../docs/PLAY_INTERNAL_TEST.md)에 있다.
