# Android 앱 — 이봉헌·유재윤

Kotlin/Compose Android 프로젝트와 Gradle wrapper를 생성했다. `app/src/main`은 기존 카메라 앱의 `TakePicture`로 원본 JPEG를 앱 전용 파일에 저장하고, 검사 ID·개체 ID·묶음 ID·작물 코드·사진 URI를 로컬 목록에 기록한다. 촬영 취소 시 빈 파일을 정리하고, 프로세스가 돌아온 뒤 미완료 촬영을 복구·정리할 수 있다. 현재 applicationId `org.visionmachine.agriclinic`은 개발용이며 Play 등록 전에 팀이 확정한다.

현재 로컬 기록 목록은 SharedPreferences JSON이며 원본 사진은 앱 전용 `files/photos`에 저장한다. Room, 재전송 WorkManager, HTTP 클라이언트, USB 수신은 다음 단위다. thumbnail을 원본처럼 사용하지 않는다.

빌드: Android SDK Platform 35, Gradle 8.9, AGP 8.7.0, Kotlin 2.0.21, JDK 17. 저장소의 `gradlew`/`gradlew.bat`를 사용한다. Windows PowerShell에서 JDK 17 `JAVA_HOME`과 `ANDROID_HOME`을 설정한 뒤 `./gradlew.bat :app:assembleDebug`를 실행한다. 산출물 `app/build/outputs/apk/debug/app-debug.apk`는 Git에서 제외한다. Android Studio의 기본 JDK가 25인 환경에서는 JDK 17을 별도로 지정해야 한다.

```text
app/src/main/java/<확정패키지>/
  MainActivity.kt                     구현됨: 촬영 UI·TakePicture·취소/복귀
  CaptureStore.kt                    구현됨: 앱 전용 사진·URI·로컬 기록
  usb/UsbSensorClient.kt              후속: 권한·기기·serial·부분 줄 조립
  data/local/                        후속: 검사·사진 URI·전송대기 Room
  data/remote/                       API·계약 DTO·오류 변환
  domain/                            검사 ID·시각·상태 흐름
  workers/UploadInspectionWorker.kt   재시도·중복 방지
  ui/capture/                        촬영→측정→검사 저장
  ui/result/                         결과·근거·모델 버전·모의 표시
  ui/history/                        검사 이력·삭제
  ui/settings/                       개발용 서버 설정·권한 상태
app/src/test/                         순수 로직/패킷/DTO
app/src/androidTest/                  실제 UI·복귀/DB 시험
```

현재 첫 작업인 촬영·저장 APK는 빌드됐다. 에뮬레이터에서 화면 기동·외부 카메라 호출·취소 시 빈 파일 정리를 확인했고, 계측 시험으로 유효한 JPEG 저장·재시작 조회·취소·잘못된 파일 거부를 확인했다. 에뮬레이터 카메라가 실제 촬영 파일을 쓰지 않아 성공 촬영의 카메라 왕복과 사진 열기는 실기기에서 확인해야 한다. 앱은 아직 측정·전송·분석 결과 기능을 제공하지 않으며 이를 화면에 명시한다. 향후 USB 미연결은 측정 없음, 모델 미준비는 분석 대기로 표시하며 정상 판정하지 않는다. 가짜 sensor는 debug build에서 눈에 띄게 표시한다.

에뮬레이터 host, 실제 휴대폰 LAN, 운영 HTTPS 주소는 다르다. 127.0.0.1은 휴대폰 자신을 가리키므로 PC 서버 주소로 사용하지 않는다. debug HTTP 예외가 필요하면 제한된 debug 설정에만 두고 release에 전역 cleartext 허용을 넣지 않는다.

wrapper JAR/properties와 빌드 설정을 커밋한다. local.properties·APK/AAB·서명키는 제외한다. 첫 APK 빌드는 코드 컴파일 검증이며 카메라 앱·실제 휴대폰 호환성 검증을 뜻하지 않는다.

계측 시험 실행: Android 에뮬레이터 또는 연결된 기기가 켜진 상태에서 `./gradlew.bat :app:connectedDebugAndroidTest`(Windows) 또는 `bash ./gradlew :app:connectedDebugAndroidTest`(Linux). 합성 JPEG만 사용하며 원본 작물 사진은 시험에 넣지 않는다.
