# Android 0.3.0 USB 센서 측정

0.4.0에서는 이 USB 연결 규격을 유지하며 [사진별 연결·센서 기준/종합 지수](ANDROID_PHOTO_SENSOR_INDEX.md)를 추가했다. 아래 0.3.0 설명은 USB 연결의 최초 인계 기록이며 현재 점수·새 UI의 사용법은 링크 문서를 따른다.

기존 `org.visionmachine.agriclinic` 앱에 UNO R4 Minima USB CDC 연결과 센서 기록 화면을 추가했다. 버전은 `0.3.0`, `versionCode=3`이다. 기존 촬영 사진과 RGB 모델·이력을 유지하며 센서 기록은 새 `sensor_records_v1` 저장소에 기록한다. 배포 상태는 [PLAY_INTERNAL_TEST](PLAY_INTERNAL_TEST.md)를 따른다.

## 사용하는 순서

1. Play 내부 테스트의 기존 비전머신 앱을 업데이트한다. 업로드 키로 서명한 로컬 APK를 Play 설치본 위에 설치하는 방식은 사용하지 않는다. Play 앱 서명키가 업로드 키와 다를 수 있다.
2. 펌웨어 `uno-r4-0.2.0`이 올라간 보드를 휴대폰의 USB-C 데이터 연결에 꽂는다. 휴대폰은 USB 호스트를 지원해야 한다. PC와 휴대폰에 보드를 동시에 연결하지 않는다.
3. 앱 첫 화면의 **USB 센서 연결 · 측정**을 누른다. **USB 연결**을 누르고 Android USB 권한 창을 허용한다. 보드 전원 LED가 켜진 것과 통신 연결 성공은 따로 확인한다.
4. 필요하면 **사진 촬영·기록**에서 기존 카메라로 촬영한 뒤 **촬영 사진 선택**으로 대상을 고른다. 사진 없이도 측정할 수 있다.
5. **네 센서 측정 · 저장**을 누른다. 요청마다 새 검사 UUID로 측정하고 실제 수신 시각·원본 패킷·오류·선택 사진 메타데이터를 기기에 저장한다.
6. 이번 측정·저장 이력을 확인한다. 최근 20건이 화면에 표시되고 최대 200건을 보관한다. **전체 이력 CSV 저장**은 보관 중인 전체 기록을 내보낸다.

사진 연결 시 새 측정의 `inspectionId=request_id`를 사용하고 원래 촬영의 ID는 `sourceCaptureId`로 보존한다. 같은 사진을 반복 측정해도 원본 사진·기존 촬영 기록을 덮어쓰지 않는다. 촬영·측정 시각을 각각 남기며 동시에 획득한 값으로 바꾸지 않는다. RGB 사진 분석과 센서값은 별도로 표시하며 융합 모델 결과를 만들지 않는다.

## 연결·오류 처리

- 지원 장치: UNO R4 Minima runtime VID `2341` / PID `0069` 한 대. 다른 USB 장치나 DFU 업로드 인터페이스를 열지 않는다.
- `usb-serial-for-android` 3.9.0의 CDC ACM을 사용한다. 현재 Kotlin 2.0.21 빌드와 호환되는 버전으로 고정했다. JitPack 저장소는 해당 그룹에만 한정한다.
- 통신은 작업 스레드에서 115200/8N1, DTR=true, RTS=false로 수행한다. 앱은 한 번에 한 요청만 보내며 제한시간은 12초, JSONL 한 줄 상한은 4096바이트다.
- USB 분할 수신을 조립하고 현재 UUID와 다른 지난 응답을 건너뛴다. 잘못된 패킷·불완전 응답·시간 초과를 새 측정값으로 저장하지 않는다.
- 권한 거절·장치 없음·분리·입출력 실패는 화면에 안내한다. 연결 해제·재측정 시 현재값을 비우고 저장 이력은 유지한다. 화면을 떠나면 연결을 닫고 돌아와 다시 연결한다. 회전 중에는 ViewModel을 유지한다.
- 센서 일부 실패의 `null`·오류와 광학 포화 경고를 보존한다. 결측을 0으로 바꾸지 않는다. `mode=mock`은 **모의 시험자료**로 표시한다.
- 토양은 ADC 원시값이며 교정된 수분 %가 아니다. 광학은 두 순차 노출의 12개 원시 채널과 측정조건이다. 표면온도와 MLX 자체 온도를 구분하며 PEC·원시값·방사율 일관성을 검사한다. 계측 오류를 작물 질병으로 해석하지 않는다.

