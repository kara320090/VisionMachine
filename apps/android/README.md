# Android 앱 — 이봉헌·유재윤

Play 내부 테스트로 배포한 0.5.0/versionCode 5는 사진 화면의 ‘4090 서버 연결 설정’에서 서버 주소·기기별 인증키를 실행 중 입력할 수 있다. Android Keystore가 자격 증명을 기기별로 암호화해 보관한다. 기존 기기 내 RGB 모델은 기본 경로로 유지하며, 서버 모드를 설정했을 때 서버 실패를 로컬 결과로 숨기지 않는다.

현재 내부 테스트 배포 버전은 `0.5.0(versionCode 5)`, 패키지는 기존 Play 앱과 같은 `org.visionmachine.agriclinic`이다. 첫 화면 바로 촬영·8장 추가/일괄 분석·사진별 센서 연결·센서/사용자 가중 종합 지수를 추가했다. 사용법·점수 정의·근거는 [ANDROID_PHOTO_SENSOR_INDEX](../../docs/ANDROID_PHOTO_SENSOR_INDEX.md), 실제 출시 상태는 [PLAY_INTERNAL_TEST](../../docs/PLAY_INTERNAL_TEST.md)를 따른다.

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

`usb-serial-for-android`는 현재 Kotlin과 호환되는 3.9.0을 사용한다. 최신 라이브러리로 올릴 때 Kotlin 메타데이터·USB CDC 회귀시험을 함께 확인한다. 이전 0.4.0 검증의 API 37.1/16KB x86_64 에뮬레이터에서는 33건 통과/skip 0, JVM 전처리·점수 계산 4건 통과였다. 0.5.0에서는 signed release 빌드·lint와 JVM 4건을 확인했으며 Windows의 Android 계측 테스트는 재실행하지 않았다. 실제 RGB 비교·저장된 보드 패킷 재생은 Git 밖 개인 시험 자산을 사용했다. 해당 자산이 없으면 관련 선택 시험은 skip되며 실제 자료를 합성값으로 대체하지 않는다.

## 저장과 서버 경로

원본 사진은 `files/photos`, 촬영 메타데이터는 기존 SharedPreferences JSON, RGB 이력은 기존 파일에 저장한다. 새 센서 기록은 별도 `sensor_records_v1`에 저장하며 원래 촬영 ID는 `sourceCaptureId`로 보존한다. 신규 측정은 새 UUID를 사용한다. Room·WorkManager 자동 재전송은 아직 구현하지 않았다.

사용자가 서버 모드를 켜면 사진 바이트, 사진 SHA-256, 촬영/작물 메타데이터와 같은 사진에 연결된 센서 기록을 `POST /api/v1/inspections`로 전송한다. 응답은 검사 ID·사진 ID·SHA-256·모델 버전/해시와 CUDA provider를 확인한 뒤 기존 결과 화면에 반영한다. 센서 종합 점수는 앱에서 유지하며 서버에서 중복 계산하지 않는다. 서버 요청 실패는 해당 사진의 실패로 표시하고 로컬 모델 결과로 자동 전환하지 않는다.

주소는 HTTPS 또는 이 4090의 `http://100.74.204.80:8000`을 사용한다. Tailscale IP를 쓰면 휴대폰과 4090이 같은 tailnet에 접속돼 있어야 한다. 현재 서버의 TryCloudflare 주소는 임시 주소라 바뀌거나 만료될 수 있다. API 키는 ZIP/APK에 포함하지 않고 서버가 발급한 키를 기기 설정 화면에 입력한다. USB 측정 이력은 앱에 저장하며, 분석 요청 때 같은 사진에 매칭된 센서 기록을 함께 보낸다.

0.5.0 release AAB는 signed build와 lint를 통과했고 2026-11-15 01:08(KST)에 기존 Play 내부 테스트 트랙으로 출시됐다. Console의 ‘내부 테스터에게 제공됨’을 확인했다. 휴대폰에서 업데이트를 설치한 뒤 서버 주소와 기기별 API 키를 설정한다. 실제 휴대폰의 인증된 사진 업로드·분석 결과 표시 왕복은 별도 확인이 필요하다.

wrapper JAR/properties·빌드 설정·소스·합성 fixture만 커밋한다. `local.properties`, APK/AAB, 서명키, 암호, 실제 사진·패킷, 모델 가중치는 Git에서 제외한다. Play 앱 업데이트용 AAB 서명·업로드 절차는 [PLAY_INTERNAL_TEST](../../docs/PLAY_INTERNAL_TEST.md)에 있다.
