# \[하드웨어/펌웨어 파트\] `uno_r4/visionmachine` 모듈 아키텍처 및 v0.1 규격 인계서

> 기본 센서만 포함했던 v0.1 당시 기록이다. 2026-11-13 v0.2.0 실측 확장과 실제 폴더 위치·실행법은 [현재 README](README.md)와 [휴대폰 인계 규격](../docs/ARDUINO_PHONE_HANDOFF.md)이 우선한다.

본 문서는 **Arduino UNO R4 Minima** 단일 제어 보드 기반의 `uno_r4/visionmachine/` 펌웨어 구조, **v0.1 데이터 계약(SensorPacket)** 준수 사항, 그리고 담당자별 향후 작업 방향을 공유하기 위해 작성되었습니다.

## 1. 개요 및 프로젝트 핵심 제약 조건

1. **단일 제어 보드 규격:**

   * 본 프로젝트의 하드웨어는 **Arduino UNO R4 Minima 1대**를 표준으로 사용합니다. (`uno_r4/` 디렉터리는 복수 보드를 의미하지 않음)

2. **v0.1 센서 범위 엄수:**

   * **SEN0308** (정전식 토양수분 센서, 아날로그 `A0` 핀 연결)

   * **SEN0334** (SHT31-F 온습도 센서, I2C 주소 `0x44` 또는 `0x45`)

   * *※ 광학 분광 센서(SEN0364) 및 적외선 표면온도 센서(SEN0206)는 v0.1 기본 패킷에 포함하지 않으며, 차광·게인·적분시간에 대한 추가 계약 정의 후 확장 단계에서 반영합니다.*

3. **요청/응답 방식 (Request-Response):**

   * 주기적 자동 송출 방식이 아닌, 호스트(Android 앱/PC)에서 JSONL 형식으로 `request_id`를 보낼 때만 **즉시 새로 측정한 1회 샘플**을 응답합니다. (오래된 캐시 데이터 사용 금지)

4. **디바이스 타임스탬프 금지:**

   * 디바이스에서 Epoch 시각을 임의로 생성하지 않습니다. 보드에서는 `boot_id`, `sequence`, `uptime_ms`만 전송하며, 실제 수신 시각은 호스트(앱)에서 기록합니다.

5. **결측 및 교정 처리 (`null` 및 `errors` 규격):**

   * `soil_adc_bits`는 펌웨어의 `analogReadResolution(12)` 설정값과 1:1로 동기화됩니다.

   * `calibration/` 절차를 통한 실측 근거 교정 전까지 `soil_index` 및 `calibration_id`는 `null`을 출력합니다.

   * 실측 실패 시 `0` 등의 더미 값을 보내지 않고, 해당 센서 리딩에 `null`을 부여하며 `errors` 배열에 에러 코드를 추가합니다.

6. **모의 출력 스크립트의 역할:**

   * `python firmware/simulate_packet.py`는 앱/서버 파서 검증 전용 모의 출력용입니다. 시리얼 장치 연결이나 하드웨어 실측 완료를 의미하지 않습니다.

## 2. 펌웨어 디렉터리 및 모듈별 역할

코드베이스는 역할 분리와 테스트 용이성을 위해 아래와 같이 7개 파일로 모듈화되어 작성되었습니다.

```
uno_r4/visionmachine/
├── visionmachine.ino       # 보드 초기화, USB CDC 루프, 요청/응답 제어
├── SensorReader.h          # 센서 계측 데이터 구조체 및 클래스 선언
├── SensorReader.cpp        # SEN0308(A0, 12-bit) 및 SEN0334(I2C) 실측 구현
├── Calibration.h           # 보정 데이터 구조체 및 클래스 선언
├── Calibration.cpp         # 원시값->보정값 변환 및 근거 교정 검증
├── UsbProtocol.h           # USB 시리얼 프로토콜 인터페이스 선언
└── UsbProtocol.cpp         # JSONL 파싱, 하드웨어 식별자 생성, SensorPacket 직렬화

```

### 모듈별 세부 설명

* **`visionmachine.ino`**

  * `115200 bps` 보드레이트로 USB CDC 시리얼을 초기화합니다.

  * 요청 수신 시 `SensorReader::readFresh()`를 호출하여 계측의 신선함(Freshness)을 보장합니다.

* **`SensorReader`**

  * `analogReadResolution(12)`를 호출해 ADC 해상도를 12-bit(0\~4095)로 고정합니다.

  * SHT31 센서 단선 후 재연결 시 I2C 버스를 자동 재초기화합니다.

