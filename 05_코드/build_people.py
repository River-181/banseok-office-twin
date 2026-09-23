"""Detail geometry: office chairs, desk equipment and seated/standing people (meters, Y-up)."""
import numpy as np
import trimesh

ROLE_COLORS = {"운영공무원": "2f4a6b", "동행공무원": "35706b", "전화실태확인원": "4a5b74",
               "방문실태확인원": "6b6b3a", "관리보조": "7a5a46", "방문객": "6e5b7a"}
SKIN, HAIR = "d9b48f", "2a2622"


def _cyl(radius, height, xyz, sections=12, axis="y"):
    mesh = trimesh.creation.cylinder(radius=radius, height=height, sections=sections)
    if axis == "y":
        mesh.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    mesh.apply_translation(xyz)
    return mesh


def chair_parts(x, z, size, face, task=True):
    """Office chair: seat pad, backrest, armrests, gas lift, 5-star base with casters."""
    cx, cz, s = x + size / 2, z + size / 2, size
    dirs = {"N": (0, -1), "S": (0, 1), "E": (1, 0), "W": (-1, 0)}[face]        # direction the person faces
    bx, bz = -dirs[0] * s * 0.36, -dirs[1] * s * 0.36                          # backrest sits behind them
    frame, soft = [], []
    soft.append(trimesh.creation.box(extents=[s * 0.78, 0.09, s * 0.78]))
    soft[-1].apply_translation([cx, 0.44, cz])
    back = trimesh.creation.box(extents=[s * 0.74 if dirs[0] == 0 else 0.09, 0.52 if task else 0.42, 0.09 if dirs[0] == 0 else s * 0.74])
    back.apply_transform(trimesh.transformations.rotation_matrix(np.radians(8) * (1 if dirs[1] >= 0 else -1), [dirs[1], 0, -dirs[0]]))
    back.apply_translation([cx + bx, 0.44 + 0.3, cz + bz])
    soft.append(back)
    if task:
        for side in (-1, 1):                                                    # armrests
            ax, az = -dirs[1] * side * s * 0.42, dirs[0] * side * s * 0.42
            arm = trimesh.creation.box(extents=[0.07 if dirs[0] == 0 else s * 0.5, 0.05, s * 0.5 if dirs[0] == 0 else 0.07])
            arm.apply_translation([cx + ax, 0.62, cz + az])
            frame.append(arm)
            frame.append(trimesh.creation.box(extents=[0.05, 0.16, 0.05]))
            frame[-1].apply_translation([cx + ax, 0.53, cz + az])
        frame.append(_cyl(0.035, 0.34, [cx, 0.24, cz]))                         # gas lift
        for k in range(5):                                                       # star base + casters
            ang = k * 2 * np.pi / 5
            leg = trimesh.creation.box(extents=[0.3, 0.04, 0.06])
            leg.apply_transform(trimesh.transformations.rotation_matrix(ang, [0, 1, 0]))
            leg.apply_translation([cx + np.cos(ang) * 0.15, 0.08, cz + np.sin(ang) * 0.15])
            frame.append(leg)
            frame.append(_cyl(0.035, 0.03, [cx + np.cos(ang) * 0.28, 0.04, cz + np.sin(ang) * 0.28], axis="x"))
    else:
        for sx, sz in ((-1, -1), (-1, 1), (1, -1), (1, 1)):                      # meeting chair legs
            frame.append(_cyl(0.022, 0.44, [cx + sx * s * 0.3, 0.22, cz + sz * s * 0.3], sections=8))
    return soft, frame


