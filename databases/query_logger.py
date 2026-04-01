# databases/query_logger.py

import os
import json
import psycopg2
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(override=True)


def get_db_config() -> dict:
    return {
        "host":     os.getenv("DB_HOST"),
        "port":     os.getenv("DB_PORT"),
        "dbname":   os.getenv("DB_NAME"),
        "user":     os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD")
    }


def log_query(
    question:       str,
    enhanced_question: str,
    workspace:      str,
    intent:         str,
    tables:         list,
    sql:            str,
    validated:      bool,
    validation_issues: list,
    latency_ms:     float
):
    """
    Logs every query attempt to metadata.query_logs table.
    Used for observability, debugging, and future improvement.
    """
    try:
        conn = psycopg2.connect(**get_db_config())
        cur  = conn.cursor()

        cur.execute("""
    INSERT INTO metadata.query_logs (
        question, enhanced_question, workspace, intent,
        tables, sql, validated, validation_issues,
        latency_ms, created_at
    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        question,
        enhanced_question,
        workspace,
        intent,
        json.dumps(tables),
        sql,
        validated,
        json.dumps(validation_issues),
        latency_ms,
        datetime.utcnow()
    ))

        conn.commit()
        cur.close()
        conn.close()

    except Exception as e:
        # Never crash pipeline because of logging failure
        print(f"  [Logger WARNING] Failed to log query: {e}")