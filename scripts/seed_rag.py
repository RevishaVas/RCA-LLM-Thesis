import os
import json
import psycopg2
from sentence_transformers import SentenceTransformer

# -------------------------
# DB connection 
# -------------------------
def conn():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        dbname=os.getenv("POSTGRES_DB", "llmrca"),
        user=os.getenv("POSTGRES_USER", "llmrca"),
        password=os.getenv("POSTGRES_PASSWORD", "llmrca"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
    )

# -------------------------
# Seed cases (one per failure mode)

# -------------------------
SEED_CASES = [
    {
        "doc_id": "case_missing_file",
        "chunk_id": "chunk_001",
        "content": (
            "FailureType=MISSING_FILE\n"
            "Symptom: FileNotFoundError while reading hydraulic_features.csv in ingest_raw_data.\n"
            "RootCause: Incorrect HYDRAULIC_CSV_PATH or missing Docker volume mount.\n"
            "Fix: Ensure docker-compose mounts ./data -> /opt/airflow/data and file exists.\n"
            "Evidence: error contains 'FileNotFoundError' and path '/opt/airflow/data/'."
        ),
    },
    {
        "doc_id": "case_schema_drift_ps3",
        "chunk_id": "chunk_001",
        "content": (
            "FailureType=SCHEMA_DRIFT_PS3\n"
            "Symptom: validate_schema fails due to missing PS3 feature columns (PS3_mean, PS3_std, PS3_min, PS3_max, PS3_rms).\n"
            "RootCause: Upstream schema change dropped PS3 signals or feature extraction stopped producing PS3_* columns.\n"
            "Fix: Restore PS3 in feature builder OR update schema contract + downstream assumptions.\n"
            "Evidence: missing column list includes 'PS3_' prefixed features."
        ),
    },
    {
        "doc_id": "case_nan_explosion",
        "chunk_id": "chunk_001",
        "content": (
            "FailureType=NAN_EXPLOSION\n"
            "Symptom: validate_data_quality fails because NaN ratio exceeds threshold in one or more feature columns.\n"
            "RootCause: Data corruption or join/missing cycles producing NaNs; preprocessing policy too strict.\n"
            "Fix: Add null-ratio metrics, impute missing values, or relax dropna policy; validate upstream extraction.\n"
            "Evidence: metrics show high null_count/null_ratio; logs mention 'NaN' or 'dropna'."
        ),
    },
    {
        "doc_id": "case_preprocess_collapse",
        "chunk_id": "chunk_001",
        "content": (
            "FailureType=PREPROCESS_EMPTY\n"
            "Symptom: preprocess_signals drops all rows; df becomes empty.\n"
            "RootCause: Over-aggressive cleaning (dropna) or invalid filtering thresholds.\n"
            "Fix: Track rows_before/rows_after, relax cleaning, use imputation, or handle outliers differently.\n"
            "Evidence: error 'No rows after preprocessing' and rows_after=0."
        ),
    },
    {
        "doc_id": "case_div0",
        "chunk_id": "chunk_001",
        "content": (
            "FailureType=DIV0\n"
            "Symptom: ZeroDivisionError during feature_engineering (ratio/normalization).\n"
            "RootCause: Denominator feature becomes zero due to constant sensor values or bad scaling.\n"
            "Fix: Add epsilon to denominator, clamp ranges, validate min/max before division.\n"
            "Evidence: traceback contains 'ZeroDivisionError' in feature_engineering."
        ),
    },
    {
        "doc_id": "case_db_constraint",
        "chunk_id": "chunk_001",
        "content": (
            "FailureType=DB_CONSTRAINT\n"
            "Symptom: load_to_postgres fails with constraint violation (NOT NULL/UNIQUE/FK).\n"
            "RootCause: Invalid transformed data or duplicate keys; mismatch between schema and data.\n"
            "Fix: Validate constraints before insert; deduplicate; enforce types; log failing row counts.\n"
            "Evidence: DB error mentions 'constraint' and table/column name."
        ),
    },
]

def main():
    model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")

    rows = []
    for case in SEED_CASES:
        vec = model.encode([case["content"]], normalize_embeddings=True)[0].tolist()
        rows.append((case["doc_id"], case["chunk_id"], case["content"], vec))

    with conn() as c:
        with c.cursor() as cur:
            # idempotent: remove existing seed rows by doc_id
            doc_ids = [r[0] for r in rows]
            cur.execute("DELETE FROM rca_knowledge WHERE source='seed' AND doc_id = ANY(%s);", (doc_ids,))

            # insert
            for doc_id, chunk_id, content, vec in rows:
                cur.execute(
                    """
                    INSERT INTO rca_knowledge (source, doc_id, chunk_id, content, embedding)
                    VALUES ('seed', %s, %s, %s, %s::vector);
                    """,
                    (doc_id, chunk_id, content, vec),
                )
        c.commit()

    print(f"✅ Seeded {len(rows)} RAG cases into rca_knowledge")

if __name__ == "__main__":
    main()
