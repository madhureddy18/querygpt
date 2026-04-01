# agents/sql_generator_agent.py

import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv(override=True)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def generate_sql(question: str, schema_str: str, rag_examples: str) -> str:

    tables_in_schema = []
    for line in schema_str.splitlines():
        if line.startswith("Table:"):
            table_name = line.replace("Table:", "").strip().split("--")[0].strip()
            tables_in_schema.append(table_name)

    allowed_tables_str = "\n".join(f"  - {t}" for t in tables_in_schema)

    system_prompt = f"""You are an expert PostgreSQL query writer for NYC taxi data.

You will be given:
1. A user question
2. The relevant database schema — the ONLY tables and columns you are allowed to use
3. Similar example SQL queries for reference

ALLOWED TABLES — use ONLY these, nothing else:
{allowed_tables_str}

RULES:
- NEVER use a table or column not listed above — if it is not there, it does not exist
- Always use fully qualified table names (schema.table_name)
- Read the schema carefully — column names and datatypes tell you how to use each table
- For division always use NULLIF(denominator, 0)
- For time columns use EXTRACT or DATE_TRUNC
- For window functions always include ORDER BY inside OVER()
- Use ROUND(...::numeric, 2) for clean numeric output
- Use ILIKE for name matching
CRITICAL:
"- Use views when they already have the columns you need"
"- Use fact tables when you need raw columns not available in views"
"- NEVER JOIN extra tables on top of views that already have those columns resolved"
- If zone/borough is used:
→ MUST join taxi_zones
- Do NOT assume columns like month_partition exist
- Only use columns present in schema
- Use ILIKE for text matching instead of exact equality
- Be careful in extract hours , because it causes error , see schema correctly and then use.

Return ONLY the SQL query. No explanation, no markdown, no code fences."""

    user_message = f"""
═══════════════════════════════════════
ALLOWED TABLES AND COLUMNS — USE ONLY THESE:
{schema_str}
═══════════════════════════════════════

Question: {question}

{rag_examples}

REMINDER: Use ONLY the tables and columns listed above. Nothing else exists.

Write the PostgreSQL query:"""

    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message}
        ],
        temperature=0
    )

    sql = response.choices[0].message.content.strip()

    # Strip markdown fences if model adds them
    if "```" in sql:
        sql = sql.split("```")[1]
        if sql.startswith("sql") or sql.startswith("SQL"):
            sql = sql[3:]
    sql = sql.strip()

    return sql

# if __name__ == "__main__":
#     from agents.column_prune_agent import prune_columns, format_pruned_schema_for_prompt
#     from rag.rag_pipeline import get_relevant_samples, format_examples_for_prompt

#     question = "Which borough had the highest average trip speed?"
#     tables   = ["analytics.fact_taxi_trips_2025_09", "analytics.taxi_zones"]

#     # Step 1: Prune schema
#     pruned     = prune_columns(question, tables)
#     schema_str = format_pruned_schema_for_prompt(pruned)

#     # Step 2: Get RAG examples
#     samples    = get_relevant_samples(question, top_k=3)
#     rag_str    = format_examples_for_prompt(samples)

#     # Step 3: Generate SQL
#     sql = generate_sql(question, schema_str, rag_str)

#     print("\nGenerated SQL:")
#     print(sql)