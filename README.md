# 반석 사무실 3D · 운영 디지털 트윈

저장소: https://github.com/River-181/banseok-office-twin (private 유지)

대전 유성구 북유성대로 336 3층으로 이전하는 사무실의 3D 모델과 운영 시뮬레이터.
도면 한 장에서 시작해 공간·가구·좌석·사람·차량·주변 지형까지 하나의 JSON을 원천으로 생성한다.

## 구조

```
04_데이터/floorplan_3F.json   단일 진실 원천 (공간·가구·좌석)
04_데이터/poi.json            주변 시설 실측 거리·방위각
05_코드/build_plan.py         JSON + 2D 클린 도면 생성
05_코드/build_glb.py          JSON → GLB (건물·주변·차량·사람 포함)
05_코드/build_site.py         건물 외피·주변 지형·주차장 디오라마·방향 표지
05_코드/build_people.py       의자·책상 장비·인물 지오메트리
05_코드/build_viewer.py       GLB + 시뮬 로그 → 단일 HTML 뷰어
05_코드/sim_model.py          객체 모델 (Seat·Member·Team·Vehicle·Case)
05_코드/sim_day.py            하루 이산사건 시뮬레이션 (SimPy)
```

## 빌드

```bash
bash 05_코드/setup.sh                 # venv: ~/.venvs/banseok3d
P=~/.venvs/banseok3d/bin/python
$P 05_코드/build_plan.py && $P 05_코드/build_glb.py
$P 05_코드/build_viewer.py            # 로컬용 (이름 포함)
$P 05_코드/build_viewer.py --public   # 공유용 (이름 제외)
$P 05_코드/sim_day.py                 # 하루 시뮬레이션
```

## 원칙

- 파생물(SVG·PNG·GLB·HTML)은 손으로 고치지 않는다. JSON과 스크립트만 고친다.
- 개인정보(이름·좌석 배정)는 `04_데이터/좌석배정.csv`와 `org.json`에만 두고, `--public` 빌드에서 제외한다.
- 가정값은 `conf` 필드로 표시한다: measured / derived / assumed.

## 커밋

```bash
bash push.sh https://github.com/River-181/banseok-office-twin.git "세션 단위 메시지"
```

개인정보(이름·좌석 배정·원본 도면·현장 사진)는 `.gitignore`로 제외된다. 푸시 후 GitHub 파일 목록을 한 번 확인할 것.

## 문서

`01_기획/` 아래 기획안, 결정로그, 질문-답변, 운영 시뮬레이터 구상, 운영 디지털 트윈 설계, 로드맵.
