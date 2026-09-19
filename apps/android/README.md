# Android 앱 — 이봉헌·유재윤

**아직 Android 프로젝트·Gradle wrapper·APK는 생성하지 않았다.** Antigravity에서 prompts/04_android.md를 실행하여 설치된 SDK/JDK/Gradle 호환성을 확인하고 이 폴더에 생성한다. 패키지명은 Play에 올리기 전 팀이 확정한다.

기술 시작안 Kotlin + Compose. 저장 Room, 재전송 WorkManager, HTTP 클라이언트는 선택/잠금 후 사용한다. 기존 카메라 호출은 원본 크기의 output URI를 받는 TakePicture 방식으로 구현한다. thumbnail을 원본처럼 사용하지 않는다.

```text
app/src/main/java/<확정패키지>/
  MainActivity.kt
  camera/CameraCapture.kt             기존 카메라 호출·URI·취소/복귀
  usb/UsbSensorClient.kt              권한·기기·serial·부분 줄 조립
  data/local/                        검사·사진 URI·전송대기 Room
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

처음 작업은 촬영·저장 APK다. USB 미연결은 측정 없음, 모델 미준비는 분석 대기로 표시하며 정상 판정하지 않는다. 가짜 sensor는 debug build에서 눈에 띄게 표시한다.

에뮬레이터 host, 실제 휴대폰 LAN, 운영 HTTPS 주소는 다르다. 127.0.0.1은 휴대폰 자신을 가리키므로 PC 서버 주소로 사용하지 않는다. debug HTTP 예외가 필요하면 제한된 debug 설정에만 두고 release에 전역 cleartext 허용을 넣지 않는다.

후속 빌드에는 gradlew·gradlew.bat·wrapper JAR/properties·빌드 설정·확정한 lockfile을 커밋한다. local.properties·APK/AAB·서명키는 제외한다. 생성되지 않은 wrapper나 SDK를 있다고 가정하지 않는다.