세부 규격 원본은 `packages/contracts/src/vm_contracts/models.py`, 펌웨어 인계는 [ARDUINO_PHONE_HANDOFF](ARDUINO_PHONE_HANDOFF.md)다.

## 코드 위치

| 파일 | 책임 |
|---|---|
| `apps/android/.../SensorActivity.kt` | 연결·측정·사진 선택·이력·CSV 화면 |
| `SensorViewModel.kt`, `SensorStore.kt` | 요청 상태, 실제 수신 시각, 원본 패킷·사진 연결 저장 |
| `usb/UsbSensorClient.kt` | 장치 열거·권한·CDC·분리·자원 정리 |
| `usb/SensorExchange.kt` | 요청·분할 응답·ID·시간 초과·취소 |
| `SensorPacketFramer.kt`, `SensorExtensions.kt` | 기본·확장 계약 검증 |
| `res/xml/usb_sensor_filter.xml` | 지정한 UNO R4 장치 연결 필터 |

위 Kotlin 파일은 모두 `apps/android/app/src/main/java/org/visionmachine/agriclinic/` 아래에 있다.

## 개발 시험과 실기기 확인

```powershell
# apps/android, JDK 17 또는 21 / SDK 36
./gradlew.bat :app:assembleDebug :app:lintDebug :app:testDebugUnitTest
./gradlew.bat :app:connectedDebugAndroidTest
```

`SensorFeatureTest`는 명시적인 합성·mock 패킷으로 확장 필드, PEC, 포화/결측, 분할·지난 ID, 취소/시간 초과, 사진 연결 저장·중복·CSV를 검사한다. `SensorScreenTest`는 장치가 없을 때 현재 실측값을 만들지 않는지 검사한다.

`RecordedFirmwarePacketTest`는 Git 밖에 보관한 실제 보드 응답을 재생하는 선택 시험이다. 개인 로컬의 `app/src/androidTest/assets/private/sensor_packet_v020_real.json`에 `received_at`와 `packet`을 가진 원본 기록이 있을 때만 실행하며 원래 수신 시각을 유지한다. 이 기록은 시험 APK의 자산이며 release APK/AAB에는 포함하지 않는다. 에뮬레이터 이력에 보관된 값은 휴대폰 USB로 새로 받은 값이 아니다.

`LiveSensorBridgeTest`는 명시적으로 실행한 로컬 PC 직렬 브리지와 `sensor_bridge_port` 인자가 있을 때만 실행한다. PC 브리지도 휴대폰 UsbManager·권한·호스트 전원의 검증을 대신하지 않는다.

실휴대폰 확인 항목:

- Play에서 기존 앱 업데이트 후 사진·RGB 이력이 유지되는지 확인.
- 권한 허용·거절 후 재시도, 네 센서 측정과 사진 ID/각 시각 확인.
- 측정 중 케이블 분리 시 현재값 초기화·이력 유지, 재연결 후 새 UUID 측정.
- 촬영/사진 보기/CSV 화면 이동·복귀 후 다시 연결, 다른 Android 기종 호환성.
- 토양의 건조/습윤 반응, 광학의 밝기 변화와 포화, 표면온도의 대상 변화. 전자부·커넥터는 흙·물 밖에 둔다.

2026-11-13 앱 작업에서는 사용자가 보드를 PC에 다시 연결할 수 없어 저장된 실제 응답 재생과 에뮬레이터 시험으로 범위를 구분했다. 휴대폰 USB 전원·권한·실제 CDC 왕복 성공을 주장하지 않는다.

참고: [Android USB host](https://developer.android.com/develop/connectivity/usb/host), [usb-serial-for-android 3.9.0](https://github.com/mik3y/usb-serial-for-android/tree/3.9.0).
