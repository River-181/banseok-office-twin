"""Banseok 3F office: single source of truth -> floorplan_3F.json + floorplan_3F_clean.svg
Units: cm. Origin: NW inner corner of main rectangle. x -> plan-right (east on drawing), y -> plan-down.
'plan_north' = top edge of the paper drawing (NOT verified true north)."""
import csv
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "04_데이터"

W, D = 2135, 1555

def rect(id_, type_, label, x, y, w, d, h, **kw):
    return dict(id=id_, type=type_, label=label, x=x, y=y, w=w, d=d, h=h, **kw)

rooms = [
    dict(id="RM-KT", name="국세 전화실", kind="enclosed", poly=[[0,0],[375,0],[375,375],[0,375]], conf="high"),
    dict(id="RM-PANTRY", name="탕비실", kind="enclosed", poly=[[375,0],[725,0],[725,375],[375,375]], conf="high"),
    dict(id="RM-STORE", name="(미상) 캐비닛실/문서고", kind="enclosed", poly=[[725,0],[1075,0],[1075,375],[725,375]], conf="mid", note="이름 없음. 기둥 C1 포함"),
    dict(id="RM-NICHE", name="(미상) 돌출부 소실", kind="enclosed", poly=[[915,-175],[1225,-175],[1225,0],[915,0]], conf="mid", note="175 치수는 돌출 깊이로 해석. 테이블 150x90"),
    dict(id="RM-R1", name="사○○실 (라벨 잘림)", kind="enclosed", poly=[[1635,0],[2135,0],[2135,450],[1635,450]], conf="high"),
    dict(id="RM-R2", name="전○○실 (라벨 잘림)", kind="enclosed", poly=[[1635,450],[2135,450],[2135,850],[1635,850]], conf="high"),
    dict(id="RM-R3", name="(미상) 소회의/작업실 A", kind="enclosed", poly=[[1745,850],[2135,850],[2135,1050],[1745,1050]], conf="high"),
    dict(id="RM-R4", name="(미상) 소회의/작업실 B", kind="enclosed", poly=[[1745,1050],[2135,1050],[2135,1250],[1745,1250]], conf="high"),
    dict(id="RM-R5", name="(미상) 회의실", kind="enclosed", poly=[[1745,1250],[2135,1250],[2135,1555],[1745,1555]], conf="high", note="우측 치수합 1530 vs 좌측 1555 -> 25cm 오차를 R5에 흡수"),
    dict(id="ZN-KG", name="국세 공무원 구역", kind="open_zone", poly=[[0,375],[380,375],[380,785],[0,785]], conf="high"),
    dict(id="ZN-KOG", name="국세외 공무원 구역", kind="open_zone", poly=[[0,785],[380,785],[380,1555],[0,1555]], conf="high"),
    dict(id="ZN-KOT", name="국세외 전화 구역", kind="open_zone", poly=[[380,375],[875,375],[875,1555],[380,1555]], conf="high"),
    dict(id="ZN-WAIT", name="방문실태확인원 대기공간", kind="open_zone", poly=[[1055,375],[1635,375],[1635,850],[1745,850],[1745,1555],[1055,1555]], conf="high"),
    dict(id="ZN-LOBBY", name="출입 로비/안내", kind="open_zone", poly=[[1075,0],[1635,0],[1635,375],[1075,375]], conf="mid"),
]

