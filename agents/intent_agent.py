# agents/intent_agent.py

import os
import psycopg2
from groq import Groq
from dotenv import load_dotenv
from pgvector.psycopg2 import register_vector
from collections import Counter
from models.shared_models import embed_model
from databases.workspace_manager import get_db_config

load_dotenv(override=True)

# ── clients ───────────────────────────────────────────────────
client      = Groq(api_key=os.getenv("GROQ_API_KEY"))

VALID_INTENTS = {
    "trip_analysis",
    "revenue_analysis",
    "location_analysis",
    "time_analysis",
    "general"
}


def classify_intent(question: str) -> str:
    """
    LLM-based intent classification.
    Sends question to Groq, returns domain string.
    """
    prompt = f"""
You are an expert data analyst.

Classify the question into ONE category:

1. trip_analysis     → counting or comparing trips, rides, distance, passengers
2. revenue_analysis  → fare, earnings, tips, payments, revenue, money
3. location_analysis → ONLY when the location itself is the subject
                       e.g. "show me zone X", "trips between X and Y",
                       "which zones exist in Manhattan"
4. time_analysis     → trends by hour, day, week, month
5. general           → truly cannot classify

CRITICAL — Grouping vs Measuring:
Zone, borough, area, location are often just GROUP BY columns.
Ask yourself: what is being COUNTED or MEASURED?

EXAMPLES:
"Which zone had the most TRIPS?"      → trip_analysis     (measuring trips)
"Which zone made the most REVENUE?"   → revenue_analysis  (measuring revenue)
"Which area is most ACTIVE?"          → trip_analysis     (measuring activity)
"Are TIPS higher in certain areas?"   → revenue_analysis  (measuring tips)
"Where are people TRAVELING from?"    → trip_analysis     (measuring travel)
"Show trips FROM zone X TO zone Y"    → location_analysis (location is the subject)
"Which zones EXIST in Manhattan?"     → location_analysis (location is the subject)

RULE: If you can replace zone/area/borough with service_type and
      the question still makes sense → it is NOT location_analysis.

Return ONLY the category name. No explanation.

Question: {question}
"""

    try:
        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {"role": "system", "content": "You are a strict intent classifier."},
                {"role": "user",   "content": prompt}
            ],
            temperature=0
        )
        intent = response.choices[0].message.content.strip().lower() # type: ignore
        return intent if intent in VALID_INTENTS else "general"

    except Exception as e:
        print(f"[ERROR] LLM intent classification failed: {e}")
        return "general"


def classify_intent_by_embedding(question: str, db_config: dict) -> tuple[str, float]:
    conn = psycopg2.connect(**db_config)
    """
    Embedding-based intent classification.
    Votes on domain by looking at top-5 most similar RAG examples.
    Returns (domain, confidence) where confidence = winning_votes / 5
    """
    embedding = embed_model.encode(question)
    register_vector(conn)
    cur  = conn.cursor()
    cur.execute("SET ivfflat.probes = 5;")

    cur.execute("""
        SELECT domain,
               1 - (embedding <=> %s) AS similarity
        FROM rag.sql_examples
        ORDER BY embedding <=> %s
        LIMIT 5
    """, (embedding, embedding))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    if not rows:
        return "general", 0.0

    domain_votes = Counter(row[0] for row in rows)
    top_domain, vote_count = domain_votes.most_common(1)[0]
    confidence = round(vote_count / len(rows), 2)

    return top_domain, confidence


def classify_intent_hybrid(question: str, db_config: dict) -> str:
    """
    Hybrid intent classification — combines LLM + embedding signals.

    Decision logic:
    - Both agree                → high confidence, return that domain
    - LLM says general          → trust embedding vote instead
    - They disagree             → trust LLM (better semantic understanding)
                                  log disagreement for future RAG improvements
    """
    llm_domain               = classify_intent(question)
    embed_domain, confidence = classify_intent_by_embedding(question, db_config)

    if llm_domain == embed_domain:
        print(f"  [Intent] LLM={llm_domain} | Embed={embed_domain} "
              f"| confidence=HIGH ✓")
        return llm_domain

    elif llm_domain == "general":
        print(f"  [Intent] LLM=general | Embed={embed_domain} "
              f"({confidence}) | using embedding vote")
        return embed_domain

    else:
        print(f"  [Intent] DISAGREE — LLM={llm_domain} | "
              f"Embed={embed_domain} | trusting LLM")
        return llm_domain

# # ── test ──────────────────────────────────────────────────────
# if __name__ == "__main__":

#     questions = [
#         "How many total trips were completed in September 2025?",
#         "What is the average trip distance across all cab types?",
#         "Which pickup zones had the most rides last week?",
#         "Show me the top 5 drop off boroughs by trip count",
#         "What is the average tip amount for yellow cabs?",
#         "Which payment method is used most — cash or card?",
#         "Compare total trips between yellow and green cabs",
#         "How many Uber and Lyft trips happened in September?",
#         "Which hour of the day has the highest trip volume?",
#         "What day of the week sees the most pickups?",
#         "Which zones generated the highest revenue last month?",
#         "At what time do we see the highest revenue from trips?",
#         "Which borough has the most trips and highest earnings?",
#         "Compare trip count and total revenue between weekdays and weekends",
#         "Which pickup locations have both high trip volume and high tips?",
#         "Where are people traveling the most from?",
#         "When is the system most busy?",
#         "Which areas perform best financially?",
#         "How do rides behave during peak hours?",
#         "Which part of the city is most active?",
#         "Show top performing segments",
#         "Give me the best areas",
#         "What trends do you see in the data?",
#         "Which category dominates?",
#         "Show important patterns",
#         "Do longer trips generate more money?",
#         "Is there a relationship between distance and fare?",
#         "Are tips higher in certain locations?",
#         "Do people travel more at night or day?",
#         "Which service type performs better overall?",
#         "top zones??",
#         "rides count yesterday",
#         "money per trip area wise",
#         "which time most rides happening",
#         "uber vs lyft which more trips bro",
#         "avg earning per ride?",
#         "where max pickups??",
#         "day wise trip stats",
#         "Which zone has highest trips at night and also highest revenue?",
#         "Compare revenue but only for busiest locations",
#         "Find areas where trips are low but earnings are high",
#         "Which day has low trips but high average fare?",
#         "Top 3 zones by revenue during peak hours"
#     ]

#     for q in questions:
#         llm_domain             = classify_intent(q)
#         embed_domain, conf     = classify_intent_by_embedding(q,db_config)
#         final_domain           = classify_intent_hybrid(q,db_config)
#         print(f"Q: {q}")
#         print(f"  LLM    → {llm_domain}")
#         print(f"  Embed  → {embed_domain} (confidence: {conf})")
#         print(f"  Final  → {final_domain}")
#         print()