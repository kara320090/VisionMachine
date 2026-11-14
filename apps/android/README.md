# Android 앱 — 이봉헌·유재윤

현재 내부 테스트 배포는 `0.6.0(versionCode 6)`, 패키지는 `org.visionmachine.agriclinic`이다. 2026-11-15 02:20(KST)에 기존 트랙의 업데이트로 출시했다. 설치·업데이트 후 앱을 열면 [4090 자동 연결](../../docs/AUTOMATIC_SERVER.md)을 수행하며 주소·API 키 입력이나 휴대폰 Tailscale 설치가 필요 없다.

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

`usb-serial-for-android` 3.9.0을 사용한다. 0.6.0 signed release 빌드·lint(오류 0/경고 28)·JVM 6건과 Android 계측 36건 통과/2건 조건부 skip을 확인했다. 설정 없는 자동 등록으로 실제 서버 CUDA 8장 분석과 매칭 모의 센서 스냅샷을 확인했다. 비공개 사진·실보드 자료는 공개 Git 밖에 보관하며 선택 시험의 조건이 없으면 skip한다. 실제 휴대폰 USB/사진 분석 왕복은 별도다.

## 저장과 서버 경로

원본 사진은 `files/photos`, 촬영 메타데이터는 기존 SharedPreferences JSON, RGB 이력은 기존 파일에 저장한다. 새 센서 기록은 별도 `sensor_records_v1`에 저장하며 원래 촬영 ID는 `sourceCaptureId`로 보존한다. 신규 측정은 새 UUID를 사용한다. Room·WorkManager 자동 재전송은 아직 구현하지 않았다.

기본 자동 연결 모드에서 사진 바이트, SHA-256, 촬영/작물 메타데이터와 같은 사진에 연결된 센서 기록을 `POST /api/v1/inspections`로 전송한다. 서버 응답의 검사·사진 ID·해시·모델과 CUDA provider를 검증해 기존 결과/이력에 반영한다. 센서·종합 점수는 기존 앱 규칙을 유지한다.

공개 `config/android-server.json`에서 HTTPS 주소를 자동 조회한다. 설치별 키는 자동으로 발급받아 Android Keystore로 암호화하며 APK에 공통 키를 넣지 않는다. 기존 VisionMachine의 임시 터널 주소가 변경되면 운영자가 manifest를 갱신한다. USB 이력은 앱에 보관하고 분석 때 동일 사진의 기록을 전송한다.

0.6.0의 Play 내부 테스트 제공 상태와 실제 서버의 자동 등록·GPU 분석 성공을 확인했다. 실제 물리 휴대폰에서의 설치와 분석 왕복은 아직 별도 확인이 필요하다.

wrapper JAR/properties·빌드 설정·소스·합성 fixture만 커밋한다. `local.properties`, APK/AAB, 서명키, 암호, 실제 사진·패킷, 모델 가중치는 Git에서 제외한다. Play 앱 업데이트용 AAB 서명·업로드 절차는 [PLAY_INTERNAL_TEST](../../docs/PLAY_INTERNAL_TEST.md)에 있다.
