# Android 0.6.0 자동 서버 연결

0.6.0/versionCode 6 후보는 새 설치 및 0.5.0 업데이트 후 서버 분석을 기본으로 선택한다.
사용자는 주소·API 키·Tailscale 설정을 입력하지 않는다. 앱이 최초 실행과 분석 요청 때
HTTPS 서버 준비 상태를 확인하고 이 설치에 한정된 인증을 자동으로 준비한다.
현재 후보의 실제 배포·시험 상태는 [STATUS](STATUS.md), Play 상태는 [PLAY_INTERNAL_TEST](PLAY_INTERNAL_TEST.md)를 따른다.

## 연결과 보관

- 공개 `config/android-server.json`에서 서버 주소를 조회한다. 주소 조회가 일시 실패하면 마지막 주소 또는 앱에 포함한 기본 HTTPS 주소를 사용한다. 이 파일과 APK에는 공통 인증키가 없다.
- 기기가 무작위 설치 UUID와 256비트 등록 증명을 만들고 Android Keystore AES-GCM으로 암호화해 보관한다. `POST /api/v1/devices/register`로 설치 전용 키를 발급받으며 API 키와 등록 증명은 URL·로그에 넣지 않는다.
- 서버는 등록 증명 및 API 키의 SHA-256만 보관한다. 같은 설치의 등록 증명을 확인해야 기존 키를 복구하거나 만료된 키를 갱신할 수 있다. 키는 30일 유효하며 앱이 자동으로 갱신한다.
- 설치 키로 조회·재시도할 수 있는 검사는 해당 설치가 만든 검사뿐이다. 기존 관리자 키와 기존 0.5.0 앱 경로는 유지한다. 기존 DB 행을 삭제하거나 소유자를 바꾸지 않는다.
- 자동 등록을 활성화한 실행 서버의 이전 `/v1/` 개발 API는 관리자 키가 있어야 접근할 수 있다. 설치 키는 이 개발 API의 권한을 받지 않는다.
- 초기 내부 시험은 설치 최대 100개, 등록 시도 분당 30회, 설치별 API 시간당 120회로 제한한다. 폐기된 기기는 등록 증명이 같아도 다시 허용하지 않는다. 이 익명 설치 등록은 사용자 로그인이나 Play Integrity 검증을 대신하지 않는다.
- 서버가 꺼졌거나 GPU/모델이 준비되지 않으면 연결 대기 또는 분석 실패를 표시한다. 정상 점수나 로컬 결과로 자동 대체하지 않는다. 사용자가 ‘기기에서 분석하기’를 명시적으로 선택할 수 있다.

## VisionMachine 서버 적용

기존 GPU 환경과 모델이 준비된 **VisionMachine clone**에서만 다음을 수행한다.
새 GPU 드라이버·시스템 Python·BlurFing 가상환경·서비스·포트·접속 경로는 변경하지 않는다.

```bash
git status --short --branch
git pull --ff-only
.venv/bin/python scripts/enable_auto_connection.py --enable
systemctl --user restart vision-machine-api
```

설정 스크립트는 이 clone의 기존 `.env`를 비공개 `storage/deployment-backups/`에 보관하고
기기 등록 활성화와 100개 한도만 설정한다. 기존 서버 키와 모델 경로는 보존한다.
일반 uvicorn은 `.env`를 자동으로 읽지 않으므로 기존 `scripts/run_gpu_server.py` 서비스로 실행한다.

기존 VisionMachine HTTPS 터널은 그대로 사용한다. 현재 주소는 임시 TryCloudflare 터널이다.
VisionMachine 터널을 새로 생성해 주소가 바뀌면 운영자가 `config/android-server.json`의
`base_url`을 실제 준비된 HTTPS 주소로 바꾸고 commit/push한다. 앱에는 설정 화면 입력이나
재설치가 필요 없다. 임시 터널을 고정 도메인이나 무중단 서비스로 표현하지 않는다.

## 검증

서버 시험은 합성 사진으로 등록 증명, 키 암호화/해시 보관, 만료·폐기, 요청 제한,
다른 설치의 검사 접근 거부와 기존 관리자 경로를 확인한다. 프로토콜 시험용 모델 객체는
실행 서버에 배포되지 않는다. 기본 Android 시험은 실제 외부 서버에 요청하지 않는다.

`AutomaticServerConnectionTest`의 라이브 시험은 `vm_live_auto=true`일 때만 실행한다.
주소나 키를 주입하지 않고 초기 자동 연결, 실제 서버 CUDA 준비 확인, 합성 사진 8장과
사진에 매칭된 합성 센서 기록 전송, 기존 결과 화면/이력 연결을 확인한다.
이 시험의 성공을 실제 휴대폰 또는 재배환경 정확도 검증으로 기록하지 않는다.
