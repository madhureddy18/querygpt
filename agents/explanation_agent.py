# agents/explanation_agent.py

import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv(override=True)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def explain_query(question: str, sql: str) -> str:
    """
    Takes the generated SQL and explains it in plain English.
    Shown below the SQL in the UI.
    """

    prompt = f"""You are a data analyst explaining a SQL query to a non-technical user.

User question: {question}

SQL query:
{sql}

Explain what this SQL does in 2-3 simple sentences:
- What data it is looking at
- What it is calculating or filtering
- What the result will show

No technical jargon. No markdown. Plain English only."""

    try:
        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"  [Explanation ERROR] {e}")
        return "Could not generate explanation."