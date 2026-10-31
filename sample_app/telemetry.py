"""Battery telemetry rules. This is the code the regression tests protect."""

CRITICAL_BELOW = 10
LOW_BELOW = 20


def battery_status(state_of_charge):
    """Turn a charge percent into a status an operator can act on."""
    if state_of_charge < CRITICAL_BELOW:
        return "critical"
    if state_of_charge < LOW_BELOW:
        return "low"
    return "ok"


def power_kw(voltage_v, current_a):
    """Power in kilowatts. Negative current means the battery is charging."""
    return round(voltage_v * current_a / 1000, 3)


def reading_errors(reading):
    """Return what is wrong with a reading. Empty = valid."""
    errors = []
    if not reading.get("unit_id"):
        errors.append("unit_id is required")
    if not _is_number(reading.get("state_of_charge")) or not 0 <= reading["state_of_charge"] <= 100:
        errors.append("state_of_charge must be 0 to 100")
    if not _is_number(reading.get("voltage_v")) or reading["voltage_v"] <= 0:
        errors.append("voltage_v must be above 0")
    if not _is_number(reading.get("current_a")):
        errors.append("current_a must be a number")
    return errors


def _is_number(value):
    # In Python, True counts as the number 1. A reading should not.
    return isinstance(value, (int, float)) and not isinstance(value, bool)
