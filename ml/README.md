# AI — 한윤섭·최승빈

현재 vm_ml/interface.py에는 Predictor 인터페이스와 pending_result만 있다. 실제 모델·학습·성능은 없다.

예정 구조:
```text
src/vm_ml/
  preprocessing.py         이미지/센서 전처리, 추론과 학습 공유
  datasets.py              검증된 manifest 읽기
  train_rgb.py             사전학습 CNN 기반 첫 RGB 모델
  train_sensor.py          규칙 기준선과 센서 단독 학습
  train_fusion.py          실제 사진-센서 짝자료만 사용
  evaluate.py              고정 split·공통 지표·오류 분석
  predictors/              모델 로딩·버전·입출력 변환
configs/                   재현 설정
model_cards/               모델별 범위·한계·전처리·출처
```

1. 공개자료 실제 확보·라벨 검토 후 RGB 기준선부터 학습한다.
2. 자체 짝자료가 준비되면 RGB·센서·융합을 같은 분할에서 비교한다. train으로 학습하고 val로 모델·특징·임곗값을 결정한다. test는 12주차 고정 후 13주차 독립평가에서 세 모델에 동일하게 적용하며 개선에 반복 사용하지 않는다. 공개 RGB 사전학습 자료를 썼다면 별도 명시한다.
3. 센서 스케일러·결측 처리·특징 선택은 train에서만 fit한다. calibration은 문서화된 물리 측정 절차로 관리하고 평가자료 라벨을 보며 튜닝하지 않는다.
4. 모델 파일은 artifacts/models/에 두고 Git에는 설정·모델 카드·전처리 코드·재현 명령·데이터/분할/가중치 해시를 기록한다.
5. 정확도 외에 작물별 혼동행렬·오경보·미탐·보류율·모델별 동일 표본 수를 보고한다. 표본이 적으면 불확실성과 그룹 수를 함께 적는다.

`uncertain` 라벨은 정답 미확정 기록이다. 별도 합의 없이 정상·이상 정답으로 바꾸거나 진단 정확도의 분모에 섞지 않는다. 모델의 `inconclusive`는 출력 보류이며 라벨의 `uncertain`과 의미가 다르다. 보류율·평가 제외 기준을 고정 전에 명시한다.

질병 확정·식품 안전·광학 수치의 내부 영상 해석은 범위 밖이다. 가중치 없는 inference에서 임의 클래스를 반환하지 않는다. PyTorch/scikit-learn은 구현 후보이며 설치·GPU 호환 버전은 실제 학습 환경에서 정한다.
