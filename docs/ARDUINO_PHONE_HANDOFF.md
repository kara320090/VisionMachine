# UNO R4 휴대폰 연결 인계 — 펌웨어 v0.2.0

2026-11-13 현재 조립된 보드에서 PC USB로 확인한 아두이노 쪽 규격이다. 이 규격을 사용하는 Android 0.3.0의 구현·시험·휴대폰 연결 방법은 [ANDROID_USB](ANDROID_USB.md)에 있다.

## 연결과 요청

- 보드: UNO R4 Minima, 정품 runtime USB VID `2341` / PID `0069`, USB CDC ACM. 업로드용 DFU 인터페이스를 직렬 포트로 열지 않는다.
- 호스트 설정: 115200, 8 data bits, parity none, 1 stop bit, DTR=true, RTS=false. 1200 baud는 업로드 모드 진입에 쓰이므로 측정 연결에 사용하지 않는다.
- USB로 전원을 받으면 펌웨어가 시작한다. 호스트가 요청할 때만 응답하며 별도 시작 버튼이나 주기적 자동 출력은 없다.
- 요청: 이스케이프 없는 ASCII 문자열 필드, 소문자 36자 UUID, JSON 한 줄 + LF. CRLF도 허용한다. LF 전 255바이트 한도이며 초과 줄은 다음 LF까지 버린다.
- 권장 수신: UTF-8 JSONL을 USB 조각 사이에서 조립, 한 줄 최대 4096바이트, 요청 제한시간 12초, 한 번에 요청 하나. 현재 정상 응답은 약 0.2초지만 통신 오류 처리에는 더 오래 걸릴 수 있다.
- 사진과 묶는 경우 `request_id`는 현재 `inspection_id`와 같아야 한다. 이전 요청·연결 세션의 값을 새 측정으로 재사용하지 않는다. 호스트에서 실제 수신 시각을 기록한다.

기본 센서만 받는 기존 요청은 그대로 지원한다. `sensor_profile` 생략 또는 `basic`이면 응답에 `extensions` 키를 넣지 않는다.

```json
{"schema_version":"0.1.0","message_type":"measure","request_id":"11111111-1111-4111-8111-111111111111"}
```

장착한 센서 4종을 받는 요청:

```json
{"schema_version":"0.1.0","message_type":"measure","request_id":"11111111-1111-4111-8111-111111111111","sensor_profile":"extended"}
```

UUID는 형식 예시이며 새 검사에 새 UUID를 사용한다. 잘못된 요청은 기존 형식의 `null` 계측값과 오류로 응답한다.

## 응답 데이터

원본 규격은 `packages/contracts/src/vm_contracts/models.py`, 생성 규격은 `contracts/schemas/sensor-measure-request.schema.json`·`sensor-packet.schema.json`이다. 요청·응답 기본 버전은 0.1.0, 펌웨어 버전은 `uno-r4-0.2.0`, 추가 센서 묶음은 `extensions.schema_version=0.1.0`이다.

| 위치 | 내용과 단위 |
|---|---|
| `readings.soil_raw` | SEN0308의 A0 12-bit ADC 정수. 프로브 연결 확인이나 수분 %를 의미하지 않는다. |
| `readings.soil_index`, `calibration_id` | 실제 건조·습윤 기준 교정 전 `null`. 계수를 만들어 넣지 않는다. |
| `readings.air_temp_c`, `air_rh_pct` | SEN0334의 같은 변환 프레임에서 읽은 °C·상대습도 %. 현재 실물 주소 0x45, 0x44도 탐색. |
| `extensions.optical` | SEN0364/AS7341, 주소 0x39. 원시 ADC 채널 12개와 아래 측정조건. |
| `extensions.surface_temperature` | SEN0206/MLX90614, 주소 0x5A. 대상·센서 자체 온도 °C, 원시 레지스터, 실제 읽은 방사율과 PEC 검사 여부. |
| `errors` | 실패 사유·광학 포화 경고. 실패한 센서는 `null`, 정상인 다른 센서는 유지. |

광학 채널 배열 순서는 `F1,F2,F3,F4,CLEAR_1,NIR_1,F5,F6,F7,F8,CLEAR_2,NIR_2`다. **두 번의 순차 노출**이며 CLEAR/NIR 두 값을 임의 평균하거나 동시에 촬영한 값으로 쓰지 않는다. 현재 설정은 gain 16×, ATIME 29, ASTEP 599, 노출당 50.04ms, LED off·주변광이다. 각 SMUX 설정 쓰기·읽기 확인과 데이터 블록 읽기를 검사하고 무한 대기를 사용하지 않는다. 포화 원시값은 보존하면서 `saturated=true`·`as7341_saturated`로 표시한다. 물리 보정된 광량·당도·병해 판정으로 바꾸지 않는다.

MLX90614는 SMBus word의 PEC CRC-8을 검사하고 원시값의 오류 비트를 거부한다. `object_temp_c`는 대상 온도, `ambient_temp_c`는 MLX 센서 자체 온도이며 SHT31의 외기 온습도와 다른 값이다. 방사율은 EEPROM에서 읽으며 쓰거나 임의 변경하지 않는다. 요청 시 RAM의 최신 센서 값을 읽고 소프트웨어의 지난 응답을 재사용하지 않는다. 이 센서의 내부 변환을 요청이 새로 트리거한다는 뜻은 아니다.

`uptime_ms`·각 추가 센서의 uptime은 부팅 이후 상대 시각이다. 실제 날짜가 아니며, 광학 시작·종료 시각과 표면온도 레지스터 읽기 시각을 구분한다.

대표 오류: `sht31_disconnected`, `sht31_read_failed`, `as7341_disconnected`, `as7341_init_failed`, `as7341_read_failed`, `as7341_saturated`, `mlx90614_disconnected`, `mlx90614_read_or_pec_failed`, `mlx90614_invalid_reading`. 계측 오류를 작물 이상 판정으로 표시하지 않는다.

## PC 재확인과 휴대폰에서 이어 할 시험

```powershell
# Windows, 저장소 최상위. 실제 포트로 바꾼다.
./firmware/Measure-UsbSensors.ps1 -Port COM9 -Profile extended -Count 3
./firmware/Measure-UsbSensors.ps1 -Port COM9 -Profile basic -Count 1
```

실제 로그는 Git에 올리지 않는다. PC 시험 후 보드를 휴대폰 USB-C 데이터 연결로 옮겨도 펌웨어는 보드에 남아 있다. Android 0.3.0은 USB 권한·CDC 연결과 기본/확장 응답 검사를 구현했다. 실제 휴대폰의 전원·통신 통과 여부는 기기 시험으로 구분한다.

휴대폰 단계에서 확인할 내용: USB 권한 승인·취소, 측정 요청/응답, USB 분리·재연결, 같은 검사에 사진·측정 연결, 밝고 어두운 조건의 광학 변화, 대상에 따른 표면온도 변화, 건조/습윤 토양 반응. 이번 PC 시험은 이 실물 조작·휴대폰 전원/통신 시험과 토양 교정을 대신하지 않는다.

근거: [Adafruit AS7341 1.4.1](https://github.com/adafruit/Adafruit_AS7341/tree/1.4.1), [AS7341 데이터시트](https://look.ams-osram.com/m/24266a3e584de4db/original/AS7341-DS000504.pdf), [Melexis MLX90614 데이터시트](https://www.melexis.com/-/media/files/documents/datasheets/mlx90614-datasheet-melexis.pdf).
