# main.py

import os
import time
import psycopg2
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from databases.workspace_manager import (
    get_db_config,
    get_all_workspaces,
    get_workspace_by_name,
    create_custom_workspace,
    delete_workspace,
)
from pipeline import run_pipeline
from agents.table_agent import suggest_tables
from agents.intent_agent import classify_intent_hybrid
from agents.prompt_enhancer import enhance_question
from agents.column_prune_agent import prune_columns, format_pruned_schema_for_prompt
from agents.sql_generator_agent import generate_sql
from agents.validation_agent import validate_and_fix
from agents.explanation_agent import explain_query
from rag.rag_pipeline import get_relevant_samples, format_examples_for_prompt
from databases.query_logger import log_query

load_dotenv()


# ═══════════════════════════════════════════════════════════════
# APP
# ═══════════════════════════════════════════════════════════════

app = FastAPI(
    title="QueryGPT API",
    description="Natural Language → SQL | NYC Taxi Data",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ════════════════════════════════════════════════════════════════
# PYDANTIC MODELS
# ════════════════════════════════════════════════════════════════

class AskRequest(BaseModel):
    question:       str
    workspace_name: str | None = None

class TableConfirmRequest(BaseModel):
    question:         str
    confirmed_tables: list[str]
    workspace_name:   str | None = None

class CreateWorkspaceRequest(BaseModel):
    name:        str
    description: str
    tables:      list[str]


# ════════════════════════════════════════════════════════════════
# HEALTH
# ════════════════════════════════════════════════════════════════

@app.get("/health")
def health():
    return {"status": "ok", "service": "QueryGPT API", "version": "2.0.0"}


# ════════════════════════════════════════════════════════════════
# WORKSPACES
# ════════════════════════════════════════════════════════════════

@app.get("/workspaces")
def list_workspaces():
    try:
        workspaces = get_all_workspaces()
        return {"workspaces": workspaces}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load workspaces: {str(e)}")


@app.get("/workspaces/{name}")
def get_workspace(name: str):
    try:
        ws = get_workspace_by_name(name)
        if not ws:
            raise HTTPException(status_code=404, detail=f"Workspace '{name}' not found.")
        return ws
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/workspaces")
def create_workspace(req: CreateWorkspaceRequest):
    if not req.name.strip():
        raise HTTPException(status_code=422, detail="Workspace name cannot be empty.")
    if not req.tables:
        raise HTTPException(status_code=422, detail="At least one table must be selected.")

    try:
        existing = get_workspace_by_name(req.name)
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Workspace '{req.name}' already exists."
            )
        ws = create_custom_workspace(
            name=req.name,
            description=req.description,
            tables=req.tables,
        )
        return {"message": f"Workspace '{req.name}' created.", "workspace": ws}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/workspaces/{name}")
