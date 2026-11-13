# 계측·펌웨어 — 최승빈·정회서

UNO R4 Minima 한 대에서 SEN0308 A0 원시값·SEN0334 온습도·SEN0364 광학·SEN0206 표면온도를 읽는다. 현재 펌웨어는 `uno-r4-0.2.0`이다. `firmware.ino`는 Arduino 시작 파일이며 실제 `setup()`·`loop()`는 `visionmachine.ino.cpp`에 있다. Arduino IDE에서는 `firmware/firmware.ino`를 연다. 휴대폰에 인계할 요청·응답·단위·시험 범위는 [ARDUINO_PHONE_HANDOFF](../docs/ARDUINO_PHONE_HANDOFF.md)를 따른다.

```text
firmware/
  firmware.ino           Arduino 스케치 시작 파일
  visionmachine.ino.cpp  초기화·측정 요청/응답
  SensorReader.h/.cpp     SEN0308 A0·SEN0334 I2C 실측
  Calibration.h/.cpp      원시→보정, calibration_id
  UsbProtocol.h/.cpp      JSONL·request ID·sequence·error
  MeasureRequest.h/.cpp   상한이 있는 측정 요청 검사·분할 수신 처리
  OpticalReader.h/.cpp    광학 설정 확인·SMUX 순차 노출·읽기/대기 오류 검사
  SensorMath.h/.cpp       SMBus PEC·표면온도 원시값 변환
  Measure-UsbSensors.ps1  PC USB 기본/확장 실측 확인
calibration/              교정 절차/허용된 예제 코드
```

## PC에서 빌드·업로드

2026-11-13 Windows에서 Arduino CLI 1.6.0, `arduino:renesas_uno` 1.6.0, Adafruit SHT31 Library 2.2.2, Adafruit BusIO 1.17.4, Adafruit AS7341 1.4.1로 빌드하고 UNO R4 Minima에 업로드했다. 표면온도는 Wire를 통해 PEC를 검사하며 별도 MLX 라이브러리를 요구하지 않는다. USB 직렬 요청·응답을 확인했으며 이 확인이 센서 보정·Android 앱 연결 완료를 뜻하지 않는다. 실제 측정 로그와 장치 식별자는 공개 저장소 밖에 보관한다.

저장소 최상위 폴더에서 실행한다. `COM3`는 예시이며 `board list`에 표시된 실제 UNO R4 Minima 포트로 바꾼다.

```powershell
arduino-cli core install arduino:renesas_uno@1.6.0
arduino-cli lib install "Adafruit SHT31 Library@2.2.2" "Adafruit BusIO@1.17.4" "Adafruit AS7341@1.4.1"
arduino-cli board list
arduino-cli compile --fqbn arduino:renesas_uno:minima firmware
arduino-cli upload --fqbn arduino:renesas_uno:minima --port COM3 firmware
```

Windows에서 `DFU-RT Port`가 드라이버 오류로 표시되거나 `LIBUSB_ERROR_NOT_FOUND`가 발생하면 공식 Renesas UNO 보드 패키지에 동봉된 서명된 `drivers/renesas.inf`를 설치한다. 보드는 일반 직렬 포트와 업로드용 DFU 인터페이스가 별개이므로 COM 포트 표시만으로 업로드 준비가 끝난 것은 아니다. Windows GCC가 긴 설치 경로에서 표준 헤더를 찾지 못하면 도구 설치 폴더를 짧은 경로로 옮긴 뒤 재빌드한다.

## 측정 요청

전원이 들어오면 프로그램은 시작하지만 측정값을 계속 출력하지 않는다. USB 직렬 연결을 115200 baud로 열고 아래 JSON 한 줄과 줄바꿈(`LF`)을 보내면 새 측정값을 한 번 반환한다. `request_id`는 요청마다 새 UUID를 사용한다.

```json
{"schema_version":"0.1.0","message_type":"measure","request_id":"00000000-0000-4000-8000-000000000000"}
```

