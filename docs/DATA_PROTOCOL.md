# 사진·센서·모델 데이터 규격

## 검사와 대상
`inspection_id`: 앱이 새 검사마다 UUID 생성, 업로드 재시도에도 유지. 같은 개체를 다시 검사하면 새 ID. `subject_id`는 개체/과실 ID, `subject_type`은 plant/fruit, 과실의 원식물을 아는 경우 `parent_plant_id`. 모르는 연결을 창작하지 않는다. `batch_id`는 구매/수확/수집 묶음 ID다.

crop_code: cherry_tomato, pepper, perilla, lettuce, bok_choy, kale, basil, rosemary. 앱의 기록 가능 작물 목록이며 검증된 진단 범위는 별도 capabilities로 반환한다.

`captured_at`와 `sensor_received_at`은 시간대 있는 ISO 8601, 서버 저장은 UTC로 정규화. UNO uptime을 날짜로 해석하지 않는다. 사진·센서 시간 간격의 허용 기준은 측정 절차에서 실험 후 정한다. 앱은 현재 요청과 다른 응답, 이전 boot/연결 세션, 오래된 값을 재사용하지 않는다.

## USB 초안
USB CDC serial, UTF-8 JSON 한 줄 + LF(JSONL). 115200은 초기 serial 설정 제안으로 실기기 확인 후 고정한다. 줄이 여러 USB read로 나뉘거나 한 read에 여러 줄이 와도 조립한다. 4096바이트 한 줄 상한은 초기 소프트웨어 보호 설정이며 광학 확장 전 재검토한다.

앱 측정 요청 예:
```json
{"schema_version":"0.1.0","message_type":"measure","request_id":"11111111-1111-4111-8111-111111111111"}
```
요청 ID는 현재 inspection_id와 동일하게 한다. 응답은 sensor-packet.schema.json 및 sensor.mock.json 형식. 장치·boot·sequence·uptime·firmware·mode·교정 ID·오류를 보존한다. 측정 실패는 null+오류코드이며 0이 아니다. protocol에 디버그 로그 문자열을 섞지 않는다. 요청 스키마/timeout·재전송·연결 세션 처리는 펌웨어·앱 첫 구현에서 명시적으로 확정한다.

## 단위
- soil_raw: 실제 ADC 정수. soil_adc_bits는 실제 사용한 해상도 10/12/14. 기본값을 실측처럼 추정하지 않는다.
- soil_index: 0~1 교정 지수. calibration_id 없으면 null. 절대 체적수분함량 %가 아니다.
- air_temp_c: 섭씨, air_rh_pct: 상대습도 %. 유효하지 않으면 null+오류.
- v0.1은 기본 센서 계약. 광학·표면온도는 검증 후 명시된 추가 스키마로 확장하고 gain/integration/광원상태/원시채널/교정 정보를 포함한다. 임의 필드 추가는 현재 extra=forbid로 거부한다.

## 모의와 모델
사진 capture_source=synthetic 또는 sensor mode=mock이면 is_mock 입력이다. 결과 warnings에 MOCK_DATA를 유지하고 앱 배지를 지우지 않는다. 테스트 데이터는 실제 학습/최종평가에서 제외한다.

모델 미탑재: status=pending_model, origin=none, outcome/confidence/model_version/model_mode=null, 원인·근거 목록 비움. 이것을 ‘정상’으로 표시하지 않는다.

완료된 실모델 결과만 origin=real_model + 모델 버전·모드(rgb/sensor/fusion)를 사용한다. outcome은 no_visible_abnormality/suspected_abnormality/inconclusive. confidence는 보정/해석 방법이 없으면 null로 둔다. 센서 누락 시 RGB fallback은 검증된 RGB 모델이 있을 때만 사용하며 모드를 명시한다.

데이터 품질·신호 조건·미지원 작물로 인한 inconclusive와 네트워크/서버 실패를 다른 상태로 표시한다.