# wall types: EXT (exterior + ribbon window), CORE (core-side solid), GYP (gypsum solid), GLS (glass partition), GLS_FILM (glass + privacy film)
walls = [
    dict(id="W-N", a=[0,0], b=[2135,0], type="CORE", t=20, conf="high", note="엘리베이터·화장실 코어 쪽 (River 확인)"),
    dict(id="W-W", a=[0,0], b=[0,1555], type="EXT", t=30, conf="mid"),
    dict(id="W-S", a=[0,1555], b=[2135,1555], type="EXT", t=30, conf="mid"),
    dict(id="W-E", a=[2135,0], b=[2135,1555], type="EXT", t=30, conf="mid"),
    dict(id="W-NICHE", poly=[[915,0],[915,-175],[1225,-175],[1225,0]], type="CORE", t=20, conf="mid"),
    dict(id="P-KT-S", a=[0,375], b=[375,375], type="GLS", t=10, conf="low", note="국세전화실 남측: 하부불투명+상부유리 가정"),
    dict(id="P-PAN-S", a=[375,375], b=[1075,375], type="GYP", t=10, conf="mid"),
    dict(id="P-KT-PAN", a=[375,0], b=[375,375], type="GYP", t=10, conf="mid"),
    dict(id="P-PAN-STO", a=[725,0], b=[725,375], type="GYP", t=10, conf="mid"),
    dict(id="P-STO-E", a=[1075,0], b=[1075,375], type="GYP", t=10, conf="mid"),
    dict(id="P-R12-W", a=[1635,0], b=[1635,850], type="GLS", t=10, conf="low"),
    dict(id="P-R1-R2", a=[1635,450], b=[2135,450], type="GYP", t=10, conf="low"),
    dict(id="P-R2-S", a=[1635,850], b=[2135,850], type="GYP", t=10, conf="low"),
    dict(id="P-R345-W", a=[1745,850], b=[1745,1555], type="GLS_FILM", t=10, conf="low"),
    dict(id="P-R3-R4", a=[1745,1050], b=[2135,1050], type="GYP", t=10, conf="low"),
    dict(id="P-R4-R5", a=[1745,1250], b=[2135,1250], type="GYP", t=10, conf="low"),
]

# doors: wall id, span along wall axis, swing side, kind
doors = [
    dict(id="D-ENT", wall="W-N", axis="x", span=[1410,1575], into="south", kind="양개 강화유리문(가정)", h=240, conf="mid", note="도면 스윙선 길이 ~165cm"),
    dict(id="D-NICHE", wall="W-N", axis="x", span=[1130,1225], into="north", kind="여닫이", h=210, conf="mid"),
    dict(id="D-KT", wall="P-KT-S", axis="x", span=[275,365], into="north", kind="여닫이(유리 가정)", h=210, conf="high"),
    dict(id="D-PAN", wall="P-PAN-S", axis="x", span=[630,720], into="north", kind="여닫이", h=210, conf="high"),
    dict(id="D-STO", wall="P-PAN-S", axis="x", span=[730,835], into="north", kind="여닫이", h=210, conf="high"),
    dict(id="D-R1", wall="P-R12-W", axis="y", span=[355,450], into="east", kind="여닫이(유리 가정)", h=210, conf="high"),
    dict(id="D-R2", wall="P-R12-W", axis="y", span=[460,555], into="east", kind="여닫이(유리 가정)", h=210, conf="high"),
    dict(id="D-R3", wall="P-R345-W", axis="y", span=[855,950], into="east", kind="여닫이(유리 가정)", h=210, conf="high"),
    dict(id="D-R4", wall="P-R345-W", axis="y", span=[1055,1150], into="east", kind="여닫이(유리 가정)", h=210, conf="high"),
    dict(id="D-R5", wall="P-R345-W", axis="y", span=[1255,1350], into="east", kind="여닫이(유리 가정)", h=210, conf="high"),
]

windows = [dict(id=f"WIN-{w}", wall=f"W-{w}", kind="ribbon", sill=85, head=245, mullion_pitch=150, conf="mid",
                note="3면 창 존재 확인(River). 로드뷰상 커튼월 띠창 + 일부 프로젝트창. 창대·상단 높이는 가정") for w in ("W", "S", "E")]

columns = [
    rect("C1", "column", "기둥", 910, 0, 100, 100, 260, conf="mid", note="도면상 ~100x100"),
    rect("C2", "column", "기둥", 2065, 1485, 70, 70, 260, conf="mid"),
]

