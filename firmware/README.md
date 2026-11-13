# 계측·펌웨어 — 최승빈·정회서

UNO R4 Minima 한 대에서 SEN0308 A0 원시값과 SEN0334 SHT31 온습도를 읽는 코드가 있다. `firmware.ino`는 Arduino가 요구하는 시작 파일이며, 실제 `setup()`·`loop()`는 기존 `visionmachine.ino.cpp`에 있다. Arduino IDE에서는 `firmware/firmware.ino`를 연다.

```text
firmware/
  firmware.ino           Arduino 스케치 시작 파일
  visionmachine.ino.cpp  초기화·측정 요청/응답
  SensorReader.h/.cpp     SEN0308 A0·SEN0334 I2C 실측
  Calibration.h/.cpp      원시→보정, calibration_id
  UsbProtocol.h/.cpp      JSONL·request ID·sequence·error
calibration/              교정 절차/허용된 예제 코드
```

## PC에서 빌드·업로드

2026-11-13 Windows에서 Arduino CLI 1.6.0, `arduino:renesas_uno` 1.6.0, Adafruit SHT31 Library 2.2.2, Adafruit BusIO 1.17.4로 빌드하고 UNO R4 Minima에 업로드했다. USB 직렬 요청·응답을 확인했으며 이 확인이 센서 보정·Android 앱 연결 완료를 뜻하지 않는다. 실제 측정 로그와 장치 식별자는 공개 저장소 밖에 보관한다.

저장소 최상위 폴더에서 실행한다. `COM3`는 예시이며 `board list`에 표시된 실제 UNO R4 Minima 포트로 바꾼다.

```powershell
arduino-cli core install arduino:renesas_uno@1.6.0
arduino-cli lib install "Adafruit SHT31 Library@2.2.2" "Adafruit BusIO@1.17.4"
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

위 UUID는 요청 형식 예시다. 응답은 `mode: real`이며, SHT31 연결·읽기 실패 시 온습도는 `null`과 오류 코드로 반환한다. 토양 ADC 숫자만으로 프로브 연결·보정의 타당성을 판정하지 않는다. AS7341 광학·MLX90614 표면온도 읽기는 이 기본 펌웨어에 포함되지 않는다. 현재 Android의 패킷 파서는 직렬 포트를 여는 기능과 별개이며 앱의 실제 USB 연결도 별도로 구현해야 한다.

디바이스에서 epoch 시각을 만들어내지 않는다. uptime·boot·sequence를 보내고 앱이 실제 수신시각을 기록한다. soil_adc_bits는 analogReadResolution 설정과 같게 한다. soil_index는 근거 교정 전 null, 실측 실패는 null+error.

포트·권한·USB CDC 지원 라이브러리는 실제 기기로 시험한다. 숫자가 나온 것만으로 완료하지 않고 교정·반복성·분리/재연결·전원 변동·단위·오래된 측정 방지를 기록한다.

광학 확장은 v0.1 기본 계약에 임의 데이터를 끼워넣지 않는다. 센서·표면온도·광원/차광/게인·적분시간을 구분한 추가 계약과 반복시험부터 정한다. 기본+추가 센서의 실제 배선은 [HARDWARE](../docs/HARDWARE.md)를 따른다. LN-3 등 추가 광원을 필수 구매로 되돌리지 않는다. 납땜/센서 회로 제작 없음.

`python firmware/simulate_packet.py`는 **모의 JSONL 출력만** 한다. serial 장치나 실측 완료를 의미하지 않는다. 앱/서버의 mock 파서 시험에만 사용한다.
