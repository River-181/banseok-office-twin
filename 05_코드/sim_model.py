"""S1 object model: floorplan_3F.json + org.json + sim_params.json -> typed objects (engine-neutral)."""
from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "04_데이터"


@dataclass
class Seat:
    id: str
    seat_no: str
    zone: str
    x: float
    y: float
    occupant: str | None = None


@dataclass
class Member:
    name: str
    role: str
    program: str | None = None
    team: str | None = None
    seat: str | None = None
    stress: float = 0.0
    skill: float = 1.0


@dataclass
class Team:
    id: str
    name: str
    members: list[str]
    vehicle: str | None = None


@dataclass
class Vehicle:
    id: str
    model: str
    seats: int
    battery_kwh: float
    km_per_kwh: float
    color: str = "#cccccc"
    soc: float = 1.0
    team: str | None = None
    odometer_km: float = 0.0

    @property
    def range_km(self) -> float:
        return self.battery_kwh * self.soc * self.km_per_kwh

    def drive(self, km: float) -> None:
        self.soc = max(0.0, self.soc - km / (self.battery_kwh * self.km_per_kwh))
        self.odometer_km += km


@dataclass
class Asset:
    id: str
    kind: str
    label: str
    zone: str | None


@dataclass
class Case:
    id: str
    program: str
    kind: str
    amount_krw: int
    district: str
    attempts: int = 0
    status: str = "open"
    history: list[str] = field(default_factory=list)


@dataclass
class Office:
    seats: dict[str, Seat]
    members: list[Member]
    teams: dict[str, Team]
    vehicles: dict[str, Vehicle]
    assets: dict[str, Asset]
    params: dict

    def summary(self) -> str:
        by_role: dict[str, int] = {}
        for m in self.members:
            by_role[m.role] = by_role.get(m.role, 0) + 1
        occupied = sum(1 for s in self.seats.values() if s.occupant)
        lines = [f"seats {len(self.seats)} (occupied {occupied})",
                 f"members {len(self.members)} " + ", ".join(f"{k} {v}" for k, v in by_role.items()),
                 f"teams {len(self.teams)}, vehicles {len(self.vehicles)}, assets {len(self.assets)}"]
        lines += [f"  {v.id}: {v.model} range {v.range_km:.0f} km" for v in self.vehicles.values()]
        return "\n".join(lines)


ASSET_TYPES = {"printer", "mfp", "shredder", "fridge", "water_dispenser", "cabinet", "locker", "equipment_rack", "sink_counter"}


def load_office() -> Office:
    plan = json.loads((DATA / "floorplan_3F.json").read_text(encoding="utf-8"))
    org = json.loads((DATA / "org.json").read_text(encoding="utf-8"))
    params = json.loads((DATA / "sim_params.json").read_text(encoding="utf-8"))

    seats = {f["seat_no"]: Seat(f["id"], f["seat_no"], f.get("room") or f.get("zone"), f["x"] + f["w"] / 2, f["y"] + f["d"] / 2)
             for f in plan["furniture"] if "seat_no" in f}
    assets = {f["id"]: Asset(f["id"], f["type"], f["label"], f.get("room") or f.get("zone"))
              for f in plan["furniture"] if f["type"] in ASSET_TYPES}
    members = [Member(m["name"], m["role"], m.get("program"), m.get("team"), m.get("seat")) for m in org["members"]]
    for m in members:
        if m.seat in seats:
            seats[m.seat].occupant = m.name
    teams = {t["id"]: Team(t["id"], t["name"], t["members"], t.get("vehicle")) for t in org["teams"]}
    defaults = params["vehicle_defaults"]
    vehicles = {v["id"]: Vehicle(v["id"], v["model"], v["seats"],
                                 v.get("battery_kwh") or defaults[v["model"]]["battery_kwh"],
                                 defaults[v["model"]]["km_per_kwh"], v.get("color", "#cccccc"), team=v.get("team"))
                for v in org["vehicles"]}
    return Office(seats, members, teams, vehicles, assets, params)


def generate_cases(params: dict, n: int, program: str = "국세외수입", seed: int = 7) -> list[Case]:
    rng = random.Random(seed)
    spec = params["cases"]
    kinds, weights = zip(*spec["types"].items())
    amount = spec["amount_krw"]
    return [Case(f"CASE-{i:05d}", program, rng.choices(kinds, weights)[0],
                 int(rng.lognormvariate(amount["lognormal_mu"], amount["lognormal_sigma"]) // 1000 * 1000),
                 rng.choice(spec["districts"]))
            for i in range(1, n + 1)]


if __name__ == "__main__":
    office = load_office()
    print(office.summary())
    sample = generate_cases(office.params, 1000)
    mix: dict[str, int] = {}
    for c in sample:
        mix[c.kind] = mix.get(c.kind, 0) + 1
    median = sorted(c.amount_krw for c in sample)[len(sample) // 2]
    print("case mix", mix, f"median {median:,} KRW")
