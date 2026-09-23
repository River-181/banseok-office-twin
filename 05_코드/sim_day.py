"""S3 simulation core: runs one working day and writes an event log the viewer can replay.
Times are minutes from 09:00. Every random draw comes from 04_데이터/sim_params.json."""
from __future__ import annotations

import json
import random
from pathlib import Path

import simpy

from sim_model import DATA, generate_cases, load_office

OUT = DATA.parent / "07_산출물" / "sim"
LUNCH_START, LUNCH_END, DAY_END = 180, 240, 540  # 12:00, 13:00, 18:00


def val(node):
    return node["value"] if isinstance(node, dict) and "value" in node else node


class Day:
    def __init__(self, office, seed=11):
        self.office, self.p, self.rng = office, office.params, random.Random(seed)
        self.env = simpy.Environment()
        self.events: list[dict] = []
        self.cases = generate_cases(self.p, 4000, seed=seed)
        self.case_i = 0
        self.stress: dict[str, float] = {}
        self.kpi = dict(dials=0, connects=0, callbacks=0, visit_referrals=0, visits=0, absent=0, km=0.0, closed=0)
        self.record_min = self.calibrate_record_time()

    def calibrate_record_time(self):
        """Dialing alone is far faster than the published plan (11.4 cases/checker/day), so the remainder of a case
        is treated as record keeping / ledger work and derived here instead of being guessed."""
        p = self.p["phone"]
        productive = DAY_END - (LUNCH_END - LUNCH_START) - 40
        cycle = 60 / val(p["dial_attempts_per_hour"]) * 0.35 + val(p["connect_rate"]) * (p["talk_min"]["mean"] + val(p["after_call_work_min"]))
        target = val(p["cases_per_checker_per_day"])
        return max(0.0, productive / target - cycle)

    ROLE_BY_PREFIX = {"외전": "전화실태확인원", "국전": "전화실태확인원", "R1": "전화실태확인원", "R2": "전화실태확인원",
                      "국공": "공무원", "외공": "공무원", "관리": "관리보조", "방문": "방문실태확인원"}

    def log(self, actor, action, where="", zone=None, **extra):
        role = next((v for k, v in self.ROLE_BY_PREFIX.items() if actor.startswith(k)), "기타")
        self.events.append(dict(t=round(self.env.now, 1), actor=actor, role=role, zone=zone or where,
                                action=action, where=where, **extra))

    @staticmethod
    def band(amount):
        """공유 산출물에는 금액대만 남긴다 (RED 규칙)."""
        for limit, label in ((300_000, "30만 미만"), (1_000_000, "30~100만"), (3_000_000, "100~300만"), (10_000_000, "300~1000만")):
            if amount < limit:
                return label
        return "1000만 이상"

    def next_case(self):
        self.case_i += 1
        return self.cases[self.case_i % len(self.cases)]

    def bump(self, actor, amount):
        s = self.p["stress"]
        self.stress[actor] = min(s["max"], self.stress.get(actor, 0) + amount)

    # ---------- phone checker ----------
    def checker(self, seat_no, seat):
        p, rng = self.p["phone"], self.rng
        s = self.p["stress"]
        last_break = 0.0
        self.log(seat_no, "출근", seat.zone, zone=seat.zone)
        while self.env.now < DAY_END:
            if LUNCH_START <= self.env.now < LUNCH_END:
                self.log(seat_no, "점심", "외출", zone=seat.zone)
                yield self.env.timeout(LUNCH_END - self.env.now)
                self.stress[seat_no] = max(0, self.stress.get(seat_no, 0) - s["recovery_lunch"])
                last_break = self.env.now
                continue
            if self.env.now - last_break >= val(self.p["workday"]["break_every_min"]):
                self.log(seat_no, "휴식", "탕비실", zone="RM-PANTRY")
                yield self.env.timeout(val(self.p["workday"]["break_min"]))
                self.stress[seat_no] = max(0, self.stress.get(seat_no, 0) - s["recovery_per_break_min"] * val(self.p["workday"]["break_min"]))
                last_break = self.env.now
                continue
            case = self.next_case()
            self.kpi["dials"] += 1
            yield self.env.timeout(60 / val(p["dial_attempts_per_hour"]) * 0.35)
            if rng.random() < val(p["connect_rate"]):
                talk = max(0.8, rng.gauss(p["talk_min"]["mean"], p["talk_min"]["sd"]))
                hostile = rng.random() < s["hostile_call_rate"]
                self.kpi["connects"] += 1
                self.log(seat_no, "통화", seat.zone, zone=seat.zone, case=case.id, kind=case.kind,
                         band=self.band(case.amount_krw), min=round(talk, 1), hostile=hostile)
                yield self.env.timeout(talk)
                self.bump(seat_no, s["per_hostile_call"] if hostile else s["per_call"])
                if rng.random() < val(p["callback_request_rate"]):
                    self.kpi["callbacks"] += 1
                    self.log(seat_no, "콜백약속", seat.zone, zone=seat.zone, case=case.id)
                if rng.random() < val(p["visit_referral_rate"]):
                    self.kpi["visit_referrals"] += 1
                    self.log(seat_no, "방문의뢰", seat.zone, zone=seat.zone, case=case.id, band=self.band(case.amount_krw))
                yield self.env.timeout(val(p["after_call_work_min"]))
            else:
                self.log(seat_no, "부재", seat.zone, zone=seat.zone, case=case.id)
            self.kpi["closed"] += 1
            self.log(seat_no, "기록정리", seat.zone, zone=seat.zone, case=case.id, min=round(self.record_min, 1))
            yield self.env.timeout(self.record_min)
        self.log(seat_no, "퇴근", seat.zone, zone=seat.zone, stress=round(self.stress.get(seat_no, 0), 1))

    # ---------- visit team ----------
    def team(self, team, vehicle):
        p, rng, s = self.p["visit"], self.rng, self.p["stress"]
        speed = val(p["avg_speed_kmh"])
        yield self.env.timeout(30)
        self.log(team.name, "출차", "주차장", zone="ZN-WAIT", vehicle=vehicle.id, crew=len(team.members))
        for _ in range(val(p["visits_per_team_per_day"])):
            if self.env.now > DAY_END - 60:
                break
            case = self.next_case()
            drive = max(10, rng.gauss(p["travel_min_per_visit"]["mean"], p["travel_min_per_visit"]["sd"])) / 2
            km = drive / 60 * speed
            vehicle.drive(km); self.kpi["km"] += km
            self.log(team.name, "이동", case.district, zone="현장", min=round(drive, 1), km=round(km, 1), soc=round(vehicle.soc, 2))
            yield self.env.timeout(drive)
            absent = rng.random() < val(p["absent_rate"])
            onsite = 3 if absent else max(4, rng.gauss(p["onsite_min"]["mean"], p["onsite_min"]["sd"]))
            self.kpi["visits"] += 1
            self.kpi["absent"] += absent
            self.log(team.name, "부재확인" if absent else "실태확인", case.district, zone="현장", case=case.id,
                     kind=case.kind, band=self.band(case.amount_krw), min=round(onsite, 1))
            yield self.env.timeout(onsite)
            for m in team.members:
                self.bump(m, s["per_visit"])
            vehicle.drive(km); self.kpi["km"] += km
            yield self.env.timeout(drive)
        self.log(team.name, "복귀", "주차장", zone="ZN-WAIT", vehicle=vehicle.id, soc=round(vehicle.soc, 2), odo=round(vehicle.odometer_km, 1))
        yield self.env.timeout(val(p["paperwork_min_per_visit"]) * self.kpi["visits"] / 2)
        self.log(team.name, "서류정리", "대기공간", zone="ZN-WAIT")

    def run(self):
        phone_seats = {n: s for n, s in self.office.seats.items() if n.startswith(("외전", "국전", "R1", "R2"))}
        for seat_no, seat in phone_seats.items():
            self.env.process(self.checker(seat_no, seat))
        for team, vehicle in zip(self.office.teams.values(), self.office.vehicles.values()):
            team.vehicle = vehicle.id
            self.env.process(self.team(team, vehicle))
        self.env.run(until=DAY_END + 60)
        return self


