# querygpt/rag/seed_sql_examples.py

import os
import psycopg2
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from rag.sql_examples import SQL_SAMPLES
from pgvector.psycopg2 import register_vector

load_dotenv(override=True)

DB_CONFIG = {
    "dbname":   os.getenv("DB_NAME"),
    "user":     os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host":     os.getenv("DB_HOST"),
    "port":     int(os.getenv("DB_PORT", 5432))
}

def seed():
    model = SentenceTransformer("all-MiniLM-L6-v2")
    conn  = psycopg2.connect(**DB_CONFIG)
    register_vector(conn)
    cur   = conn.cursor()

    # Clear existing data so re-running is safe
    cur.execute("TRUNCATE TABLE rag.sql_examples RESTART IDENTITY;")

    for sample in SQL_SAMPLES:
        # Embed only the question — NOT the SQL answer
        embedding = model.encode(sample["question"])

        cur.execute("""
            INSERT INTO rag.sql_examples 
                (question, sql_answer, domain, difficulty, embedding)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            sample["question"],
            sample["sql_answer"].strip(),
            sample["domain"],
            sample["difficulty"],
            embedding
        ))
        print(f"  Inserted: {sample['domain']:10s} | {sample['difficulty']:8s} | {sample['question'][:55]}")

    conn.commit()
    cur.close()
    conn.close()
    print(f"\nDone. {len(SQL_SAMPLES)} examples seeded into rag.sql_examples")

if __name__ == "__main__":
    seed()