#agents/column_prune_agent.py

from pgvector.psycopg2 import register_vector
from dotenv import load_dotenv
import psycopg2
from sentence_transformers import SentenceTransformer
from groq import Groq
import os
import json

load_dotenv(override=True)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def fetch_columns_from_db(table_names: list[str], db_config: dict) -> dict:
    """
    Fetches column names AND data types from information_schema
    for given fully-qualified table names (schema.table).

    Returns:
        {
          "analytics.fact_taxi_trips_2025_09": [
              ("pickup_datetime", "timestamp without time zone"),
              ("total_amount",    "numeric"),
              ...
          ]
        }
    """
    schema_map = {}
    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()

    for full_name in table_names:
        parts = full_name.split(".")
        if len(parts) != 2:
            continue
        schema_name, table_name = parts

        cur.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
        """, (schema_name, table_name))

        rows = cur.fetchall()  # [("col_name", "data_type"), ...]
        if rows:
            schema_map[full_name] = rows  # list of tuples

    cur.close()
    conn.close()
    return schema_map

def build_schema_string(schema_map: dict) -> str:
    """
    Converts schema dict into readable text for the LLM prompt.

    Input:
        {
          "analytics.fact_taxi_trips_2025_09": [
              ("pickup_datetime", "timestamp without time zone"),
              ("total_amount",    "numeric"),
          ]
        }

    Output:
        Table: analytics.fact_taxi_trips_2025_09
        Columns:
          - pickup_datetime  (timestamp without time zone)
          - total_amount     (numeric)
    """
    lines = []

    for table, columns in schema_map.items():
        lines.append(f"Table: {table}")
        lines.append("Columns:")
        for col_name, data_type in columns:
            lines.append(f"  - {col_name}  ({data_type})")
        lines.append("")  # blank line between tables

    return "\n".join(lines)

def prune_columns(question: str, table_names: list[str], db_config: dict) -> dict:
    schema_map = fetch_columns_from_db(table_names, db_config)
    """
    Takes question + selected table names.
    Returns only the columns needed to answer the question.

    Returns:
        {
          "analytics.fact_taxi_trips_2025_09": [
              ("pulocationid", "integer"),
              ("avg_speed_mph", "numeric")
          ],
          "analytics.taxi_zones": [
              ("locationid", "integer"),
              ("borough", "text")
          ]
        }
    """
    # Step 1: Fetch live columns + datatypes from DB
    if not schema_map:
        print("  [Prune] No columns found for given tables.")
        return {}

    # Step 2: Format into readable text for LLM
    schema_str = build_schema_string(schema_map)

    # Step 3: Build prompt and call Groq
    system_prompt = """You are a database schema pruning expert.

Given a user question and database tables with columns and datatypes,
return ONLY the columns needed to answer the question.

CRITICAL RULES:
- ONLY return columns that are explicitly listed in the schema below
- NEVER invent or assume columns that are not in the schema
- NEVER add columns from other tables into the wrong table
- pickup_hour and pickup_day_of_week are pre-computed integers — include them directly, never re-extract from pickup_datetime
- avg_speed_mph is pre-computed — include it directly, never recalculate
- pickup_borough, pickup_zone, dropoff_borough, dropoff_zone only exist in views.trips_with_zones — never add them to fact tables
- pulocationid and dolocationid are JOIN keys for fact tables — include them when joining to analytics.taxi_zones
- locationid is the JOIN key for analytics.taxi_zones — always include it

INCLUDE:
- JOIN keys when two tables need to be joined
- GROUP BY columns
- Aggregation target columns
- Filter columns
- Pre-computed columns relevant to the question

EXCLUDE:
- Everything else
- Any column not explicitly present in the schema

Return ONLY valid JSON. No explanation, no markdown, no code fences.

Output format:
{
  "schema.table_name": [
      ["col1", "datatype"],
      ["col2", "datatype"]
  ]
}"""

    user_message = f"""Question: {question}

Schema:
{schema_str}

Return pruned columns as JSON."""

    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message}
        ],
        temperature=0.1
    )

    raw = response.choices[0].message.content.strip() # type: ignore

    # Defensive JSON extraction
    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        pruned = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"  [Prune ERROR] JSON parse failed: {e}")
        print(f"  [Prune RAW] {raw}")
        # Fallback: return full schema unpruned — pipeline keeps running
        return schema_map

    total_cols = sum(len(v) for v in pruned.values())
    print(f"  [Prune] {total_cols} columns selected from {len(pruned)} tables")
    return pruned

def format_pruned_schema_for_prompt(pruned: dict) -> str:
    """
    Formats pruned schema dict into a compact string
    for injection into the SQL Generator prompt.

    Input:
        {
          "analytics.fact_taxi_trips_2025_09": [
              ["pulocationid", "integer"],
              ["avg_speed_mph", "numeric"]
          ],
          "analytics.taxi_zones": [
              ["locationid", "integer"],
              ["borough",    "text"]
          ]
        }

    Output:
        Table: analytics.fact_taxi_trips_2025_09
        Columns:
          - pulocationid  (integer)
          - avg_speed_mph (numeric)

        Table: analytics.taxi_zones
        Columns:
          - locationid (integer)
          - borough    (text)
    """
    lines = []

    for table, columns in pruned.items():
        lines.append(f"Table: {table}")
        lines.append("Columns:")
        for col in columns:
            # col is ["col_name", "datatype"]
            lines.append(f"  - {col[0]}  ({col[1]})")
        lines.append("")

    return "\n".join(lines)


# if __name__ == "__main__":
#     question = "Which borough had the highest average trip speed?"
#     tables = [
#         "analytics.fact_taxi_trips_2025_09",
#         "analytics.taxi_zones"
#     ]

#     pruned = prune_columns(question, tables)

#     print("\nPruned schema (raw dict):")
#     print(json.dumps(pruned, indent=2))

#     print("\nFormatted for SQL Generator prompt:")
#     print(format_pruned_schema_for_prompt(pruned))