# databases/workspace_manager.py

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv(override=True)

def get_db_config() -> dict:
    """
    Single source of truth — always reads from .env
    Change database? Just update .env. Nothing else changes.
    """
    return {
        "host":     os.getenv("DB_HOST"),
        "port":     os.getenv("DB_PORT"),
        "dbname":   os.getenv("DB_NAME"),
        "user":     os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD")
    }


def get_all_workspaces() -> list[dict]:
    conn = psycopg2.connect(**get_db_config())
    cur  = conn.cursor()

    cur.execute("""
        SELECT id, name, description, domain, workspace_type, tables
        FROM metadata.workspaces
        ORDER BY workspace_type DESC, name ASC
    """)

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        {
            "id":             row[0],
            "name":           row[1],
            "description":    row[2],
            "domain":         row[3],
            "workspace_type": row[4],
            "tables":         row[5]
        }
        for row in rows
    ]


def get_workspace_by_name(name: str) -> dict:
    conn = psycopg2.connect(**get_db_config())
    cur  = conn.cursor()

    cur.execute("""
        SELECT id, name, description, domain, workspace_type, tables
        FROM metadata.workspaces
        WHERE name = %s
    """, (name,))

    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return {}

    return {
        "id":             row[0],
        "name":           row[1],
        "description":    row[2],
        "domain":         row[3],
        "workspace_type": row[4],
        "tables":         row[5],
        "db_config":      get_db_config()  # always from .env
    }


def create_custom_workspace(
    name: str,
    description: str,
    tables: list[str]
) -> dict:
    conn = psycopg2.connect(**get_db_config())
    cur  = conn.cursor()

    cur.execute("""
        INSERT INTO metadata.workspaces
            (name, description, domain, workspace_type, tables)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
    """, (name, description, "general", "custom", tables))

    conn.commit()
    cur.close()
    conn.close()

    return get_workspace_by_name(name)


def delete_workspace(name: str) -> bool:
    conn = psycopg2.connect(**get_db_config())
    cur  = conn.cursor()

    cur.execute("""
        SELECT workspace_type FROM metadata.workspaces
        WHERE name = %s
    """, (name,))

    row = cur.fetchone()

    if not row:
        cur.close()
        conn.close()
        return False

    if row[0] == "system":
        print(f"  [Workspace] Cannot delete system workspace '{name}'")
        cur.close()
        conn.close()
        return False

    cur.execute("DELETE FROM metadata.workspaces WHERE name = %s", (name,))
    conn.commit()
    cur.close()
    conn.close()
    return True


# ── test ──────────────────────────────────────────────────────
if __name__ == "__main__":
    for w in get_all_workspaces():
        print(f"[{w['workspace_type']}] {w['name']}")

    ws = get_workspace_by_name("Trip Analysis")
    print(f"\nDB: {ws['db_config']['dbname']} @ {ws['db_config']['host']}")