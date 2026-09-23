# 공개 식물 이상 이미지 자료 검토

확인일: 2026-09-23

## 결론

케일과 깻잎을 대신할 1순위 후보는 **가지와 오이**다. 두 작물은 같은 공개자료에서 정상(신선)·병해 잎 이미지가 함께 제공되고, Mendeley Data 상세 페이지의 `Download All`로 한 번에 받을 수 있다. 해당 자료는 CC BY 4.0이며 가지 2,944장, 오이 2,159장을 명시한다.

이 변경은 아직 팀의 최종 작물 변경 결정이 아니다. 결정 전까지 학교 계획서와 `docs/PROJECT_SCOPE.md`의 후보 8종은 유지한다.

## 추천 자료

| 우선순위 | 자료 | 쓸 수 있는 작물·용도 | 규모·라벨 | 내려받기 | 라이선스·주의 |
|---|---|---|---|---|---|
| 1 | PlantVillage | 토마토, 피망, 감자, 딸기 등 RGB 기본 학습 | 전체 54,306장, 14개 작물, 26개 병해. 정상·병해 폴더 라벨 | [공식 GitHub](https://github.com/spMohanty/PlantVillage-Dataset) 또는 [Hugging Face](https://huggingface.co/datasets/mohanty/PlantVillage) | Hugging Face 카드: CC BY-SA 3.0. 배경이 단순한 잎 사진이므로 현장 성능으로 해석하지 않는다. |
| 2 | Plant Leaf Freshness and Disease Detection Dataset From Bangladesh | **가지·오이 대체 후보**, 토마토·콜리플라워·여주·박 포함 | 가지 2,944장, 오이 2,159장, 토마토 2,449장, 콜리플라워 1,598장 등. fresh/diseased | [Mendeley Data 상세 페이지](https://data.mendeley.com/datasets/n67gctmjyj/2)의 `Download All` | CC BY 4.0. 폴더명과 실제 이미지 수를 받은 뒤 다시 검사한다. |
| 3 | PlantDoc 분류 자료 | 토마토·피망·감자·딸기 등 실제 배경 보강·독립시험 | 전체 2,598장, 13개 작물, 최대 17개 병해 | [분류용 공식 GitHub](https://github.com/pratikkayal/PlantDoc-Dataset) | CC BY 4.0. 인터넷 수집 이미지이므로 중복·출처 편향을 검사한다. |
| 4 | PlantDoc 객체탐지 자료 | 병해 잎 위치 표시 실험 | RGB와 경계상자, train/test CSV | [객체탐지용 공식 GitHub](https://github.com/pratikkayal/PlantDoc-Object-Detection-Dataset) | CC BY 4.0. 분류 모델만 만들 때는 3번이 더 간단하다. |
| 보조 | A Database of Leaf Images | 바질 정상/병해 후보 검토 | 12개 식물, 전체 4,503장, 정상 2,278장·병해 2,225장 | [Mendeley Data 상세 페이지](https://data.mendeley.com/datasets/hb74ynkjcn/5) | CC BY 4.0. 바질별 표본 수와 클래스 폴더를 내려받은 뒤 확인해야 한다. |

## 후보 8종에 적용하는 안

현재 후보 중 케일·깻잎만 바꾸는 최소 변경안은 다음과 같다.

| 현재 | 변경 제안 | 이유 |
|---|---|---|
| 케일 | 가지 | 정상·병해 2,944장이 한 공개자료에 있고 단일 페이지에서 일괄 다운로드 가능 |
| 깻잎 | 오이 | 정상·병해 2,159장이 같은 형식으로 제공되어 가지와 전처리 절차를 공유 가능 |

대안 순서는 콜리플라워, 감자, 딸기다. 콜리플라워는 같은 Mendeley 자료에 1,598장이 있으며, 감자와 딸기는 PlantVillage와 PlantDoc에 모두 등장한다. 실제 화분 시연용 식물과 학습 후보 8종은 구분한다. 공개 이미지만 확보한 작물을 실제 센서 융합 성능까지 검증했다고 쓰지 않는다.

## 가장 쉬운 내려받기

원본 이미지는 공개 Git 저장소에 커밋하지 않고, 이 저장소의 무시 대상인 `data/raw/` 아래에 둔다.

```powershell
# PlantVillage 전체 복제
git clone --depth 1 https://github.com/spMohanty/PlantVillage-Dataset.git data/raw/plantvillage

# PlantDoc 분류 자료 전체 복제
git clone --depth 1 https://github.com/pratikkayal/PlantDoc-Dataset.git data/raw/plantdoc-classification
```

PlantVillage는 공식 저장소가 안내하는 Hugging Face 방식도 사용할 수 있다.

```python
from datasets import load_dataset

dataset = load_dataset("mohanty/PlantVillage", "color")
```

가지·오이 자료는 Mendeley Data 상세 페이지에서 `Download All`을 누른 뒤 압축을 `data/raw/mendeley_leaf_freshness/`에 푼다. 다운로드 파일명과 해시는 `data/catalog/`에 별도로 기록한다.

## 학습·평가 적용 규칙

- 공개자료는 RGB 사전학습·기본 모델 후보에 사용한다. 공개 사진에 센서값을 임의로 붙이지 않는다.
- 정상 폴더는 `healthy`, 병해·손상 폴더는 `suspected_abnormal`로 먼저 통합할 수 있다. 세부 병명은 충분한 라벨 검토가 끝난 클래스에만 유지한다.
- PlantVillage의 비슷한 잎 사진은 같은 개체 그룹이 train/test에 섞이지 않도록 공식 leaf grouping 기반 분할을 사용한다.
- PlantDoc과 자체 휴대폰 사진은 배경·조명 차이를 확인하는 별도 개발시험에 우선 사용한다.
- 최종 독립시험에는 학습·튜닝에 쓰지 않은 자체 개체·과실을 사용한다. 공개자료 성능과 자체 독립 성능을 따로 보고한다.
- 중복 사진, 깨진 파일, 극단적 저해상도, 워터마크, 잘못된 작물·라벨을 검사한 뒤 manifest를 만든다.

## 채택 전 확인

1. 팀이 케일·깻잎을 가지·오이로 바꾸는 데 합의했는지 확인한다.
2. 자료를 실제로 내려받아 폴더별 파일 수와 손상 파일을 검사한다.
3. 데이터셋 이름·버전·URL·라이선스·확인일·해시를 manifest와 모델 카드에 남긴다.
4. 원본은 변경하지 않고 파생본의 전처리 코드와 생성 이력을 기록한다.
5. 학교 계획서의 후보 작물명은 팀 합의 후 한 번에 수정한다.
