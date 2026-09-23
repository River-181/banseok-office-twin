"""office_3F.glb + floorplan_3F.json (+ 좌석배정.csv) -> viewer/index.html
--public : leave names out -> viewer/index_public.html (the one to share online)."""
import base64
import csv
import json
import sys
from pathlib import Path

import build_site

PUBLIC = "--public" in sys.argv
ROOT = Path(__file__).resolve().parent.parent
glb = (ROOT / "07_산출물" / "glb" / "office_3F.glb").read_bytes()
model = json.loads((ROOT / "04_데이터" / "floorplan_3F.json").read_text(encoding="utf-8"))

names = {}
seat_csv = ROOT / "04_데이터" / "좌석배정.csv"
if seat_csv.exists() and not PUBLIC:
    with open(seat_csv, encoding="utf-8-sig") as fp:
        names = {row["id"]: row["name"].strip() for row in csv.DictReader(fp) if row["name"].strip()}

rooms = {r["id"]: r["name"] for r in model["rooms"]}
info, seats = {}, []
for f in model["furniture"]:
    info[f["id"]] = dict(label=f["label"], where=rooms.get(f.get("room") or f.get("zone"), ""),
                         equip=f.get("equip", []), seat=f.get("seat_no", ""), name=names.get(f["id"], ""))
    if "seat_no" in f:
        seats.append(dict(id=f["id"], x=(f["x"] + f["w"] / 2) / 100, z=(f["y"] + f["d"] / 2) / 100))
org_path = ROOT / "04_데이터" / "org.json"
teams = {}
if org_path.exists():
    org = json.loads(org_path.read_text(encoding="utf-8"))
    teams = {t["id"]: t["name"] for t in org.get("teams", [])}
    for v in org.get("vehicles", []):  # vehicles carry no personal data -> safe for public builds
        info[v["id"]] = dict(label=v["model"], where="주차장 디오라마 (실제 위치 별도·미정)", seat=v["id"], name="",
                             equip=[f'{v["seats"]}인승', "전기차", teams.get(v["team"], "팀 미배정")])
labels = [dict(name=r["name"], x=sum(p[0] for p in r["poly"]) / len(r["poly"]) / 100,
               z=sum(p[1] for p in r["poly"]) / len(r["poly"]) / 100) for r in model["rooms"]]


CALLOUTS = [  # [x, z, y-offset, title, body] in scene metres; y is added to the 3F floor
    [15.0, -0.6, 2.4, "출입문", "엘리베이터 홀에서 들어오는 유일한 출입구. 폭 약 1.7m, 양개 유리문으로 가정했다."],
    [13.8, 1.1, 1.9, "안내데스크 · 관리", "관리보조 2석이 출입문을 바라본다. 방문객 접수와 차량 배차가 여기서 시작된다."],
    [6.3, 10.4, 2.1, "국세외 전화 구역", "전화실태확인원 24석. 4열 2행 클러스터 3개, 클러스터 사이 통로 180cm."],
    [1.9, 1.9, 2.2, "국세 전화실", "국세 전화 6석. 남측은 하부 불투명 + 상부 유리 파티션으로 가정(현장 확인 필요)."],
    [1.9, 9.5, 2.2, "국세외 공무원 구역", "운영 2 · 동행 3석. 1인당 약 5.9㎡로, 정부청사 하위직 기준 7㎡에 근접."],
    [5.5, 1.9, 2.0, "탕비실", "싱크대·냉장고·정수기와 원탁 2개. 휴식 시간에 직원들이 이쪽으로 이동한다."],
    [14.0, 11.0, 2.2, "방문실태확인원 대기공간", "고정석 없이 원탁 6개와 테이블 3개. 출동 전 대기와 복귀 후 서류 정리."],
    [19.4, 13.8, 2.2, "회의실 (240×120)", "우측 3개 실 중 가장 큰 방. 이름은 미확인."],
    [9.3, 11.0, 2.0, "사물함 · 가벽", "전화 구역과 대기공간을 나누는 경계. 가벽 6cm + 선반 40cm."],
]

