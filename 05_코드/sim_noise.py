"""L2 acoustics: speech noise map of the floor (0.5 m grid, A-weighted dB).
Direct field + barrier insertion loss + one diffuse reverberant field (Sabine). No CFD-grade claims —
the point is comparing layouts (with / without the 가벽), not certifying absolute levels."""
from __future__ import annotations

import json
import math
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "04_데이터"
CELL = 0.5                      # m
EAR_H = 1.2                     # seated ear height
SPEECH_LP_1M = 60.0             # normal phone voice, dB(A) at 1 m
LW = SPEECH_LP_1M + 11          # sound power level of one talker
ALPHA = 0.35                    # average absorption: tile carpet + acoustic ceiling + screens (open-plan office)
TALK_SHARE = 0.35               # connect rate: share of seats on a call at any moment
BARRIER_DB = {"desk_screen": 4.0, "screen": 5.0, "partition": 8.0, "shelf": 8.0, "locker": 9.0,
              "GYP": 25.0, "CORE": 25.0, "EXT": 25.0, "GLS": 22.0, "GLS_FILM": 22.0}
BARRIER_CAP = 28.0


def seg_hit(p, q, a, b):
    """True if segment p-q crosses segment a-b."""
    def cross(o, s, e):
        return (s[0] - o[0]) * (e[1] - o[1]) - (s[1] - o[1]) * (e[0] - o[0])
    d1, d2, d3, d4 = cross(a, b, p), cross(a, b, q), cross(p, q, a), cross(p, q, b)
    return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0))


def barriers(model, with_partitions=True):
    """Every sound-blocking segment as (p0, p1, insertion loss dB)."""
    out = []
    for w in model["walls"]:
        pts = w["poly"] if "poly" in w else [w["a"], w["b"]]
        for i in range(len(pts) - 1):
            out.append((tuple(v / 100 for v in pts[i]), tuple(v / 100 for v in pts[i + 1]), BARRIER_DB.get(w["type"], 20.0)))
    if with_partitions:
        for p in model["partitions"]:
            out.append((tuple(v / 100 for v in p["a"]), tuple(v / 100 for v in p["b"]), BARRIER_DB[p["type"]]))
        for f in model["furniture"]:
            if f["type"] in ("locker", "partition", "shelf") and f["h"] >= 150:
                x, z, w_, d_ = f["x"] / 100, f["y"] / 100, f["w"] / 100, f["d"] / 100
                long_side = ((x + w_ / 2, z), (x + w_ / 2, z + d_)) if d_ >= w_ else ((x, z + d_ / 2), (x + w_, z + d_ / 2))
                out.append((long_side[0], long_side[1], BARRIER_DB[f["type"]]))
    return out


def room_constant(model, alpha=ALPHA):
    w, d, h = 21.35, 15.55, model["meta"]["defaults"]["ceiling"] / 100
    surface = 2 * (w * d) + 2 * h * (w + d)
    return surface * alpha / (1 - alpha)


def sources(model):
    """Phone seats: position and the share of time they are talking."""
    out = []
    for f in model["furniture"]:
        if f["type"] == "desk" and f.get("seat_no", "").startswith(("외전", "국전", "R1", "R2")):
            out.append(((f["x"] + f["w"] / 2) / 100, (f["y"] + f["d"] / 2) / 100, f["seat_no"]))
    return out


def level_at(point, srcs, bars, r_const, share):
    energy = 0.0
    for sx, sz, _ in srcs:
        r = max(0.8, math.dist(point, (sx, sz)))
        hits = [db for a, b, db in bars if seg_hit(point, (sx, sz), a, b)]
        direct = LW - 20 * math.log10(r) - 11 - min(sum(hits), BARRIER_CAP)
        # only a single full-height element (a wall) separates the reverberant field; stacked screens do not
        wall = max(hits, default=0.0)
        reverb = LW - 10 * math.log10(r_const / 4) - (wall if wall >= 20 else 0)
        energy += share * (10 ** (direct / 10) + 10 ** (reverb / 10))
    return 10 * math.log10(energy) if energy > 0 else 0.0


