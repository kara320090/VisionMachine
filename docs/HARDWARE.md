# 한 대의 UNO에 연결하는 센서 구성

검토 기준: 2026-09-19 제조사 문서. 아래는 전압·주소·단자 규격상 가능한 배선이며 실물 조립, 휴대폰 USB 전원/통신 시험, 작물 진단 유효성 검증을 대신하지 않는다.

| 구성 | 연결 | 전원/주소 |
|---|---|---|
| UNO R4 Minima + DFR0265 | UNO에 확장판 장착 | 5V 보드, 외부 전원을 임의로 중복 연결하지 않음 |
| SEN0308 토양수분 | 확장판 A0/VCC/GND, 추가 GND선은 제조사 배선 준수 | 공급 3.3–5.5V, 출력 0–2.9V |
| DFR0759 | 확장판 I2C 단자에 Gravity 완성 케이블 | 전원/GND/SCL/SDA 분배, 주소 변환기 아님 |
| SEN0334 온습도 | 분배판 | 3.3–5.5V, 주소 0x44 또는 0x45. 프로그램 기본 0x45와 실제 설정을 대조 |
| SEN0364 광학 | 같은 분배판 | 3.3–5V, 주소 0x39 |
| SEN0206 표면온도 | 같은 분배판 | 3.3–5V, 기본 주소 0x5A |

세 I2C 센서의 주소는 중복되지 않는다. 센서는 각 1개를 연결하며 같은 모델을 추가할 때는 주소 충돌을 다시 검토한다. 완제품 Gravity 모듈·해당 연결 케이블을 사용한다. 헤더 없는 유사 breakout 제품으로 바꾸고 납땜을 요구하지 않는다. 공급품 버전·케이블 양 끝과 VCC/GND/SCL/SDA 순서를 주문/조립 전에 대조한다.

휴대폰은 USB host 역할로 UNO에 연결하고 앱이 USB 데이터와 사진을 묶어 서버로 전송한다. 무선통신은 휴대폰이 담당한다. UNO에 Wi-Fi 모듈이나 두 번째 제어보드를 추가하지 않는다. 센서 펌웨어와 Android USB 수신 코드는 개발해야 하며 케이블만 연결하면 앱 결과가 나오는 단계가 아니다.

## 구현/실물 확인 순서

1. 기본 센서의 원시 읽기와 I2C scan 결과를 기록한다. GPIO 출력 핀으로 센서 전원을 공급하지 않는다.
2. 세 I2C 센서를 한 bus에서 읽고 오류·결측을 구분한다. 펌웨어에서 bus 속도·재시도·측정 순서를 통일한다.
3. USB host 지원 기준 휴대폰에서 권한, 실제 수신, 전원 안정성, 분리/재연결을 시험한다.
4. 보정 전 soil_index는 null이다. 광학 게인·적분시간·조명·거리, 표면온도 측정 범위를 기록한다.
5. 토양 프로브는 흙에, 온습도 센서는 외기에, 광학/표면온도는 측정 대상에 노출한다. 모든 센서를 밀폐함 안에 넣지 않는다. 본체 케이스 치수와 센서 지지대는 실제 배치 후 확정한다.

전자저울·당도계·별도 유료 서버/저장소는 현재 필수 구매항목이 아니다. 서버의 DB/사진 저장 기능은 필요하며 로컬 PC 저장부터 개발할 수 있다. 추가 IR 광원을 검증된 필수품으로 간주하지 않는다. SEN0364의 내장 LED로 시작하되 근적외선 측정의 유효성이 확보됐다고 쓰지 않는다.

v0.1.0 USB/검사 계약은 기본 토양수분·온습도만 정의한다. 추가 센서를 실측으로 포함하기 전 계약의 확장 필드·단위·결측·측정조건을 합의하고 버전을 올리며 앱/서버/AI를 함께 갱신한다.

## 제조사 근거

- [UNO R4 Minima](https://docs.arduino.cc/hardware/uno-r4-minima/)
- [DFR0265](https://wiki.dfrobot.com/dfr0265/), [DFR0759](https://www.dfrobot.com/product-2179.html), [Gravity 케이블](https://www.dfrobot.com/product-1581.html)
- [SEN0308](https://wiki.dfrobot.com/sen0308/), [SEN0334](https://wiki.dfrobot.com/sen0334/), [SEN0364](https://wiki.dfrobot.com/sen0364/), [SEN0206](https://wiki.dfrobot.com/sen0206/)
- [I2C 주소 목록](https://github.com/DFRobot/I2C_Addresses), [MLX90614 기본 주소](https://github.com/DFRobot/DFRobot_MLX90614/blob/master/DFRobot_MLX90614.h)
- [Android USB host](https://developer.android.com/develop/connectivity/usb/host)
