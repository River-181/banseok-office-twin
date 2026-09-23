"""floorplan_3F.json -> 07_산출물/glb/office_3F.glb (meters, Y-up, node name = JSON id)."""
import json
from pathlib import Path

import numpy as np
import trimesh
from trimesh.visual.material import PBRMaterial

import build_people
import build_site

ROOT = Path(__file__).resolve().parent.parent
MODEL = json.loads((ROOT / "04_데이터" / "floorplan_3F.json").read_text(encoding="utf-8"))
OUT = ROOT / "07_산출물" / "glb" / "office_3F.glb"
CEILING = MODEL["meta"]["defaults"]["ceiling"] / 100

def material(hex_color, alpha=1.0, rough=0.8):
    rgb = [int(hex_color[i:i+2], 16) for i in (0, 2, 4)]
    return PBRMaterial(baseColorFactor=rgb + [int(alpha * 255)], roughnessFactor=rough, metallicFactor=0.0,
                       alphaMode="BLEND" if alpha < 1 else "OPAQUE", doubleSided=alpha < 1)

MAT = dict(EXT=material("2f3e4e"), CORE=material("8a8a8a"), GYP=material("e8e4dc"), frame=material("9aa5b1"),
           glass=material("8fd0f7", 0.28, 0.1), film=material("d6ecf7", 0.6, 0.3), floor=material("cfc8b8"),
           desk=material("c9b79c"), table=material("d9c7a3"), round_table=material("d9c7a3"), cabinet=material("9e9686"),
           locker=material("9e9686"), printer=material("f4f4f4"), mfp=material("f4f4f4"), shredder=material("eeeeee"),
           fridge=material("f5f5f5"), water_dispenser=material("dfe9f0"), sink_counter=material("b0bec5"),
           partition_shelf=material("8d6e63"), partition=material("8d6e63"), reception=material("b39a6b"),
           equipment_rack=material("333333"), shelf=material("a1887f"), desk_panel=material("5c6b73"), column=material("777777"),
           chair_task=material("2d3540"), chair_meeting=material("6d7b8a"), screen=material("8d6e63"), desk_screen=material("7fa3a8"))

scene = trimesh.Scene()

def box(x0, z0, x1, z1, y0, y1):
    m = trimesh.creation.box(extents=[max(x1 - x0, 0.01), y1 - y0, max(z1 - z0, 0.01)])
    m.apply_translation([(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2])
    return m

def add(name, parts, mat):
    mesh = trimesh.util.concatenate(parts) if isinstance(parts, list) else parts
    mesh.visual = trimesh.visual.TextureVisuals(material=mat)
    scene.add_geometry(mesh, node_name=name, geom_name=name)

def wall_slices(kind):
    if kind == "EXT":
        return [(0, 0.85, "EXT"), (0.85, 2.45, "glass"), (2.45, CEILING, "EXT")]
    if kind == "GLS":
        return [(0, 0.9, "frame"), (0.9, CEILING, "glass")]
    if kind == "GLS_FILM":
        return [(0, 1.0, "glass"), (1.0, 1.7, "film"), (1.7, CEILING, "glass")]
    return [(0, CEILING, kind)]

def segments(a, b, door_spans):
    horizontal = a[1] == b[1]
    s0, s1 = sorted([a[0], b[0]] if horizontal else [a[1], b[1]])
    fixed = a[1] if horizontal else a[0]
    cur, solid, headers = s0, [], []
    for d0, d1 in sorted(door_spans):
        if d0 > cur:
            solid.append((cur, d0))
        headers.append((d0, d1))
        cur = max(cur, d1)
    if cur < s1:
        solid.append((cur, s1))
    return horizontal, fixed, solid, headers

def slab(horizontal, fixed, s0, s1, t, y0, y1):
    a, b, k, r = s0 / 100, s1 / 100, fixed / 100, t / 200
    return box(a, k - r, b, k + r, y0, y1) if horizontal else box(k - r, a, k + r, b, y0, y1)

doors_by_wall = {}
for d in MODEL["doors"]:
    doors_by_wall.setdefault(d["wall"], []).append((d["span"], d["h"] / 100))

for w in MODEL["walls"]:
    pieces = [(w["poly"][i], w["poly"][i + 1]) for i in range(len(w["poly"]) - 1)] if "poly" in w else [(w["a"], w["b"])]
    for n, (a, b) in enumerate(pieces):
        spans = doors_by_wall.get(w["id"], []) if "a" in w else []
        horizontal, fixed, solid, headers = segments(a, b, [s for s, _ in spans])
        by_mat = {}
        for s0, s1 in solid:
            for y0, y1, m in wall_slices(w["type"]):
                by_mat.setdefault(m, []).append(slab(horizontal, fixed, s0, s1, w["t"], y0, y1))
        for (s0, s1), (_, door_h) in zip(headers, sorted(spans)):
            head_mat = "GYP" if w["type"] in ("GLS", "GLS_FILM", "GYP") else w["type"]
            by_mat.setdefault(head_mat, []).append(slab(horizontal, fixed, s0, s1, w["t"], min(door_h, CEILING - 0.05), CEILING))
        for m, parts in by_mat.items():
            add(f'{w["id"]}_{n}_{m}', parts, MAT[m])

add("FLOOR", [box(-0.15, -0.15, 21.5, 15.7, -0.02, 0), box(9.15, -1.75, 12.25, -0.16, -0.02, 0)], MAT["floor"])

def desk_like(f):
    x0, z0, x1, z1 = f["x"] / 100, f["y"] / 100, (f["x"] + f["w"]) / 100, (f["y"] + f["d"]) / 100
    top = f["h"] / 100
    parts = [box(x0, z0, x1, z1, top - 0.03, top)]
    if f["w"] >= f["d"]:
        parts += [box(x0 + .03, z0 + .03, x0 + .06, z1 - .03, 0, top - .03), box(x1 - .06, z0 + .03, x1 - .03, z1 - .03, 0, top - .03)]
    else:
        parts += [box(x0 + .03, z0 + .03, x1 - .03, z0 + .06, 0, top - .03), box(x0 + .03, z1 - .06, x1 - .03, z1 - .03, 0, top - .03)]
    return parts

def round_table(f):
    r, cx, cz, top = f["w"] / 200, (f["x"] + f["w"] / 2) / 100, (f["y"] + f["d"] / 2) / 100, f["h"] / 100
    plate = trimesh.creation.cylinder(radius=r, height=0.04, sections=32)
    plate.apply_translation([0, 0, 0]); plate.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    plate.apply_translation([cx, top - 0.02, cz])
    leg = trimesh.creation.cylinder(radius=0.04, height=top - 0.04, sections=12)
    leg.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0])); leg.apply_translation([cx, (top - 0.04) / 2, cz])
    return [plate, leg]

