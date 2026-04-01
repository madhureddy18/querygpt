#agents/table_agent.py

from pgvector.psycopg2 import register_vector
from dotenv import load_dotenv
import psycopg2
from sentence_transformers import SentenceTransformer
from groq import Groq
import os
import json
from models.shared_models import embed_model

load_dotenv(override=True)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def get_candidate_tables(question, db_config: dict, top_n=8, threshold=0.15):
    que_embedding = embed_model.encode(question)

    conn = psycopg2.connect(**db_config)
    register_vector(conn)
    cur = conn.cursor()

    cur.execute("""
        SELECT table_name, schema_name, description,
               1 - (embedding <=> %s) AS similarity
        FROM metadata.table_registry
        ORDER BY embedding <=> %s
        LIMIT %s
    """, (que_embedding, que_embedding, top_n))

    results = cur.fetchall()
    cur.close()
    conn.close()

    candidates = []
    for row in results:
        if row[3] > threshold:
            candidates.append({
                "table_name": row[0],
                "schema_name": row[1],
                "description": row[2],
                "similarity": round(row[3], 4)
            })

    return candidates


def rerank_tables(question, candidates):
    if not candidates:
        return []

    tables_text = "\n".join([
    f"- {c['schema_name']}.{c['table_name']}: {c['description']}"
    for c in candidates
    ])

    prompt = f"""You are a data engineer selecting tables for a SQL query.

AVAILABLE TABLES — these are the ONLY tables that exist in this database:
{tables_text}

User Question: {question}

RULES:
- Select ONLY tables from the list above — no other tables exist
- Read each description carefully before selecting
- Select the most specific table that answers the question
- Fewer tables is better — avoid redundant selections
CRITICAL:
- PREFER BASE TABLES (analytics.fact_*)
- Avoid views unless explicitly required
IMPORTANT:
- If question involves zone, borough, location → MUST include analytics.taxi_zones
- Select ALL necessary tables to answer the question correctly
- Do NOT omit required tables (especially dimension tables like example taxi_zones)


Return ONLY a JSON array of fully qualified table names from the list above.
Example: ["analytics.fact_taxi_trips_2025_09", "analytics.taxi_zones"]
No explanation, no markdown, nothing else."""

    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1
    )

    raw = response.choices[0].message.content.strip()

    try:
        selected_tables = json.loads(raw)
    except json.JSONDecodeError:
        selected_tables = candidates[0]["table_name"]

    return selected_tables


def suggest_tables(question, db_config: dict, allowed_tables: list = None):
    candidates = get_candidate_tables(question, db_config)

    # Filter candidates to only workspace tables if provided
    if allowed_tables:
        candidates = [
            c for c in candidates
            if f"{c['schema_name']}.{c['table_name']}" in allowed_tables
        ]

    selected = rerank_tables(question, candidates)
    return selected


# print(suggest_tables("compare total trips between yellow and green taxis"))