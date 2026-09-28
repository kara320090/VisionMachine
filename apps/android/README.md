# Android 앱 — 이봉헌·유재윤

Kotlin/Compose Android 프로젝트와 Gradle wrapper를 생성했다. `app/src/main`은 기존 카메라 앱의 `TakePicture`로 원본 JPEG를 앱 전용 파일에 저장하고, 검사 ID·개체 ID·묶음 ID·작물 코드·사진 URI를 로컬 목록에 기록한다. 촬영 취소 시 빈 파일을 정리하고, 프로세스가 돌아온 뒤 미완료 촬영을 복구·정리할 수 있다. 현재 applicationId `org.visionmachine.agriclinic`은 개발용이며 Play 등록 전에 팀이 확정한다.

현재 로컬 기록 목록·전송 상태는 SharedPreferences JSON이며 원본 사진은 앱 전용 `files/photos`에 저장한다. 디버그 앱은 사진 SHA-256과 계약 메타데이터를 로컬 서버 `POST /v1/inspections`에 전송한다. 업로드 실패·앱 중단 후에는 같은 검사 ID로 수동 재시도한다. `pending_model`은 AI 분석 대기로 표시하고, 완료된 모의 결과가 오면 모의 표시를 유지한다. Room, 자동 재전송 WorkManager, 실측 USB 수신은 후속 작업이다. thumbnail을 원본처럼 사용하지 않는다.

빌드: Android SDK Platform 35, Gradle 8.9, AGP 8.7.0, Kotlin 2.0.21, JDK 17. 저장소의 `gradlew`/`gradlew.bat`를 사용한다. Windows PowerShell에서 JDK 17 `JAVA_HOME`과 `ANDROID_HOME`을 설정한 뒤 `./gradlew.bat :app:assembleDebug`를 실행한다. 산출물 `app/build/outputs/apk/debug/app-debug.apk`는 Git에서 제외한다. Android Studio의 기본 JDK가 25인 환경에서는 JDK 17을 별도로 지정해야 한다.

```text
app/src/main/java/<확정패키지>/
  MainActivity.kt                     구현됨: 촬영 UI·TakePicture·취소/복귀
  CaptureStore.kt                    구현됨: 앱 전용 사진·URI·로컬 기록
  SensorPacketFramer.kt               구현됨: JSONL 줄 조립·계약/요청 ID 검사·모의 표시
  usb/UsbSensorClient.kt              후속: USB 권한·기기·serial·실측 수신
  data/local/                        후속: 검사·사진 URI·전송대기 Room
  InspectionUploadClient.kt           구현됨: 디버그 loopback 사진 업로드·응답 검증
  data/remote/                       후속: 운영 HTTPS·인증·계약 DTO·오류 변환
  domain/                            검사 ID·시각·상태 흐름
  workers/UploadInspectionWorker.kt   재시도·중복 방지
  ui/capture/                        촬영→측정→검사 저장
  ui/result/                         결과·근거·모델 버전·모의 표시
  ui/history/                        검사 이력·삭제
  ui/settings/                       개발용 서버 설정·권한 상태
app/src/test/                         순수 로직/패킷/DTO
app/src/androidTest/                  실제 UI·복귀/DB 시험
```

현재 촬영·저장 APK와 디버그 loopback 서버 전송을 구현했다. 에뮬레이터에서 화면 기동·외부 카메라 호출·취소 시 빈 파일 정리를 확인했다. 에뮬레이터 카메라가 실제 촬영 파일을 쓰지 않아 성공 촬영의 카메라 왕복과 사진 열기는 실기기에서 확인해야 한다. 실측 USB·실제 AI 분석은 아직 없으며, 센서 미취득을 `not_acquired`, 모델 미준비를 분석 대기로 기록하고 정상 판정하지 않는다.

디버그 연결은 개발 PC에서 `uvicorn`을 `127.0.0.1:8000`에 실행하고 `adb reverse tcp:8000 tcp:8000`을 설정한다. 이때 앱의 `127.0.0.1:8000`이 ADB를 통해 PC loopback으로 전달된다. ADB reverse 없이 일반 휴대폰의 `127.0.0.1`은 휴대폰 자신이다. release에는 cleartext 예외와 전송 버튼이 없으며 운영 HTTPS·인증은 아직 구현하지 않았다. 디버그 앱의 `usesCleartextTraffic` 예외는 디버그 manifest에만 있다.

wrapper JAR/properties와 빌드 설정을 커밋한다. local.properties·APK/AAB·서명키는 제외한다. 첫 APK 빌드는 코드 컴파일 검증이며 카메라 앱·실제 휴대폰 호환성 검증을 뜻하지 않는다.

계측 시험 실행: Android 에뮬레이터 또는 연결된 기기가 켜진 상태에서 `./gradlew.bat :app:connectedDebugAndroidTest`(Windows) 또는 `bash ./gradlew :app:connectedDebugAndroidTest`(Linux). 합성 JPEG만 사용하며 원본 작물 사진은 시험에 넣지 않는다.

`SensorPacketFramer`는 USB CDC 입력 바이트에서 4096바이트 이내 JSONL 한 줄을 조립하고 계약 필드·범위·현재 검사 ID를 확인한다. `mode=mock`을 그대로 표시하고 잘못된 UTF-8, 불완전/초과 줄, 이전 검사 응답을 거부한다. 아직 Android USB 권한·serial 장치 연결이나 실측 패킷 수신은 구현하지 않았다.

에뮬레이터에서 합성 JPEG와 ADB reverse를 사용해 실제 로컬 FastAPI 서버의 업로드 201·조회 200을 확인했다. 실휴대폰 카메라·USB 장치·운영 HTTPS 연결은 별도 시험이 필요하다.