def chair(f):
    x0, z0, s, p, t = f["x"] / 100, f["y"] / 100, f["w"] / 100, 0.05, 0.05
    top = f["h"] / 100
    parts = [box(x0 + p, z0 + p, x0 + s - p, z0 + s - p, 0.42, 0.47),
             box(x0 + s / 2 - .03, z0 + s / 2 - .03, x0 + s / 2 + .03, z0 + s / 2 + .03, 0, 0.42)]
    back = dict(N=(x0 + p, z0 + s - p - t, x0 + s - p, z0 + s - p), S=(x0 + p, z0 + p, x0 + s - p, z0 + p + t),
                E=(x0 + p, z0 + p, x0 + p + t, z0 + s - p), W=(x0 + s - p - t, z0 + p, x0 + s - p, z0 + s - p))[f["face"]]
    return parts + [box(*back, 0.47, top)]

ROLE_OF = {"운영공무원": "운영공무원", "동행공무원": "동행공무원", "전화": "전화실태확인원", "관리": "관리보조"}
PEOPLE_MAT = {role: material(c) for role, c in build_people.ROLE_COLORS.items()}
SKIN_MAT, HAIR_MAT = material(build_people.SKIN), material(build_people.HAIR)
SCREEN_MAT, PLASTIC_MAT, CHAIR_FRAME = material("15181c", rough=0.25), material("2b2f36"), material("6a6f77", rough=0.4)
DESKS = {f["id"]: f for f in MODEL["furniture"] if f["type"] == "desk"}

def role_of(label):
    return next((v for k, v in ROLE_OF.items() if label.startswith(k)), "전화실태확인원")

for f in MODEL["furniture"]:
    kind = f["type"]
    if kind == "chair":
        task = f["kind"] == "task"
        soft, frame = build_people.chair_parts(f["x"] / 100, f["y"] / 100, f["w"] / 100, f["face"], task)
        add(f["id"], soft, MAT[f"chair_{f['kind']}"])
        add(f["id"] + "_frame", frame, CHAIR_FRAME)
        desk = DESKS.get(f["id"][3:].rsplit("-", 1)[0])
        if task and desk:  # someone working at that desk
            role = role_of(desk["label"])
            body, skin, hair = build_people.person(f["x"] / 100 + f["w"] / 200, f["y"] / 100 + f["d"] / 200, f["face"])
            add(f'PEOPLE_{f["id"]}', body, PEOPLE_MAT[role])
            add(f'PEOPLE_{f["id"]}_skin', skin, SKIN_MAT)
            add(f'PEOPLE_{f["id"]}_hair', hair, HAIR_MAT)
    elif kind == "round_table":
        add(f["id"], round_table(f), MAT[kind])
    elif kind in ("desk", "table"):
        add(f["id"], desk_like(f), MAT[kind])
        if kind == "desk":
            screens, plastics = build_people.desk_equipment(f, f.get("equip", []))
            if screens:
                add(f'{f["id"]}_screen', screens, SCREEN_MAT)
            add(f'{f["id"]}_gear', plastics, PLASTIC_MAT)
    else:
        add(f["id"], box(f["x"] / 100, f["y"] / 100, (f["x"] + f["w"]) / 100, (f["y"] + f["d"]) / 100, 0, f["h"] / 100), MAT[kind])

