"""Smoke test: can we log in to every database?"""
import pytest

pytestmark = pytest.mark.smoke


def test_tc13_database_login_works(databases, database_settings):
    """TC-13: The QA login works on every database."""
    for db in database_settings:
        assert databases[db["name"]].execute("SELECT current_user").fetchone()[0] == db["user"]
