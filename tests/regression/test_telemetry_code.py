"""Regression tests for the application code: boundaries and bad input."""
import pytest

from sample_app.telemetry import battery_status, power_kw, reading_errors

pytestmark = [pytest.mark.regression, pytest.mark.code]

VALID = {"unit_id": "UPS-001", "state_of_charge": 80, "voltage_v": 480, "current_a": 100}


@pytest.mark.parametrize("charge, expected", [
    (0, "critical"),
    (9.9, "critical"),
    (10, "low"),       # boundary: exactly 10 is low, not critical
    (19.9, "low"),
    (20, "ok"),        # boundary: exactly 20 is ok, not low
    (100, "ok"),
])
def test_tc14_battery_status_boundaries(charge, expected):
    """TC-14: The status changes exactly at the 10% and 20% limits."""
    assert battery_status(charge) == expected


@pytest.mark.parametrize("voltage, current, expected", [
    (480, 100, 48.0),    # discharging
    (480, -100, -48.0),  # charging gives negative power
    (480, 0, 0.0),       # idle
])
def test_tc15_power_calculation(voltage, current, expected):
    """TC-15: Power is correct when discharging, charging, and idle."""
    assert power_kw(voltage, current) == expected


def test_tc16_valid_reading_has_no_errors():
    """TC-16 (positive): A good reading is accepted."""
    assert reading_errors(VALID) == []


@pytest.mark.parametrize("field, bad_value", [
    ("unit_id", ""),
    ("state_of_charge", -1),
    ("state_of_charge", 101),
    ("state_of_charge", "80"),   # a number sent as text
    ("state_of_charge", True),   # in Python, True counts as the number 1
    ("voltage_v", 0),
    ("current_a", None),
])
def test_tc16_bad_reading_is_rejected(field, bad_value):
    """TC-16 (negative): A bad value in any field is reported."""
    assert reading_errors({**VALID, field: bad_value}) != []
