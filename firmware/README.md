# 계측·펌웨어 — 최승빈·정회서

현재 실제 Arduino 스케치는 없다. 지원 보드 core와 센서 라이브러리·케이블·전압을 확인한 뒤 `uno_r4/visionmachine/visionmachine.ino`를 만든다. 이 폴더가 여러 보드를 뜻하지 않는다. 제어보드는 UNO R4 Minima 한 대다.

```text
uno_r4/visionmachine/
  visionmachine.ino       초기화·측정 요청/응답
  SensorReader.h/.cpp     SEN0308 A0·SEN0334 I2C 실측
  Calibration.h/.cpp      원시→보정, calibration_id
  UsbProtocol.h/.cpp      JSONL·request ID·sequence·error
calibration/              교정 절차/허용된 예제 코드
```

디바이스에서 epoch 시각을 만들어내지 않는다. uptime·boot·sequence를 보내고 앱이 실제 수신시각을 기록한다. soil_adc_bits는 analogReadResolution 설정과 같게 한다. soil_index는 근거 교정 전 null, 실측 실패는 null+error.

포트·권한·USB CDC 지원 라이브러리는 실제 기기로 시험한다. 숫자가 나온 것만으로 완료하지 않고 교정·반복성·분리/재연결·전원 변동·단위·오래된 측정 방지를 기록한다.

광학 확장은 v0.1 기본 계약에 임의 데이터를 끼워넣지 않는다. 센서·표면온도·광원/차광/게인·적분시간을 구분한 추가 계약과 반복시험부터 정한다. 기본+추가 센서의 실제 배선은 [HARDWARE](../docs/HARDWARE.md)를 따른다. LN-3 등 추가 광원을 필수 구매로 되돌리지 않는다. 납땜/센서 회로 제작 없음.

`python firmware/simulate_packet.py`는 **모의 JSONL 출력만** 한다. serial 장치나 실측 완료를 의미하지 않는다. 앱/서버의 mock 파서 시험에만 사용한다.
