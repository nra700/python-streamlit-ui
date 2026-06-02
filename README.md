# Bus Charging Scheduler

A scheduling system for electric buses on the Bengaluru → Kochi route, built with Python + Streamlit.

## Quick Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

The app opens at `http://localhost:8501`. Pick any scenario from the dropdown.

## Running the Project

### Create a Virtual Environment

**macOS / Linux**

```bash
python -m venv venv
source venv/bin/activate
```

**Windows**

```bash
python -m venv venv
venv\Scripts\activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run the Application

```bash
streamlit run app.py
```

The application will be available at:

`http://localhost:8501`

## Explore Scenarios

The application includes five predefined scenarios:

- **Scenario 1** – Even spacing
- **Scenario 2** – Bunched departures
- **Scenario 3** – Asymmetric load
- **Scenario 4** – Operator fairness emphasis
- **Scenario 5** – Worst-case charger contention

For each scenario, the UI displays:

- Bus schedules
- Charging plans
- Station queues
- Wait times
- Schedule summary metrics

## Running Tests

Run all tests:

```bash
pytest
```

Run tests with verbose output:

```bash
pytest -v
```

Run a specific test file:

```bash
pytest tests/test_validator.py
```

```bash
pytest tests/test_rules.py
```

## How to Change a Weight

Open the relevant scenario JSON file (e.g. `scenarios/scenario_1.json`) and edit the `weights` block:

```json
"weights": {
  "individual": 1.0,
  "operator":   2.0,
  "overall":    0.5
}
```

You can also override weights at runtime using the sidebar sliders in the app.

## How to Add a New Rule

1. Open `scheduler/rules.py`.
2. Write a class that extends `BaseRule`:

```python
class ElectricityCostRule(BaseRule):
    weight_key = "electricity"   # must match key in scenario JSON weights

    def cost(self, bus, candidate, state):
        # candidate.charge_start_min = wall-clock minute charging begins
        hour = (candidate.charge_start_min // 60) % 24
        peak_hours = range(18, 22)
        return 2.0 if hour in peak_hours else 1.0
```

3. Register it at the bottom of `rules.py`:

```python
RULE_REGISTRY.append(ElectricityCostRule())
```

4. Add `"electricity": 1.5` to any scenario's `weights` block.

Done. The engine picks it up automatically.

## How to Add a New Scenario

Copy any existing scenario JSON, give it a new `scenario_id` and filename (`scenario_6.json`), edit the buses and weights. Drop it in `scenarios/`. The app picks it up on next load.

## Project Structure

```text
bus-charging-scheduler/
├── app.py                  # Streamlit UI
├── scheduler/
│   ├── engine.py           # Greedy simulation + cost scoring
│   ├── rules.py            # Pluggable cost rules
│   ├── models.py           # Domain dataclasses
│   ├── loader.py           # JSON scenario loader
│   └── validator.py        # Schedule validation
├── tests/
│   ├── test_validator.py
│   └── test_rules.py
├── scenarios/
│   ├── scenario_1.json     # Even spacing
│   ├── scenario_2.json     # Bunched start
│   ├── scenario_3.json     # Asymmetric load
│   ├── scenario_4.json     # Operator heavy (KPN)
│   └── scenario_5.json     # Worst case convergence
├── ARCHITECTURE.md
├── README.md
└── requirements.txt
```
<img width="1470" height="956" alt="Screenshot 2026-06-02 at 2 55 52 PM" src="https://github.com/user-attachments/assets/69161323-c8ce-44dc-b319-5be2d35f661d" />

