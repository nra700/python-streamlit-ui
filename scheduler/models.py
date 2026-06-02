"""
Core data models for the bus charging scheduler.
All domain objects are plain dataclasses — no business logic here.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict


@dataclass
class Segment:
    """A road segment between two stops on a route."""
    from_stop: str
    to_stop: str
    distance_km: float


@dataclass
class Route:
    """A full route described as an ordered list of segments."""
    segments: List[Segment]
    charging_stations: List[str]   # ordered list of schedulable stations
    endpoints: List[str]           # origin / destination (not scheduled)

    def stops_in_order(self) -> List[str]:
        """All stops from origin to destination in order."""
        stops = [self.segments[0].from_stop]
        for seg in self.segments:
            stops.append(seg.to_stop)
        return stops

    def distance_between(self, a: str, b: str) -> float:
        """Total distance between stop a and stop b (order-independent)."""
        stops = self.stops_in_order()
        ia, ib = stops.index(a), stops.index(b)
        if ia > ib:
            ia, ib = ib, ia
        return sum(s.distance_km for s in self.segments[ia:ib])

    def stations_between(self, origin: str, destination: str) -> List[str]:
        """Charging stations a bus travelling from origin→destination visits."""
        stops = self.stops_in_order()
        io, id_ = stops.index(origin), stops.index(destination)
        if io < id_:
            return [s for s in self.charging_stations if stops.index(s) > io and stops.index(s) < id_]
        else:
            # reverse direction
            rev = list(reversed(stops))
            ro, rd = rev.index(origin), rev.index(destination)
            return [s for s in reversed(self.charging_stations)
                    if stops.index(s) > id_ and stops.index(s) < io]


@dataclass
class Physics:
    """Physical constants for the simulation."""
    battery_range_km: float
    charge_duration_min: float
    speed_kmh: float

    def travel_time_min(self, distance_km: float) -> float:
        return (distance_km / self.speed_kmh) * 60


@dataclass
class Bus:
    """A single bus with its departure info."""
    bus_id: str
    operator: str
    origin: str
    destination: str
    departure_time_min: float   # minutes since midnight
    priority: int = 0           
    tags: Dict = field(default_factory=dict)  


@dataclass
class ChargingStop:
    """A single charging event for one bus at one station."""
    station: str
    arrive_min: float       # when bus physically arrives at station
    wait_min: float         # how long bus queues before charger is free
    charge_start_min: float # = arrive_min + wait_min
    charge_end_min: float   # = charge_start_min + charge_duration
    segment_distance_km: float  # distance driven to reach this station


@dataclass
class BusSchedule:
    bus: Bus
    charging_stops: List[ChargingStop]
    departure_min: float
    arrival_min: float

    def total_wait_min(self) -> float:
        return sum(s.wait_min for s in self.charging_stops)

    def trip_duration_min(self) -> float:
        return self.arrival_min - self.departure_min


@dataclass
class ScenarioResult:
    """Full output of a scheduler run."""
    scenario_id: str
    bus_schedules: List[BusSchedule]
    station_queues: Dict[str, List[ChargingStop]]  # station -> ordered list of stops
