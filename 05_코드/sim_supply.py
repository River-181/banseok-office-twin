"""Phase 2: pantry stock and the parking round-trip that visit teams lose before every trip."""
from __future__ import annotations

import json
import math
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "04_데이터"

STAFF = 51          # 좌석 수 기준 (교대 없다고 가정)
VISIT_TEAMS = 2
ITEMS = {   # 1인 1일 소비량 (assumed), 포장 단위, 현재 재고(미입력 시 0)
    "맥심 모카골드": dict(per_person_day=1.2, pack=100, unit="스틱", stock_packs=3),
    "둥글레차": dict(per_person_day=0.4, pack=100, unit="티백", stock_packs=2),
    "종이컵": dict(per_person_day=2.0, pack=1000, unit="개", stock_packs=1),
    "생수 500ml": dict(per_person_day=0.6, pack=40, unit="병", stock_packs=4),
    "A4 용지": dict(per_person_day=8.0, pack=2500, unit="장", stock_packs=2),
}
PARKING = dict(walk_m=0, walk_min_one_way=0, note="주차장 위치 미정 — 0이면 왕복 시간 반영 없음")


def stock_report(staff=STAFF):
    rows = {}
    for name, it in ITEMS.items():
        daily = it["per_person_day"] * staff
        have = it["stock_packs"] * it["pack"]
        rows[name] = dict(daily=round(daily, 1), stock=have, unit=it["unit"],
                          days_left=round(have / daily, 1) if daily else None,
                          monthly_packs=math.ceil(daily * 21 / it["pack"]))
    return rows


def parking_impact(walk_min_one_way, visits_per_team_per_day=4, teams=VISIT_TEAMS):
    """Every trip costs a round trip on foot plus unlocking/logging the car."""
    admin_min = 4                      # 차량일지·열쇠·점검
    per_trip = walk_min_one_way * 2 + admin_min
    daily = per_trip * visits_per_team_per_day
    return dict(per_trip_min=per_trip, per_team_day_min=daily, all_teams_day_min=daily * teams,
                lost_visits_per_day=round(daily / 110, 2), monthly_hours=round(daily * teams * 21 / 60, 1))


if __name__ == "__main__":
    report = dict(stock=stock_report(), parking={})
    print(f"{'품목':<14}{'하루 소비':>10}{'현재 재고':>12}{'남은 일수':>10}{'월 발주':>10}")
    for name, r in report["stock"].items():
        print(f"{name:<14}{r['daily']:>9.1f}{r['unit']}{r['stock']:>11}{r['unit']}{r['days_left']:>10.1f}{r['monthly_packs']:>9}팩")
    print("\n주차장 도보 시간별 손실 (방문 2팀 기준)")
    for minutes in (0, 3, 5, 8, 12):
        p = parking_impact(minutes)
        report["parking"][f"{minutes}분"] = p
        print(f"  편도 {minutes:>2}분 → 1회 {p['per_trip_min']:>2}분, 하루 {p['all_teams_day_min']:>3}분, "
              f"월 {p['monthly_hours']:>5.1f}시간, 방문 {p['lost_visits_per_day']}건 상당 손실")
    (DATA / "supply_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
