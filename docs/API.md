# HTTP API: 구현된 것과 다음 설계

## 현재 실제 구현
| method/path | 기능 |
|---|---|
| GET /healthz | 프로세스 상태. 모델/DB 준비 완료 의미 아님 |
| GET /v1/capabilities | 후보 작물, 검증된 진단작물 빈 목록, 모델 미탑재, 구현/대기 기능 |
| POST /v1/dev/validate-inspection | inspection JSON 형식·의미 검증 후 pending_model 응답. 사진 저장 없음 |

로컬 전용이며 인증 미구현. 기본 bind는 127.0.0.1. 실제 사진이나 비밀을 공개 서버에 올리기 전에 아래 기능을 구현한다.

## 다음 서버 작업에서 구현할 계약안
| method/path | 입력/동작 |
|---|---|
| POST /v1/inspections | multipart `photo` 파일 + `metadata` JSON 문자열. metadata는 공통 InspectionMetadata |
| GET /v1/inspections/{inspection_id} | 소유자 범위로 검사 상태·메타데이터·분석 결과 조회 |
| GET /v1/inspections | 소유자별 최신순 이력, opaque cursor·limit. 실제 DB 경로 노출 금지 |
| DELETE /v1/inspections/{inspection_id} | 소유자 검사 및 파일 삭제/보존 정책 적용 |
| POST /v1/inspections/{inspection_id}/analysis | 모델 탑재 후 분석 요청/재시도; 동일 작업 중복 방지 |

첫 업로드 201, 동일 ID+동일 canonical metadata/사진 재전송은 기존 검사 반환 200, ID는 같고 내용이 다르면 409. 삭제 후 같은 ID 재시도 정책은 tombstone 포함 후속 설계에서 확정한다. 다른 사용자의 ID/내용은 공개하지 않는다.

업로드는 실제 JPEG/PNG decoder·크기/픽셀 상한·SHA-256 검사를 한다. filename은 저장경로로 쓰지 않고 서버가 생성한 안전한 키를 사용한다. 임시파일·DB 트랜잭션·원자적 이동·실패/재시작 복구를 테스트한다. 적절한 최대 크기는 기준 휴대폰 사진으로 결정하고 설정화한다.

사진과 JSON을 같은 multipart에서 보낼 때 metadata는 Form 문자열로 받고 검증한다. JSON Body와 multipart를 동시에 요구하지 않는다. 해당 구현 시 python-multipart 및 이미지 디코더 의존성을 잠그고 테스트한다.

오류는 request_id와 코드 INVALID_METADATA/INVALID_IMAGE/HASH_MISMATCH/ID_CONFLICT/UNAUTHORIZED/STORAGE_UNAVAILABLE 등을 응답한다. 파일 경로·토큰·stack trace를 반환하지 않는다. FastAPI 422의 현재 형태와 제품 오류 envelope의 차이는 후속 구현에서 정리한다.

인증은 다사용자 외부 테스트 전에 구현한다. 초기 로컬 개발을 위해 APK 안에 영구 공용 API 키를 넣지 않는다. 앱·서버 연결은 HTTPS, 권한은 서버에서 검증한다. OpenAPI는 구현 코드에서 생성하고 예정 API를 구현된 것처럼 광고하지 않는다.

참고: https://fastapi.tiangolo.com/tutorial/request-files/
