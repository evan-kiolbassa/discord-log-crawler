import os
import time
from typing import Iterator

import pytest
import pymysql

from discord_log_crawler.config import load_config
from discord_log_crawler.db import get_conn, init_schema, cursor


def _wait_for_mysql(host: str, port: int, user: str, password: str, database: str, timeout: int = 60) -> None:
    start = time.time()
    last_err = None
    while time.time() - start < timeout:
        try:
            conn = pymysql.connect(host=host, port=port, user=user, password=password, database=database)
            conn.close()
            return
        except Exception as e:  # noqa: BLE001 - broad during boot-up
            last_err = e
            time.sleep(1)
    raise RuntimeError(f"MySQL not ready after {timeout}s: {last_err}")


@pytest.fixture(scope="function")
def db_conn() -> Iterator[pymysql.connections.Connection]:
    """Yield a ready MySQL connection against the configured database.

    Skips if connection cannot be established and environment variables
    are not provided. In CI and docker-compose, env variables are set so
    the connection should succeed.
    """
    cfg = load_config()
    # Wait until MySQL is ready (CI and docker-compose use services)
    _wait_for_mysql(cfg.db.host, cfg.db.port, cfg.db.user, cfg.db.password, cfg.db.database, timeout=90)
    conn = get_conn(cfg.db)
    init_schema(conn)
    try:
        yield conn
    finally:
        # Cleanup tables between tests
        with cursor(conn) as cur:
            cur.execute("SET FOREIGN_KEY_CHECKS=0")
            for tbl in ("moderation_events", "player_aliases", "players"):
                cur.execute(f"TRUNCATE TABLE {tbl}")
            cur.execute("SET FOREIGN_KEY_CHECKS=1")
        conn.close()

