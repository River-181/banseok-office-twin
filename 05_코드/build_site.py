"""Building shell, surroundings and the parking diorama (meters, Y-up, drawing frame: x = drawing right = SE, z = drawing down = SW).
Surroundings are schematic (conf low): positions from Naver/Kakao map screenshots, heights from roadview."""
import numpy as np
import trimesh

FLOOR_HEIGHTS = [4.5, 3.9, 3.9, 3.9, 3.9, 3.9, 3.9, 3.9, 3.9]  # 1F commercial, 2F~9F office
FLOOR3_Y = sum(FLOOR_HEIGHTS[:2])                                # 8.4 m: our office floor
ROOF_Y = sum(FLOOR_HEIGHTS)
OFFICE_W, OFFICE_D, CORE_D = 21.35, 15.55, 3.6                   # office rectangle + core strip on the NE (drawing top)
BLD_X0, BLD_X1, BLD_Z0, BLD_Z1 = -0.3, OFFICE_W + 0.3, -CORE_D, OFFICE_D + 0.3


def site_materials(material):
    return dict(ground=material("d9d6cc"), asphalt=material("5a5f66"), lane=material("f4f4f4"), sidewalk=material("c9c4b8"),
                grass=material("9cb77f"), hill=material("7f9d68"), field=material("b9c98f"), tree=material("5e8a4f"), trunk=material("7a5c3e"),
                spandrel=material("dfe3e6"), band=material("2f5f8a", 0.55, 0.15), stone=material("c7c2ba"), core=material("b8b8b8"),
                roof=material("9aa0a6"), sign_green=material("3a9a4a"), apt=material("eef0f2"), apt_glass=material("9fb4c7"),
                shop=material("d8cfc2"), shed=material("aab4be"), base=material("3b4046"), leader=material("e08a2e"), island=material("cfd3d6"))


def add_building(add, box, M):
    """Tower shell. 3F walls are skipped (the detailed office sits there); floors above 3F are tagged BLD_UP for the hide toggle."""
    y = 0.0
    for level, h in enumerate(FLOOR_HEIGHTS, start=1):
        tag = "BLD_UP" if level > 3 else "BLD"
        slab = box(BLD_X0, BLD_Z0, BLD_X1, BLD_Z1, y + h - 0.3, y + h - 0.06)
        # the 3F slab is our office ceiling -> own tag so it can be hidden without hiding the shell
        slab_name = "CEIL_F3_SLAB" if level == 3 else f"{tag}_F{level}_SLAB"
        add(slab_name, slab, M["roof"] if level == len(FLOOR_HEIGHTS) else M["spandrel"])
        if level != 3:
            skin = "stone" if level <= 2 else "band"
            walls = [box(BLD_X0, BLD_Z1 - 0.2, BLD_X1, BLD_Z1, y, y + h - 0.3),        # SW (road)
                     box(BLD_X0, BLD_Z0, BLD_X0 + 0.2, BLD_Z1, y, y + h - 0.3),        # NW
                     box(BLD_X1 - 0.2, BLD_Z0, BLD_X1, BLD_Z1, y, y + h - 0.3)]        # SE
            add(f"{tag}_F{level}_SKIN", walls, M[skin])
            add(f"{tag}_F{level}_SPANDREL", [box(BLD_X0 - 0.02, BLD_Z1 - 0.02, BLD_X1 + 0.02, BLD_Z1 + 0.02, y, y + 0.9),
                                              box(BLD_X0 - 0.02, BLD_Z0, BLD_X0 + 0.02, BLD_Z1, y, y + 0.9),
                                              box(BLD_X1 - 0.02, BLD_Z0, BLD_X1 + 0.02, BLD_Z1, y, y + 0.9)], M["spandrel"])
        y += h
    # core (EV / stairs / toilets): solid below and above 3F; on 3F only its back strip, leaving the lift-lobby corridor
    # in front of the office entrance (the niche room sits inside that corridor)
    add("BLD_CORE_LOW", box(BLD_X0, BLD_Z0, BLD_X1, -0.1, 0, FLOOR3_Y), M["core"])
    add("BLD_CORE_3F", box(BLD_X0, BLD_Z0, BLD_X1, -2.0, FLOOR3_Y, FLOOR3_Y + FLOOR_HEIGHTS[2]), M["core"])
    add("BLD_UP_CORE", box(BLD_X0, BLD_Z0, BLD_X1, -0.1, FLOOR3_Y + FLOOR_HEIGHTS[2], ROOF_Y + 3.2), M["core"])
    add("BLD_SIGN_4F", box(BLD_X0 + 2, BLD_Z1 + 0.02, BLD_X1 - 2, BLD_Z1 + 0.08, 12.9, 13.9), M["sign_green"])


