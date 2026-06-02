
from scheduler.validator import validate_schedule

def test_import():
    assert callable(validate_schedule)