위 UUID는 요청 형식 예시다. 기본 요청은 토양·온습도 형식을 그대로 반환한다. 네 센서를 모두 받으려면 `"sensor_profile":"extended"` 문자열 필드를 추가한다. 광학·표면온도는 버전이 있는 `extensions`에만 넣는다. 실패 센서는 `null`과 오류 코드로 반환하고 정상인 다른 센서 값은 유지한다. 토양 ADC 숫자만으로 프로브 연결·보정의 타당성을 판정하지 않는다. 현재 Android의 패킷 파서는 기본 형식용이며 실제 USB 연결·확장 응답 처리는 앱 단계에서 구현한다.

요청은 세 필수 필드와 선택적 `sensor_profile`(`basic`/`extended`)만 허용한다. 필드 순서·바깥 공백·CRLF는 허용하고 누락·중복·알 수 없는 필드, 다른 버전·종류, 잘못된 JSON 구문과 UUID는 거부한다. Android가 생성하는 소문자 36자 UUID와 이스케이프 없는 ASCII 문자열을 사용한다. 범용 JSON 파서가 아니므로 `\u` 같은 문자열 이스케이프도 허용하지 않는다. LF 전 최대 255바이트(선택적 CR 포함)를 넘으면 오류를 한 번 반환하고 다음 LF까지 버린다. USB 수신이 여러 번으로 나뉘어도 버린 줄의 뒷부분을 새 요청으로 읽지 않는다. 유효한 요청 ID가 없을 때 오류 응답에는 예시의 대체 UUID가 들어간다.

온도와 습도는 `Adafruit_SHT31::readBoth()`로 한 번 변환한 동일 프레임에서 얻는다. 두 함수를 따로 호출해 서로 다른 변환 결과를 묶지 않는다. 읽기/CRC 실패 시 수치를 만들어내지 않고 기존 `null`·오류 규칙을 유지한다. 라이브러리 동작 근거: [Adafruit SHT31 2.2.2 소스](https://github.com/adafruit/Adafruit_SHT31/blob/2.2.2/Adafruit_SHT31.cpp).

SHT31은 `0x44`·`0x45`를 탐색한다. 주소 확인 직후 1ms 간격을 두어 다음 주소 탐색·드라이버 초기화를 바로 연속 실행하지 않는다. 시험한 UNO R4/core 1.6.0/공유 허브에서는 이 간격 없는 버전이 `0x45` 온습도 초기화에 실패했고 간격을 둔 버전은 정상값을 반환했다. 현재 광학 `0x39`·표면온도 `0x5A`도 확장 요청에서 실제 값을 반환한다. 광학 설정이 초기화되거나 읽기가 실패하면 다음 요청에서 재설정한다.

## 보드 없이 요청 처리 회귀시험

GCC/Clang이 있는 환경 또는 MSVC Developer Command Prompt에서 저장소 최상위의 `python scripts/check_firmware.py`를 실행한다. 실제 펌웨어의 `MeasureRequest.cpp`를 호스트용으로 빌드하고 실행하며 보드에 업로드하지 않는다. 필드 순서, 모든 두 조각 수신 경계, 잘못된 요청, 길이 상한과 USB 조각 사이의 초과 줄 폐기·복구를 검사한다. 센서·배선·Android USB 동작 시험은 별개다. Linux Python CI에서도 이 검사를 실행한다.

디바이스에서 epoch 시각을 만들어내지 않는다. uptime·boot·sequence를 보내고 앱이 실제 수신시각을 기록한다. soil_adc_bits는 analogReadResolution 설정과 같게 한다. soil_index는 근거 교정 전 null, 실측 실패는 null+error.

포트·권한·USB CDC 지원 라이브러리는 실제 기기로 시험한다. 숫자가 나온 것만으로 완료하지 않고 교정·반복성·분리/재연결·전원 변동·단위·오래된 측정 방지를 기록한다.

광학 확장은 기본 `readings`를 바꾸지 않고 명시적으로 요청한 `extensions`에 추가한다. 게인·적분시간·주변광·LED off·원시 채널·포화 상태를 보존한다. 기본+추가 센서의 실제 배선은 [HARDWARE](../docs/HARDWARE.md)를 따른다. LN-3 등 추가 광원을 필수 구매로 되돌리지 않는다. 납땜/센서 회로 제작 없음.

`python firmware/simulate_packet.py`는 **모의 JSONL 출력만** 한다. serial 장치나 실측 완료를 의미하지 않는다. 앱/서버의 mock 파서 시험에만 사용한다.