* **`Calibration`**

  * `kEnableGroundedCalibration` 플래그가 `false`일 경우, `soil_index`를 임의로 계산하지 않고 `calibration_id: null`, `soil_index: null`을 반환합니다.

  * 교정 완료 시 수식 적용:
    

    $$
    soil\_index = \text{constrain}\left(\frac{dry\_raw - soil\_raw}{dry\_raw - wet\_raw},\; 0.0,\; 1.0\right)
    $$

* **`UsbProtocol`**

  * RA4M1 칩셋 고유 ID 기반의 `device_id`와 부팅 시점 엔트로피 기반의 `boot_id`를 자동 생성합니다.

  * Pydantic 모델 `SensorPacket` (`vm_contracts/models.py`) 스키마와 100% 일치하는 JSONL 패킷을 구성합니다.

## 3. v0.1 JSONL 통신 패킷 명세

### 3.1 요청 패킷 (Host $\rightarrow$ UNO R4 Minima)

* **포맷:** JSONL (개행 문자 `\n` 구분)

* **예시:**

  ```
  {"request_id": "11111111-1111-4111-8111-111111111111"}
  
  ```

### 3.2 응답 패킷 (UNO R4 Minima $\rightarrow$ Host)

#### 1) 정상 측정 응답 (근거 교정 적용 전)

```
{
  "schema_version": "0.1.0",
  "message_type": "measurement",
  "request_id": "11111111-1111-4111-8111-111111111111",
  "device_id": "uno-r4-3a9f10c2",
  "boot_id": "boot-004f8a12",
  "firmware_version": "uno-r4-0.1.0",
  "sequence": 0,
  "uptime_ms": 2410,
  "mode": "real",
  "calibration_id": null,
  "readings": {
    "soil_adc_bits": 12,
    "soil_raw": 1642,
    "soil_index": null,
    "air_temp_c": 24.15,
    "air_rh_pct": 53.40
  },
  "errors": []
}

```

#### 2) 센서 단선/계측 실패 응답 예시 (SHT31 분리 시)

```
{
  "schema_version": "0.1.0",
  "message_type": "measurement",
  "request_id": "11111111-1111-4111-8111-111111111111",
  "device_id": "uno-r4-3a9f10c2",
  "boot_id": "boot-004f8a12",
  "firmware_version": "uno-r4-0.1.0",
  "sequence": 1,
  "uptime_ms": 5120,
  "mode": "real",
  "calibration_id": null,
  "readings": {
    "soil_adc_bits": 12,
    "soil_raw": 1640,
    "soil_index": null,
    "air_temp_c": null,
    "air_rh_pct": null
  },
  "errors": [
    "sht31_disconnected"
  ]
}

```

## 4. 파트별 향후 작업 방향 및 검증 체크리스트

### 4.1 하드웨어 및 펌웨어 파트

1. **실기기 업로드 및 실측 검증:**

   * 실기기(UNO R4 Minima)에 `uno_r4/visionmachine/visionmachine.ino` 업로드 후 시리얼 모니터로 요청/응답 검증

2. **토양수분 센서 캘리브레이션 (`calibration/` 작업):**

   * 공기 중 건조 상태(Dry Reference ADC) 및 완전 침수 상태(Wet Reference ADC) 실측 데이터 수집

   * 측정된 상수를 `Calibration.cpp`의 `kGroundedDryAdc`, `kGroundedWetAdc`에 반영하고 `kEnableGroundedCalibration = true` 전환

3. **가상 환경 시험 및 기록 작성:**

   * 단순 수치 출력 확인에 그치지 않고, 아래 5개 항목 테스트 결과 기록 작성:

     * **반복성(Repeatability):** 동일 조건 연속 100회 요청 시 오차 범위

     * **분리 및 재연결(Disconnect/Reconnect):** SHT31 I2C 케이블 탈착 시 자동 복구 여부

     * **전원 변동(Power Fluctuation):** 5V 전원 변동 시 ADC 튐 현상 검증

     * **단위 및 해상도 검증:** 12-bit ADC 출력 범위(0\~4095) 정합성

     * **오래된 측정 방지 검증:** 요청 수신 직후 실측 수행 여부 (`uptime_ms` 변화 확인)

### 4.2 Android 앱 파트 전달 및 연동 사항

1. **DTR(Data Terminal Ready) 설정 필수:**

   * UNO R4 Minima는 Native USB CDC를 사용하므로, 스마트폰 App에서 USB 포트를 Open한 후 반드시 `port.setDTR(true)`를 실행해야 통신이 개시됩니다.

2. **JSONL 파싱 및 타임스탬프 기록:**

   * 앱은 요청 송신 시 UUID 형식의 `request_id`를 생성하여 전송해야 합니다.

   * 응답 패킷의 `uptime_ms`와 별개로, 앱이 응답을 최종 수신한 시점의 스마트폰 Epoch 타임스탬프를 DB에 함께 기록합니다.
