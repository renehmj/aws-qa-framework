import os

import psycopg
from psycopg import sql


def password_for(db, session):
    """A short-lived IAM token on RDS. Otherwise a password from an env variable."""
    if db.get("auth") == "iam":
        return session.client("rds").generate_db_auth_token(
            DBHostname=db["host"], Port=db["port"], DBUsername=db["user"]
        )
    return db.get("password") or os.environ[db["password_env"]]


def connect(db, password):
    """Open a read-only connection. TLS is required unless the config turns it off."""
    return psycopg.connect(
        host=db["host"], port=db["port"], dbname=db["dbname"], user=db["user"],
        password=password, connect_timeout=5, autocommit=True,
        sslmode=db.get("sslmode", "verify-full"), sslrootcert=db.get("sslrootcert"),
        options="-c default_transaction_read_only=on",
    )


def wrong_password_problems(db):
    """A wrong password must be refused. A network error is not a pass."""
    try:
        connect(db, "wrong-password").close()
    except psycopg.OperationalError as error:
        if "authentication failed" in str(error):
            return []
        raise
    return [f"{db['name']}: login worked with a wrong password"]


def write_access_problems(conn, tables):
    """The QA login must not be a superuser and must not be able to write."""
    problems = []
    if conn.execute("SELECT rolsuper FROM pg_roles WHERE rolname = current_user").fetchone()[0]:
        problems.append("QA login is a superuser")
    for table in tables:
        for action in ("INSERT", "UPDATE", "DELETE"):
            query = "SELECT has_table_privilege(current_user, %s, %s)"
            if conn.execute(query, (table, action)).fetchone()[0]:
                problems.append(f"QA login can {action} on {table}")
    return problems


def row_count_problems(conn, table, min_rows):
    """The table must hold at least min_rows rows."""
    query = sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table))
    count = conn.execute(query).fetchone()[0]
    return [f"{table}: {count} rows, expected at least {min_rows}"] if count < min_rows else []


def null_problems(conn, table, columns):
    """These columns must never be empty."""
    problems = []
    for column in columns:
        query = sql.SQL("SELECT count(*) FROM {} WHERE {} IS NULL").format(
            sql.Identifier(table), sql.Identifier(column)
        )
        count = conn.execute(query).fetchone()[0]
        if count:
            problems.append(f"{table}.{column}: {count} empty values")
    return problems


def duplicate_problems(conn, table, key):
    """Each key must appear only once."""
    columns = sql.SQL(", ").join(map(sql.Identifier, key))
    query = sql.SQL("SELECT {key} FROM {table} GROUP BY {key} HAVING count(*) > 1").format(
        key=columns, table=sql.Identifier(table)
    )
    return [f"{table}: duplicate key {row}" for row in conn.execute(query).fetchall()]


def compare_problems(conns, table):
    """Every database must hold the same rows as the first one.

    A changed row counts as one missing and one extra.
    """
    query = sql.SQL("SELECT * FROM {}").format(sql.Identifier(table))
    copies = {name: set(conn.execute(query).fetchall()) for name, conn in conns.items()}
    first_name, first_rows = next(iter(copies.items()))

    problems = []
    for name, rows in copies.items():
        if rows != first_rows:
            problems.append(
                f"{table}: {name} differs from {first_name}, "
                f"{len(first_rows - rows)} missing, {len(rows - first_rows)} extra"
            )
    return problems
