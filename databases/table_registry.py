#databases/table_registry

from pgvector.psycopg2 import register_vector
from dotenv import load_dotenv
import psycopg2
from sentence_transformers import SentenceTransformer
from databases.tables_metadata import metadata
import os

load_dotenv(override=True)

model = SentenceTransformer("all-MiniLM-L6-v2")

DB_CONFIG = {
    "dbname":   os.getenv("DB_NAME"),
    "user":     os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host":     os.getenv("DB_HOST"),
    "port":     os.getenv("DB_PORT")
}

def table_metadata():

    conn = psycopg2.connect(**DB_CONFIG) # type: ignore
    register_vector(conn)
    cur  = conn.cursor()
    cur.execute("TRUNCATE TABLE metadata.table_registry RESTART IDENTITY;")

    for data in metadata:
        text_to_embed = f"""
        Table: {data['schema_name']}.{data['table_name']}
        Description: {data['description']}
        Use Cases: {data['examples']}
        Columns: {", ".join(data['key_columns'])}
        """
        desc_embedding = model.encode(text_to_embed)
        
        cur.execute("""insert into metadata.table_registry ("table_name", "schema_name", "description", "key_columns","embedding")
                     values(%s,%s,%s,%s,%s)

                    """,
                    (data["table_name"],data["schema_name"],data["description"],data["key_columns"],desc_embedding)
                    )
    conn.commit()
    cur.close()
    conn.close()
    print("Metadata Inserted Succesfully")
table_metadata()
