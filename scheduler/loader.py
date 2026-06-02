"""
Scenario loader: reads a JSON scenario file and returns domain model objects.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Tuple

from scheduler.models import Bus, Physics, Route, Segment


def _parse_time(t: str) -> float:
    """Convert 'HH:MM' to minutes since midnight."""
    h, m = map(int, t.split(":"))
    return h * 60 + m


def minutes_to_hhmm(minutes: float) -> str:
    """Convert minutes since midnight to 'HH:MM' string."""
    total = int(round(minutes))
    h = (total // 60) % 24
    m = total % 60
    return f"{h:02d}:{m:02d}"


def load_scenario(path: str | Path) -> Tuple[str, str, list[Bus], Route, Physics, Dict[str, int], Dict[str, float]]:
    """
    Load a scenario JSON file.

    Returns:
        (scenario_id, scenario_name, buses, route, physics, chargers_per_station, weights)
    """
    with open(path) as f:
        data = json.load(f)

    scenario_id = data["scenario_id"]
    scenario_name = data.get("name", scenario_id)

    # Route
    segments = [
        Segment(
            from_stop=s["from"],
            to_stop=s["to"],
            distance_km=s["distance_km"],
        )
        for s in data["route"]["segments"]
    ]
    route = Route(
        segments=segments,
        charging_stations=data["route"]["charging_stations"],
        endpoints=data["route"]["endpoints"],
    )

    # Physics
    ph = data["physics"]
    physics = Physics(
        battery_range_km=ph["battery_range_km"],
        charge_duration_min=ph["charge_duration_min"],
        speed_kmh=ph["speed_kmh"],
    )

    # Chargers per station
    chargers_per_station: Dict[str, int] = data.get("chargers_per_station", {})

    # Weights
    weights: Dict[str, float] = data.get("weights", {})

    # Buses
    buses = []
    for b in data["buses"]:
        buses.append(Bus(
            bus_id=b["bus_id"],
            operator=b["operator"],
            origin=b["origin"],
            destination=b["destination"],
            departure_time_min=_parse_time(b["departure_time"]),
            priority=b.get("priority", 0),
            tags=b.get("tags", {}),
        ))

    return scenario_id, scenario_name, buses, route, physics, chargers_per_station, weights


def list_scenarios(scenarios_dir: str | Path) -> list[Path]:
    """Return all scenario JSON files sorted by name."""
    d = Path(scenarios_dir)
    return sorted(d.glob("scenario_*.json"))
