# Android 사진·센서와 4090 서버

2026-11-14: 기존 RGB 화면의 개별/최대 8장 순차 처리에서 선택할 수 있는 서버 경로를 추가했다.
원본 ZIP 서버는 시작점으로 검토했으며 실제 구현은 이 저장소의 `vm_server`에 통합했다.
기존 `/v1/inspections` 로컬 개발 API와 센서 점수 규칙은 유지한다.

기존 C_seed42 체크포인트에서 ONNX를 복원했고 모델 카드의 SHA-256과 정확히 일치했다.
새 학습·다른 모델·카드 해시 변경은 없다. 실제 CUDA 추론과 앱 에뮬레이터의 8장 성공 결과를 확인했다.
원본 PyTorch CPU와 ONNX CUDA의 합성 RGB 8개 출력 최대 차이는 0.000003934였다.
실휴대폰/Tailscale 접속과 새 재배환경 정확도 평가는 이 확인에 포함하지 않는다.

## 확인한 앱·모델 계약

- `AnalysisActivity`의 TakePicture·갤러리·다중 파일 선택, 사진별 상태와 실패 후 다음 사진 처리를 사용한다.
- `RgbRecord`의 normal/abnormal과 abnormal >= 0.5 표시, 200건 이력과 CSV를 유지한다.
- `RgbPreprocessor`/`LocalRgbEngine`/`vision_rgb_model.json`이 근거다. EXIF 방향 → RGB → Pillow BICUBIC 짧은 변 256 → 중앙 224(ties-to-even) → float32 /255 → ImageNet mean/std → NCHW `[1,3,224,224]`다.
- 실제 ONNX 세션은 float32 `image [1,3,224,224]` 하나와 `probabilities [1,2]` 출력이며 normal/abnormal 순서다. 센서 입력은 없다.
- 모델 SHA-256: `ffa909c3453a9d1e2f4c601292748f6cb30cb3e4507921cd42578410f7d15629`.
- 모델에 센서·작물 텐서를 임의로 추가하지 않는다. `tomato`, `cherry_tomato`, `kale` 등 사진 화면의 기록 코드를 유지하며 기존 촬영 계약의 8개 코드를 바꾸지 않는다. 가지는 기존 화면과 동일하게 RGB 적용 범위 밖이다.
- 파일 한도는 RGB 앱과 같은 24MiB, 24Mpixel, 최대 한 변 16,384, 종횡비 40이다. 원본 EXIF·파일 해시를 보존하여 저장한다.

## 센서 점수 보존

센서 패킷은 기존 SensorPacket 계약을 검증한다. `soil_raw`는 ADC 원시값과 `soil_adc_bits`,
`soil_index`는 교정 ID가 있는 0~1 지수이며 보정 수분 %가 아니다. `air_temp_c`는 °C,
`air_rh_pct`는 %, AS7341은 정해진 순서의 12개 원시 카운트와 노출/게인/포화 정보,
MLX90614는 raw 및 대상/자체 온도 °C와 방사율·PEC 확인을 전송한다.

사진 참조 ID·작물·사진 SHA-256가 모두 일치하는 SensorStore 기록만 보낸다.
USB 측정 ID와 사진 ID는 서로 다른 ID로 보존한다. 결측은 null이고 갤러리 촬영시각은 미상으로 보낸다.
서버는 앱의 `assessment_json`을 원문 스냅샷으로 보관하고 점수를 다시 계산하지 않는다.
`SensorScoring.kt`와 `CompositeIndex.kt`의 식·결측/포화/mock 보류·가중치는 변경하지 않았다.
서버의 RGB 결과만 기존 `CompositeIndex.attach`에 연결한다.

## API와 재시도

`POST /api/v1/inspections`: `X-API-Key`, multipart `payload` JSON과 `photos` 1~8개다.
JSON 원본은 `packages/contracts/src/vm_contracts/models.py`의 RgbInspectionRequest/Result,
생성 규격은 `contracts/schemas/rgb-inspection*.schema.json`과 OpenAPI다.
파일 순서와 payload.photos 순서가 일치해야 하며 각 원본 해시를 검증한다.

Android는 기존 진행/개별 실패 표시를 보존하기 위해 최대 8장을 한 장씩 순차 요청한다.
서버 API 자체도 한 요청의 1~8장을 지원한다. 파일/센서 스냅샷으로 만든 안정된 검사 ID로 수동 재시도한다.
같은 ID·내용은 저장된 응답(200), 처음은 201, 같은 ID의 다른 내용은 409다.
GPU의 일시적 추론 오류는 완료 결과로 캐시하지 않고 503을 반환한다. 서버 중복 GPU 실행은 한 worker의 lock으로 직렬화한다.
연결 제한 10초·응답 제한 180초이며 redirect는 따라가지 않아 자격 증명을 다른 주소에 보내지 않는다.
기기 모델로 자동 전환하지 않는다. 결과 이력·CSV에 실행 공급자와 서버 검사 ID를 보존한다.

