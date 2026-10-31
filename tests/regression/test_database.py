"""Regression tests for the databases. Run these after every deployment."""
import pytest

from checks.database import (
    compare_problems,
    duplicate_problems,
    null_problems,
    row_count_problems,
    write_access_problems,
    wrong_password_problems,
)

pytestmark = [pytest.mark.regression, pytest.mark.database]


def _on_every_database(databases, check):
    return [f"{name}: {problem}" for name, conn in databases.items() for problem in check(conn)]


def test_tc22_wrong_password_is_refused(databases, config):
    """TC-22 (negative): A wrong password can not log in."""
    problems = [problem for db in config["databases"] for problem in wrong_password_problems(db)]
    assert not problems, "\n".join(problems)


def test_tc23_qa_login_is_read_only(databases, config):
    """TC-23 (negative): The QA login can not change data."""
    tables = [table["name"] for table in config["database_tables"]]
    problems = _on_every_database(databases, lambda conn: write_access_problems(conn, tables))
    assert not problems, "\n".join(problems)


def test_tc24_tables_have_rows(databases, config):
    """TC-24: Every table holds the expected minimum of rows."""
    problems = [
        problem
        for table in config["database_tables"]
        for problem in _on_every_database(
            databases, lambda conn: row_count_problems(conn, table["name"], table["min_rows"])
        )
    ]
    assert not problems, "\n".join(problems)


def test_tc25_required_columns_are_not_empty(databases, config):
    """TC-25: Required columns have no empty values."""
    problems = [
        problem
        for table in config["database_tables"]
        for problem in _on_every_database(
            databases, lambda conn: null_problems(conn, table["name"], table["not_null"])
        )
    ]
    assert not problems, "\n".join(problems)


def test_tc26_no_duplicate_keys(databases, config):
    """TC-26: No key appears twice."""
    problems = [
        problem
        for table in config["database_tables"]
        for problem in _on_every_database(
            databases, lambda conn: duplicate_problems(conn, table["name"], table["key"])
        )
    ]
    assert not problems, "\n".join(problems)


def test_tc27_all_databases_hold_the_same_data(databases, config):
    """TC-27: Redundant databases match after a deployment."""
    problems = [
        problem
        for table in config["database_tables"]
        for problem in compare_problems(databases, table["name"])
    ]
    assert not problems, "\n".join(problems)