def tree(x, z, h=6.0):
    top = trimesh.creation.cone(radius=h * 0.28, height=h * 0.7, sections=10)
    top.apply_transform(trimesh.transformations.rotation_matrix(-np.pi / 2, [1, 0, 0]))
    top.apply_translation([x, h * 0.3, z])
    trunk = trimesh.creation.cylinder(radius=0.15, height=h * 0.3, sections=8)
    trunk.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    trunk.apply_translation([x, h * 0.15, z])
    return top, trunk


def add_surroundings(add, box, M):
    add("SITE_GROUND", box(-90, -90, 110, 110, -0.10, -0.05), M["ground"])
    # 북유성대로: 8-lane arterial parallel to the SW face (≈36 m incl. median), near edge ~12 m from the facade
    road_z0 = BLD_Z1 + 12
    add("SITE_ROAD_MAIN", box(-90, road_z0, 110, road_z0 + 36, -0.045, 0.0), M["asphalt"])
    add("SITE_ROAD_MEDIAN", box(-90, road_z0 + 17, 110, road_z0 + 19, 0.004, 0.2), M["grass"])
    add("SITE_LANES", [box(-90, road_z0 + d - 0.08, 110, road_z0 + d + 0.08, 0.004, 0.014) for d in (4.3, 8.6, 23.1, 27.4)], M["lane"])
    add("SITE_SIDEWALK_SW", box(-90, BLD_Z1 + 0.3, 110, road_z0 + 0.01, -0.04, 0.12), M["sidewalk"])
    # side street along the SE face (street parking seen in roadview) and back road on the NE (북유성대로316번길)
    add("SITE_ROAD_SE", box(BLD_X1 + 3, -60, BLD_X1 + 11, road_z0 - 0.01, -0.035, 0.006), M["asphalt"])
    add("SITE_ROAD_NE", box(-90, BLD_Z0 - 26, 110, BLD_Z0 - 20, -0.03, 0.012), M["asphalt"])
    # neighbours (schematic boxes, heights from roadview/map labels)
    blocks = {
        "SITE_NB_CHURCH_NW": ((-24, -8, -6, 10), 9, "shop"),         # 고백교회·공임나라 쪽 저층
        "SITE_NB_ANNEX_NW": ((-11, 11, -3, 18), 7, "shed"),
        "SITE_NB_BENZ_N": ((-40, -58, -8, -32), 12, "shed"),         # 벤츠 서비스센터
        "SITE_NB_88MOTO_SE": ((BLD_X1 + 14, 2, BLD_X1 + 34, 16), 8, "shop"),
        "SITE_NB_SHOPS_SE": ((BLD_X1 + 14, 18, BLD_X1 + 30, 26), 7, "shop"),
        "SITE_NB_HYUNDAI_S": ((BLD_X1 + 36, 6, BLD_X1 + 56, 24), 9, "shed"),
        "SITE_NB_3M_E": ((BLD_X1 + 16, -30, BLD_X1 + 32, -14), 6, "shed"),
    }
    for name, ((x0, z0, x1, z1), h, mat) in blocks.items():
        add(name, box(x0, z0, x1, z1, 0, h), M[mat])
    # 반석마을 apartments across the road (tall slabs)
    for i, x in enumerate((-60, -28, 4, 36, 68)):
        z0 = road_z0 + 36 + 18 + (i % 2) * 14
        add(f"SITE_APT_{i + 1}", box(x, z0, x + 22, z0 + 12, 0, 54 + (i % 3) * 6), M["apt"])
    # greenery to the east: fields and a hill
    add("SITE_FIELD_E", box(BLD_X1 + 42, -70, 110, -10, -0.025, 0.05), M["field"])
    hill = trimesh.creation.icosphere(subdivisions=2, radius=1.0)
    hill.apply_scale([45, 14, 40]); hill.apply_translation([95, -4, -70])
    add("SITE_HILL_E", hill, M["hill"])
    trees = [t for x in range(-80, 105, 12) for t in tree(x, road_z0 - 2.5, 7)]
    trees += [t for x in range(-80, 105, 16) for t in tree(x, road_z0 + 18, 6)]
    tops, trunks = trees[0::2], trees[1::2]
    add("SITE_TREES", list(tops), M["tree"]); add("SITE_TRUNKS", list(trunks), M["trunk"])


