# RCA-LLM-Thesis

> **Automated Root Cause Analysis using Large Language Models on Hydraulic System Data**

A thesis project that combines a LangGraph-based LLM reasoning agent, Apache Airflow pipeline orchestration, a pgvector-backed PostgreSQL database, and a Streamlit dashboard to perform automated Root Cause Analysis (RCA) on industrial hydraulic system sensor data.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Services](#services)
- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [Project Structure](#project-structure)
- [Tech Stack](#tech-stack)

---

## Overview

This system ingests hydraulic sensor data, detects anomalies and failures via scheduled Airflow DAGs, and automatically triggers an LLM-based RCA agent that diagnoses the root cause of each failure. Results are stored in a shared PostgreSQL database (with vector embeddings via pgvector) and surfaced in a human-in-the-loop Streamlit dashboard.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Docker Compose Stack                  │
│                                                         │
│  ┌────────────┐    ┌────────────┐    ┌──────────────┐  │
│  │  Airflow   │    │ RCA Agent  │    │  Streamlit   │  │
│  │ (Pipeline  │───▶│ (LangGraph │───▶│  Dashboard   │  │
│  │  DAGs)     │    │  + LLM)    │    │  (UI)        │  │
│  └─────┬──────┘    └─────┬──────┘    └──────┬───────┘  │
│        │                 │                  │           │
│        └─────────────────▼──────────────────┘           │
│                    ┌──────────┐                         │
│                    │PostgreSQL│                         │
│                    │+ pgvector│                         │
│                    └──────────┘                         │
└─────────────────────────────────────────────────────────┘
```

---

## Services

### `postgres` — Unified Storage Layer
- Image: `pgvector/pgvector:pg15`
- Serves as the single database for Airflow metadata, application data, and vector embeddings.
- Initialised via SQL scripts in `db/init/`.

### `airflow` — Workflow Orchestrator
- Runs on `LocalExecutor` backed by PostgreSQL.
- Executes hydraulic pipeline DAGs that ingest CSV sensor data, detect failures, and write events to the database.
- Accessible at **http://localhost:8083** (admin / admin).

### `rca-agent` — Reasoning Engine
- Built with **LangGraph** and powered by **Groq** (fast inference) and/or **Gemini** LLMs.
- Polls the database for new failure events and generates RCA reports, storing results back to PostgreSQL.

### `streamlit` — Visualization Layer
- Human-in-the-loop dashboard for reviewing RCA results in real time.
- Accessible at the port defined by `STREAMLIT_PORT` (default **8501**).

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) v3.9+
- A **Groq API key** (get one at https://console.groq.com)
- Optionally a **Gemini API key** (https://aistudio.google.com)

---

## Getting Started

1. **Clone the repository**

```bash
git clone https://github.com/RevishaVas/RCA-LLM-Thesis.git
cd RCA-LLM-Thesis
```

2. **Create your environment file**

```bash
cp .env.example .env   # or create .env manually (see Configuration below)
```

3. **Set the Airflow user ID** (Linux/macOS)

```bash
echo "AIRFLOW_UID=$(id -u)" >> .env
```

4. **Build and start all services**

```bash
docker compose up --build
```

5. **Access the UIs**

| Service   | URL                        | Credentials     |
|-----------|----------------------------|-----------------|
| Airflow   | http://localhost:8083       | admin / admin   |
| Streamlit | http://localhost:8501       | —               |

---

## Configuration

Create a `.env` file in the project root with the following variables:

```env
# PostgreSQL
POSTGRES_DB=llmrca
POSTGRES_USER=llmrca
POSTGRES_PASSWORD=your_password
POSTGRES_PORT=5432

# Airflow
AIRFLOW_UID=1000          # output of `id -u` on Linux/macOS

# LLM APIs
GEMINI_API_KEY=your_gemini_key
GROQ_API_KEY=your_groq_key
GROQ_MODEL=llama3-8b-8192  # or any supported Groq model

# Failure simulation
FAILURE_MODE=valve_blockage  # type of hydraulic failure to inject

# Streamlit
STREAMLIT_PORT=8501
```

---

## Project Structure

```
RCA-LLM-Thesis/
├── db/
│   └── init/                  # SQL initialisation scripts run on first start
├── scripts/                   # Utility / helper scripts
├── services/
│   ├── airflow/
│   │   ├── dags/              # Airflow DAG definitions (hydraulic pipeline)
│   │   ├── logs/
│   │   └── plugins/
│   ├── rca-agent/             # LangGraph RCA agent service
│   └── streamlit/
│       └── app/app.py         # Streamlit dashboard
├── data/                      # Hydraulic sensor CSV data (mounted read-only)
├── docker-compose.yml
├── .gitignore
└── README.md
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Orchestration | Apache Airflow (LocalExecutor) |
| LLM Reasoning | LangGraph, Groq (Llama 3), Google Gemini |
| Database | PostgreSQL 15 + pgvector |
| Dashboard | Streamlit |
| Containerisation | Docker Compose |
| Language | Python 3 |

---

## Author

**RevishaVas** — thesis project exploring LLM-driven automated root cause analysis for industrial systems.