def summary(day):
    k, checkers = day.kpi, len([1 for n in day.office.seats if n.startswith(("외전", "국전", "R1", "R2"))])
    avg_stress = sum(day.stress.values()) / max(1, len(day.stress))
    return {
        "전화석": checkers, "발신": k["dials"], "연결": k["connects"],
        "연결률": round(k["connects"] / max(1, k["dials"]), 3),
        "1인당 연결": round(k["connects"] / max(1, checkers), 1),
        "1인당 처리건": round(k["closed"] / max(1, checkers), 1),
        "케이스당 기록시간(보정)": round(day.record_min, 1),
        "콜백약속": k["callbacks"], "방문의뢰": k["visit_referrals"],
        "방문": k["visits"], "부재": k["absent"], "주행 km": round(k["km"], 1),
        "평균 스트레스": round(avg_stress, 1), "이벤트": len(day.events),
    }


if __name__ == "__main__":
    day = Day(load_office()).run()
    OUT.mkdir(parents=True, exist_ok=True)
    result = dict(meta=dict(day_minutes=DAY_END, start="09:00"), kpi=summary(day),
                  stress={k: round(v, 1) for k, v in day.stress.items()}, events=day.events)
    (OUT / "day_001.json").write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    for k, v in result["kpi"].items():
        print(f"{k}: {v}")