# standard furniture catalog (KS/조달 통용 규격 기준 가정, 실측 시 여기만 수정): w, d, h in cm
CATALOG = dict(
    desk_op=(140, 70, 72),      # 사무용 책상 W1400
    desk_std=(120, 60, 72),     # 사무용 책상 W1200
    desk_call=(100, 60, 72),    # 콜센터 책상 W1000 (전화실태확인원)
    locker=(90, 45, 180),       # 스틸 사물함 D450
    shelf=(40, 180),            # 선반 D400, H1800
    partition_wall=(6, 180),    # 이동식 가벽 T60
)
F = []  # furniture
def add(*a, **k): F.append(rect(*a, **k))

# 국세 전화실
add("KT-P1", "printer", "프린터", 96, 0, 46, 45, 90, room="RM-KT")
add("KT-P2", "printer", "프린터", 143, 0, 46, 45, 90, room="RM-KT")
for i, (x, y) in enumerate([(65, 75), (125, 75), (65, 195), (125, 195)], 1):
    add(f"KT-D{i}", "desk", "전화(내+전)", x, y, 60, 120, 72, rot=90, room="RM-KT", equip=["내부망PC", "전화"])
add("KT-D5", "desk", "전화(내+전)", 315, 20, 60, 120, 72, rot=90, room="RM-KT", equip=["내부망PC", "전화"])
add("KT-D6", "desk", "전화(내+전)", 315, 140, 60, 120, 72, rot=90, room="RM-KT", equip=["내부망PC", "전화"])

# 탕비실
add("PAN-WD", "water_dispenser", "정수기", 380, 45, 40, 40, 110, room="RM-PANTRY")
add("PAN-SINK", "sink_counter", "싱크대", 375, 90, 60, 220, 85, room="RM-PANTRY")
add("PAN-FR", "fridge", "냉장고", 375, 310, 65, 65, 180, room="RM-PANTRY")
add("PAN-T1", "table", "테이블", 430, 5, 90, 60, 72, room="RM-PANTRY")
add("PAN-RT1", "round_table", "원탁 Ø80", 515, 110, 80, 80, 72, room="RM-PANTRY")
add("PAN-RT2", "round_table", "원탁 Ø80", 515, 230, 80, 80, 72, room="RM-PANTRY")

# 캐비닛실
for i in range(6):
    add(f"STO-CAB{i+1}", "cabinet", "캐비닛", 725, i*45, 55, 45, 180, room="RM-STORE")
for i in range(4):
    add(f"STO-CAB{i+7}", "cabinet", "캐비닛", 1020, 190+i*45, 55, 45, 180, room="RM-STORE")
add("NIC-T1", "table", "테이블 150x90", 920, -175, 150, 90, 72, room="RM-NICHE")

# 로비/안내
add("LOB-CAB1", "cabinet", "캐비닛", 1075, 270, 55, 45, 180, zone="ZN-LOBBY")
add("LOB-CAB2", "cabinet", "캐비닛", 1075, 315, 55, 45, 180, zone="ZN-LOBBY")
add("LOB-FR1", "fridge", "냉장고", 905, 380, 60, 60, 180, zone="ZN-KOT")
add("LOB-FR2", "fridge", "냉장고", 965, 380, 60, 60, 180, zone="ZN-KOT")
add("LOB-WD", "water_dispenser", "정수기", 1025, 380, 45, 45, 110, zone="ZN-KOT")
add("LOB-MG1", "desk", "관리(내)", 1260, 10, 90, 95, 72, zone="ZN-LOBBY", equip=["내부망PC"], conf="low")
add("LOB-MG2", "desk", "관리(내)", 1260, 105, 90, 95, 72, zone="ZN-LOBBY", equip=["내부망PC"], conf="low")
add("LOB-INFO", "reception", "안내데스크", 1353, 10, 55, 190, 105, zone="ZN-LOBBY")