def replay_payload(model, names):
    """Turn the S3 event log into compact per-person state timelines the viewer can interpolate."""
    log_path = ROOT / "07_산출물" / "sim" / "day_001.json"
    if not log_path.exists():
        return dict(day=540, people={}, teams=[], kpi=[])
    log = json.loads(log_path.read_text(encoding="utf-8"))
    seat_chair, seat_pos = {}, {}
    desks = {f["id"]: f for f in model["furniture"] if f["type"] == "desk"}
    for f in model["furniture"]:
        if f["type"] == "chair" and f.get("kind") == "task":
            desk = desks.get(f["id"][3:].rsplit("-", 1)[0])
            if desk and "seat_no" in desk:
                seat_chair[desk["seat_no"]] = f["id"]
                seat_pos[desk["seat_no"]] = [(f["x"] + f["w"] / 2) / 100, (f["y"] + f["d"] / 2) / 100]
    break_min = log.get("meta", {}).get("break_min", 10)
    people = {}
    for e in log["events"]:
        actor = e["actor"]
        if actor not in seat_chair:
            continue
        track = people.setdefault(actor, dict(chair=seat_chair[actor], pos=seat_pos[actor], states=[[0, "desk"]]))
        if e["action"] == "휴식":
            track["states"] += [[e["t"], "break"], [e["t"] + break_min, "desk"]]
        elif e["action"] == "점심":
            track["states"] += [[e["t"], "lunch"], [240, "desk"]]
        elif e["action"] == "퇴근":
            track["states"].append([e["t"], "off"])
    teams, order = {}, []
    for e in log["events"]:
        if e["actor"].endswith("팀"):
            teams.setdefault(e["actor"], []).append(dict(t=e["t"], what=e["action"], where=e.get("where", ""), soc=e.get("soc")))
            if e["actor"] not in order:
                order.append(e["actor"])
    kpi, connects, closed = [], 0, 0
    calls = []
    for e in log["events"]:
        if e["action"] == "통화":
            connects += 1
            calls.append((e["t"], e["t"] + e.get("min", 4)))
        elif e["action"] == "기록정리":
            closed += 1
        kpi.append((e["t"], connects, closed))
    sampled = []
    for t in range(0, 541, 5):
        c = next((v for v in reversed(kpi) if v[0] <= t), (0, 0, 0))
        oncall = sum(1 for a, b in calls if a <= t < b)
        sampled.append([t, c[1], c[2], oncall])
    return dict(day=540, people=people, teams=[dict(name=n, events=teams[n]) for n in order], kpi=sampled)

sign_path = ROOT / "04_데이터" / "signpost.json"
signs = json.loads(sign_path.read_text(encoding="utf-8")) if sign_path.exists() else []
replay = replay_payload(model, names)
html = (Path(__file__).parent / "viewer_template.html").read_text(encoding="utf-8")
html = (html.replace("__GLB__", base64.b64encode(glb).decode())
            .replace("__INFO__", json.dumps(info, ensure_ascii=False))
            .replace("__SEATS__", json.dumps(seats))
            .replace("__HAS_NAMES__", "true" if names else "false")
            .replace("__FLOOR_Y__", str(build_site.FLOOR3_Y))
            .replace("__CALLOUTS__", json.dumps(CALLOUTS, ensure_ascii=False))
            .replace("__SIGNS__", json.dumps(signs, ensure_ascii=False))
            .replace("__REPLAY__", json.dumps(replay, ensure_ascii=False))
            .replace("__PARK__", json.dumps([float(v) for v in build_site.DIORAMA_ORIGIN]))
            .replace("__LABELS__", json.dumps(labels, ensure_ascii=False)))
out = Path(__file__).parent / "viewer" / ("index_public.html" if PUBLIC else "index.html")
out.write_text(html, encoding="utf-8")
print(f"{out.name}: {out.stat().st_size/1024:.0f} KB, names={len(names)}")
