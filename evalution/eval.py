# eval/eval.py

import json
import os
import re
from dotenv import load_dotenv
from groq import Groq

from databases.workspace_manager import get_db_config
from agents.table_agent import suggest_tables
from agents.column_prune_agent import prune_columns, format_pruned_schema_for_prompt
from rag.rag_pipeline import get_relevant_samples, format_examples_for_prompt
from agents.sql_generator_agent import generate_sql
from agents.intent_agent import classify_intent_hybrid
from agents.validation_agent import static_validate

load_dotenv(override=True)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

ALLOWED_TABLES = [
    "analytics.fact_taxi_trips_2025_09",
    "analytics.fact_taxi_trips_2025_08",
    "analytics.taxi_zones",
    "analytics.dim_date",
    "raw.fhvhv_tripdata_2025_09",
    "raw.fhvhv_tripdata_2025_08",
    "raw.yellow_tripdata_2025_09",
    "raw.yellow_tripdata_2025_08",
    "raw.green_tripdata_2025_09",
    "raw.green_tripdata_2025_08",
    "raw.fhv_tripdata_2025_09",
    "raw.fhv_tripdata_2025_08",
    "staging.trips_unified_2025_09",
    "staging.trips_unified_2025_08",
    "views.fact_taxi_trips_all",
    "views.trips_with_zones",
    "views.revenue_by_borough",
    "views.trips_by_hour",
    "views.trips_by_day_of_week",
    "views.service_type_summary",
    "views.zone_performance"
]


# ── 1. Load Golden Dataset ────────────────────────────────────────────────────

def load_golden_dataset(path="evalution/golden_sql.json"):
    with open(path, "r") as f:
        return json.load(f)


# ── 2. Run Pipeline ───────────────────────────────────────────────────────────

from databases.workspace_manager import get_workspace_by_name

DOMAIN_TO_WORKSPACE = {
    "trips":    "Trip Analysis",
    "revenue":  "Revenue",
    "zones":    "Location Intelligence",
    "time":     "Time Analysis",
}

def run_pipeline(question: str, db_config: dict, domain: str = None) -> dict:
    try:
        intent = classify_intent_hybrid(question, db_config)

        # Use workspace scoping to limit table candidates
        workspace_name = DOMAIN_TO_WORKSPACE.get(domain, None)
        allowed_tables = None

        if workspace_name:
            ws = get_workspace_by_name(workspace_name)
            if ws:
                allowed_tables = ws["tables"]

        tables = suggest_tables(question, db_config, allowed_tables=allowed_tables)
        if not tables:
            return {"success": False, "generated_sql": None, "schema_str": None, "error": "No tables selected"}

        pruned     = prune_columns(question, tables, db_config)
        schema_str = format_pruned_schema_for_prompt(pruned)

        domain_for_rag = None if intent == "general" else intent
        samples    = get_relevant_samples(question, db_config, domain=domain_for_rag, top_k=3)
        rag_str    = format_examples_for_prompt(samples)

        sql = generate_sql(question, schema_str, rag_str)

        return {
            "success":       True,
            "generated_sql": sql,
            "schema_str":    schema_str,
            "error":         None
        }

    except Exception as e:
        return {
            "success":       False,
            "generated_sql": None,
            "schema_str":    None,
            "error":         str(e)
        }

# ── 3. Exact Match ────────────────────────────────────────────────────────────

def exact_match(golden_sql: str, generated_sql: str) -> bool:
    def normalize(sql):
        return " ".join(sql.lower().strip().split())
    return normalize(golden_sql) == normalize(generated_sql)


# ── 4. Hallucination Check ────────────────────────────────────────────────────

def check_hallucination(generated_sql: str, db_config: dict) -> list[str]:
    """
    Uses static_validate from validation_agent (sqlglot-based).
    Returns list of hallucinated table names found in the SQL.
    """
    result = static_validate(generated_sql, db_config)
    return result["hallucinated_tables"]


