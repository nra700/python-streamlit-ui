"""
Pluggable cost rules for the scheduling engine.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scheduler.models import Bus, ChargingStop
    from scheduler.engine import SimState


class BaseRule(ABC):
    weight_key: str = ""

    @abstractmethod
    def cost(self, bus, candidate, state) -> float:
        ...


class IndividualWaitRule(BaseRule):
    """Penalises long waits for a single bus. weight_key: individual"""
    weight_key = "individual"

    def cost(self, bus, candidate, state):
        return candidate.wait_min


class OperatorFairnessRule(BaseRule):
    """Penalises worsening the average delay for the bus's operator. weight_key: operator"""
    weight_key = "operator"

    def cost(self, bus, candidate, state):
        op = bus.operator
        current_avg = state.operator_avg_wait(op)
        count = state.operator_bus_count(op)
        projected = (current_avg * count + candidate.wait_min) / (count + 1)
        return projected


class OverallNetworkRule(BaseRule):
    """Penalises increasing total network delay. weight_key: overall"""
    weight_key = "overall"

    def cost(self, bus, candidate, state):
        return state.total_wait_min + candidate.wait_min


# Add new rule instances here
RULE_REGISTRY = [
    IndividualWaitRule(),
    OperatorFairnessRule(),
    OverallNetworkRule(),
]


class ArrivalTimeRule(BaseRule):
    weight_key = "arrival"
    def cost(self, bus, candidate, state):
        return candidate.charge_end_min

RULE_REGISTRY.append(ArrivalTimeRule())