# 국세 공무원 구역
add("KG-CAB", "cabinet", "캐비닛", 0, 380, 50, 45, 180, zone="ZN-KG")
add("KG-OP", "desk", "운영공무원(내+외+전)", 90, 465, 140, 70, 72, zone="ZN-KG", equip=["내부망PC", "외부망PC", "전화"])
add("KG-PR", "printer", "프린터", 300, 380, 50, 45, 90, zone="ZN-KG")
add("KG-D1", "desk", "동행공무원(내+외)", 90, 628, 70, 140, 72, rot=90, zone="ZN-KG", equip=["내부망PC", "외부망PC"])
add("KG-D2", "desk", "동행공무원(내+외+전)", 160, 628, 70, 140, 72, rot=90, zone="ZN-KG", equip=["내부망PC", "외부망PC", "전화"])
# 국세외 공무원 구역
add("KOG-CAB", "cabinet", "캐비닛", 0, 785, 50, 45, 180, zone="ZN-KOG")
add("KOG-OP", "desk", "운영공무원(내+외+전)", 90, 880, 140, 70, 72, zone="ZN-KOG", equip=["내부망PC", "외부망PC", "전화"])
add("KOG-PR1", "printer", "프린터", 300, 790, 50, 45, 90, zone="ZN-KOG")
for i, (x, y, lab) in enumerate([(90, 1040, "운영공무원(내+외+전)"), (160, 1040, "동행공무원(내+외)"), (90, 1180, "동행공무원(내+외)"), (160, 1180, "동행공무원(내+외)")], 1):
    add(f"KOG-D{i}", "desk", lab, x, y, 70, 140, 72, rot=90, zone="ZN-KOG")
for i in range(3):
    add(f"KOG-PR{i+2}", "printer", "프린터", 180+i*50, 1450, 50, 45, 90, zone="ZN-KOG")
add("KOG-RACK", "equipment_rack", "장비랙", 0, 1505, 155, 50, 200, zone="ZN-KOG")

# 국세외 전화 구역: 3 clusters x (2 rows x 4 cols), desks 120x70 (assumed), 180cm aisles (standard)
KOT_X0, KOT_ROWS, (KOT_W, KOT_D) = 385, [740, 1040, 1340], CATALOG["desk_call"][:2]
for c, cy in enumerate(KOT_ROWS, 1):
    for r in (1, 2):
        for col in range(1, 5):
            add(f"KOT-C{c}R{r}-{col}", "desk", "전화(내+전)", KOT_X0+(col-1)*KOT_W, cy+(r-1)*KOT_D, KOT_W, KOT_D, 72,
                zone="ZN-KOT", equip=["내부망PC", "전화"], conf="mid")

# 사물함 / 가벽 / 복합기
add("LOCKER", "locker", "사물함", 875, 780, CATALOG["locker"][1], 775, 180, zone="ZN-KOT")
add("WALL-SHELF", "partition", "가벽", 920, 705, CATALOG["partition_wall"][0], 850, 180, zone="ZN-WAIT")
add("SHELF", "shelf", "선반", 926, 705, CATALOG["shelf"][0], 850, CATALOG["shelf"][1], zone="ZN-WAIT")
add("MFP1", "mfp", "복합기", 1000, 645, 62, 55, 110, zone="ZN-WAIT")
add("MFP2", "mfp", "복합기", 1062, 645, 62, 55, 110, zone="ZN-WAIT")
add("SHRED", "shredder", "세단기", 1124, 645, 61, 55, 80, zone="ZN-WAIT")
add("WALL-SHORT", "partition", "가벽", 1055, 705, 105, 40, 150, zone="ZN-WAIT")
add("WAIT-WD", "water_dispenser", "정수기", 1072, 750, 55, 42, 110, zone="ZN-WAIT")

