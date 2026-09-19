# 데이터 파일 위치

Git에 넣는 것: catalog의 자료 출처·검토 상태, templates의 빈 표, examples의 명시된 합성 자료. 실제 원본/정답은 여기 포함하지 않는다. 공개자료 URL은 해당 데이터셋을 직접 확인한 후 정확한 공식 상세 페이지를 입력한다.

로컬 실제 파일은 raw/, interim/, processed/, private/, splits/private/ 아래 생성한다. .gitignore가 추적에서 제외한다. 개인별 절대경로는 manifest에 기록하지 않고 데이터 루트 기준 상대경로를 사용한다.

manifest.synthetic.csv의 파일 경로·해시는 전부 가상이며 사진이 들어 있지 않다. 테스트용 3행은 실제 수집량·분할 비율·학습 자료가 아니다. collect/labels/calibration 표에도 실제 수치를 넣기 전에는 헤더만 둔다.
