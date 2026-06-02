
from scheduler.models import ScenarioResult

def validate_schedule(result, battery_range_km=240):
    errors = []

    for sched in result.bus_schedules:
        for stop in sched.charging_stops:
            if stop.segment_distance_km > battery_range_km:
                errors.append(f"{sched.bus.bus_id}: range violation")
            if stop.wait_min < 0:
                errors.append(f"{sched.bus.bus_id}: negative wait")

    for station, stops in result.station_queues.items():
        ordered = sorted(stops, key=lambda s: s.charge_start_min)
        for i in range(1, len(ordered)):
            if ordered[i].charge_start_min < ordered[i-1].charge_end_min:
                errors.append(f"{station}: charger overlap")

    return errors