# 대기공간
for i, (cx, cy) in enumerate([(1120, 950), (1370, 950), (1620, 950), (1120, 1200), (1370, 1200), (1620, 1200)], 1):
    add(f"WAIT-RT{i}", "round_table", "원탁 Ø120(가정)", cx-60, cy-60, 120, 120, 72, zone="ZN-WAIT", conf="mid")
for i, x in enumerate([1140, 1295, 1450], 1):
    add(f"WAIT-T{i}", "table", "테이블 150x90", x, 1460, 150, 90, 72, zone="ZN-WAIT")

# R1 / R2 : tablet phone desks with side panels
for r, cy in ((1, 130), (2, 200)):
    for col in range(1, 4):
        add(f"R1-{r}-{col}", "desk", "전화(태블릿)", 1775+(col-1)*120, cy, 120, 70, 72, room="RM-R1", equip=["태블릿", "전화"])
for (r, cy, cols) in ((1, 580, 3), (2, 650, 2)):
    for col in range(1, cols+1):
        add(f"R2-{r}-{col}", "desk", "전화(태블릿)", 1775+(col-1)*120, cy, 120, 70, 72, room="RM-R2", equip=["태블릿", "전화"])
for i, x in enumerate([1770, 1890, 2010], 1):
    add(f"R1-PNL{i}", "desk_panel", "칸막이", x, 115, 5, 170, 120, room="RM-R1")
    add(f"R2-PNL{i}", "desk_panel", "칸막이", x, 565, 5, 170, 120, room="RM-R2")

# R3~R5
for i, x in enumerate([1755, 1880, 2005], 1):
    add(f"R3-T{i}", "table", "테이블 120x60", x, 985, 120, 60, 72, room="RM-R3")
for i, x in enumerate([1760, 1945], 1):
    add(f"R4-T{i}", "table", "테이블 180x80", x, 1165, 180, 80, 72, room="RM-R4")
add("R5-T1", "table", "테이블 240x120", 1830, 1305, 240, 120, 72, room="RM-R5")

# chairs: side = where the person sits relative to the desk/table
byid = {f["id"]: f for f in F}
def chair(id_, cx, cy, face, kind="task"):
    size = 60 if kind == "task" else 50
    F.append(rect(id_, "chair", "의자", cx-size/2, cy-size/2, size, size, 100 if kind == "task" else 85, face=face, kind=kind))
FACE = dict(N="S", S="N", W="E", E="W")
def seat(fid, side, n=1, kind="task", gap=32):
    f = byid[fid]
    for k in range(n):
        t = (k+1)/(n+1)
        if side in "NS":
            cx, cy = f["x"]+f["w"]*t, (f["y"]-gap if side == "N" else f["y"]+f["d"]+gap)
        else:
            cx, cy = (f["x"]-gap if side == "W" else f["x"]+f["w"]+gap), f["y"]+f["d"]*t
        chair(f"CH-{fid}-{side}{k+1}", cx, cy, FACE[side], kind)

for fid, side in [("KT-D1","W"),("KT-D3","W"),("KT-D2","E"),("KT-D4","E"),("KT-D5","W"),("KT-D6","W"),
                  ("KG-OP","N"),("KG-D1","W"),("KG-D2","E"),("KOG-OP","N"),("KOG-D1","W"),("KOG-D3","W"),("KOG-D2","E"),("KOG-D4","E"),
                  ("LOB-MG1","W"),("LOB-MG2","W")]:
    seat(fid, side)
for f in list(F):
    fid = f["id"]
    if fid.startswith("KOT-") or fid.startswith("R1-") or fid.startswith("R2-"):
        if f["type"] == "desk":
            row = fid.split("R")[-1].split("-")[0] if fid.startswith("KOT-") else fid.split("-")[1]
            seat(fid, "N" if row == "1" else "S")
for fid, side, n in [("R3-T1","N",1),("R3-T2","N",1),("R3-T3","N",1),("R4-T1","N",2),("R4-T2","N",2),("R5-T1","N",3),("R5-T1","S",3),
                     ("WAIT-T1","N",2),("WAIT-T2","N",2),("WAIT-T3","N",2),("PAN-T1","S",1),("NIC-T1","S",2)]:
    seat(fid, side, n, kind="meeting")
