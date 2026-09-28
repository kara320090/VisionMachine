# HTTP API: 구현된 것과 다음 설계

## 현재 실제 구현
| method/path | 기능 |
|---|---|
| GET /healthz | 프로세스 상태. 모델/DB 준비 완료 의미 아님 |
| GET /v1/capabilities | 후보 작물, 검증된 진단작물 빈 목록, 모델 미탑재, 구현/대기 기능 |
| POST /v1/dev/validate-inspection | inspection JSON 형식·의미 검증 후 pending_model 응답. 사진 저장 없음 |
| POST /v1/inspections | 로컬 전용 multipart `photo` + `metadata` JSON 문자열. 실제 JPEG/PNG 검사·저장; 첫 요청 201, 동일 재시도 200, ID 충돌 409 |
| GET /v1/inspections/{inspection_id} | 로컬 SQLite에서 메타데이터·pending_model 결과 단건 조회. 사진 바이트는 반환하지 않음 |

로컬 전용이며 인증 미구현. 업로드·조회는 loopback 클라이언트만 허용하고 `uvicorn --host 127.0.0.1`로 실행한다. 공개 서버나 다사용자 서비스에 연결하기 전에는 인증·HTTPS·소유자 범위가 필요하다.

현재 구현의 OpenAPI는 `contracts/openapi.json`에 있으며 `python scripts/export_openapi.py`로 재생성한다. `python -m vm_server init-db`는 로컬 DB 초기화 도구다. 업로드 경로도 처음 사용할 때 저장소를 초기화한다. 사진은 `VM_STORAGE_DIR/uploads` 아래에 서버 생성 이름으로 저장하며 응답에 경로를 싣지 않는다.

## 다음 서버 작업에서 구현할 계약안
| method/path | 입력/동작 |
|---|---|
| GET /v1/inspections | 소유자별 최신순 이력, opaque cursor·limit. 실제 DB 경로 노출 금지 |
| DELETE /v1/inspections/{inspection_id} | 소유자 검사 및 파일 삭제/보존 정책 적용 |
| POST /v1/inspections/{inspection_id}/analysis | 모델 탑재 후 분석 요청/재시도; 동일 작업 중복 방지 |

현재 로컬 업로드는 첫 요청 201, 동일 ID+동일 canonical metadata/사진 재전송은 기존 검사 반환 200, ID는 같고 내용이 다르면 409다. 삭제 후 같은 ID 재시도 정책은 tombstone 포함 후속 설계에서 확정한다. 다사용자 권한은 구현되지 않았다.

업로드는 실제 JPEG/PNG decoder·12 MiB 바이트 상한·24 Mpixel 상한·SHA-256 검사를 한다. filename은 저장경로로 쓰지 않고 서버가 생성한 안전한 키를 사용한다. 임시파일·DB 트랜잭션·원자적 이동·실패 정리와 재시작 후 조회를 시험했다. 프로세스 강제 종료 때 생긴 orphan 파일의 자동 복구는 미구현이다. 상한값은 기준 휴대폰 시험 후 조정한다.

사진과 JSON을 같은 multipart에서 보낼 때 metadata는 Form 문자열로 받고 검증한다. JSON Body와 multipart를 동시에 요구하지 않는다. python-multipart와 Pillow 버전은 requirements.lock.txt에 고정했다.

수동 검증 오류는 `detail.request_id`와 `detail.code`에 INVALID_METADATA/INVALID_IMAGE/HASH_MISMATCH/ID_CONFLICT/LOCAL_ONLY/STORAGE_UNAVAILABLE 등을 반환한다. 파일 경로·토큰·stack trace를 반환하지 않는다. FastAPI의 기본 422와 제품 오류 envelope의 통일은 후속 작업이다.

인증은 다사용자 외부 테스트 전에 구현한다. 초기 로컬 개발을 위해 APK 안에 영구 공용 API 키를 넣지 않는다. 앱·서버 연결은 HTTPS, 권한은 서버에서 검증한다. OpenAPI는 구현 코드에서 생성하고 예정 API를 구현된 것처럼 광고하지 않는다.

참고: https://fastapi.tiangolo.com/tutorial/request-files/
