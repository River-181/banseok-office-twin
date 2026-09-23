"""L5 layout scenarios: apply simple transforms to floorplan_3F.json, then score each layout
with the noise (L2) and environment (L1) models so two options can be compared side by side."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import sim_env
import sim_noise

DATA = Path(__file__).resolve().parent.parent / "04_데이터"
BASE = json.loads((DATA / "floorplan_3F.json").read_text(encoding="utf-8"))

LAYOUTS = {
    "A 도면 그대로": [],
    "B 전화섬 창가에서 후퇴": [("move", "KOT-", 0, -150), ("move", "CH-KOT-", 0, -150), ("move_partition", "DS-KOT", 0, -150)],
    "C 가벽 제거 + 흡음 보강": [("drop", "WALL-SHELF"), ("drop", "SHELF"), ("absorb", 0.50)],
}


def apply(layout):
    model, alpha = copy.deepcopy(BASE), sim_noise.ALPHA
    for rule in layout:
        kind = rule[0]
        if kind == "move":
            _, prefix, dx, dy = rule
            for f in model["furniture"]:
                if f["id"].startswith(prefix):
                    f["x"] += dx; f["y"] += dy
        elif kind == "move_partition":
            _, prefix, dx, dy = rule
            for p in model["partitions"]:
                if p["id"].startswith(prefix):
                    p["a"] = [p["a"][0] + dx, p["a"][1] + dy]; p["b"] = [p["b"][0] + dx, p["b"][1] + dy]
        elif kind == "drop":
            model["furniture"] = [f for f in model["furniture"] if f["id"] != rule[1]]
        elif kind == "absorb":
            alpha = rule[1]
    return model, alpha


def score(model, alpha):
    cells, nx, nz = sim_noise.grid(model, alpha=alpha)
    zones = sim_noise.zone_stats(model, cells, nx, nz)
    summer = sim_env.analyse(model, sim_env.SCENARIOS["여름 오후(8월 15시)"])
    phone_env = summer["zones"]["국세외 전화 구역"]
    seats = sim_noise.seat_exposure(model)
    # how many phone seats actually sit in the hot/bright 3 m perimeter band
    perim_seats = sum(1 for f in model["furniture"]
                      if f["type"] == "desk" and f.get("seat_no", "").startswith("외전")
                      and (f["y"] + f["d"] >= 1555 - 300 or f["x"] <= 300 or f["x"] + f["w"] >= 2135 - 300))
    return dict(phone_noise=zones["국세외 전화 구역"], wait_noise=zones["방문실태확인원 대기공간"],
                worst_seat=max(seats.values()), phone_load_w=phone_env["load_w"], perimeter_seats=perim_seats,
                perimeter=phone_env["perimeter_w_m2"], core=phone_env["core_w_m2"], ac_kw=phone_env["ac_kw"])


if __name__ == "__main__":
    out = {}
    for name, rules in LAYOUTS.items():
        model, alpha = apply(rules)
        out[name] = score(model, alpha)
    (DATA / "layout_compare.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    head = f"{'배치안':<22}{'전화 소음':>10}{'대기 소음':>10}{'최악 좌석':>10}{'창가 좌석':>10}"
    print(head); print("-" * len(head))
    for name, s in out.items():
        print(f"{name:<22}{s['phone_noise']['mean']:>10.1f}{s['wait_noise']['mean']:>10.1f}"
              f"{s['worst_seat']:>10.1f}{s['perimeter_seats']:>10}")