for f in [f for f in F if f["type"] == "round_table"]:
    for side in (("N","S","E","W") if f["w"] >= 100 else ("W","E")):
        seat(f["id"], side, kind="meeting", gap=22 if f["w"] >= 100 else 28)

# readable seat numbers per zone (names live in 04_데이터/좌석배정.csv, never in this file)
SEAT_PREFIX = [("KT-D", "국전"), ("KG-", "국공"), ("KOG-", "외공"), ("KOT-", "외전"), ("R1-", "R1"), ("R2-", "R2"), ("LOB-MG", "관리")]
seat_count = {}
for f in F:
    prefix = next((p for k, p in SEAT_PREFIX if f["id"].startswith(k)), None) if f["type"] == "desk" else None
    if prefix:
        seat_count[prefix] = seat_count.get(prefix, 0) + 1
        f["seat_no"] = f"{prefix}-{seat_count[prefix]:02d}"

# zone partitions (desk-level screens)
parts = [
    ("PT-KG1", [20, 620], [320, 620], 120), ("PT-KG2", [160, 620], [160, 776], 120),
    ("PT-FREE", [378, 440], [378, 640], 150),
    ("PT-KOG1", [20, 1032], [320, 1032], 120), ("PT-KOG3", [20, 1328], [320, 1328], 120),
    ("PT-KOG4", [160, 1032], [160, 1328], 120),
    ("PT-KOT-W", [378, 655], [378, 1555], 120),
]
partitions = [dict(id=i, a=a, b=b, h=h, type="screen", conf="mid") for i, a, b, h in parts]

# low desk-mounted screens on phone-operator desks (desk top 72 + ~38)
for c, cy in enumerate(KOT_ROWS, 1):
    partitions.append(dict(id=f"DS-KOT{c}-F", a=[KOT_X0, cy+KOT_D], b=[KOT_X0+4*KOT_W, cy+KOT_D], h=110, type="desk_screen", conf="mid"))
    for i, x in enumerate([KOT_X0+KOT_W, KOT_X0+2*KOT_W, KOT_X0+3*KOT_W], 1):
        partitions.append(dict(id=f"DS-KOT{c}-S{i}", a=[x, cy], b=[x, cy+2*KOT_D], h=110, type="desk_screen", conf="mid"))
partitions += [dict(id="DS-KT-F", a=[125, 75], b=[125, 315], h=110, type="desk_screen", conf="mid"),
               dict(id="DS-KT-S", a=[65, 195], b=[185, 195], h=110, type="desk_screen", conf="mid")]

annotations = [
    dict(kind="handwriting", text=t, near=n, conf="low") for t, n in [
        ("현아", "KOT-C2R1-2 위"), ("다솔(?)", "KOT-C2R1-3 위"), ("○경(?)", "KOT-C2R2-2 아래"), ("은영", "KOT-C2R2-3 아래"),
        ("민경", "KOT-C3R1-2 위"), ("인숙", "KOT-C3R1-3 위"), ("경희", "KOT-C3R2-2 아래"), ("원석(?)", "KOT-C3R2-4 아래")]
] + [dict(kind="tape", text="흰 테이프로 가려진 이름", near="각 클러스터 1열 위/아래", conf="high")]