for c in MODEL["columns"]:
    add(c["id"], box(c["x"] / 100, c["y"] / 100, (c["x"] + c["w"]) / 100, (c["y"] + c["d"]) / 100, 0, CEILING), MAT["column"])

for p in MODEL["partitions"]:
    (ax, az), (bx, bz) = p["a"], p["b"]
    on_desk = p["type"] == "desk_screen"
    r = 0.015 if on_desk else 0.02
    add(p["id"], box(min(ax, bx) / 100 - r, min(az, bz) / 100 - r, max(ax, bx) / 100 + r, max(az, bz) / 100 + r,
                     0.72 if on_desk else 0, p["h"] / 100), MAT[p["type"]])


for pid, (px, pz, pface, prole) in {
        "RECEPTION": (13.0, 1.1, "E", "관리보조"),
        "WAIT1": (12.4, 10.2, "S", "방문객"), "WAIT2": (14.2, 10.2, "W", "방문객"),
        "CREW1": (15.6, 4.6, "S", "방문실태확인원"), "CREW2": (16.4, 4.6, "S", "방문실태확인원"),
        "CREW3": (17.2, 4.6, "S", "방문실태확인원")}.items():
    body, skin, hair = build_people.person(px, pz, pface, seated=False)
    for parts, mat, tag in ((body, PEOPLE_MAT[prole], ""), (skin, SKIN_MAT, "_skin"), (hair, HAIR_MAT, "_hair")):
        add(f"PEOPLE_{pid}{tag}", parts, mat)


# ---------- office goes to 3F, then building shell + surroundings ----------
for geom in scene.geometry.values():
    geom.apply_translation([0, build_site.FLOOR3_Y, 0])
SITE = build_site.site_materials(material)
build_site.add_building(add, box, SITE)
build_site.add_surroundings(add, box, SITE)
build_site.add_parking_diorama(add, box, SITE)
SIGN_TIPS = build_site.add_signpost(add, box, SITE, ROOT / "04_데이터" / "poi.json")
(ROOT / "04_데이터" / "signpost.json").write_text(json.dumps(SIGN_TIPS, ensure_ascii=False), encoding="utf-8")

def lifted(parts, dy):
    parts = parts if isinstance(parts, list) else [parts]
    for part in parts:
        part.apply_translation([0, dy, 0])
    return parts

# ---------- vehicles (on the parking diorama; real lot location unknown) ----------
ORG_PATH = ROOT / "04_데이터" / "org.json"
VEHICLE_SPECS = {  # real dimensions (m); side silhouettes as (x/L, y/H), front at x=0
    "기아 EV6": dict(L=4.68, W=1.88, H=1.55, wheelbase=2.90, wheel_r=0.37, light="rear",
                    body=[(0, .20), (0, .40), (.05, .50), (.25, .58), (.93, .63), (1, .58), (1, .24), (.96, .20)],
                    cabin=[(.27, .58), (.46, .94), (.63, 1), (.80, .90), (.95, .64)]),
    "현대 코나 일렉트릭": dict(L=4.355, W=1.825, H=1.575, wheelbase=2.66, wheel_r=0.35, light="front",
                         body=[(0, .22), (0, .50), (.03, .60), (.22, .66), (.97, .68), (1, .62), (1, .24), (.97, .22)],
                         cabin=[(.27, .66), (.42, .96), (.86, 1), (.97, .86), (.97, .68)]),
}
GLASS_DARK, TIRE, LAMP_W, LAMP_R = material("1f2a33", 0.85, 0.1), material("1b1b1b"), material("f7f3e8"), material("c0262d")

def extrude_profile(points, L, H, width, z_center, x0):
    from shapely.geometry import Polygon
    poly = Polygon([(x0 + px * L, py * H) for px, py in points])
    mesh = trimesh.creation.extrude_polygon(poly, width)
    mesh.apply_translation([0, 0, z_center - width / 2])
    return mesh

