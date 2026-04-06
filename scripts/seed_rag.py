import os
import json
import psycopg2
from sentence_transformers import SentenceTransformer

# -------------------------
# DB connection 
# -------------------------
def conn():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        dbname=os.getenv("POSTGRES_DB", "llmrca"),
        user=os.getenv("POSTGRES_USER", "llmrca"),
        password=os.getenv("POSTGRES_PASSWORD", "llmrca"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
    )

# -------------------------
# Seed cases (one per failure mode)

# -------------------------
# SEED_CASES = [
#     {
#         "doc_id": "case_missing_file",
#         "chunk_id": "chunk_001",
#         "content": (
#             "FailureType=MISSING_FILE\n"
#             "Symptom: FileNotFoundError while reading hydraulic_features.csv in ingest_raw_data.\n"
#             "RootCause: Incorrect HYDRAULIC_CSV_PATH or missing Docker volume mount.\n"
#             "Fix: Ensure docker-compose mounts ./data -> /opt/airflow/data and file exists.\n"
#             "Evidence: error contains 'FileNotFoundError' and path '/opt/airflow/data/'."
#         ),
#     },
#     {
#         "doc_id": "case_schema_drift_ps3",
#         "chunk_id": "chunk_001",
#         "content": (
#             "FailureType=SCHEMA_DRIFT_PS3\n"
#             "Symptom: validate_schema fails due to missing PS3 feature columns (PS3_mean, PS3_std, PS3_min, PS3_max, PS3_rms).\n"
#             "RootCause: Upstream schema change dropped PS3 signals or feature extraction stopped producing PS3_* columns.\n"
#             "Fix: Restore PS3 in feature builder OR update schema contract + downstream assumptions.\n"
#             "Evidence: missing column list includes 'PS3_' prefixed features."
#         ),
#     },
#     {
#         "doc_id": "case_nan_explosion",
#         "chunk_id": "chunk_001",
#         "content": (
#             "FailureType=NAN_EXPLOSION\n"
#             "Symptom: validate_data_quality fails because NaN ratio exceeds threshold in one or more feature columns.\n"
#             "RootCause: Data corruption or join/missing cycles producing NaNs; preprocessing policy too strict.\n"
#             "Fix: Add null-ratio metrics, impute missing values, or relax dropna policy; validate upstream extraction.\n"
#             "Evidence: metrics show high null_count/null_ratio; logs mention 'NaN' or 'dropna'."
#         ),
#     },
#     {
#         "doc_id": "case_preprocess_collapse",
#         "chunk_id": "chunk_001",
#         "content": (
#             "FailureType=PREPROCESS_EMPTY\n"
#             "Symptom: preprocess_signals drops all rows; df becomes empty.\n"
#             "RootCause: Over-aggressive cleaning (dropna) or invalid filtering thresholds.\n"
#             "Fix: Track rows_before/rows_after, relax cleaning, use imputation, or handle outliers differently.\n"
#             "Evidence: error 'No rows after preprocessing' and rows_after=0."
#         ),
#     },
#     {
#         "doc_id": "case_div0",
#         "chunk_id": "chunk_001",
#         "content": (
#             "FailureType=DIV0\n"
#             "Symptom: ZeroDivisionError during feature_engineering (ratio/normalization).\n"
#             "RootCause: Denominator feature becomes zero due to constant sensor values or bad scaling.\n"
#             "Fix: Add epsilon to denominator, clamp ranges, validate min/max before division.\n"
#             "Evidence: traceback contains 'ZeroDivisionError' in feature_engineering."
#         ),
#     },
#     {
#         "doc_id": "case_db_constraint",
#         "chunk_id": "chunk_001",
#         "content": (
#             "FailureType=DB_CONSTRAINT\n"
#             "Symptom: load_to_postgres fails with constraint violation (NOT NULL/UNIQUE/FK).\n"
#             "RootCause: Invalid transformed data or duplicate keys; mismatch between schema and data.\n"
#             "Fix: Validate constraints before insert; deduplicate; enforce types; log failing row counts.\n"
#             "Evidence: DB error mentions 'constraint' and table/column name."
#         ),
#     },
# ]

