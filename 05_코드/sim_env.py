"""L1 environment: sun position, solar gain per facade, zone cooling loads and AC sizing.
Steady-state balance per zone (no CFD). Outdoor temperatures are typical Daejeon values (conf: assumed)."""
from __future__ import annotations

import json
import math
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "04_데이터"
LAT, LNG = 36.3946, 127.3135
FACADES = {"남서(북유성대로)": 238.0, "남동(소로)": 148.0, "북서(공임나라 쪽)": 328.0}   # outward normal azimuths
FACADE_LEN = {"남서(북유성대로)": 21.35, "남동(소로)": 15.55, "북서(공임나라 쪽)": 15.55}
WINDOW_H, SHGC, U_WIN, U_WALL = 1.6, 0.50, 2.4, 0.35        # ribbon window height m, glass gain, W/m²K
CEILING_H = 2.6
GAIN_PERSON, GAIN_PC, GAIN_MONITOR, GAIN_LIGHT = 75, 90, 30, 8   # W, W, W, W/m²
SCENARIOS = {"여름 오후(8월 15시)": dict(month=8, day=5, hour=15, outdoor=31.0),
             "겨울 아침(1월 9시)": dict(month=1, day=15, hour=9, outdoor=-4.0),
             "환절기(5월 14시)": dict(month=5, day=15, hour=14, outdoor=21.0)}
INDOOR = 26.0


def sun_position(month, day, hour, lat=LAT, lng=LNG, tz=9):
    """NOAA-style solar altitude/azimuth (degrees). Hour is local clock time."""
    n = int(30.44 * (month - 1)) + day
    gamma = 2 * math.pi / 365 * (n - 1 + (hour - 12) / 24)
    eqtime = 229.18 * (0.000075 + 0.001868 * math.cos(gamma) - 0.032077 * math.sin(gamma)
                       - 0.014615 * math.cos(2 * gamma) - 0.040849 * math.sin(2 * gamma))
    decl = (0.006918 - 0.399912 * math.cos(gamma) + 0.070257 * math.sin(gamma)
            - 0.006758 * math.cos(2 * gamma) + 0.000907 * math.sin(2 * gamma)
            - 0.002697 * math.cos(3 * gamma) + 0.00148 * math.sin(3 * gamma))
    time_offset = eqtime + 4 * lng - 60 * tz
    tst = hour * 60 + time_offset
    ha = math.radians(tst / 4 - 180)
    lat_r = math.radians(lat)
    alt = math.asin(math.sin(lat_r) * math.sin(decl) + math.cos(lat_r) * math.cos(decl) * math.cos(ha))
    az = math.atan2(-math.sin(ha) * math.cos(decl),
                    math.cos(lat_r) * math.sin(decl) - math.sin(lat_r) * math.cos(decl) * math.cos(ha))
    return math.degrees(alt), (math.degrees(az) + 360) % 360


def irradiance(alt_deg):
    """Clear-sky direct normal + diffuse horizontal (W/m²), Meinel approximation."""
    if alt_deg <= 3:
        return 0.0, 0.0
    am = 1 / math.sin(math.radians(alt_deg))
    dni = 1000 * 0.7 ** (am ** 0.678)
    return dni, 0.12 * dni


def facade_gain(alt, az, dni, dhi, facade_az, length):
    """Solar heat gain through one ribbon window (W)."""
    area = length * WINDOW_H
    cos_i = (math.cos(math.radians(alt)) * math.cos(math.radians(az - facade_az)))
    direct = max(0.0, cos_i) * dni
    return (direct + dhi * 0.5) * area * SHGC, max(0.0, cos_i)


def zone_people(model):
    counts = {}
    for f in model["furniture"]:
        if f["type"] == "desk" and "seat_no" in f:
            key = f.get("room") or f.get("zone")
            counts[key] = counts.get(key, 0) + 1
    return counts


def zone_area(poly):
    xs = [p[0] / 100 for p in poly]; zs = [p[1] / 100 for p in poly]
    return (max(xs) - min(xs)) * (max(zs) - min(zs))


