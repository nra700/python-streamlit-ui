from __future__ import annotations

from itertools import combinations
from typing import Dict, List, Tuple

from scheduler.models import (
    Bus,
    BusSchedule,
    ChargingStop,
    Physics,
    Route,
    ScenarioResult,
)

from scheduler.rules import (
    RULE_REGISTRY,
    BaseRule,
)


class SimState:

    def __init__(self):
        self.charger_free: Dict[str, List[float]] = {}
        self._operator_waits: Dict[str, List[float]] = {}
        self.total_wait_min: float = 0.0

    def init_station(self, station: str, num_chargers: int = 1):
        self.charger_free[station] = [0.0] * num_chargers

    def earliest_charger_slot(
        self,
        station: str,
        arrive_min: float,
    ) -> Tuple[float, int]:

        slots = self.charger_free[station]

        best_idx = min(
            range(len(slots)),
            key=lambda i: max(slots[i], arrive_min),
        )

        start = max(
            slots[best_idx],
            arrive_min,
        )

        return start, best_idx

    def commit_charger(
        self,
        station: str,
        charger_idx: int,
        charge_end: float,
    ):
        self.charger_free[station][charger_idx] = charge_end

    def record_wait(
        self,
        operator: str,
        wait_min: float,
    ):
        self._operator_waits.setdefault(
            operator,
            [],
        ).append(wait_min)

        self.total_wait_min += wait_min

    def operator_avg_wait(
        self,
        operator: str,
    ) -> float:

        waits = self._operator_waits.get(
            operator,
            [],
        )

        return (
            sum(waits) / len(waits)
            if waits
            else 0.0
        )

    def operator_bus_count(
        self,
        operator: str,
    ) -> int:

        return len(
            self._operator_waits.get(
                operator,
                [],
            )
        )


def valid_station_subsets(
    bus: Bus,
    route: Route,
    physics: Physics,
) -> List[List[str]]:

    available = route.stations_between(
        bus.origin,
        bus.destination,
    )

    rng = physics.battery_range_km

    valid = []

    for size in range(len(available) + 1):

        for subset in combinations(
            available,
            size,
        ):

            pts = (
                [bus.origin]
                + list(subset)
                + [bus.destination]
            )

            feasible = all(
                route.distance_between(
                    pts[i],
                    pts[i + 1],
                ) <= rng
                for i in range(len(pts) - 1)
            )

            if feasible:
                valid.append(
                    list(subset)
                )

    return valid


def build_candidate_plan(
    bus: Bus,
    stations: List[str],
    route: Route,
    physics: Physics,
    state: SimState,
):

    stops = []

    current_time = (
        bus.departure_time_min
    )

    prev_stop = bus.origin

    for station in stations:

        dist = route.distance_between(
            prev_stop,
            station,
        )

        travel = physics.travel_time_min(
            dist
        )

        arrive = (
            current_time + travel
        )

        charge_start, _ = (
            state.earliest_charger_slot(
                station,
                arrive,
            )
        )

        wait = (
            charge_start - arrive
        )

        charge_end = (
            charge_start
            + physics.charge_duration_min
        )

        stops.append(
            ChargingStop(
                station=station,
                arrive_min=arrive,
                wait_min=wait,
                charge_start_min=charge_start,
                charge_end_min=charge_end,
                segment_distance_km=dist,
            )
        )

        current_time = charge_end
        prev_stop = station

    final_dist = route.distance_between(
        prev_stop,
        bus.destination,
    )

    arrival_min = (
        current_time
        + physics.travel_time_min(
            final_dist
        )
    )

    return stops, arrival_min


def score_plan(
    bus: Bus,
    stops: List[ChargingStop],
    state: SimState,
    weights: Dict[str, float],
    rules: List[BaseRule],
):

    total = 0.0

    for stop in stops:

        for rule in rules:

            weight = weights.get(
                rule.weight_key,
                0.0,
            )

            if weight != 0:
                total += (
                    weight
                    * rule.cost(
                        bus,
                        stop,
                        state,
                    )
                )

    return total


def run_scheduler(
    buses: List[Bus],
    route: Route,
    physics: Physics,
    chargers_per_station: Dict[str, int],
    weights: Dict[str, float],
    scenario_id: str = "unknown",
) -> ScenarioResult:

    state = SimState()

    for station in route.charging_stations:

        state.init_station(
            station,
            chargers_per_station.get(
                station,
                1,
            ),
        )

    sorted_buses = sorted(
        buses,
        key=lambda b: b.departure_time_min,
    )

    bus_schedules = []

    station_queues = {
        s: []
        for s in route.charging_stations
    }

    for bus in sorted_buses:

        subsets = valid_station_subsets(
            bus,
            route,
            physics,
        )

        if not subsets:
            raise ValueError(
                f"No valid plan for {bus.bus_id}"
            )

        best_plan = None
        best_arrival = None
        best_score = float("inf")

        for subset in subsets:

            stops, arrival = (
                build_candidate_plan(
                    bus,
                    subset,
                    route,
                    physics,
                    state,
                )
            )

            score = score_plan(
                bus,
                stops,
                state,
                weights,
                RULE_REGISTRY,
            )

            if (
                score < best_score
                or (
                    score == best_score
                    and (
                        best_arrival is None
                        or arrival < best_arrival
                    )
                )
            ):
                best_score = score
                best_plan = stops
                best_arrival = arrival

        for stop in best_plan:

            _, charger_idx = (
                state.earliest_charger_slot(
                    stop.station,
                    stop.arrive_min,
                )
            )

            state.commit_charger(
                stop.station,
                charger_idx,
                stop.charge_end_min,
            )

            state.record_wait(
                bus.operator,
                stop.wait_min,
            )

            station_queues[
                stop.station
            ].append(stop)

        bus_schedules.append(
            BusSchedule(
                bus=bus,
                charging_stops=best_plan,
                departure_min=bus.departure_time_min,
                arrival_min=best_arrival,
            )
        )

    for station in station_queues:
        station_queues[station].sort(
            key=lambda x: x.charge_start_min
        )

    return ScenarioResult(
        scenario_id=scenario_id,
        bus_schedules=bus_schedules,
        station_queues=station_queues,
    )