# rag/rag_pipeline.py

import os
import psycopg2
from dotenv import load_dotenv
from pgvector.psycopg2 import register_vector
from models.shared_models import embed_model


load_dotenv(override=True)



def get_relevant_samples(question: str, db_config: dict, domain: str = None, top_k: int = 5) -> list[dict]:
    """
    Searches pgvector for the most similar SQL examples to the question.
    Optionally filters by domain for faster, more accurate results.

    Args:
        question : natural language question from user
        domain   : intent domain — filters search scope
                   pass None to search across all domains
        top_k    : number of examples to return

    Returns:
        list of dicts: [{ question, sql_answer, domain, difficulty, similarity }]
    """
    if domain == "general":
        domain = None # type: ignore

    embedding = embed_model.encode(question)
    conn = psycopg2.connect(**db_config)
    register_vector(conn)
    cur  = conn.cursor()
    cur.execute("SET ivfflat.probes = 5;")

    if domain:
        cur.execute("""
            SELECT question,
                   sql_answer,
                   domain,
                   difficulty,
                   1 - (embedding <=> %s) AS similarity
            FROM rag.sql_examples
            WHERE domain = %s
            ORDER BY embedding <=> %s
            LIMIT %s
        """, (embedding, domain, embedding, top_k))
    else:
        cur.execute("""
            SELECT question,
                   sql_answer,
                   domain,
                   difficulty,
                   1 - (embedding <=> %s) AS similarity
            FROM rag.sql_examples
            ORDER BY embedding <=> %s
            LIMIT %s
        """, (embedding, embedding, top_k))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    results = []
    for row in rows:
        results.append({
            "question":   row[0],
            "sql_answer": row[1],
            "domain":     row[2],
            "difficulty": row[3],
            "similarity": round(float(row[4]), 4)
        })

    if results and results[0]["similarity"] < 0.4:
        print(f"  [RAG WARNING] Low similarity: {results[0]['similarity']} "
              f"— no strong match for: '{question}'")

    return results


def get_samples_multi_domain(question: str, db_config: dict, domains: list[str], top_k: int = 3) -> list[dict]:
    """
    For multi-domain questions — searches multiple domains,
    takes top_k from each, re-ranks by similarity score.

    Used when intent classification has low confidence
    and the question spans multiple domains.
    """
    all_samples = []
    for domain in domains:
        samples = get_relevant_samples(question, db_config, domain=domain, top_k=top_k)
        all_samples.extend(samples)

    all_samples.sort(key=lambda x: x["similarity"], reverse=True)
    return all_samples[:top_k * len(domains)]


def format_examples_for_prompt(samples: list[dict]) -> str:
    """
    Formats retrieved SQL examples into a few-shot prompt block.
    This text block gets injected into the LLM prompt on Day 7.
    """
    if not samples:
        return "No relevant examples found."

    lines = ["Relevant SQL examples:\n"]
    for i, s in enumerate(samples, 1):
        lines.append(f"Example {i}:")
        lines.append(f"Question: {s['question']}")
        lines.append(f"SQL:\n{s['sql_answer'].strip()}")
        lines.append("")

    return "\n".join(lines)


def get_relevant_samples_for_question(question: str, db_config: dict, top_k: int = 5) -> list[dict]:

    """
    Main entry point for the rest of the system.

    Internally runs:
    1. classify_intent_hybrid  → get domain
    2. get_relevant_samples    → search pgvector filtered by domain

    This is the single function called by the pipeline on Day 7.
    """
    from agents.intent_agent import classify_intent_hybrid

    domain  = classify_intent_hybrid(question, db_config)

    if domain == "general":
        domain = None

    samples = get_relevant_samples(question, db_config, domain=domain, top_k=top_k)
    print(f"  [RAG] → {len(samples)} examples retrieved "
          f"(best: {samples[0]['similarity'] if samples else 'none'})")

    return samples


# ── test ──────────────────────────────────────────────────────
# if __name__ == "__main__":

#     test_questions = [
#         "How many trips happened today?",
#         "Which zone made the most revenue?",
#         "What is the busiest hour in Brooklyn?",
#         "Show me trips from JFK to Manhattan",
#         "What is the weather today?",
#     ]

#     for q in test_questions:
#         print(f"\n{'='*60}")
#         print(f"Q: {q}")
#         results = get_relevant_samples_for_question(q, top_k=5)
#         for r in results:
#             print(f"     [{r['similarity']}]  {r['question'][:55]}")
#         print()
#         print(format_examples_for_prompt(results[:2]))
