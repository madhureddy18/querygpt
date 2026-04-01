# agents/validation_agent.py

import os
import re
import json
import psycopg2
import sqlglot
from sqlglot import exp
from groq import Groq
from dotenv import load_dotenv

load_dotenv(override=True)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# ── Static table check ────────────────────────────────────────────────────────

def get_existing_tables(db_config: dict) -> list[str]:
    """Fetch all real tables and views from the database."""
    conn = psycopg2.connect(**db_config)
    cur  = conn.cursor()

    cur.execute("""
        SELECT table_schema || '.' || table_name
        FROM information_schema.tables
        WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
        UNION
        SELECT table_schema || '.' || table_name
        FROM information_schema.views
        WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
    """)

    tables = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    return tables



def extract_tables_from_sql(sql: str) -> list[str]:
    """
    Extract actual table references from SQL using proper AST parsing.
    Uses sqlglot — correctly identifies tables, ignores alias.column patterns.
    """
    try:
        tables = set()
        parsed = sqlglot.parse(sql, dialect="postgres")

        for statement in parsed:
            if statement is None:
                continue
            for table in statement.find_all(exp.Table):
                # Only include if it has a schema (e.g. analytics.fact_taxi_trips)
                if table.db:
                    tables.add(f"{table.db}.{table.name}".lower())
                # If no schema, still include bare table name for checking
                elif table.name:
                    tables.add(table.name.lower())

        return list(tables)

    except Exception as e:
        print(f"  [Validation] sqlglot parse failed: {e} — falling back to empty list")
        return []


def static_validate(sql: str, db_config: dict) -> dict:
    """
    Check if all tables referenced in SQL actually exist in the database.
    Uses sqlglot AST parsing — no false positives from alias.column patterns.
    """
    existing = [t.lower() for t in get_existing_tables(db_config)]
    used     = extract_tables_from_sql(sql)

    # Only flag tables that have a schema prefix — bare names are too ambiguous
    hallucinated = [
        t for t in used
        if "." in t and t not in existing
    ]

    return {
        "valid":               len(hallucinated) == 0,
        "hallucinated_tables": hallucinated,
        "tables_used":         used
    }


# ── LLM validation ────────────────────────────────────────────────────────────

def llm_validate(sql: str, schema_str: str, question: str) -> dict:
    """
    LLM checks if the SQL answers the question and uses correct columns.
    Returns validation result with specific issues.
    """

    prompt = f"""You are a strict SQL validator for PostgreSQL.

Question: {question}

Allowed Schema (ONLY these tables and columns exist):
{schema_str}

Generated SQL:
{sql}

Check the SQL for these issues:
1. Does it use any table NOT in the schema above?
2. Does it use any column NOT listed for that table in the schema?
3. Does the SQL logic actually answer the question?
4. Are JOIN conditions correct?

Return ONLY valid JSON:
{{
  "valid": true or false,
  "issues": ["issue 1", "issue 2"],
  "fix_hint": "one sentence on how to fix if invalid, or empty string if valid"
}}"""

    try:
        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        raw = response.choices[0].message.content.strip()

        # Clean markdown fences
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        # Safe JSON extraction
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            return json.loads(match.group())

        return {"valid": False, "issues": ["LLM response unparseable"], "fix_hint": ""}

    except Exception as e:
        return {"valid": False, "issues": [str(e)], "fix_hint": ""}


# ── Auto fix ──────────────────────────────────────────────────────────────────

def fix_sql(sql: str, schema_str: str, question: str, issues: list[str]) -> str:
    """
    Sends broken SQL back to LLM with specific issues to fix.
    """
    issues_str = "\n".join(f"- {i}" for i in issues)

    prompt = f"""You are an expert PostgreSQL query writer.

The following SQL has issues. Fix it.

Question: {question}

Allowed Schema (use ONLY these tables and columns):
{schema_str}

Broken SQL:
{sql}

Issues found:
{issues_str}

Rules:
- Fix ONLY the issues listed
- Use ONLY tables and columns from the schema above
- Return ONLY the corrected SQL query, nothing else"""

    try:
        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        fixed = response.choices[0].message.content.strip()

        if "```" in fixed:
            fixed = fixed.split("```")[1]
            if fixed.startswith("sql") or fixed.startswith("SQL"):
                fixed = fixed[3:]
        return fixed.strip()

    except Exception as e:
        print(f"  [Validation] Fix failed: {e}")
        return sql


# ── Main validate function ────────────────────────────────────────────────────

def validate_and_fix(
    sql: str,
    schema_str: str,
    question: str,
    db_config: dict
) -> dict:
    """
    Full validation pipeline:
    1. Static check  — are all tables real?
    2. LLM check     — are columns and logic correct?
    3. Auto fix      — if issues found, attempt fix

    Returns:
    {
        "sql":      final SQL (fixed or original),
        "valid":    True/False,
        "issues":   [...],
        "fixed":    True/False
    }
    """

    print("\n  [Validation] Running static table check...")
    static = static_validate(sql, db_config)

    if static["hallucinated_tables"]:
        print(f"  [Validation] ❌ Hallucinated tables: {static['hallucinated_tables']}")
        issues  = [f"Table does not exist: {t}" for t in static["hallucinated_tables"]]
        fixed   = fix_sql(sql, schema_str, question, issues)
        return {
            "sql":    fixed,
            "valid":  False,
            "issues": issues,
            "fixed":  True
        }

    print("  [Validation] ✓ Static check passed")
    print("  [Validation] Running LLM validation...")

    llm_result = llm_validate(sql, schema_str, question)

    if not llm_result["valid"]:
        print(f"  [Validation] ❌ LLM issues: {llm_result['issues']}")
        fixed = fix_sql(sql, schema_str, question, llm_result["issues"])
        return {
            "sql":    fixed,
            "valid":  False,
            "issues": llm_result["issues"],
            "fixed":  True
        }

    print("  [Validation] ✓ LLM check passed")
    return {
        "sql":    sql,
        "valid":  True,
        "issues": [],
        "fixed":  False
    }