SQLite는 `storage/rgb_inspections.sqlite3`, 원본/메타데이터는 `storage/rgb_uploads/`에 저장한다.
기존 개발 DB와 분리하며 기존 기록을 삭제하지 않는다. 강제 종료로 남은 orphan 파일 자동 정리는 후속이다.

## Ubuntu 설치와 실행

Python 3.12의 venv를 사용한다. 시스템 NVIDIA 드라이버를 변경하지 않는다.
`server/gpu-requirements.lock.txt`는 확인한 Linux 조합이다(ORT 1.23.2, CUDA runtime 12.9, cuDNN 9).
드라이버는 이 CUDA 버전을 지원해야 한다. nvidia-smi의 CUDA 표시는 설치된 toolkit 버전과 구분한다.
[ORT 공식 호환표](https://onnxruntime.ai/docs/execution-providers/CUDA-ExecutionProvider.html)를 확인한다.

```bash
bash server/install_gpu_ubuntu.sh
# .env에 VM_HOST=<이 PC의 Tailscale IP>, VM_API_KEY=<로컬 생성 키> 설정
.venv/bin/python scripts/check_gpu_runtime.py
.venv/bin/python scripts/run_gpu_server.py
```

모델 기본 경로는 `apps/android/app/src/main/assets/vision_rgb_cseed42.onnx`다.
서버만 다른 비공개 경로를 쓰려면 VM_RGB_MODEL_PATH를 설정한다. 모델·비밀키는 커밋하지 않는다.
파일이 없거나 해시/입출력이 다르거나 CUDA 세션을 만들지 못하면 `/health/ready`와 추론은 503이다.
다른 모델이나 임의 점수를 반환하지 않는다.

ONNX가 빠진 새 clone에서는 등록된 체크포인트로 `scripts/restore_rgb_model.py`를 실행해 복원할 수 있다.
검증한 변환 환경은 PyTorch 2.14.1+cpu / torchvision 0.29.1+cpu / onnx 1.23.2다.
스크립트는 원본 체크포인트 SHA를 먼저 확인하고 ONNX SHA까지 기존 카드와 같을 때만 저장한다.
동결된 학습 코드·체크포인트는 읽기만 한다. 변환 출처는 `server/models/export-provenance.json`에 기록했다.

실제 모델 파일을 확보한 뒤 다음으로 실제 추론과 CUDA 노드 프로파일을 확인한다.

```bash
.venv/bin/python scripts/verify_rgb_model.py --synthetic-probe --report storage/model-verification.json
# 실제 재배환경 정확도를 뜻하지 않는 합성 입력 실행 검사다.
```

## 휴대폰 접속과 자격 증명

사진 화면의 ‘4090 서버 연결 설정’에서 같은 tailnet의 서버 주소와 기기용 키를 실행 중 입력한다.
키는 Android Keystore AES-GCM으로 암호화해 저장하며 APK/BuildConfig에 고정하지 않는다.
공개 앱 배포용 사용자 로그인·만료/폐기 가능한 토큰·소유자별 권한은 별도 작업이다.

이 기기의 Tailscale HTTP 예외는 `100.74.204.80` 호스트에만 두며 다른 cleartext 호스트는 허용하지 않는다.
debug만 기존 loopback과 에뮬레이터 호스트 주소를 추가 허용한다. HTTPS URL은 시스템 CA 검증을 사용한다.
서버는 loopback 또는 Tailscale IP에만 실행하며 전체 인터페이스 바인딩을 허용하지 않는다.
Tailscale HTTP는 해당 VPN 터널이 필수다. 공개 인터넷에 HTTP 포트를 열지 않는다.
HTTPS/Tailscale Serve 또는 다른 기기 주소를 적용할 때 서버 바인딩과 Android 호스트 정책을 함께 확인한다.

## 검증 구분

서버 테스트의 TransportStub은 합성 프로토콜 시험용이며 실행 서버에 설치되는 모델이 아니다.
전처리는 기존 Android 픽셀 해시와 비교한다. `ServerRgbTest`는 응답/해시 검증과 암호화 저장을 검사한다.
실제 서버 계측시험은 vm_test_server_url/key 인자를 명시했을 때만 수행하며, 모델 미탑재의 8장 503 응답과
실제 모델을 쓴 성공 결과를 구분한다. 장치·서버 모델이 없을 때 완료된 추론이나 휴대폰 시험으로 보고하지 않는다.
사용자가 요청한 대화형 에뮬레이터 실행에서는 `vm_keep_server_config=true`를 명시해 연결 설정을
기기에 암호화해 유지할 수 있다. 이후 일반 앱을 실행하면 저장한 백엔드로 연결한다. 기본 시험은 원래 설정을 복구한다.
