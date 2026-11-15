# Android 0.6.1 화면 개선

기존 앱의 촬영·분석·센서·기록을 같은 초록색/크림색 테마로 정리한 UI 업데이트다. 패키지는 `org.visionmachine.agriclinic`, versionCode 7 / versionName 0.6.1이다. Play에 제공 중인 0.6.0과 구분하며, 0.6.1의 Play 출시는 별도다.

## 사용 흐름

1. 첫 화면에서 작물을 고르고 **바로 촬영** 또는 **사진 추가**를 누른다. 사진 선택기 대신 **파일에서 추가**도 사용할 수 있다. 한 번에 최대 8장이다.
2. 사진이 생기면 큰 안내 영역이 접히고 **선택 N장 모두 분석**이 하단에 고정된다. 번호 카드를 누르면 해당 사진·작물·대기/완료/실패 상태를 확인한다. 선택 작물은 사진별로 바꿀 수 있고 **이 사진만 분석**도 유지한다.
3. 결과가 나오면 사진·결과 카드로 이동한다. 정상/이상 모델 출력을 기존과 동일한 소수 여섯 자리로 보여 준다. 출력값을 보정된 진단 확률로 표시하지 않는다. 연결된 센서 점수와 사용자 가중 종합 지수도 별도로 표시한다. 센서가 없으면 미연결 상태를 표시한다.
4. 하단 **USB 센서** 또는 사진 카드의 **이 사진에 센서 측정**으로 측정 화면을 연다. 장치 연결, 사진 연결, 작물 기준, 측정값·이력을 카드로 나눴다. 원래 USB 권한·통신·결측/오류 처리·단위는 그대로다. 측정하지 않은 수치를 만들지 않는다.
5. 하단 **분석 기록**에서 기기에 보관된 결과를 조회한다. 전체/이상 의심 필터, 기록별 상세 패널, 전체 CSV 내보내기를 제공한다. 필터 기준은 기존 `RgbRecord.label`과 같은 이상 출력 0.5 이상이다. 기록을 비우거나 저장 형식을 바꾸지 않는다.

## 옵션과 연결 상태

- 상단 연결 표시를 누르면 현재 서버/기기 분석 상태와 재연결·기기 분석 전환을 확인한다. 최초 자동 연결·설치별 인증은 [기존 구현](AUTOMATIC_SERVER.md)을 사용하며 주소·키 입력을 추가하지 않는다.
- 사진 준비 카드의 조절 아이콘은 개체·묶음 ID와 종합 지수 가중치 패널을 연다. 선택 ID는 새 촬영에만 기록하고, 가중치는 다음 분석부터 적용한다. 화면 재생성 후에도 입력 중인 ID를 보존한다.
- 분석 범위와 시험 기능 안내는 화면 아래에서 연다. 모델 버전·처리시간·검사 ID·입력 해시는 결과의 **분석 정보 자세히**에 있다. 센서 기준·항목별 원값·편차·근거는 **기준·항목별 상세 보기**에서 확인한다.
- 대기/처리/실패 메시지를 유지하며, 사진 선택은 상태·선택 여부를 접근성 정보로도 제공한다. 주요 버튼은 최소 48dp 터치 영역을 사용하고 화면과 상세 패널은 스크롤할 수 있다.

## 변경 경계

Android 화면과 UI 계측시험만 변경했다. `RgbAnalysisViewModel`, 전처리, 모델 가중치, 서버 통신·인증·자동 연결, 사진/센서 대응, 센서 계산식, 저장소·CSV, 펌웨어는 변경하지 않는다. 4090 및 BlurFing 서비스 설정·재시작·배포 작업은 이 UI 변경에 포함하지 않는다.

## 확인 방법

JDK 21과 기존 Android SDK에서 실행한다.

```powershell
cd apps/android
./gradlew.bat :app:assembleDebug :app:assembleDebugAndroidTest :app:lintDebug :app:testDebugUnitTest --no-daemon
adb -s <VisionMachine-test-device> install -r app/build/outputs/apk/debug/app-debug.apk
adb -s <VisionMachine-test-device> install -r app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk
adb -s <VisionMachine-test-device> shell am instrument -w org.visionmachine.agriclinic.test/androidx.test.runner.AndroidJUnitRunner
```

`AnalysisNavigationTest`는 선택 ID/옵션 패널의 재생성 보존, 빈 기록/필터/촬영 복귀, 합성 PNG를 실제 기기 내 모델로 분석한 뒤 결과·기록 상세에서 원출력을 확인하는 사용자 흐름을 검사한다. 기존 기록과 연결 모드는 시험 전후 보존한다. 최신 Android의 제거된 `InputManager.getInstance`를 호출하지 않는 안정판 Espresso 3.7.0과 AndroidX Test 1.7.0/1.3.0을 시험 APK에 사용한다. 근거: [AndroidX Test 릴리스 노트](https://developer.android.com/jetpack/androidx/releases/test).

실서버·PC 센서 브리지 시험은 기존과 같이 명시적 실행 조건을 제공할 때만 수행한다. 에뮬레이터의 합성 사진과 실물 휴대폰·작물·USB 측정 시험을 구분한다. 모델·APK/AAB·실제 사진·시험 캡처는 공개 Git에 추가하지 않는다.