# ── 5. LLM Judge ─────────────────────────────────────────────────────────────

def llm_judge(
    question: str,
    golden_sql: str,
    generated_sql: str,
    hallucinated_tables: list
) -> dict:

    allowed_str = "\n".join(f"  - {t}" for t in ALLOWED_TABLES)

    hallucination_warning = ""
    if hallucinated_tables:
        hallucination_warning = f"""
⚠️ HALLUCINATION DETECTED:
The Generated SQL uses these tables that DO NOT EXIST in the database:
{chr(10).join(f"  - {t}" for t in hallucinated_tables)}
Maximum score allowed: 0.2
"""

    prompt = f"""You are a strict SQL evaluator.

ALLOWED TABLES — these are the ONLY valid tables in this database:
{allowed_str}

{hallucination_warning}

Score the Generated SQL from 0.0 to 1.0:
- 1.0 : Logically identical — same result even if syntax differs, uses correct tables
- 0.8 : Correct logic, minor differences (alias, formatting), uses correct tables
- 0.6 : Partially correct — right approach but missing conditions or columns
- 0.4 : Wrong aggregation or filter but right tables
- 0.2 : Uses hallucinated tables (tables not in allowed list)
- 0.0 : Completely wrong or empty

If hallucinated tables were detected above — score MUST be 0.2 or lower.

Question: {question}

Golden SQL:
{golden_sql}

Generated SQL:
{generated_sql}

Return ONLY valid JSON:
{{
  "score": 0.0,
  "hallucinated_tables": [],
  "reason": "one sentence"
}}"""

    try:
        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        raw = response.choices[0].message.content.strip()
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        match = re.search(r"\{.*\}", raw.strip(), re.DOTALL)
        if match:
            result = json.loads(match.group())
            # Enforce hallucination penalty regardless of LLM opinion
            if hallucinated_tables and result.get("score", 0) > 0.2:
                result["score"] = 0.2
                result["reason"] = f"Hallucinated tables: {hallucinated_tables}. " + result.get("reason", "")
            return result

        return {"score": 0.0, "hallucinated_tables": [], "reason": "LLM response unparseable"}

    except Exception as e:
        return {"score": 0.0, "hallucinated_tables": [], "reason": f"LLM judge failed: {str(e)}"}


# ── 6. Compile Results ────────────────────────────────────────────────────────

def compile_results(dataset: list, db_config: dict) -> list:
    results = []

    for i, entry in enumerate(dataset):
        print(f"\n[{i+1}/{len(dataset)}] {entry['question'][:70]}...")

        output = run_pipeline(entry["question"], db_config, domain=entry["domain"])

        if not output["success"]:
            results.append({
                "id":                  entry["id"],
                "question":            entry["question"],
                "domain":              entry["domain"],
                "difficulty":          entry["difficulty"],
                "golden_sql":          entry["golden_sql"],
                "generated_sql":       None,
                "exact_match":         False,
                "hallucinated_tables": [],
                "llm_score":           0.0,
                "reason":              f"Pipeline error: {output['error']}",
                "status":              "ERROR"
            })
            print(f"  ❌ Pipeline error: {output['error']}")
            continue

        gen_sql  = output["generated_sql"]
        is_exact = exact_match(entry["golden_sql"], gen_sql)

        # Hallucination check using sqlglot
        hallucinated = check_hallucination(gen_sql, db_config)
        if hallucinated:
            print(f"  ⚠️  Hallucinated tables: {hallucinated}")

        # LLM judge with hallucination penalty enforced
        judge = llm_judge(
            entry["question"],
            entry["golden_sql"],
            gen_sql,
            hallucinated
        )

        status = "PASS" if judge["score"] >= 0.6 else "FAIL"

        results.append({
            "id":                  entry["id"],
            "question":            entry["question"],
            "domain":              entry["domain"],
            "difficulty":          entry["difficulty"],
            "golden_sql":          entry["golden_sql"],
            "generated_sql":       gen_sql,
            "exact_match":         is_exact,
            "hallucinated_tables": hallucinated,
            "llm_score":           judge["score"],
            "reason":              judge["reason"],
            "status":              status
        })

        print(f"  Exact: {is_exact} | Hallucinated: {len(hallucinated)} | Score: {judge['score']} | {status}")
        print(f"  Reason: {judge['reason']}")

    return results


