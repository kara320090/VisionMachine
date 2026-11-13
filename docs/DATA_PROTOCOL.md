# 사진·센서·모델 데이터 규격

## 검사와 대상
`inspection_id`: 앱이 새 검사마다 UUID 생성, 업로드 재시도에도 유지. 같은 개체를 다시 검사하면 새 ID. `subject_id`는 개체/과실 ID, `subject_type`은 plant/fruit, 과실의 원식물을 아는 경우 `parent_plant_id`. 모르는 연결을 창작하지 않는다. `batch_id`는 구매/수확/수집 묶음 ID다.

crop_code: cherry_tomato, pepper, cucumber, lettuce, bok_choy, eggplant, basil, rosemary. 앱의 기록 가능 작물 목록이며 검증된 진단 범위는 별도 capabilities로 반환한다.

`captured_at`와 `sensor_received_at`은 시간대 있는 ISO 8601, 서버 저장은 UTC로 정규화. UNO uptime을 날짜로 해석하지 않는다. 사진·센서 시간 간격의 허용 기준은 측정 절차에서 실험 후 정한다. 앱은 현재 요청과 다른 응답, 이전 boot/연결 세션, 오래된 값을 재사용하지 않는다.

## USB 규격
USB CDC serial, 115200/8N1/DTR=true, UTF-8 JSON 한 줄 + LF(JSONL). 줄이 여러 USB read로 나뉘거나 한 read에 여러 줄이 와도 조립한다. 호스트 수신 한도 4096바이트, 보드 요청 한도 LF 전 255바이트다. v0.2.0 기본·광학/표면온도 확장은 [ARDUINO_PHONE_HANDOFF](ARDUINO_PHONE_HANDOFF.md)를 따른다.

앱 측정 요청 예:
```json
{"schema_version":"0.1.0","message_type":"measure","request_id":"11111111-1111-4111-8111-111111111111"}
```
요청 ID는 현재 inspection_id와 동일하게 한다. 요청 원본은 `SensorMeasureRequest`, 응답은 `SensorPacket`이다. 생략 또는 `basic` 프로필은 기존 토양·온습도 응답, `sensor_profile=extended`는 버전이 있는 `extensions`를 추가한다. 장치·boot·sequence·uptime·firmware·mode·교정 ID·오류를 보존한다. 측정 실패는 null+오류코드이며 0이 아니다. 디버그 문자열을 섞지 않으며 한 번에 한 요청, 호스트 제한시간 12초를 사용한다. 실제 휴대폰 연결 세션·재시도 처리는 앱 단계에서 시험한다.

## 단위
- soil_raw: 실제 ADC 정수. soil_adc_bits는 실제 사용한 해상도 10/12/14. 기본값을 실측처럼 추정하지 않는다.
- soil_index: 0~1 교정 지수. calibration_id 없으면 null. 절대 체적수분함량 %가 아니다.
- air_temp_c: 섭씨, air_rh_pct: 상대습도 %. 유효하지 않으면 null+오류.
- 광학·표면온도는 기본 `readings`를 유지하고 명시된 선택적 `extensions`로 확장한다. 게인·노출 설정·광원 상태·원시 채널·포화, 표면온도 원시 레지스터·실제 방사율·PEC 여부를 보존한다. 알 수 없는 필드는 계속 extra=forbid로 거부한다. 확장 없는 모델을 직렬화할 때는 `extensions` 키를 생략한다.

## 모의와 모델
사진 capture_source=synthetic 또는 sensor mode=mock이면 is_mock 입력이다. 결과 warnings에 MOCK_DATA를 유지하고 앱 배지를 지우지 않는다. 테스트 데이터는 실제 학습/최종평가에서 제외한다.

모델 미탑재: status=pending_model, origin=none, outcome/confidence/model_version/model_mode=null, 원인·근거 목록 비움. 이것을 ‘정상’으로 표시하지 않는다.

완료된 실모델 결과만 origin=real_model + 모델 버전·모드(rgb/sensor/fusion)를 사용한다. outcome은 no_visible_abnormality/suspected_abnormality/inconclusive. confidence는 보정/해석 방법이 없으면 null로 둔다. 센서 누락 시 RGB fallback은 검증된 RGB 모델이 있을 때만 사용하며 모드를 명시한다.

데이터 품질·신호 조건·미지원 작물로 인한 inconclusive와 네트워크/서버 실패를 다른 상태로 표시한다.