def desk_equipment(desk, equip):
    """Monitors, keyboard, phone or tablet on a desk, oriented to the person's side."""
    x, z, w, d, top = desk["x"] / 100, desk["y"] / 100, desk["w"] / 100, desk["d"] / 100, desk["h"] / 100
    long_x = w >= d
    screens, plastics = [], []
    n_screen = sum(1 for e in equip if e.endswith("PC"))
    for i in range(max(n_screen, 1) if "태블릿" not in equip else 0):
        off = (i - (n_screen - 1) / 2) * 0.5
        panel = trimesh.creation.box(extents=[0.46 if long_x else 0.05, 0.3, 0.05 if long_x else 0.46])
        cx = x + w / 2 + (off if long_x else 0)
        cz = z + d / 2 + (0 if long_x else off)
        panel.apply_translation([cx, top + 0.28, cz - d * 0.28 if long_x else cz, ][:3])
        panel.apply_translation([0, 0, 0])
        screens.append(panel)
        stand = trimesh.creation.box(extents=[0.16, 0.12, 0.12])
        stand.apply_translation([cx, top + 0.07, cz - d * 0.28 if long_x else cz])
        plastics.append(stand)
    if "태블릿" in equip:
        tab = trimesh.creation.box(extents=[0.19, 0.24, 0.02])
        tab.apply_transform(trimesh.transformations.rotation_matrix(np.radians(-25), [1, 0, 0]))
        tab.apply_translation([x + w / 2, top + 0.11, z + d / 2])
        screens.append(tab)
    if "전화" in equip:
        phone = trimesh.creation.box(extents=[0.17, 0.06, 0.13])
        phone.apply_translation([x + w * 0.78, top + 0.03, z + d * 0.7])
        plastics.append(phone)
    key = trimesh.creation.box(extents=[0.38 if long_x else 0.14, 0.02, 0.14 if long_x else 0.38])
    key.apply_translation([x + w / 2, top + 0.02, z + d * 0.72 if long_x else z + d / 2])
    plastics.append(key)
    return screens, plastics


def person(x, z, face, seated=True, height=1.7):
    """Low-poly figure: head, torso, arms, legs. Seated pose folds the thighs toward the desk."""
    dirs = {"N": (0, -1), "S": (0, 1), "E": (1, 0), "W": (-1, 0)}[face]
    fx, fz = dirs
    body, skin, hair = [], [], []
    hip_y = 0.47 if seated else 0.88
    torso = trimesh.creation.box(extents=[0.38, 0.55 if seated else 0.6, 0.24])
    torso.apply_transform(trimesh.transformations.rotation_matrix(np.arctan2(fx, fz), [0, 1, 0]))
    torso.apply_translation([x, hip_y + 0.3, z])
    body.append(torso)
    for side in (-1, 1):
        arm = trimesh.creation.box(extents=[0.11, 0.42, 0.12])
        arm.apply_translation([x - fz * side * 0.24, hip_y + 0.3, z + fx * side * 0.24])
        body.append(arm)
        if seated:
            thigh = trimesh.creation.box(extents=[0.15 if fx == 0 else 0.42, 0.14, 0.42 if fx == 0 else 0.15])
            thigh.apply_translation([x - fz * side * 0.1 + fx * 0.21, hip_y - 0.03, z + fx * side * 0.1 + fz * 0.21])
            body.append(thigh)
            shin = trimesh.creation.box(extents=[0.13, 0.42, 0.13])
            shin.apply_translation([x - fz * side * 0.1 + fx * 0.4, hip_y - 0.27, z + fx * side * 0.1 + fz * 0.4])
            body.append(shin)
        else:
            leg = trimesh.creation.box(extents=[0.14, 0.86, 0.14])
            leg.apply_translation([x - fz * side * 0.1, 0.44, z + fx * side * 0.1])
            body.append(leg)
    neck_y = hip_y + 0.62
    head = trimesh.creation.icosphere(subdivisions=2, radius=0.105)
    head.apply_scale([1, 1.18, 1]); head.apply_translation([x, neck_y + 0.11, z])
    skin.append(head)
    cap = trimesh.creation.icosphere(subdivisions=2, radius=0.108)
    cap.apply_scale([1, 1.1, 1])
    cap.apply_translation([x - fx * 0.012, neck_y + 0.15, z - fz * 0.012])
    hair.append(cap)
    for side in (-1, 1):                                   # hands on the desk / at the sides
        hand = trimesh.creation.icosphere(subdivisions=1, radius=0.055)
        hand.apply_translation([x - fz * side * 0.23 + fx * (0.3 if seated else 0.02), hip_y + 0.16, z + fx * side * 0.23 + fz * (0.3 if seated else 0.02)])
        skin.append(hand)
    return body, skin, hair
