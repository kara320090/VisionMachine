# Android RGB 사진 점검 시험 경로

2026-11-15 Play 내부 테스트로 배포한 0.5.0은 [바로 촬영·8장 추가/일괄·사진별 센서/종합 지수](ANDROID_PHOTO_SENSOR_INDEX.md)에 선택형 4090 서버 RGB 분석을 추가한다. 시스템 사진 선택기와 다중 파일 선택기를 제공한다. 아래는 현재에도 유지하는 기기 내 모델·전처리·가중치 기준이다. 새 종합 지수는 사용자 가중평균이며 학습된 센서 융합 결과가 아니다.

런처의 ‘사진 점검’에서 선택한 사진은 기본적으로 기기 내 ONNX Runtime CPU로 처리한다. 사용자가 ‘4090 서버 연결 설정’에 HTTPS/Tailscale 주소와 인증키를 저장하면 서버 모드로 전환해 실제 사진과 매칭된 센서 기록을 보낸다. 서버 결과는 기존 RGB 화면/이력으로 돌아오며, 설정된 서버가 실패하면 기기 결과로 자동 대체하지 않는다.

## 구현 범위

- 시스템 문서 선택기로 JPEG/PNG 최대 8장을 선택한다. 첫 사진 개별 분석과 선택 사진 일괄 분석을 제공한다. 사진을 바꾸면 현재 결과를 지우고 기존 누적 기록은 보존한다.
- PC 캡스톤 시연의 EfficientNet-B0 C_seed42 RGB 모델을 사용한다. 두 출력은 normal/abnormal이며 abnormal >= 0.5로 구분한다. 보정된 진단 확률, 병명·원인, USB 센서 결과를 생성하지 않는다.
- 모델의 학습 대상 범위는 바질·청경채·오이·케일·상추·고추·로즈마리·토마토다. 기존 촬영용 `crop_code` 목록을 바꾸지 않는다. 모델에는 작물 코드가 입력되지 않는다. 이 범위가 현장 정확도 검증 완료를 뜻하지 않는다.
- SHA-256, 원본 파일명, 두 출력값, 처리 시간, UTC 시각, 모델 버전을 최근 200건까지 앱 전용 저장소에 보관한다. CSV는 사용자가 고른 위치에 내보내며 수식으로 시작하는 파일명을 이스케이프한다. 사진 자체는 기록 파일에 복사하지 않는다.
- 파일 24MiB·2,400만 화소·한 변 16,384px·종횡비 40:1 이내를 허용한다. EXIF 8방향을 반영하고 PIL BICUBIC 256 짧은 변 리사이즈 → 중앙 224 크롭 → ImageNet 정규화를 재현한다. 중간 전체 크기 픽셀 배열이나 리사이즈 비트맵을 만들지 않고 필요한 행만 처리한다.

## 비공개 모델과 빌드

`apps/android/app/src/main/assets/vision_rgb_model.json`은 공개 모델 카드다. 가중치 `.onnx`와 실제 사진/시험 정답은 Git ignore 대상으로 유지한다. 승인된 비공개 모델을 가진 개발자만 다음으로 준비한다.

```powershell
python apps/android/tools/prepare_rgb_asset.py --model <private-onnx-path>
cd apps/android
./gradlew.bat :app:testDebugUnitTest :app:assembleDebug :app:lintDebug
```

SHA-256가 카드와 다르면 준비가 실패한다. 모델이 없는 디버그 빌드는 모델 오류를 표시하며 정상 결과를 만들지 않는다. 릴리스는 모델 파일이 없으면 빌드를 중단한다. 앱에서도 모델 파일 SHA-256를 확인한다. 서명 환경변수와 내부 테스트 배포 절차는 `PLAY_INTERNAL_TEST.md`를 따른다.

ONNX opset 17, ONNX Runtime Android 1.31.1, 원본 체크포인트 및 변환 모델의 해시는 모델 카드에 고정한다. 모델 변환은 PyTorch 2.14.1 CPU/torchvision 0.29.1, `torch.onnx.export(..., dynamo=False, opset_version=17)`, softmax 2출력으로 수행했다. 학습 가중치·임곗값은 변경하지 않았다.

## 시험 구분

`RgbPreprocessorTest`는 합성 패턴의 5개 크기(3000×4000 포함)를 Pillow로 계산한 픽셀 SHA-256와 비교한다. `LocalRgbEngineTest`와 `RgbViewModelTest`는 비공개 `androidTest/assets/private/`가 준비된 환경에서 실제 모델 8개 입력 비교, EXIF 8방향, 12MP 처리, 사진 변경 초기화, 일괄 처리, 기록·CSV를 시험한다. 비공개 사진은 시험 APK에만 포함하며 배포 APK에는 넣지 않는다. 공개 clone에 비공개 fixture가 없으면 해당 시험은 명시적으로 skip된다.

기존 보관 예시 사진의 변환·실행 일치 시험은 독립 성능 평가나 신규 재배환경 정확도가 아니다. 실제 Android 휴대전화의 촬영·권한·성능 시험은 에뮬레이터 시험과 별도로 확인해야 한다.
