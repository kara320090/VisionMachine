# Android 앱 — 이봉헌·유재윤

현재 소스는 `0.3.0(versionCode 3)`, 패키지는 기존 Play 앱과 같은 `org.visionmachine.agriclinic`이다. 기존 런처·사진·기록·모델을 유지하며 USB 센서 화면을 추가했다. 실제 출시 상태는 [PLAY_INTERNAL_TEST](../../docs/PLAY_INTERNAL_TEST.md)를 따른다.

- 런처 `AnalysisActivity`: 실제 ONNX RGB 모델의 개별/최대 8장 일괄 분석, 사진 변경 시 현재 결과 초기화, 200건 이력·CSV. 모델 자산 준비·제한·전처리 검사는 [ANDROID_RGB](../../docs/ANDROID_RGB.md).
- `MainActivity`: 기존 카메라 앱으로 원본 JPEG 촬영, 검사·개체·묶음·작물 코드·사진 URI 저장, 취소 시 빈 파일 정리, 중단된 촬영 복구. 사진별 센서 측정으로 이동한다.
- `SensorActivity`: UNO R4 Minima USB 권한·CDC 연결, 토양/온습도/광학/표면온도 확장 요청·응답, 촬영 사진 연결, 최근 20건 표시/200건 보관·CSV, 연결·계측 오류 처리. 사용법·시험 범위는 [ANDROID_USB](../../docs/ANDROID_USB.md), 펌웨어 규격은 [ARDUINO_PHONE_HANDOFF](../../docs/ARDUINO_PHONE_HANDOFF.md).
- 실제 휴대폰의 USB 호스트 전원·권한·분리/재연결 성공은 에뮬레이터나 저장 응답 재생과 구분한다. 토양을 보정 수분 %로 표시하지 않으며 RGB와 센서의 융합 진단을 만들지 않는다.

## 빌드와 시험

SDK/target 36, Gradle Wrapper 8.11.1, AGP 8.10.1, Kotlin/Compose 2.0.21, 소스 타깃 JDK 17이다. JDK 17 또는 21을 사용한다. 이번 Windows 빌드는 JDK 21.0.13에서 확인했다. Android Studio 기본 JDK 25가 선택된 환경에서는 호환 JDK를 지정한다.

```powershell
./gradlew.bat :app:assembleDebug :app:lintDebug :app:testDebugUnitTest
# 에뮬레이터 또는 개발용 기기가 켜진 상태
./gradlew.bat :app:connectedDebugAndroidTest
```

`usb-serial-for-android`는 현재 Kotlin과 호환되는 3.9.0을 사용한다. 최신 라이브러리로 올릴 때 Kotlin 메타데이터·USB CDC 회귀시험을 함께 확인한다. 이번 API 37.1/16KB x86_64 에뮬레이터에서는 27건 통과/skip 0, JVM 전처리 비교 1건 통과다. 실제 RGB 비교·저장된 보드 패킷 재생은 Git 밖 개인 시험 자산을 사용했다. 해당 자산이 없으면 관련 선택 시험은 skip되며 실제 자료를 합성값으로 대체하지 않는다.

## 저장과 서버 경로

원본 사진은 `files/photos`, 촬영 메타데이터는 기존 SharedPreferences JSON, RGB 이력은 기존 파일에 저장한다. 새 센서 기록은 별도 `sensor_records_v1`에 저장하며 원래 촬영 ID는 `sourceCaptureId`로 보존한다. 신규 측정은 새 UUID를 사용한다. Room·WorkManager 자동 재전송은 아직 구현하지 않았다.

디버그 빌드만 사진 SHA-256과 계약 메타데이터를 로컬 서버 `POST /v1/inspections`에 전송할 수 있다. 서버를 `127.0.0.1:8000`에 실행하고 `adb reverse tcp:8000 tcp:8000`으로 연결한다. reverse 없는 일반 휴대폰의 loopback은 휴대폰 자신이다. 실패 후 같은 검사 ID로 수동 재시도하며 `pending_model`·mock 응답을 그대로 표시한다.

release에는 cleartext 예외·개발 서버 전송 버튼이 없다. 운영 HTTPS·인증·서버 AI·센서 융합 모델은 연결하지 않았다. 이번 USB 기록은 기기에 저장하며 서버에 자동 전송하지 않는다.

wrapper JAR/properties·빌드 설정·소스·합성 fixture만 커밋한다. `local.properties`, APK/AAB, 서명키, 암호, 실제 사진·패킷, 모델 가중치는 Git에서 제외한다. Play 앱 업데이트용 AAB 서명·업로드 절차는 [PLAY_INTERNAL_TEST](../../docs/PLAY_INTERNAL_TEST.md)에 있다.
