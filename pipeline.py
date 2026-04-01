# pipeline.py

import time
from agents.prompt_enhancer      import enhance_question
from agents.intent_agent         import classify_intent_hybrid
from agents.table_agent          import suggest_tables
from agents.column_prune_agent   import prune_columns, format_pruned_schema_for_prompt
from agents.sql_generator_agent  import generate_sql
from agents.validation_agent     import validate_and_fix
from agents.explanation_agent    import explain_query
from rag.rag_pipeline            import get_relevant_samples, format_examples_for_prompt
from databases.workspace_manager import get_workspace_by_name
from databases.query_logger      import log_query


def run_pipeline(question: str, workspace_name: str) -> dict:
    """
    Full production QueryGPT pipeline.

    Steps:
        0. Load workspace
        1. Prompt Enhancer     → clean vague questions
        2. Intent Agent        → classify domain
        3. Table Agent         → select tables
        4. Column Prune Agent  → select columns
        5. RAG Pipeline        → fetch examples
        6. SQL Generator       → generate SQL
        7. Validation Agent    → static + LLM check + auto-fix + retry
        8. Explanation Agent   → plain English explanation
        9. Logger              → store full trace
    """

    start_time = time.time()

    print(f"\n{'='*60}")
    print(f"Question  : {question}")
    print(f"Workspace : {workspace_name}")
    print(f"{'='*60}")

    # ── Step 0: Load Workspace ─────────────────────────────────
    workspace = get_workspace_by_name(workspace_name)
    if not workspace:
        return {
            "question":          question,
            "enhanced_question": question,
            "workspace":         workspace_name,
            "intent":            None,
            "tables":            [],
            "schema":            None,
            "sql":               None,
            "validated":         False,
            "validation_issues": [],
            "explanation":       None,
            "latency_ms":        0,
            "error":             f"Workspace '{workspace_name}' not found"
        }

    db_config        = workspace["db_config"]
    workspace_tables = workspace["tables"]
    workspace_domain = workspace["domain"]

    print(f"\n[0/8] Workspace: {db_config['dbname']} | domain: {workspace_domain}")

    # ── Step 1: Prompt Enhancer ────────────────────────────────
    print("\n[1/8] Enhancing question...")
    enhanced_question = enhance_question(question)

    # ── Step 2: Intent ─────────────────────────────────────────
    print("\n[2/8] Classifying intent...")
    intent = classify_intent_hybrid(enhanced_question, db_config)
    if intent == "general" and workspace_domain != "general":
        intent = workspace_domain
    print(f"  → Intent: {intent}")

    # ── Step 3: Tables ─────────────────────────────────────────
    print("\n[3/8] Selecting tables...")
    tables = suggest_tables(enhanced_question, db_config, allowed_tables=workspace_tables)
    if not tables:
        tables = workspace_tables
    print(f"  → Tables: {tables}")

    # ── Step 4: Column Pruning ─────────────────────────────────
    print("\n[4/8] Pruning columns...")
    pruned     = prune_columns(enhanced_question, tables, db_config)
    schema_str = format_pruned_schema_for_prompt(pruned)

    # ── Step 5: RAG ────────────────────────────────────────────
    print("\n[5/8] Fetching RAG examples...")
    domain  = None if intent == "general" else intent
    samples = get_relevant_samples(enhanced_question, db_config, domain=domain, top_k=3)
    rag_str = format_examples_for_prompt(samples)

    # ── Step 6 + 7: Generate → Validate → Retry ───────────────
    sql               = None
    validated         = False
    validation_issues = []

    MAX_RETRIES = 2

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"\n[6/8] Generating SQL (attempt {attempt})...")
        sql = generate_sql(enhanced_question, schema_str, rag_str)
        print(f"  → Generated:\n{sql}")

        print(f"\n[7/8] Validating SQL (attempt {attempt})...")
        val_result        = validate_and_fix(sql, schema_str, enhanced_question, db_config)
        sql               = val_result["sql"]
        validated         = val_result["valid"]
        validation_issues = val_result["issues"]

        if val_result["fixed"]:
            print(f"  → Auto-fixed SQL:\n{sql}")

        if validated:
            break

        if attempt < MAX_RETRIES:
            print(f"  → Validation failed, retrying...")
            rag_str = f"PREVIOUS ATTEMPT ISSUES: {validation_issues}\n\n" + rag_str

    # ── Step 8: Explanation ────────────────────────────────────
    print("\n[8/8] Generating explanation...")
    explanation = explain_query(enhanced_question, sql)
    print(f"  → {explanation}")

    # ── Logging ────────────────────────────────────────────────
    latency_ms = round((time.time() - start_time) * 1000, 2)

    log_query(
        question           = question,
        enhanced_question  = enhanced_question,
        workspace          = workspace_name,
        intent             = intent,
        tables             = tables,
        sql                = sql,
        validated          = validated,
        validation_issues  = validation_issues,
        latency_ms         = latency_ms
    )

    print(f"\n{'='*60}")
    print(f"Final SQL:\n{sql}")
    print(f"Latency: {latency_ms}ms")
    print(f"{'='*60}\n")

    return {
        "question":          question,
        "enhanced_question": enhanced_question,
        "workspace":         workspace_name,
        "intent":            intent,
        "tables":            tables,
        "schema":            schema_str,
        "sql":               sql,
        "validated":         validated,
        "validation_issues": validation_issues,
        "explanation":       explanation,
        "latency_ms":        latency_ms,
        "error":             None
    }


if __name__ == "__main__":
    test_cases = [
        ("For each borough, find the hour with the single highest trip count in September 2025.", "Time Analysis"),
    ]

    for question, workspace in test_cases:
        print(f"\n{'#'*60}")
        result = run_pipeline(question, workspace_name=workspace)

        if result.get("error"):
            print(f"ERROR: {result['error']}")
            continue

        print(f"\n── RESULT ──")
        print(f"Original   : {result.get('question')}")
        print(f"Enhanced   : {result.get('enhanced_question')}")
        print(f"Intent     : {result.get('intent')}")
        print(f"Tables     : {result.get('tables')}")
        print(f"Validated  : {result.get('validated')}")
        print(f"Issues     : {result.get('validation_issues')}")
        print(f"Latency    : {result.get('latency_ms')}ms")
        print(f"\nSQL:\n{result.get('sql')}")
        print(f"\nExplanation:\n{result.get('explanation')}")