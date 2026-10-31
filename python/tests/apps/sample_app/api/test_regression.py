"""Regression tests for the API: right answers, and right refusals."""
import pytest
import requests

pytestmark = pytest.mark.regression

GOOD_READING = {"unit_id": "UPS-001", "state_of_charge": 15, "voltage_v": 480, "current_a": 100}


def _headers(api):
    return {"Authorization": f"Bearer {api['token']}"}


def test_tc17_valid_reading_is_saved(api):
    """TC-17 (positive): A good reading is saved and can be read back."""
    saved = requests.post(f"{api['url']}/readings", json=GOOD_READING, headers=_headers(api), timeout=5)
    assert saved.status_code == 201
    assert saved.json() == {"unit_id": "UPS-001", "status": "low", "power_kw": 48.0}

    read_back = requests.get(f"{api['url']}/units/UPS-001", headers=_headers(api), timeout=5)
    assert read_back.json()["status"] == "low"


def test_tc18_bad_reading_is_refused(api):
    """TC-18 (negative): A bad reading gets a 400 and a clear reason."""
    bad = {**GOOD_READING, "state_of_charge": 101}
    response = requests.post(f"{api['url']}/readings", json=bad, headers=_headers(api), timeout=5)
    assert response.status_code == 400
    assert response.json()["errors"] == ["state_of_charge must be 0 to 100"]


@pytest.mark.parametrize("headers", [
    {},
    {"Authorization": "Bearer wrong-token"},
], ids=["no-token", "wrong-token"])
def test_tc19_login_is_required(api, headers):
    """TC-19 (negative): No token or a wrong token gets a 401."""
    response = requests.post(f"{api['url']}/readings", json=GOOD_READING, headers=headers, timeout=5)
    assert response.status_code == 401


def test_tc20_unknown_unit_is_not_found(api):
    """TC-20 (edge): A unit that does not exist gets a 404, not a crash."""
    response = requests.get(f"{api['url']}/units/UPS-999", headers=_headers(api), timeout=5)
    assert response.status_code == 404