def wheel(x, z, r, width):
    w = trimesh.creation.cylinder(radius=r, height=width, sections=24)
    w.apply_translation([x, r, z])
    return w

MODEL_DIR = ROOT / "02_자료" / "차량모델"
MODEL_FILES = {"기아 EV6": "EV6.glb", "현대 코나 일렉트릭": "KONA.glb"}
MAX_FACES_PER_CAR = 40000

def axis_alignment(extents):
    length, up = int(np.argmax(extents)), int(np.argmin(extents))
    side = 3 - length - up
    rot = np.zeros((4, 4)); rot[3, 3] = 1
    rot[0, length] = rot[1, up] = rot[2, side] = 1
    if np.linalg.det(rot[:3, :3]) < 0:
        rot[2, side] = -1
    return rot

def imported_parts(model, spec, x0, zc):
    """Real car asset from 02_자료/차량모델 -> list of meshes scaled to real length, front facing the building."""
    path = MODEL_DIR / MODEL_FILES.get(model, "")
    if not path.is_file():
        return None
    cfg_path = MODEL_DIR / "models.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8")).get(model, {}) if cfg_path.exists() else {}
    parts = [g.copy() for g in trimesh.load(path, force="scene").dump() if hasattr(g, "faces") and len(g.faces)]
    total = sum(len(g.faces) for g in parts)
    if total > MAX_FACES_PER_CAR:
        for i, g in enumerate(parts):
            try:
                parts[i] = g.simplify_quadric_decimation(face_count=max(50, int(len(g.faces) * MAX_FACES_PER_CAR / total)))
            except Exception:
                pass  # fast_simplification missing -> keep full detail
    bounds = trimesh.util.concatenate([p.copy() for p in parts]).bounds
    align = axis_alignment(bounds[1] - bounds[0])
    if cfg.get("flip"):
        align = trimesh.transformations.rotation_matrix(np.pi, [0, 1, 0]) @ align
    for g in parts:
        g.apply_transform(align)
    lo, hi = trimesh.util.concatenate([p.copy() for p in parts]).bounds
    scale = spec["L"] / (hi[0] - lo[0])
    for g in parts:
        g.apply_translation(-np.array([lo[0], lo[1], (lo[2] + hi[2]) / 2]))
        g.apply_scale(scale)
        g.apply_translation([x0, 0, zc])
    return parts

if ORG_PATH.exists():
    vehicles = json.loads(ORG_PATH.read_text(encoding="utf-8")).get("vehicles", [])
    for i, v in enumerate(vehicles):
        spec = VEHICLE_SPECS[v["model"]]
        x0, oy, zc = build_site.slot_center(i)
        L, Wd, H = spec["L"], spec["W"], spec["H"]
        real = imported_parts(v["model"], spec, x0, zc)
        if real:
            for k, part in enumerate(lifted(real, oy)):
                scene.add_geometry(part, node_name=f'{v["id"]}_part{k}', geom_name=f'{v["id"]}_part{k}')
            continue
        add(f'{v["id"]}_body', lifted(extrude_profile(spec["body"], L, H, Wd, zc, x0), oy), material(v["color"].lstrip("#"), rough=0.35))
        add(f'{v["id"]}_cabin', lifted(extrude_profile(spec["cabin"], L, H, Wd * 0.86, zc, x0), oy), GLASS_DARK)
        front_axle = x0 + (L - spec["wheelbase"]) / 2
        tires = [wheel(ax, zc + side * (Wd / 2 - 0.12), spec["wheel_r"], 0.26)
                 for ax in (front_axle, front_axle + spec["wheelbase"]) for side in (-1, 1)]
        add(f'{v["id"]}_wheels', lifted(tires, oy), TIRE)
        bar_y = 0.56 * H
        if spec["light"] == "rear":   # EV6: full-width rear light bar
            add(f'{v["id"]}_lamp', lifted([box(x0 + L - 0.02, zc - Wd / 2 + 0.05, x0 + L + 0.005, zc + Wd / 2 - 0.05, bar_y, bar_y + 0.05)], oy), LAMP_R)
        else:                        # Kona: seamless front LED strip
            add(f'{v["id"]}_lamp', lifted([box(x0 - 0.005, zc - Wd / 2 + 0.05, x0 + 0.02, zc + Wd / 2 - 0.05, bar_y + 0.05, bar_y + 0.08)], oy), LAMP_W)

OUT.parent.mkdir(parents=True, exist_ok=True)
scene.export(OUT)
print(f"{OUT.name}: {len(scene.geometry)} nodes, {OUT.stat().st_size/1024:.0f} KB")
