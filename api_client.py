# api_client.py

import os
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

API_BASE_URL         = os.getenv("API_BASE_URL", "http://sqlgpt-api-service:8000").rstrip("/")
SUGGEST_TABLES_TIMEOUT = 30
GENERATE_SQL_TIMEOUT   = 90
WORKSPACE_TIMEOUT      = 10


def _handle(resp: requests.Response) -> dict:
    try:
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        return {"error": f"[{resp.status_code}] {detail}"}
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot reach the backend. Is FastAPI running?"}
    except requests.exceptions.Timeout:
        return {"error": "Request timed out. Backend may be busy."}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}


def suggest_tables(question: str, workspace_name: str | None = None) -> dict:
    try:
        resp = requests.post(
            f"{API_BASE_URL}/suggest-tables",
            json={"question": question, "workspace_name": workspace_name},
            timeout=SUGGEST_TABLES_TIMEOUT,
        )
        return _handle(resp)
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot reach the backend. Is FastAPI running?"}
    except requests.exceptions.Timeout:
        return {"error": "Timed out waiting for table suggestions."}


def generate_sql(question: str, confirmed_tables: list, workspace_name: str | None = None) -> dict:
    try:
        resp = requests.post(
            f"{API_BASE_URL}/generate-sql",
            json={
                "question":         question,
                "confirmed_tables": confirmed_tables,
                "workspace_name":   workspace_name,
            },
            timeout=GENERATE_SQL_TIMEOUT,
        )
        return _handle(resp)
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot reach the backend. Is FastAPI running?"}
    except requests.exceptions.Timeout:
        return {"error": "SQL generation timed out. Try a simpler question."}


def get_all_workspaces() -> dict:
    try:
        resp = requests.get(f"{API_BASE_URL}/workspaces", timeout=WORKSPACE_TIMEOUT)
        return _handle(resp)
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot reach the backend."}
    except requests.exceptions.Timeout:
        return {"error": "Workspace list request timed out."}


def get_workspace(name: str) -> dict:
    try:
        resp = requests.get(f"{API_BASE_URL}/workspaces/{name}", timeout=WORKSPACE_TIMEOUT)
        return _handle(resp)
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot reach the backend."}
    except requests.exceptions.Timeout:
        return {"error": "Request timed out."}


def create_workspace(name: str, description: str, tables: list) -> dict:
    try:
        resp = requests.post(
            f"{API_BASE_URL}/workspaces",
            json={"name": name, "description": description, "tables": tables},
            timeout=WORKSPACE_TIMEOUT,
        )
        return _handle(resp)
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot reach the backend."}
    except requests.exceptions.Timeout:
        return {"error": "Request timed out."}


def delete_workspace(name: str) -> dict:
    try:
        resp = requests.delete(f"{API_BASE_URL}/workspaces/{name}", timeout=WORKSPACE_TIMEOUT)
        return _handle(resp)
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot reach the backend."}
    except requests.exceptions.Timeout:
        return {"error": "Request timed out."}


def list_all_tables() -> dict:
    try:
        resp = requests.get(f"{API_BASE_URL}/tables", timeout=WORKSPACE_TIMEOUT)
        return _handle(resp)
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot reach the backend."}
    except requests.exceptions.Timeout:
        return {"error": "Request timed out."}