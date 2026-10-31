"""Self-tests for database checks. Bad data goes into temporary tables.

Temporary tables disappear when the connection closes, so the databases stay clean.
"""
from pathlib import Path
from unittest.mock import MagicMock

import psycopg
import pytest

from checks.shared.database import (
    compare_problems,
    databases_for,
    duplicate_problems,
    null_problems,
    row_count_problems,
    write_access_problems,
    wrong_password_problems,
)

pytestmark = pytest.mark.selftest


@pytest.fixture
def admin(databases, config):
    """Writable connections, used only to build bad data. Closed after each test."""
    conns = {
        db["name"]: psycopg.connect(
            host=db["host"], port=db["port"], dbname=db["dbname"],
            user="postgres", password=db["password"], sslmode=db["sslmode"], autocommit=True,
        )
        for db in config["databases"]
    }
    for conn in conns.values():
        conn.execute("CREATE TEMP TABLE units (unit_id text, site text)")
    yield conns
    for conn in conns.values():
        conn.close()


def _insert(conn, *rows):
    for row in rows:
        conn.execute("INSERT INTO units VALUES (%s, %s)", row)


def test_app_only_gets_its_own_databases():
    shared = {"name": "shared"}
    web = {"name": "web-db", "project": "web"}
    mobile = {"name": "mobile-db", "project": "mobile"}
    test_file = Path("tests/apps/web/database/test_smoke.py")
    assert databases_for([shared, web, mobile], test_file) == [shared, web]


def test_empty_table_is_caught(admin):
    assert row_count_problems(admin["primary"], "units", 1) == ["units: 0 rows, expected at least 1"]


def test_null_value_is_caught(admin):
    _insert(admin["primary"], ("UPS-1", None))
    assert null_problems(admin["primary"], "units", ["site"]) == ["units.site: 1 empty values"]


def test_duplicate_key_is_caught(admin):
    _insert(admin["primary"], ("UPS-1", "a"), ("UPS-1", "b"))
    assert "duplicate key" in duplicate_problems(admin["primary"], "units", ["unit_id"])[0]


def test_same_data_is_not_flagged(admin):
    """No false alarm: rows in a different order are still the same data."""
    _insert(admin["primary"], ("UPS-1", "a"), ("UPS-2", "b"))
    _insert(admin["redundant"], ("UPS-2", "b"), ("UPS-1", "a"))
    assert compare_problems(admin, "units") == []


def test_row_missing_on_one_database_is_caught(admin):
    _insert(admin["primary"], ("UPS-1", "a"), ("UPS-2", "b"))
    _insert(admin["redundant"], ("UPS-1", "a"))
    assert compare_problems(admin, "units") == ["units: redundant differs from primary, 1 missing, 0 extra"]


def test_changed_row_on_one_database_is_caught(admin):
    _insert(admin["primary"], ("UPS-1", "a"))
    _insert(admin["redundant"], ("UPS-1", "changed"))
    assert compare_problems(admin, "units") == ["units: redundant differs from primary, 1 missing, 1 extra"]


def test_superuser_login_is_caught(admin):
    problems = write_access_problems(admin["primary"], ["units"])
    assert "QA login is a superuser" in problems
    assert "QA login can INSERT on units" in problems


def test_login_with_wrong_password_is_caught(config, monkeypatch):
    """A server that lets anyone in must fail the test."""
    monkeypatch.setattr("checks.shared.database.connect", lambda db, password: MagicMock())
    problems = wrong_password_problems(config["databases"][0])
    assert problems == ["primary: login worked with a wrong password"]


def test_network_error_is_not_a_pass(config):
    """Edge case: a refused password is a pass. A dead server is not."""
    dead = {**config["databases"][0], "port": 59997}
    with pytest.raises(psycopg.OperationalError):
        wrong_password_problems(dead)