def grid(model, with_partitions=True, share=TALK_SHARE, alpha=ALPHA):
    srcs, bars, r_const = sources(model), barriers(model, with_partitions), room_constant(model, alpha)
    nx, nz = int(21.35 / CELL) + 1, int(15.55 / CELL) + 1
    return [[round(level_at(((i + 0.5) * CELL, (j + 0.5) * CELL), srcs, bars, r_const, share), 1)
             for i in range(nx)] for j in range(nz)], nx, nz


def zone_stats(model, cells, nx, nz):
    zones = {z["id"]: (z["name"], z["poly"]) for z in model["rooms"]}
    def inside(poly, x, z):          # ray casting: the waiting zone is L-shaped, a bounding box would lie
        pts = [(p[0] / 100, p[1] / 100) for p in poly]
        hit = False
        for (x1, z1), (x2, z2) in zip(pts, pts[1:] + pts[:1]):
            if (z1 > z) != (z2 > z) and x < x1 + (z - z1) / (z2 - z1) * (x2 - x1):
                hit = not hit
        return hit
    out = {}
    for zid, (name, poly) in zones.items():
        vals = [cells[j][i] for j in range(nz) for i in range(nx) if inside(poly, (i + 0.5) * CELL, (j + 0.5) * CELL)]
        if vals:
            out[name] = dict(mean=round(sum(vals) / len(vals), 1), max=round(max(vals), 1))
    return out


def seat_exposure(model, with_partitions=True):
    srcs, bars, r_const = sources(model), barriers(model, with_partitions), room_constant(model)
    out = {}
    for sx, sz, seat in srcs:
        others = [s for s in srcs if s[2] != seat]
        out[seat] = round(level_at((sx, sz), others, bars, r_const, TALK_SHARE), 1)
    return out


if __name__ == "__main__":
    model = json.loads((DATA / "floorplan_3F.json").read_text(encoding="utf-8"))
    cells, nx, nz = grid(model)
    bare, _, _ = grid(model, with_partitions=False)
    absorb, _, _ = grid(model, alpha=0.50)       # 흡음 천장·벽 보강
    worst, _, _ = grid(model, share=1.0)         # 전원 동시 통화
    stats, stats_bare = zone_stats(model, cells, nx, nz), zone_stats(model, bare, nx, nz)
    scenarios = dict(기본=stats, 가벽제거=stats_bare,
                     흡음보강=zone_stats(model, absorb, nx, nz), 전원통화=zone_stats(model, worst, nx, nz))
    seats = seat_exposure(model)
    result = dict(meta=dict(cell=CELL, nx=nx, nz=nz, ear_h=EAR_H, speech_lp_1m=SPEECH_LP_1M,
                            talk_share=TALK_SHARE, note="A-weighted dB, 35% of phone seats talking"),
                  grid=cells, grid_no_partitions=bare, grid_absorption=absorb, zones=stats,
                  zones_no_partitions=stats_bare, scenarios=scenarios, seats=seats)
    (DATA / "noise_map.json").write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    print(f"grid {nx}x{nz}, peak {max(max(r) for r in cells):.1f} dB")
    for name, s in stats.items():
        delta = stats_bare.get(name, {}).get("mean", s["mean"]) - s["mean"]
        print(f"{name:<22} 평균 {s['mean']:>5.1f} 최대 {s['max']:>5.1f}  (가벽 없을 때 +{delta:.1f})")
    print("가장 시끄러운 좌석:", ", ".join(f"{k} {v}" for k, v in sorted(seats.items(), key=lambda kv: -kv[1])[:5]))
    key = "국세외 전화 구역"
    print("\n시나리오별 " + key)
    for name, st in scenarios.items():
        print(f"  {name:<6} 평균 {st[key]['mean']:.1f} dB, 최대 {st[key]['max']:.1f} dB")
