
from scheduler.rules import RULE_REGISTRY

def test_rules_registered():
    assert len(RULE_REGISTRY) >= 3