# ── 7. Print Report ───────────────────────────────────────────────────────────

def print_report(results: list):
    total     = len(results)
    passed    = sum(1 for r in results if r["status"] == "PASS")
    failed    = sum(1 for r in results if r["status"] == "FAIL")
    errors    = sum(1 for r in results if r["status"] == "ERROR")
    exact     = sum(1 for r in results if r["exact_match"])
    avg_score = round(sum(r["llm_score"] for r in results) / total, 3)
    hallucination_count = sum(1 for r in results if r["hallucinated_tables"])

    print("\n" + "="*60)
    print("           QUERYGPT EVALUATION REPORT")
    print("="*60)
    print(f"  Total Questions    : {total}")
    print(f"  Passed (≥0.6)      : {passed}  ({round(passed/total*100)}%)")
    print(f"  Failed (<0.6)      : {failed}")
    print(f"  Errors             : {errors}")
    print(f"  Exact Matches      : {exact}")
    print(f"  Avg LLM Score      : {avg_score}")
    print(f"  Hallucinations     : {hallucination_count}/{total} queries")
    print("="*60)

    # Domain breakdown
    print("\n── By Domain ──")
    for domain in ["trips", "revenue", "zones", "time"]:
        domain_results = [r for r in results if r["domain"] == domain]
        if not domain_results:
            continue
        domain_pass  = sum(1 for r in domain_results if r["status"] == "PASS")
        domain_avg   = round(sum(r["llm_score"] for r in domain_results) / len(domain_results), 3)
        domain_halluc = sum(1 for r in domain_results if r["hallucinated_tables"])
        print(f"  {domain:<12} → {domain_pass}/{len(domain_results)} passed | avg: {domain_avg} | hallucinations: {domain_halluc}")

    # Difficulty breakdown
    print("\n── By Difficulty ──")
    for diff in ["medium", "hard", "complex"]:
        diff_results = [r for r in results if r["difficulty"] == diff]
        if not diff_results:
            continue
        diff_pass  = sum(1 for r in diff_results if r["status"] == "PASS")
        diff_avg   = round(sum(r["llm_score"] for r in diff_results) / len(diff_results), 3)
        print(f"  {diff:<10} → {diff_pass}/{len(diff_results)} passed | avg: {diff_avg}")

    # Hallucination breakdown
    halluc_results = [r for r in results if r["hallucinated_tables"]]
    if halluc_results:
        print("\n── Hallucinated Queries ──")
        for r in halluc_results:
            print(f"\n  Q{r['id']}: {r['question'][:60]}")
            print(f"  Fake tables: {r['hallucinated_tables']}")
            print(f"  Score: {r['llm_score']}")

    # Failures
    failures = [r for r in results if r["status"] in ("FAIL", "ERROR")]
    if failures:
        print("\n── Failed Questions ──")
        for r in failures:
            print(f"\n  [{r['status']}] Q{r['id']}: {r['question'][:60]}")
            print(f"  Score  : {r['llm_score']}")
            print(f"  Reason : {r['reason']}")
            if r["generated_sql"]:
                print(f"  Generated: {r['generated_sql'][:120]}...")

    print("\n" + "="*60)

    with open("evalution/eval_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("  Results saved → evalution/eval_results.json")
    print("="*60)


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    db_config = get_db_config()
    dataset   = load_golden_dataset()

    print(f"Loaded {len(dataset)} golden questions.")
    print("Starting evaluation...\n")

    results = compile_results(dataset, db_config)
    print_report(results)