model = dict(
    meta=dict(site="대전광역시 유성구 북유성대로 336 3층 (반석동 664-3)", units="cm", origin="NW inner corner (drawing top-left)",
              axes="x=drawing right, y=drawing down", plan_north="drawing top = building NE face (core side). Azimuth of drawing-up ≈ 58° (Naver map footprint, walls parallel to 북유성대로)",
              orientation=dict(top="NE 58° 코어(엘베·화장실)", right="SE 148° 88모토 쪽 소로", bottom="SW 238° 북유성대로", left="NW 328° 공임나라 쪽", conf="mid"),
              footprint=[W, D], scale_note="원본 도면은 축척 불일치 개략도. 치수 텍스트 우선, 미표기 치수는 국소 비례 추정",
              defaults=dict(ceiling=260, floor_to_floor=390, ext_wall=30, partition=10, door=[90, 210], desk_h=72, screen_h=120)),
    rooms=rooms, walls=walls, doors=doors, windows=windows, columns=columns, partitions=partitions, furniture=F, annotations=annotations)

json.dump(model, open(DATA_DIR / "floorplan_3F.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

SEAT_CSV = DATA_DIR / "좌석배정.csv"
if not SEAT_CSV.exists():
    with open(SEAT_CSV, "w", newline="", encoding="utf-8-sig") as fp:
        writer = csv.writer(fp)
        writer.writerow(["seat_no", "id", "role", "name"])
        writer.writerows([f["seat_no"], f["id"], f["label"], ""] for f in F if "seat_no" in f)

# ---------- SVG ----------
PAD, S = 60, 0.5  # px per cm
def X(v): return PAD + v*S
def Y(v): return PAD + (v+175)*S
col = dict(EXT="#1b2a3a", CORE="#555", GYP="#8a8a8a", GLS="#3aa0d8", GLS_FILM="#7fbfe0")
fill = dict(desk="#d9d4c7", table="#e6dcc4", round_table="#e6dcc4", cabinet="#b9b1a0", printer="#fff", mfp="#fff", shredder="#fff",
            fridge="#fff", water_dispenser="#fff", sink_counter="#cfd8dc", locker="#b9b1a0", partition_shelf="#a1887f", partition="#a1887f",
            reception="#c8b28a", chair="#6d7b8a", shelf="#a1887f", equipment_rack="#444", desk_panel="#777", column="#6b6b6b")
out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {int(X(W)+PAD)} {int(Y(D)+PAD+30)}" font-family="sans-serif">',
       '<rect width="100%" height="100%" fill="#fbfaf7"/>']
for r in rooms:
    pts = " ".join(f"{X(x)},{Y(y)}" for x, y in r["poly"])
    out.append(f'<polygon id="{r["id"]}" points="{pts}" fill="{"#eef3f7" if r["kind"]=="enclosed" else "#f6f3ea"}" stroke="none"/>')
for f in F:
    if f["type"] == "round_table":
        out.append(f'<circle id="{f["id"]}" cx="{X(f["x"]+f["w"]/2)}" cy="{Y(f["y"]+f["d"]/2)}" r="{f["w"]/2*S}" fill="{fill[f["type"]]}" stroke="#666" stroke-width="0.6"/>')
    else:
        sw = 1.6 if f.get("circled") else 0.6
        sc = "#c0392b" if f.get("circled") else "#666"
        out.append(f'<rect id="{f["id"]}" x="{X(f["x"])}" y="{Y(f["y"])}" width="{f["w"]*S}" height="{f["d"]*S}" fill="{fill.get(f["type"],"#ddd")}" stroke="{sc}" stroke-width="{sw}"/>')
for c in columns:
    out.append(f'<rect id="{c["id"]}" x="{X(c["x"])}" y="{Y(c["y"])}" width="{c["w"]*S}" height="{c["d"]*S}" fill="#6b6b6b"/>')
for p in partitions:
    out.append(f'<line id="{p["id"]}" x1="{X(p["a"][0])}" y1="{Y(p["a"][1])}" x2="{X(p["b"][0])}" y2="{Y(p["b"][1])}" stroke="#8d6e63" stroke-width="2" stroke-dasharray="4 2"/>')
for w in walls:
    sw = max(2, w["t"]*S*0.5)
    if "poly" in w:
        pts = " ".join(f"{X(x)},{Y(y)}" for x, y in w["poly"])
        out.append(f'<polyline id="{w["id"]}" points="{pts}" fill="none" stroke="{col[w["type"]]}" stroke-width="{sw}"/>')
    else:
        out.append(f'<line id="{w["id"]}" x1="{X(w["a"][0])}" y1="{Y(w["a"][1])}" x2="{X(w["b"][0])}" y2="{Y(w["b"][1])}" stroke="{col[w["type"]]}" stroke-width="{sw}"/>')
for w in windows:
    wl = next(v for v in walls if v["id"] == w["wall"])
    out.append(f'<line x1="{X(wl["a"][0])}" y1="{Y(wl["a"][1])}" x2="{X(wl["b"][0])}" y2="{Y(wl["b"][1])}" stroke="#8fd0f7" stroke-width="3.5" stroke-dasharray="{w["mullion_pitch"]*S-2} 2"/>')
for d in doors:
    wl = next(v for v in walls if v["id"] == d["wall"])
    a, b = d["span"]
    if d["axis"] == "x":
        y = wl["a"][1] if "a" in wl else 0
        out.append(f'<line x1="{X(a)}" y1="{Y(y)}" x2="{X(b)}" y2="{Y(y)}" stroke="#fbfaf7" stroke-width="7"/>')
        dy = -1 if d["into"] == "north" else 1
        if d["id"] == "D-ENT":
            m, r = (a+b)/2, (b-a)/2*S
            out.append(f'<path d="M{X(a)},{Y(y)} L{X(a)},{Y(y+(m-a))} A{r},{r} 0 0 0 {X(m)},{Y(y)} M{X(b)},{Y(y)} L{X(b)},{Y(y+(b-m))} A{r},{r} 0 0 1 {X(m)},{Y(y)}" fill="none" stroke="#e67e22" stroke-width="1"/>')
            continue
        out.append(f'<path d="M{X(a)},{Y(y)} L{X(a)},{Y(y+dy*(b-a))} A{(b-a)*S},{(b-a)*S} 0 0 {1 if dy<0 else 0} {X(b)},{Y(y)}" fill="none" stroke="#e67e22" stroke-width="1"/>')
    else:
        x = wl["a"][0]
        out.append(f'<line x1="{X(x)}" y1="{Y(a)}" x2="{X(x)}" y2="{Y(b)}" stroke="#fbfaf7" stroke-width="7"/>')
        out.append(f'<path d="M{X(x)},{Y(a)} L{X(x+(b-a))},{Y(a)} A{(b-a)*S},{(b-a)*S} 0 0 1 {X(x)},{Y(b)}" fill="none" stroke="#e67e22" stroke-width="1"/>')
for r in rooms:
    xs = [p[0] for p in r["poly"]]; ys = [p[1] for p in r["poly"]]
    cx, cy = sum(xs)/len(xs), min(ys) + 22
    out.append(f'<text x="{X(cx)}" y="{Y(cy)}" font-size="10" text-anchor="middle" fill="#1b2a3a" font-weight="bold">{r["name"]}</text>')
out.append(f'<text x="{PAD}" y="{Y(D)+28}" font-size="10" fill="#333">Banseok 3F clean redraw · units cm · 1px=2cm · ext wall(navy) core(gray) gypsum(light gray) glass(blue) · drawing-up ≈ NE 58°</text>')
out.append("</svg>")
open(DATA_DIR / "floorplan_3F_clean.svg", "w", encoding="utf-8").write("\n".join(out))
try:
    import cairosvg
    cairosvg.svg2png(url=str(DATA_DIR / "floorplan_3F_clean.svg"), write_to=str(DATA_DIR / "floorplan_3F_clean.png"), output_width=2000)
    png_note = "png updated"
except Exception as err:  # cairo system lib missing -> brew install cairo
    png_note = f"png skipped ({type(err).__name__})"
print(len(F), "furniture;", sum(1 for f in F if f["type"] == "desk"), "desks;", png_note)