def remove_workspace(name: str):
    try:
        success = delete_workspace(name)
        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete '{name}'. It may be a system workspace or does not exist."
            )
        return {"message": f"Workspace '{name}' deleted."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tables")
def list_all_tables():
    try:
        conn = psycopg2.connect(**get_db_config())
        cur  = conn.cursor()
        cur.execute("""
            SELECT schema_name || '.' || table_name AS full_name,
                   schema_name,
                   table_name,
                   description
            FROM metadata.table_registry
            ORDER BY schema_name, table_name
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()

        return {
            "tables": [
                {
                    "full_name":   row[0],
                    "schema_name": row[1],
                    "table_name":  row[2],
                    "description": row[3],
                }
                for row in rows
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load tables: {str(e)}")


# ════════════════════════════════════════════════════════════════
# PIPELINE — STEP 1: Suggest Tables
# ════════════════════════════════════════════════════════════════

@app.post("/suggest-tables")
def suggest_tables_endpoint(req: AskRequest):
    """
    STEP 1 of 2 — Enhance question + intent + table suggestion.
    Returns suggested tables for user to confirm before SQL generation.
    """
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="Question cannot be empty.")

    # ── Enhance ───────────────────────────────────────────────
    try:
        enhanced_question = enhance_question(question)
    except Exception as e:
        enhanced_question = question
        print(f"  [Enhancer WARNING] {e} — using original")

    db_config      = get_db_config()
    allowed_tables = None

    # ── Workspace scope ───────────────────────────────────────
    if req.workspace_name:
        try:
            ws = get_workspace_by_name(req.workspace_name)
            if not ws:
                raise HTTPException(
                    status_code=404,
                    detail=f"Workspace '{req.workspace_name}' not found."
                )
            db_config      = ws["db_config"]
            allowed_tables = ws["tables"]
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Workspace load failed: {str(e)}"
            )

    # ── Intent ────────────────────────────────────────────────
    try:
        intent = classify_intent_hybrid(enhanced_question, db_config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Intent Agent failed: {str(e)}")

    # ── Tables ────────────────────────────────────────────────
    try:
        tables = suggest_tables(
            enhanced_question,
            db_config,
            allowed_tables=allowed_tables
        )

        if isinstance(tables, str):
            tables = [tables]
        if not isinstance(tables, list):
            tables = []

        if not tables and allowed_tables:
            tables = allowed_tables

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Table Agent failed: {str(e)}")

    return {
        "question":          question,
        "enhanced_question": enhanced_question,
        "workspace_name":    req.workspace_name,
        "intent":            intent,
        "suggested_tables":  tables,
    }


# ════════════════════════════════════════════════════════════════
# PIPELINE — STEP 2: Generate SQL
# ════════════════════════════════════════════════════════════════

@app.post("/generate-sql")
def generate_sql_endpoint(req: TableConfirmRequest):
    """
    STEP 2 of 2 — Full SQL generation after user confirms tables.

    Path A — workspace_name provided:
        Delegates to run_pipeline() — full agent chain with
        prompt enhancer, validation, explanation, and logging.

    Path B — no workspace:
        Runs full agent chain directly using master DB config
        and user-confirmed table list. Also logs the query.
    """
    question         = req.question.strip()
    confirmed_tables = req.confirmed_tables

    if not question:
        raise HTTPException(status_code=422, detail="Question cannot be empty.")
    if not confirmed_tables:
        raise HTTPException(
            status_code=422,
            detail="At least one confirmed table required."
        )

    # ── Path A: Workspace ──────────────────────────────────────
    if req.workspace_name:
        try:
            result = run_pipeline(
                question=question,
                workspace_name=req.workspace_name,
            )
            if result.get("error"):
                raise HTTPException(status_code=500, detail=result["error"])
            return result
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Pipeline failed: {str(e)}"
            )

    # ── Path B: No workspace ───────────────────────────────────
    start     = time.time()
    db_config = get_db_config()

    # Enhance
    try:
        enhanced = enhance_question(question)
    except Exception:
        enhanced = question

    # Intent
    try:
        intent = classify_intent_hybrid(enhanced, db_config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Intent Agent failed: {str(e)}")

    # Column pruning on user-confirmed tables
    try:
        pruned     = prune_columns(enhanced, confirmed_tables, db_config)
        schema_str = format_pruned_schema_for_prompt(pruned)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Column Prune Agent failed: {str(e)}"
        )

    # RAG
    try:
        domain  = None if intent == "general" else intent
        samples = get_relevant_samples(enhanced, db_config, domain=domain, top_k=3)
        rag_str = format_examples_for_prompt(samples)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG Pipeline failed: {str(e)}")

    # Generate + Validate + Retry
    sql               = None
    validated         = False
    validation_issues = []
    MAX_RETRIES       = 2

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            sql = generate_sql(enhanced, schema_str, rag_str)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"SQL Generator failed: {str(e)}"
            )

        try:
            val_result        = validate_and_fix(sql, schema_str, enhanced, db_config)
            sql               = val_result["sql"]
            validated         = val_result["valid"]
            validation_issues = val_result["issues"]
        except Exception as e:
            print(f"  [Validation WARNING] {e}")
            validated = False

        if validated:
            break

        if attempt < MAX_RETRIES:
            print(f"  [API] Validation failed attempt {attempt} — retrying...")
            rag_str = f"PREVIOUS ATTEMPT ISSUES: {validation_issues}\n\n" + rag_str

    # Explanation
    try:
        explanation = explain_query(enhanced, sql)
    except Exception:
        explanation = ""

    latency_ms = round((time.time() - start) * 1000, 2)

    # Log — same as pipeline does for workspace path
    try:
        log_query(
            question          = question,
            enhanced_question = enhanced,
            workspace         = "none",
            intent            = intent,
            tables            = confirmed_tables,
            sql               = sql,
            validated         = validated,
            validation_issues = validation_issues,
            latency_ms        = latency_ms
        )
    except Exception as e:
        print(f"  [Logger WARNING] {e}")

    return {
        "question":          question,
        "enhanced_question": enhanced,
        "workspace":         None,
        "intent":            intent,
        "tables":            confirmed_tables,
        "schema":            schema_str,
        "sql":               sql,
        "validated":         validated,
        "validation_issues": validation_issues,
        "explanation":       explanation,
        "latency_ms":        latency_ms,
        "error":             None,
    }


# ════════════════════════════════════════════════════════════════
# RUN
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)