def zone_facades(poly):
    """Which facades a zone touches (0 = touching the SW road side, etc.)."""
    xs = [p[0] / 100 for p in poly]; zs = [p[1] / 100 for p in poly]
    touch = {}
    if max(zs) >= 15.3:
        touch["남서(북유성대로)"] = max(xs) - min(xs)
    if min(xs) <= 0.2:
        touch["북서(공임나라 쪽)"] = max(zs) - min(zs)
    if max(xs) >= 21.1:
        touch["남동(소로)"] = max(zs) - min(zs)
    return touch


def analyse(model, scenario):
    alt, az = sun_position(scenario["month"], scenario["day"], scenario["hour"])
    dni, dhi = irradiance(alt)
    per_facade = {}
    for name, f_az in FACADES.items():
        gain, cos_i = facade_gain(alt, az, dni, dhi, f_az, FACADE_LEN[name])
        per_facade[name] = dict(gain_w=round(gain), sunlit=cos_i > 0.02, incidence=round(math.degrees(math.acos(min(1, max(-1, cos_i)))), 1) if cos_i > 0 else None)
    people = zone_people(model)
    dt = scenario["outdoor"] - INDOOR
    zones = {}
    for z in model["rooms"]:
        area = zone_area(z["poly"])
        n = people.get(z["id"], 0)
        internal = n * (GAIN_PERSON + GAIN_PC + GAIN_MONITOR) + area * GAIN_LIGHT
        solar = 0.0
        for fname, length in zone_facades(z["poly"]).items():
            share = length / FACADE_LEN[fname]
            solar += per_facade[fname]["gain_w"] * share
        envelope = 0.0
        for fname, length in zone_facades(z["poly"]).items():
            envelope += (U_WIN * length * WINDOW_H + U_WALL * length * (CEILING_H - WINDOW_H)) * dt
        load = internal + solar + envelope
        # perimeter band (3 m from the glass) carries all solar + envelope; internal gains follow floor area
        perim_len = sum(zone_facades(z["poly"]).values())
        perim_area = min(area, perim_len * 3.0)
        core_area = max(0.0, area - perim_area)
        perim_load = solar + envelope + internal * (perim_area / area if area else 0)
        core_load = internal * (core_area / area if area else 0)
        zones[z["name"]] = dict(area=round(area, 1), people=n, internal_w=round(internal), solar_w=round(solar),
                                envelope_w=round(envelope), load_w=round(load),
                                load_per_m2=round(load / area, 1) if area else 0,
                                perimeter_w_m2=round(perim_load / perim_area, 1) if perim_area else None,
                                core_w_m2=round(core_load / core_area, 1) if core_area else None,
                                mode="냉방" if load > 0 else "난방",
                                ac_kw=round(abs(load) / 1000 * 1.15, 1))
    return dict(sun=dict(altitude=round(alt, 1), azimuth=round(az, 1), dni=round(dni), dhi=round(dhi)),
                facades=per_facade, outdoor=scenario["outdoor"], indoor=INDOOR, zones=zones)


if __name__ == "__main__":
    model = json.loads((DATA / "floorplan_3F.json").read_text(encoding="utf-8"))
    report = {name: analyse(model, sc) for name, sc in SCENARIOS.items()}
    (DATA / "env_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    for name, r in report.items():
        print(f"\n== {name} · 외기 {r['outdoor']}℃ · 태양 고도 {r['sun']['altitude']}° 방위 {r['sun']['azimuth']}° ==")
        for f, v in r["facades"].items():
            print(f"  {f:<16} 일사 {v['gain_w']:>6} W  {'직사' if v['sunlit'] else '그늘'}")
        top = sorted(r["zones"].items(), key=lambda kv: -abs(kv[1]["load_w"]))[:4]
        for zname, z in top:
            band = f" 창가 {z['perimeter_w_m2']} / 안쪽 {z['core_w_m2']} W/㎡" if z["core_w_m2"] is not None else ""
            print(f"  {zname:<20} {z['people']:>2}명 {z['area']:>5.1f}㎡  {z['mode']} {abs(z['load_w']):>5} W ({z['load_per_m2']:>4.0f} W/㎡) → {z['ac_kw']} kW{band}")
        heat = [k for k, v in r["zones"].items() if v["mode"] == "난방"]
        if heat:
            print("  난방 필요:", ", ".join(heat))