# ---------- parking diorama ----------
# The real lot is elsewhere (location unknown). Instead of faking it next to the building we show it as a floating
# "inset diorama": its own raised plinth, a scale-model base, and a dashed leader line back to the entrance — the same
# convention architectural boards and city-builder games use for off-site facilities (inset vignette + leader).
DIORAMA_ORIGIN = np.array([44.0, 18.0, -30.0])   # x, y(height), z : floats above the east fields, clear of the site
DIORAMA_SIZE = (7.0, 16.2)                        # plinth footprint for 6 slots x 2.5 m


def add_parking_diorama(add, box, M):
    ox, oy, oz = DIORAMA_ORIGIN
    w, d = DIORAMA_SIZE
    add("PARK_PLINTH", box(ox - 0.6, oz - 0.6, ox + w + 0.6, oz + d + 0.6, oy - 1.2, oy - 0.07), M["base"])
    add("PARK_SLAB", box(ox - 0.3, oz - 0.3, ox + w + 0.3, oz + d + 0.3, oy - 0.05, oy - 0.005), M["asphalt"])
    add("PARK_LINES", [box(ox + 0.3, oz + 0.3 + 2.5 * i - 0.05, ox + w - 0.5, oz + 0.3 + 2.5 * i + 0.05, oy + 0.002, oy + 0.007)
                       for i in range(7)], M["lane"])  # lines sit 5 mm proud of the slab
    entrance = np.array([15.0, 0.2, BLD_Z0 - 0.5])
    target = np.array([ox, oy - 0.6, oz + d / 2])
    dashes = []
    for k in range(0, 40, 2):
        a, b = k / 40, (k + 1) / 40
        p = entrance + (target - entrance) * a + np.array([0, np.sin(np.pi * a) * 10, 0])
        q = entrance + (target - entrance) * b + np.array([0, np.sin(np.pi * b) * 10, 0])
        seg = trimesh.creation.cylinder(radius=0.12, segment=[p, q], sections=6)
        dashes.append(seg)
    add("PARK_LEADER", dashes, M["leader"])
    return ox, oy, oz


def slot_center(i):
    ox, oy, oz = DIORAMA_ORIGIN
    return ox + 0.5, oy, oz + 0.3 + 2.5 * (i + 0.5)


# ---------- direction signpost for real-world POIs (distances measured from 북유성대로 336) ----------
SIGN_POS = (24.5, 0.0, 17.0)          # by the sidewalk on the 북유성대로 side
SIGN_PICKS = ["반석역 (1호선 종점)", "반석역 버스정류장(북유성대로)", "CU 대전반석점 (24h)", "포유마트", "동네약국", "우리은행 노은지점", "역전우동0410 반석점"]


def add_signpost(add, box, M, poi_path):
    """Arrow boards on one pole, each turned to the real bearing of that place."""
    import json as _json
    if not poi_path.exists():
        return []
    pois = {p["name"]: p for p in _json.loads(poi_path.read_text(encoding="utf-8"))["pois"]}
    sx, _, sz = SIGN_POS
    add("SITE_SIGN_POLE", box(sx - 0.06, sz - 0.06, sx + 0.06, sz + 0.06, 0, 3.6), M["core"])
    tips = []
    for i, name in enumerate(SIGN_PICKS):
        poi = pois.get(name)
        if not poi:
            continue
        theta = np.radians(poi["bearing"] - 148.0)          # drawing x-axis points at azimuth 148°
        y = 3.2 - i * 0.34
        board = trimesh.creation.box(extents=[2.1, 0.26, 0.05])
        board.apply_translation([1.15, 0, 0])
        board.apply_transform(trimesh.transformations.rotation_matrix(-theta, [0, 1, 0]))
        board.apply_translation([sx, y, sz])
        add(f"SITE_SIGN_{i}", board, M["spandrel"] if i % 2 else M["sidewalk"])
        tips.append(dict(name=name.split(" (")[0], m=poi["walk_m"], min=poi["walk_min"],
                         pos=[sx + np.cos(theta) * 2.4, y + 0.2, sz + np.sin(theta) * 2.4]))
    return tips
