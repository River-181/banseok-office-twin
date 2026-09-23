"""L6-a circulation check: turn the day's event log into walking paths, a traffic heat map,
zone-crossing counts and the 출동 준비→출차 delay."""
from __future__ import annotations

import json
import math
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "04_데이터"
LOG = DATA.parent / "07_산출물" / "sim" / "day_001.json"
CELL = 0.5
CORRIDOR_Z = 3.6                      # the aisle people cross to reach the pantry / exit
PANTRY = (5.5, 2.0)
EXIT = (15.0, -0.5)


def seat_positions(model):
    out = {}
    for f in model["furniture"]:
        if f["type"] == "desk" and "seat_no" in f:
            out[f["seat_no"]] = ((f["x"] + f["w"] / 2) / 100, (f["y"] + f["d"] / 2) / 100)
    return out


def blocked_grid(model, nx, nz):
    """Walkable grid: walls block (doors stay open), furniture blocks, chairs do not."""
    blocked = [[False] * nx for _ in range(nz)]
    door_spans = {}
    for d in model["doors"]:
        door_spans.setdefault(d["wall"], []).append(d["span"])
    def block_seg(a, b, spans, horizontal):
        steps = int(math.dist(a, b) / (CELL / 2)) + 1
        for s in range(steps + 1):
            t = s / steps
            x, z = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
            along = (x if horizontal else z) * 100
            if any(lo - 5 <= along <= hi + 5 for lo, hi in spans):
                continue                                   # doorway
            i, j = int(x / CELL), int(z / CELL)
            if 0 <= i < nx and 0 <= j < nz:
                blocked[j][i] = True
    for w in model["walls"]:
        pts = w["poly"] if "poly" in w else [w["a"], w["b"]]
        spans = door_spans.get(w["id"], [])
        for k in range(len(pts) - 1):
            p0 = (pts[k][0] / 100, pts[k][1] / 100); p1 = (pts[k + 1][0] / 100, pts[k + 1][1] / 100)
            block_seg(p0, p1, spans, abs(p1[1] - p0[1]) < 0.01)
    for f in model["furniture"]:
        if f["type"] in ("chair",):
            continue
        for i in range(int(f["x"] / 100 / CELL), int((f["x"] + f["w"]) / 100 / CELL) + 1):
            for j in range(int(f["y"] / 100 / CELL), int((f["y"] + f["d"]) / 100 / CELL) + 1):
                if 0 <= i < nx and 0 <= j < nz:
                    blocked[j][i] = True
    return blocked


def astar(blocked, start, goal, nx, nz):
    import heapq
    def free(i, j):
        return 0 <= i < nx and 0 <= j < nz and not blocked[j][i]
    def nearest_free(c):
        if free(*c):
            return c
        for r in range(1, 8):
            for di in range(-r, r + 1):
                for dj in (-r, r):
                    for cand in ((c[0] + di, c[1] + dj), (c[0] + dj, c[1] + di)):
                        if free(*cand):
                            return cand
        return c
    start, goal = nearest_free(start), nearest_free(goal)
    open_q = [(0, start)]
    came, cost = {start: None}, {start: 0}
    while open_q:
        _, cur = heapq.heappop(open_q)
        if cur == goal:
            break
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            nxt = (cur[0] + di, cur[1] + dj)
            if not free(*nxt):
                continue
            step = 1.41 if di and dj else 1.0
            new = cost[cur] + step
            if new < cost.get(nxt, 1e9):
                cost[nxt] = new
                came[nxt] = cur
                heapq.heappush(open_q, (new + abs(nxt[0] - goal[0]) + abs(nxt[1] - goal[1]), nxt))
    if goal not in came:
        return []
    path, cur = [], goal
    while cur:
        path.append(cur); cur = came[cur]
    return path[::-1]


