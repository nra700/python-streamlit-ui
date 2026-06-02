"""
Bus Charging Scheduler — Streamlit UI
"""

import streamlit as st
import pandas as pd
from pathlib import Path

from scheduler.loader import load_scenario, list_scenarios, minutes_to_hhmm
from scheduler.engine import run_scheduler

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Bus Charging Scheduler",
    page_icon="🚌",
    layout="wide",
)

# ── Styling ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

h1, h2, h3 { font-family: 'Space Mono', monospace !important; }

.stApp { background: #0d1117; color: #e6edf3; }

section[data-testid="stSidebar"] {
    background: #161b22;
    border-right: 1px solid #30363d;
}

div[data-testid="metric-container"] {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 12px 16px;
}

.stDataFrame { border: 1px solid #30363d; border-radius: 8px; }

.operator-kpn      { color: #58a6ff; font-weight: 600; }
.operator-freshbus { color: #3fb950; font-weight: 600; }
.operator-flixbus  { color: #f78166; font-weight: 600; }

.scenario-badge {
    display: inline-block;
    background: #1f6feb22;
    border: 1px solid #1f6feb;
    color: #58a6ff;
    border-radius: 20px;
    padding: 2px 12px;
    font-family: 'Space Mono', monospace;
    font-size: 0.75rem;
    margin-bottom: 8px;
}

.section-header {
    font-family: 'Space Mono', monospace;
    font-size: 0.7rem;
    letter-spacing: 0.15em;
    color: #8b949e;
    text-transform: uppercase;
    margin: 24px 0 8px 0;
    padding-bottom: 6px;
    border-bottom: 1px solid #21262d;
}

.wait-high { color: #f78166; }
.wait-mid  { color: #e3b341; }
.wait-low  { color: #3fb950; }

.route-viz {
    display: flex;
    align-items: center;
    gap: 0;
    margin: 16px 0;
    flex-wrap: wrap;
}
.route-stop {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 6px 14px;
    font-family: 'Space Mono', monospace;
    font-size: 0.8rem;
    color: #e6edf3;
}
.route-stop.endpoint {
    background: #1f6feb22;
    border-color: #1f6feb;
    color: #58a6ff;
}
.route-stop.charging {
    background: #238636aa;
    border-color: #2ea043;
    color: #3fb950;
}
.route-arrow {
    color: #8b949e;
    padding: 0 6px;
    font-size: 0.75rem;
}
.route-dist {
    font-size: 0.65rem;
    color: #8b949e;
    font-family: 'Space Mono', monospace;
}
</style>
""", unsafe_allow_html=True)

# ── Load scenarios ────────────────────────────────────────────────────────────
SCENARIOS_DIR = Path(__file__).parent / "scenarios"
scenario_files = list_scenarios(SCENARIOS_DIR)

scenario_map = {}
for sf in scenario_files:
    sid, sname, buses, route, physics, chargers, weights = load_scenario(sf)
    scenario_map[sname] = sf

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🚌 Bus Scheduler")
    st.markdown("---")

    selected_name = st.selectbox(
        "Select Scenario",
        options=list(scenario_map.keys()),
        index=0,
    )

    st.markdown("---")
    st.markdown("### ⚖️ Override Weights")
    st.caption("These override the scenario defaults.")

    override_weights = st.toggle("Enable weight overrides", value=False)

    sid, sname, buses, route, physics, chargers, weights = load_scenario(scenario_map[selected_name])

    if override_weights:
        w_individual = st.slider("Individual bus weight", 0.0, 5.0, float(weights.get("individual", 1.0)), 0.1)
        w_operator   = st.slider("Operator fairness weight", 0.0, 5.0, float(weights.get("operator", 1.0)), 0.1)
        w_overall    = st.slider("Overall network weight", 0.0, 5.0, float(weights.get("overall", 1.0)), 0.1)
        weights = {"individual": w_individual, "operator": w_operator, "overall": w_overall}

    st.markdown("---")
    st.markdown("**Active weights**")
    for k, v in weights.items():
        st.markdown(f"`{k}` → **{v}**")

    st.markdown("---")
    st.caption(f"Speed: {physics.speed_kmh} km/h · Range: {physics.battery_range_km} km · Charge: {physics.charge_duration_min} min")

# ── Run scheduler ─────────────────────────────────────────────────────────────
result = run_scheduler(buses, route, physics, chargers, weights, scenario_id=sid)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(f'<div class="scenario-badge">{sid.upper()}</div>', unsafe_allow_html=True)
st.title(sname)

# ── Top metrics ───────────────────────────────────────────────────────────────
total_buses   = len(result.bus_schedules)
total_wait    = sum(s.total_wait_min() for s in result.bus_schedules)
avg_wait      = total_wait / total_buses if total_buses else 0
max_wait      = max((s.total_wait_min() for s in result.bus_schedules), default=0)
avg_trip      = sum(s.trip_duration_min() for s in result.bus_schedules) / total_buses if total_buses else 0

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Buses", total_buses)
c2.metric("Total wait (min)", f"{total_wait:.0f}")
c3.metric("Avg wait / bus (min)", f"{avg_wait:.1f}")
c4.metric("Max wait (min)", f"{max_wait:.0f}")
c5.metric("Avg trip duration (min)", f"{avg_trip:.0f}")

# ── Route visualisation ───────────────────────────────────────────────────────
st.markdown('<div class="section-header">Route</div>', unsafe_allow_html=True)

route_html = '<div class="route-viz">'
stops = route.stops_in_order()
for i, stop in enumerate(stops):
    cls = "endpoint" if stop in route.endpoints else "charging"
    route_html += f'<div class="route-stop {cls}">{stop}</div>'
    if i < len(stops) - 1:
        seg = route.segments[i]
        route_html += f'<div style="display:flex;flex-direction:column;align-items:center">'
        route_html += f'<span class="route-arrow">──▶</span>'
        route_html += f'<span class="route-dist">{seg.distance_km} km</span>'
        route_html += '</div>'
route_html += '</div>'
st.markdown(route_html, unsafe_allow_html=True)

# ── Scenario input table ──────────────────────────────────────────────────────
st.markdown('<div class="section-header">Scenario Input</div>', unsafe_allow_html=True)

input_rows = []
for b in buses:
    input_rows.append({
        "Bus ID": b.bus_id,
        "Operator": b.operator.upper(),
        "Direction": f"{b.origin} → {b.destination}",
        "Departure": minutes_to_hhmm(b.departure_time_min),
    })

input_df = pd.DataFrame(input_rows)
st.dataframe(input_df, use_container_width=True, hide_index=True)

# ── Per-bus timetable ─────────────────────────────────────────────────────────
st.markdown('<div class="section-header">Per-Bus Timetable</div>', unsafe_allow_html=True)

OPERATOR_COLORS = {"kpn": "🔵", "freshbus": "🟢", "flixbus": "🔴"}

bus_rows = []
for sched in sorted(result.bus_schedules, key=lambda s: s.bus.departure_time_min):
    b = sched.bus
    icon = OPERATOR_COLORS.get(b.operator, "⚪")
    stops_used = " → ".join(s.station for s in sched.charging_stops) if sched.charging_stops else "—"
    charges_detail = []
    for cs in sched.charging_stops:
        charges_detail.append(
            f"{cs.station}  arrive {minutes_to_hhmm(cs.arrive_min)}  "
            f"wait {cs.wait_min:.0f}m  "
            f"charge {minutes_to_hhmm(cs.charge_start_min)}–{minutes_to_hhmm(cs.charge_end_min)}"
        )

    bus_rows.append({
        "Bus ID": f"{icon} {b.bus_id}",
        "Operator": b.operator.upper(),
        "Route": f"{b.origin} → {b.destination}",
        "Departs": minutes_to_hhmm(sched.departure_min),
        "Charges at": stops_used,
        "Total wait (min)": f"{sched.total_wait_min():.0f}",
        "Arrives": minutes_to_hhmm(sched.arrival_min),
        "Trip duration (min)": f"{sched.trip_duration_min():.0f}",
    })

bus_df = pd.DataFrame(bus_rows)
st.dataframe(bus_df, use_container_width=True, hide_index=True)

# ── Expandable detail per bus ─────────────────────────────────────────────────
with st.expander("🔍 Detailed charging timeline per bus"):
    for sched in sorted(result.bus_schedules, key=lambda s: s.bus.departure_time_min):
        b = sched.bus
        icon = OPERATOR_COLORS.get(b.operator, "⚪")
        st.markdown(f"**{icon} {b.bus_id}** — {b.operator.upper()} — {b.origin} → {b.destination} — departs {minutes_to_hhmm(sched.departure_min)}")

        if not sched.charging_stops:
            st.markdown("  _No charging stops_")
        else:
            detail_rows = []
            for cs in sched.charging_stops:
                wait_label = f"{cs.wait_min:.0f} min"
                detail_rows.append({
                    "Station": cs.station,
                    "Arrive": minutes_to_hhmm(cs.arrive_min),
                    "Wait": wait_label,
                    "Charge start": minutes_to_hhmm(cs.charge_start_min),
                    "Charge end": minutes_to_hhmm(cs.charge_end_min),
                    "Segment dist (km)": f"{cs.segment_distance_km:.0f}",
                })
            st.dataframe(pd.DataFrame(detail_rows), use_container_width=True, hide_index=True)

        st.markdown(f"  **Arrives {b.destination}:** {minutes_to_hhmm(sched.arrival_min)} &nbsp;|&nbsp; **Total wait:** {sched.total_wait_min():.0f} min &nbsp;|&nbsp; **Trip:** {sched.trip_duration_min():.0f} min")
        st.markdown("---")

# ── Per-station view ──────────────────────────────────────────────────────────
st.markdown('<div class="section-header">Per-Station Charging Queue</div>', unsafe_allow_html=True)

station_cols = st.columns(len(route.charging_stations))

for col, station in zip(station_cols, route.charging_stations):
    with col:
        stops_at = result.station_queues.get(station, [])
        # Sort by charge_start_min to show actual queue order
        stops_sorted = sorted(stops_at, key=lambda s: s.charge_start_min)

        st.markdown(f"#### 📍 Station {station}")
        st.caption(f"{len(stops_sorted)} bus(es) · {chargers.get(station, 1)} charger(s)")

        if not stops_sorted:
            st.info("No buses charged here.")
        else:
            rows = []
            for idx, cs in enumerate(stops_sorted, 1):
                # Find which bus owns this stop
                bus_id = "—"
                for sched in result.bus_schedules:
                    if any(s is cs for s in sched.charging_stops):
                        bus_id = sched.bus.bus_id
                        break
                rows.append({
                    "#": idx,
                    "Bus": bus_id,
                    "Arrive": minutes_to_hhmm(cs.arrive_min),
                    "Wait": f"{cs.wait_min:.0f}m",
                    "Start": minutes_to_hhmm(cs.charge_start_min),
                    "End": minutes_to_hhmm(cs.charge_end_min),
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ── Operator summary ──────────────────────────────────────────────────────────
st.markdown('<div class="section-header">Operator Summary</div>', unsafe_allow_html=True)

operators = sorted(set(b.bus_id.split("-")[0] + "-" + b.operator for b in buses), key=lambda x: x.split("-")[1])
op_names = sorted(set(b.operator for b in buses))

op_rows = []
for op in op_names:
    op_scheds = [s for s in result.bus_schedules if s.bus.operator == op]
    if not op_scheds:
        continue
    total_op_wait = sum(s.total_wait_min() for s in op_scheds)
    avg_op_wait   = total_op_wait / len(op_scheds)
    max_op_wait   = max(s.total_wait_min() for s in op_scheds)
    avg_op_trip   = sum(s.trip_duration_min() for s in op_scheds) / len(op_scheds)
    icon = OPERATOR_COLORS.get(op, "⚪")
    op_rows.append({
        "Operator": f"{icon} {op.upper()}",
        "Buses": len(op_scheds),
        "Total wait (min)": f"{total_op_wait:.0f}",
        "Avg wait (min)": f"{avg_op_wait:.1f}",
        "Max wait (min)": f"{max_op_wait:.0f}",
        "Avg trip (min)": f"{avg_op_trip:.0f}",
    })

st.dataframe(pd.DataFrame(op_rows), use_container_width=True, hide_index=True)

st.markdown("---")
st.caption("Bus Charging Scheduler · Built with Python + Streamlit")
