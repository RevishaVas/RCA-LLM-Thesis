import os
import psycopg2

def pg_conn():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        dbname=os.getenv("POSTGRES_DB", "llmrca"),
        user=os.getenv("POSTGRES_USER", "llmrca"),
        password=os.getenv("POSTGRES_PASSWORD", "llmrca"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
    )