def walk_cells(path):
    cells = []
    for (x1, z1), (x2, z2) in zip(path, path[1:]):
        steps = max(1, int(math.dist((x1, z1), (x2, z2)) / CELL))
        for s in range(steps + 1):
            t = s / steps
            cells.append((int((x1 + (x2 - x1) * t) / CELL), int((z1 + (z2 - z1) * t) / CELL)))
    return cells


def trips(log, seats):
    """Every walk the day produced: (from, to, actor, minute)."""
    out = []
    for e in log["events"]:
        pos = seats.get(e["actor"])
        if not pos:
            continue
        if e["action"] == "휴식":
            out += [(pos, PANTRY, e["actor"], e["t"]), (PANTRY, pos, e["actor"], e["t"] + 10)]
        elif e["action"] == "점심":
            out += [(pos, EXIT, e["actor"], e["t"]), (EXIT, pos, e["actor"], 240)]
        elif e["action"] == "퇴근":
            out.append((pos, EXIT, e["actor"], e["t"]))
    return out


def zone_of(model, x, z):
    for zdef in model["rooms"]:
        pts = [(p[0] / 100, p[1] / 100) for p in zdef["poly"]]
        hit = False
        for (x1, z1), (x2, z2) in zip(pts, pts[1:] + pts[:1]):
            if (z1 > z) != (z2 > z) and x < x1 + (z - z1) / (z2 - z1) * (x2 - x1):
                hit = not hit
        if hit:
            return zdef["name"]
    return "복도/기타"


if __name__ == "__main__":
    model = json.loads((DATA / "floorplan_3F.json").read_text(encoding="utf-8"))
    log = json.loads(LOG.read_text(encoding="utf-8"))
    seats = seat_positions(model)
    nx, nz = int(21.35 / CELL) + 1, int(15.55 / CELL) + 1
    heat = [[0] * nx for _ in range(nz)]
    crossings, distance = {}, 0.0
    blocked = blocked_grid(model, nx, nz)
    cache = {}
    for a, b, actor, t in trips(log, seats):
        key = (round(a[0], 1), round(a[1], 1), round(b[0], 1), round(b[1], 1))
        if key not in cache:
            cache[key] = astar(blocked, (int(a[0] / CELL), int(a[1] / CELL)), (int(b[0] / CELL), int(b[1] / CELL)), nx, nz)
        cells = cache[key]
        distance += len(cells) * CELL
        for i, j in cells:
            heat[j][i] += 1
            name = zone_of(model, (i + 0.5) * CELL, (j + 0.5) * CELL)
            crossings[name] = crossings.get(name, 0) + 1
    # 출동 준비 → 출차 (teams)
    gate = {}
    for e in log["events"]:
        if e["actor"].endswith("팀") and e["action"] in ("출차", "복귀"):
            gate.setdefault(e["actor"], []).append((e["action"], e["t"]))
    busiest = sorted(((heat[j][i], i, j) for j in range(nz) for i in range(nx)), reverse=True)[:5]
    result = dict(meta=dict(cell=CELL, trips=len(trips(log, seats)), total_km=round(distance / 1000, 2),
                            note="A* on a walkable grid: walls block, doorways open, furniture blocks"),
                  heat=heat, crossings=crossings, blocked=[[int(v) for v in row] for row in blocked])
    (DATA / "flow_map.json").write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    print(f"이동 {result['meta']['trips']}회, 총 보행거리 {distance:,.0f} m")
    print("\n통과량 상위 구역")
    for name, n in sorted(crossings.items(), key=lambda kv: -kv[1])[:6]:
        print(f"  {name:<22} {n:>6} 셀·통과")
    print("\n가장 붐비는 지점 (x, z in m)")
    for count, i, j in busiest:
        print(f"  ({(i + 0.5) * CELL:>5.1f}, {(j + 0.5) * CELL:>5.1f})  {count}회 · {zone_of(model, (i + 0.5) * CELL, (j + 0.5) * CELL)}")