SEED_CASES = [

# -------------------------------------------------
# Missing input file
# -------------------------------------------------
{
"doc_id": "rag_missing_input_file",
"chunk_id": "chunk_001",
"content": (
"Pipeline Stage: Data Ingestion\n"
"Task: ingest_raw_data\n"
"Error Type: FileNotFoundError\n"
"Failure Category: Missing Input Dataset\n\n"

"Observed Symptoms:\n"
"- Airflow ingestion task fails immediately\n"
"- pandas.read_csv raises FileNotFoundError\n"
"- dataset path cannot be resolved at runtime\n"
"- downstream tasks are skipped\n\n"

"Likely Root Cause:\n"
"The configured dataset path is invalid or the input file is not available "
"inside the execution environment. This commonly occurs in containerized "
"Airflow deployments when Docker volume mounts are misconfigured, upstream "
"data export jobs fail, or environment-specific file paths differ between "
"local and runtime environments.\n\n"

"Evidence Pattern:\n"
"- FileNotFoundError in task logs\n"
"- read_csv failure referencing missing file\n"
"- failure occurs in ingestion stage\n\n"

"Corrective Actions:\n"
"- verify dataset path configuration\n"
"- confirm file exists in mounted directory\n"
"- validate container volume mounts\n"
"- rerun upstream data export\n\n"

"Preventive Actions:\n"
"- add file existence validation before ingestion\n"
"- monitor upstream dataset availability\n"
"- implement ingestion readiness checks"
)
},

# -------------------------------------------------
# Schema drift
# -------------------------------------------------
{
"doc_id": "rag_schema_drift",
"chunk_id": "chunk_001",
"content": (
"Pipeline Stage: Schema Validation\n"
"Task: validate_schema\n"
"Error Type: ValueError\n"
"Failure Category: Schema Drift\n\n"

"Observed Symptoms:\n"
"- schema validation step fails\n"
"- expected columns missing or renamed\n"
"- dataframe column mismatch detected\n"
"- downstream feature processing halted\n\n"

"Likely Root Cause:\n"
"Upstream data producer modified the dataset schema without updating "
"downstream validation logic. This may include renamed columns, removed "
"features, or additional unexpected fields. Schema drift is a common ETL "
"failure when pipelines enforce strict schema contracts.\n\n"

"Evidence Pattern:\n"
"- missing column errors in logs\n"
"- dataframe.columns mismatch\n"
"- failure during validate_schema task\n\n"

"Corrective Actions:\n"
"- update expected schema definition\n"
"- align upstream data producer\n"
"- implement schema mapping layer\n"
"- update feature extraction logic\n\n"

"Preventive Actions:\n"
"- version schema contracts\n"
"- add schema compatibility validation\n"
"- alert on column changes"
)
},

# -------------------------------------------------
# NaN explosion
# -------------------------------------------------
{
"doc_id": "rag_nan_explosion",
"chunk_id": "chunk_001",
"content": (
"Pipeline Stage: Data Quality Validation\n"
"Task: validate_data_quality\n"
"Error Type: ValueError\n"
"Failure Category: Excessive Missing Values\n\n"

"Observed Symptoms:\n"
"- validation step fails due to NaN values\n"
"- high null ratio detected\n"
"- dataset rejected by quality checks\n"
"- preprocessing stage not executed\n\n"

"Likely Root Cause:\n"
"Missing values introduced during upstream joins, resampling, or feature "
"extraction. This often occurs when sensor data is incomplete, time windows "
"do not align, or transformation logic drops values. Strict data quality "
"thresholds trigger pipeline failure.\n\n"

"Evidence Pattern:\n"
"- logs reference NaN or null values\n"
"- dropna removes large portion of dataset\n"
"- validation threshold exceeded\n\n"

"Corrective Actions:\n"
"- inspect upstream feature extraction\n"
"- apply missing value imputation\n"
"- relax null ratio threshold\n"
"- validate join logic\n\n"

"Preventive Actions:\n"
"- monitor null ratio metrics\n"
"- enforce completeness checks\n"
"- add data quality alerts"
)
},

# -------------------------------------------------
# Empty dataframe after preprocessing
# -------------------------------------------------
{
"doc_id": "rag_empty_after_preprocess",
"chunk_id": "chunk_001",
"content": (
"Pipeline Stage: Signal Preprocessing\n"
"Task: preprocess_signals\n"
"Error Type: ValueError\n"
"Failure Category: Empty Dataset After Cleaning\n\n"

"Observed Symptoms:\n"
"- preprocessing removes all rows\n"
"- dataframe becomes empty\n"
"- downstream feature engineering fails\n"
"- pipeline stops before aggregation\n\n"

"Likely Root Cause:\n"
"Over-aggressive filtering logic such as dropna(), outlier removal, or "
"threshold-based filtering removed all records. This commonly occurs in "
"sparse sensor datasets where missing values are frequent.\n\n"

"Evidence Pattern:\n"
"- dataset size becomes zero\n"
"- dropna applied to dataframe\n"
"- failure after preprocessing stage\n\n"

"Corrective Actions:\n"
"- relax filtering thresholds\n"
"- use imputation instead of dropna\n"
"- inspect missing value distribution\n"
"- validate preprocessing rules\n\n"

"Preventive Actions:\n"
"- track row counts between stages\n"
"- alert when dataset shrinks drastically\n"
"- validate preprocessing assumptions"
)
},

# -------------------------------------------------
# Divide by zero
# -------------------------------------------------
{
"doc_id": "rag_divide_by_zero",
"chunk_id": "chunk_001",
"content": (
"Pipeline Stage: Feature Engineering\n"
"Task: feature_engineering\n"
"Error Type: ZeroDivisionError\n"
"Failure Category: Divide By Zero\n\n"

"Observed Symptoms:\n"
"- feature engineering task fails\n"
"- ZeroDivisionError raised\n"
"- ratio based feature computation fails\n"
"- pipeline stops during feature calculation\n\n"

"Likely Root Cause:\n"
"Division performed using denominator values equal to zero. This commonly "
"occurs during normalization, ratio calculations, or scaling when sensor "
"values are constant or missing.\n\n"

"Evidence Pattern:\n"
"- ZeroDivisionError in traceback\n"
"- failure in feature_engineering\n"
"- ratio or normalization calculation\n\n"

"Corrective Actions:\n"
"- add epsilon to denominator\n"
"- validate denominator before division\n"
"- clamp values\n"
"- handle zero variance features\n\n"

"Preventive Actions:\n"
"- implement safe division utility\n"
"- monitor zero variance signals\n"
"- enforce normalization checks"
)
},

# -------------------------------------------------
# DB constraint
# -------------------------------------------------
{
"doc_id": "rag_db_constraint",
"chunk_id": "chunk_001",
"content": (
"Pipeline Stage: Data Loading\n"
"Task: load_to_postgres\n"
"Error Type: ValueError\n"
"Failure Category: Database Constraint Violation\n\n"

"Observed Symptoms:\n"
"- database insert fails\n"
"- constraint violation error\n"
"- load stage aborted\n"
"- transaction rollback triggered\n\n"

"Likely Root Cause:\n"
"Transformed dataset violates database constraints such as NOT NULL, "
"unique keys, or data type mismatch. This commonly occurs when upstream "
"transformations produce invalid values or duplicate records.\n\n"

"Evidence Pattern:\n"
"- constraint violation in logs\n"
"- insert operation failure\n"
"- failure in load_to_postgres task\n\n"

"Corrective Actions:\n"
"- validate data before insert\n"
"- remove duplicates\n"
"- enforce schema types\n"
"- check null constraints\n\n"

"Preventive Actions:\n"
"- add pre-load validation\n"
"- enforce unique keys\n"
"- log invalid rows"
)
}

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
            #cur.execute("DELETE FROM rca_knowledge WHERE source='seed' AND doc_id = ANY(%s);", (doc_ids,))
            cur.execute("DELETE FROM rca_knowledge WHERE source='seed';")
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
