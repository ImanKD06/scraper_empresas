"""
Conexión MySQL pura — sin ORM, sin SQLAlchemy.
mysql-connector-python con pool de conexiones.
"""
import mysql.connector
from mysql.connector import pooling
import config

_pool = None

def get_pool():
    global _pool
    if _pool is None:
        _pool = pooling.MySQLConnectionPool(
            pool_name="crm",
            pool_size=5,
            host=config.DB_HOST,
            port=config.DB_PORT,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME,
            charset="utf8mb4",
            autocommit=False,
        )
    return _pool


def query(sql: str, params=None) -> list:
    """SELECT → lista de dicts."""
    conn = get_pool().get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params or ())
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


def one(sql: str, params=None):
    """SELECT → un dict o None."""
    rows = query(sql, params)
    return rows[0] if rows else None


def run(sql: str, params=None) -> int:
    """INSERT/UPDATE/DELETE → lastrowid."""
    conn = get_pool().get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params or ())
        conn.commit()
        return cur.lastrowid
    finally:
        cur.close()
        conn.close()