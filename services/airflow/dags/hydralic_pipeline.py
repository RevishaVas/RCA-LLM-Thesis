
import os
import json
import time
from datetime import datetime
import pandas as pd

from airflow import DAG
from airflow.operators.python import PythonOperator

from failure_callback import log_incident
from utils.pg import pg_conn

FAILURE_MODE = os.getenv("FAILURE_MODE", "NONE").upper()
CSV_PATH = os.getenv("HYDRAULIC_CSV_PATH", "/opt/airflow/data/hydraulic_features.csv")

def ingest_raw_data(**_):
    if FAILURE_MODE == "MISSING_FILE":
        raise FileNotFoundError("Injected failure: missing hydraulic CSV")
    pd.read_csv(CSV_PATH)

def validate_schema(**_):
    if FAILURE_MODE == "SCHEMA_DRIFT":
        raise ValueError("Injected failure: schema drift")

def validate_data_quality(**_):
    if FAILURE_MODE == "NAN_EXPLOSION":
        raise ValueError("Injected failure: NaN explosion")

def preprocess_signals(**_):
    df = pd.read_csv(CSV_PATH).dropna()
    if df.empty:
        raise ValueError("No rows after preprocessing")

def feature_engineering(**_):
    if FAILURE_MODE == "DIV0":
        raise ZeroDivisionError("Injected divide by zero")

def aggregate_by_cycle(**_):
    df = pd.read_csv(CSV_PATH)
    df["cycle_id"] = df.index // 100
    df.groupby("cycle_id").mean(numeric_only=True)

def load_to_postgres(**_):
    if FAILURE_MODE == "DB_CONSTRAINT":
        raise ValueError("Injected DB constraint failure")

with DAG(
    dag_id="hydraulic_condition_monitoring_pipeline",
    start_date=datetime(2025, 1, 1),
    schedule=None,
    catchup=False,
    tags=["thesis", "rca"],
) as dag:

    t1 = PythonOperator(task_id="ingest_raw_data", python_callable=ingest_raw_data, on_failure_callback=log_incident)
    t2 = PythonOperator(task_id="validate_schema", python_callable=validate_schema, on_failure_callback=log_incident)
    t3 = PythonOperator(task_id="validate_data_quality", python_callable=validate_data_quality, on_failure_callback=log_incident)
    t4 = PythonOperator(task_id="preprocess_signals", python_callable=preprocess_signals, on_failure_callback=log_incident)
    t5 = PythonOperator(task_id="feature_engineering", python_callable=feature_engineering, on_failure_callback=log_incident)
    t6 = PythonOperator(task_id="aggregate_by_cycle", python_callable=aggregate_by_cycle, on_failure_callback=log_incident)
    t7 = PythonOperator(task_id="load_to_postgres", python_callable=load_to_postgres, on_failure_callback=log_incident)

    t1 >> t2 >> t3 >> t4 >> t5 >> t6 >> t7
