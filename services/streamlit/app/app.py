import os
import json
import psycopg2
import pandas as pd
import streamlit as st


# =====================================================
# DB CONNECTION
# =====================================================
def conn():
    """
    Uses env vars if set.
    - Inside Docker: POSTGRES_HOST=postgres
    - From Windows host: POSTGRES_HOST=localhost
    """
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        dbname=os.getenv("POSTGRES_DB", "llmrca"),
        user=os.getenv("POSTGRES_USER", "llmrca"),
        password=os.getenv("POSTGRES_PASSWORD", "llmrca"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
    )


# =====================================================
# UI HELPERS
# =====================================================
def status_badge(status: str) -> str:
    return {
        "FAILED": "🔴 FAILED",
        "PROCESSING": "🟡 PROCESSING",
        "RESOLVED": "🟢 RESOLVED",
        "NEEDS_REVIEW": "🟠 NEEDS_REVIEW",
        "NEW": "⚪ NEW",
    }.get(status, status or "")


def pill(status: str) -> str:
    return {
        "FAILED": "🔴",
        "PROCESSING": "🟡",
        "RESOLVED": "🟢",
        "NEEDS_REVIEW": "🟠",
        "NEW": "⚪",
    }.get(status, "⚪")


def safe_json(x):
    """Convert jsonb/text/None -> python obj safely."""
    if x is None:
        return {}
    if isinstance(x, (dict, list)):
        return x
    if isinstance(x, str):
        try:
            return json.loads(x)
        except Exception:
            return {"raw": x}
    return {"raw": str(x)}


# =====================================================
# PAGE SETUP + FULL-WIDTH DASHBOARD STYLE
# =====================================================
st.set_page_config(
    page_title="LLM-RCA Observability Console",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>

/* ===== FULL WIDTH LAYOUT ===== */
.block-container {
  padding-top: 1rem;
  padding-bottom: 2rem;
  padding-left: 2.5rem;
  padding-right: 2.5rem;
  max-width: none !important;
}

/* hide streamlit chrome */
header {visibility: hidden;}
footer {visibility: hidden;}

/* ===== TYPO ===== */
h1, h2, h3 {
  letter-spacing: -0.02em;
  margin-bottom: 0.35rem;
}
p { margin-bottom: 0.4rem; }

/* ===== TABLE ===== */
[data-testid="stDataFrame"] {
  border-radius: 14px;
  overflow: hidden;
}

/* ===== CARDS ===== */
.card {
  border: 1px solid rgba(99,102,241,0.25);
  border-radius: 16px;
  padding: 16px 18px;
  background: rgba(99,102,241,0.06);
}

.card-plain {
  border: 1px solid rgba(49,51,63,0.18);
  border-radius: 16px;
  padding: 16px 18px;
  background: rgba(0,0,0,0.02);
}

.kpi {
  border: 1px solid rgba(49,51,63,0.18);
  border-radius: 16px;
  padding: 14px 16px;
  background: rgba(0,0,0,0.02);
}
.kpi .label {
  font-size: 12px;
  opacity: 0.70;
}
.kpi .value {
  font-size: 22px;
  font-weight: 750;
  margin-top: 2px;
}
.kpi .sub {
  font-size: 12px;
  opacity: 0.60;
  margin-top: 4px;
}

.badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 650;
  border: 1px solid rgba(49,51,63,0.18);
  background: rgba(0,0,0,0.02);
  margin-right: 6px;
}

.scrollbox {
  max-height: 560px;
  overflow-y: auto;
  border: 1px solid rgba(49,51,63,0.18);
  border-radius: 14px;
  padding: 12px 14px;
  background: rgba(0,0,0,0.02);
  white-space: pre-wrap;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12.5px;
  line-height: 1.5;
}

.hr {
  height: 1px;
  background: rgba(49,51,63,0.14);
  margin: 14px 0;
}

.smallmuted { opacity: 0.70; font-size: 12.5px; }


/* Hero status card */
.kpi.status {
  border-left: 6px solid rgba(34,197,94,1);
  background: rgba(34,197,94,0.06);
}

/* If you want NEEDS_REVIEW to pop too */
.kpi.warn {
  border-left: 6px solid rgba(245,158,11,1);
  background: rgba(245,158,11,0.06);
}

/* RCA verdict strip */
.verdict {
  border-left: 6px solid rgba(34,197,94,1);
  background: rgba(34,197,94,0.06);
}
.verdict.warn {
  border-left: 6px solid rgba(245,158,11,1);
  background: rgba(245,158,11,0.06);
}
.verdict.fail {
  border-left: 6px solid rgba(239,68,68,1);
  background: rgba(239,68,68,0.06);
}


.kpi.fail {
  border-left: 6px solid rgba(239,68,68,1);
  background: rgba(239,68,68,0.06);
}



</style>
""",
    unsafe_allow_html=True,
)


# =====================================================
# HEADER
# =====================================================
st.title(" LLM-RCA Observability Console")
st.markdown(
    """
<div class="card">
  <b>End-to-end loop:</b> Airflow failure → Incident logging → Metrics & logs → RAG retrieval → Multi-model RCA → HITL decision
  <div class="smallmuted">Use filters to find incidents. Select one to view logs, metrics, RAG retrieval and RCA outputs.</div>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown('<div class="hr"></div>', unsafe_allow_html=True)


# =====================================================
# FILTERS
# =====================================================
with st.container():
    c1, c2, c3, c4, c5 = st.columns([1.2, 1.1, 1.1, 2.3, 1.3])
    with c1:
        show_resolved = st.checkbox("Show resolved", value=True)
    with c2:
        only_failed = st.checkbox("Only failed", value=False)
    with c3:
        limit = st.selectbox("Rows", [25, 50, 100, 200], index=1)
    with c4:
        search = st.text_input("Search (dag/task/run/error)", value="").strip()
    with c5:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()


# =====================================================
# INCIDENT QUERY
# =====================================================
where = []
params = []

if only_failed:
    where.append("status = 'FAILED'")
elif not show_resolved:
    where.append("status IN ('FAILED','PROCESSING','NEEDS_REVIEW','NEW')")

if search:
    where.append(
        """
        (
            dag_id ILIKE %s OR
            task_id ILIKE %s OR
            run_id ILIKE %s OR
            coalesce(error_message,'') ILIKE %s
        )
        """
    )
    s = f"%{search}%"
    params.extend([s, s, s, s])

where_sql = (" WHERE " + " AND ".join(where)) if where else ""

query = f"""
WITH ranked AS (
  SELECT
    id, ts, dag_id, task_id, run_id, try_number, status,
    left(coalesce(error_message,''), 160) AS error_preview,
    ROW_NUMBER() OVER (
      PARTITION BY dag_id, task_id, run_id
      ORDER BY try_number DESC, ts DESC
    ) AS rn
  FROM incidents
  {where_sql}
)
SELECT id, ts, dag_id, task_id, run_id, try_number, status, error_preview
FROM ranked
WHERE rn = 1
ORDER BY ts DESC
LIMIT {int(limit)};
"""

with conn() as c:
    incidents = pd.read_sql(query, c, params=params)


# =====================================================
# KPI + TABLE
# =====================================================
if incidents.empty:
    st.info("No incidents found.")
    st.stop()

k1, k2, k3, k4 = st.columns([1, 1, 1, 2])
k1.metric("🔴 Failed", int((incidents.status == "FAILED").sum()))
k2.metric("🟡 Processing", int((incidents.status == "PROCESSING").sum()))
k3.metric("🟢 Resolved", int((incidents.status == "RESOLVED").sum()))
k4.markdown(
    "<div class='card-plain'><b>Tip:</b> Select an incident below to open the diagnostic workspace.</div>",
    unsafe_allow_html=True,
)

disp = incidents.copy()
disp["status"] = disp["status"].apply(status_badge)
disp = disp[["id", "ts", "status", "dag_id", "task_id", "run_id", "try_number", "error_preview"]]
st.dataframe(disp, use_container_width=True, hide_index=True)

st.markdown('<div class="hr"></div>', unsafe_allow_html=True)


# =====================================================
# INCIDENT DETAIL SELECTOR
# =====================================================
st.subheader("Incident Workspace")

options = [""] + incidents["id"].astype(str).tolist()


def fmt(x):
    if x == "":
        return "— Select an incident —"
    r = incidents.loc[incidents["id"].astype(str) == x].iloc[0]
    return f"{pill(r['status'])} {x[:8]}… | {r['dag_id']} / {r['task_id']} | try {r['try_number']}"


choice = st.selectbox("Select incident", options, format_func=fmt, index=0)
selected_id = choice if choice != "" else None

if not selected_id:
    st.info("Select an incident to view details.")
    st.stop()


# =====================================================
# LOAD DETAIL DATA
# =====================================================
with conn() as c:
    logs = pd.read_sql(
        """
        SELECT ts, source, message
        FROM task_logs
        WHERE incident_id=%s
        ORDER BY ts DESC
        LIMIT 60;
        """,
        c,
        params=(selected_id,),
    )

    metrics = pd.read_sql(
        """
        SELECT ts, metrics
        FROM incident_metrics
        WHERE incident_id=%s
        ORDER BY ts DESC
        LIMIT 1;
        """,
        c,
        params=(selected_id,),
    )

    results = pd.read_sql(
        """
        SELECT ts, model_name, root_cause, confidence, recommendation,
               evidence, retrieved_cases, raw_response
        FROM rca_results
        WHERE incident_id=%s
        ORDER BY ts DESC;
        """,
        c,
        params=(selected_id,),
    )

    jobs = pd.read_sql(
        """
        SELECT id, status, attempts, last_error, ts, updated_at
        FROM rca_jobs
        WHERE incident_id=%s
        ORDER BY ts DESC
        LIMIT 1;
        """,
        c,
        params=(selected_id,),
    )

row = incidents.loc[incidents["id"].astype(str) == selected_id].iloc[0]
selected_status = row["status"]

# parse metrics for failure_mode
failure_mode = None
m_ts = None
if not metrics.empty:
    m_ts = metrics.iloc[0]["ts"]
    m_obj = safe_json(metrics.iloc[0]["metrics"])
    failure_mode = m_obj.get("failure_mode")

job_status = jobs.iloc[0]["status"] if not jobs.empty else "—"
job_attempts = int(jobs.iloc[0]["attempts"]) if not jobs.empty else 0
job_last_error = jobs.iloc[0]["last_error"] if (not jobs.empty and jobs.iloc[0]["last_error"]) else None


# =====================================================
# SUMMARY + JOB ACTION ROW
# =====================================================
st.markdown("### Summary")

s1, s2, s3, s4, s5 = st.columns([1.2, 1.8, 1.5, 1.1, 1.3])



status_class = "status"
if selected_status == "NEEDS_REVIEW":
    status_class = "warn"
elif selected_status == "FAILED":
    status_class = "fail"

s1.markdown(
    f"""
<div class="kpi {status_class}">
  <div class="label">Status</div>
  <div class="value">{status_badge(selected_status)}</div>
  <div class="sub">{row["ts"]}</div>
</div>
""",
    unsafe_allow_html=True,
)


s2.markdown(
    f"""
<div class="kpi">
  <div class="label">DAG / Task</div>
  <div class="value">{row["dag_id"]}</div>
  <div class="sub">{row["task_id"]} · try {int(row["try_number"])}</div>
</div>
""",
    unsafe_allow_html=True,
)

s3.markdown(
    f"""
<div class="kpi">
  <div class="label">Run ID</div>
  <div class="value">{str(row["run_id"])[:18]}…</div>
  <div class="sub">Incident: {selected_id[:8]}…</div>
</div>
""",
    unsafe_allow_html=True,
)

s4.markdown(
    f"""
<div class="kpi">
  <div class="label">Failure Mode</div>
  <div class="value">{failure_mode or "—"}</div>
  <div class="sub">{("Metrics: " + str(m_ts)) if m_ts else ""}</div>
</div>
""",
    unsafe_allow_html=True,
)

s5.markdown(
    f"""
<div class="kpi">
  <div class="label">RCA Job</div>
  <div class="value">{job_status}</div>
  <div class="sub">Attempts: {job_attempts}</div>
</div>
""",
    unsafe_allow_html=True,
)

if job_last_error:
    st.warning(job_last_error)

a1, a2 = st.columns([3.2, 1.2])
with a2:
    if st.button("📝 Request RCA", use_container_width=True):
        try:
            with conn() as c:
                with c.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO rca_jobs (incident_id, status, attempts, last_error, ts, updated_at)
                        VALUES (%s, 'PENDING', 0, NULL, now(), now())
                        ON CONFLICT (incident_id) DO NOTHING;
                        """,
                        (selected_id,),
                    )
                c.commit()
            st.success("RCA job queued ✅")
            st.rerun()
        except Exception as e:
            st.error(str(e))

st.markdown('<div class="hr"></div>', unsafe_allow_html=True)


# =====================================================
# TABS
# =====================================================
tab_logs, tab_metrics, tab_rca, tab_raw = st.tabs(
    [" Logs", " Metrics", " RCA (Compare)", " Raw (debug)"]
)


# -------------------------
# LOGS TAB
# -------------------------
with tab_logs:
    st.subheader("Logs (tail)")
    if logs.empty:
        st.info("No logs.")
    else:
        text = "\n\n".join(f"[{r.ts}][{r.source}] {r.message}" for r in logs.itertuples())
        st.markdown(f'<div class="scrollbox">{text}</div>', unsafe_allow_html=True)


# -------------------------
# METRICS TAB
# -------------------------
with tab_metrics:
    st.subheader("Metrics Snapshot")
    if metrics.empty:
        st.info("No metrics.")
    else:
        st.caption(f"Latest: {metrics.iloc[0]['ts']}")
        m = safe_json(metrics.iloc[0]["metrics"])

        # show as tiles (up to 12)
        keys = list(m.keys())
        if not keys:
            st.info("Metrics payload is empty.")
        else:
            cols = st.columns(4)
            for i, k in enumerate(keys[:12]):
                v = m.get(k)
                cols[i % 4].markdown(
                    f"""
<div class="kpi">
  <div class="label">{k.replace("_"," ").title()}</div>
  <div class="value">{str(v)[:40]}</div>
</div>
""",
                    unsafe_allow_html=True,
                )

        with st.expander("Show raw JSON", expanded=False):
            st.json(m)


# -------------------------
# RCA TAB (side-by-side)
# -------------------------
with tab_rca:
    st.subheader("RCA Results (Side-by-side Model Comparison)")

    
    verdict_cls = "verdict"
    verdict_text = "System-generated RCA based on logs, metrics, and retrieved historical cases."
    if selected_status == "NEEDS_REVIEW":
        verdict_cls = "verdict warn"
        verdict_text = "At least one model is low-confidence or missing evidence. Human review recommended."
    elif selected_status == "FAILED":
        verdict_cls = "verdict fail"
        verdict_text = "RCA agent failed to produce a valid output. Check job logs / model connectivity."

    st.markdown(
        f"""
    <div class="card {verdict_cls}">
    <b>RCA Verdict</b><br/>
    <span class="smallmuted">{verdict_text}</span>
    </div>
    """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)


    # HITL banner
    if selected_status == "NEEDS_REVIEW":
        st.warning("🟠 NEEDS_REVIEW: At least one model is low-confidence or missing evidence.")
    elif selected_status == "RESOLVED":
        st.success("🟢 RESOLVED: Outputs look confident and evidence-backed.")
    elif selected_status == "FAILED":
        st.error("🔴 FAILED: RCA agent failed to produce results.")
    else:
        st.info(f"Status: {selected_status}")

    if results.empty:
        st.info("No RCA result yet.")
    else:
        # Build latest-per-model (in case multiple rows exist)
        by_model = {}
        for r in results.sort_values("ts", ascending=False).itertuples():
            if r.model_name not in by_model:
                by_model[r.model_name] = r

        models = list(by_model.values())
        cols = st.columns(len(models)) if len(models) > 1 else [st.container()]

        for col, r in zip(cols, models):
            with col:
                try:
                    conf_val = float(r.confidence)
                except Exception:
                    conf_val = 0.0

                # Header
                st.markdown(
                    f"""
<div class="card-plain">
  <b>{r.model_name}</b><br/>
  <span class="smallmuted">Updated: {r.ts}</span>
  <div class="hr"></div>
  <span class="badge">Confidence {conf_val:.2f}</span>
</div>
""",
                    unsafe_allow_html=True,
                )
                st.progress(min(max(conf_val, 0.0), 1.0))

                # Root cause
                st.markdown(
                    f"""
<div class="card">
  <b>Root Cause</b>
  <div class="hr"></div>
  <div style="white-space: pre-wrap; font-size: 14px; line-height: 1.55;">{r.root_cause}</div>
</div>
""",
                    unsafe_allow_html=True,
                )

#                 


                rec_text = r.recommendation or ""
                if "Preventive actions:" in rec_text:
                    corrective_part, preventive_part = rec_text.split("Preventive actions:", 1)
                else:
                    corrective_part, preventive_part = rec_text, ""

                corrective_part = corrective_part.replace("Corrective actions:", "").strip()
                preventive_part = preventive_part.strip()

                st.markdown(
                    f"""
                <div class="card-plain">
                <b> Corrective actions</b>
                <div class="hr"></div>
                <div style="white-space: pre-wrap; font-size: 13.5px; line-height: 1.55;">{corrective_part or "—"}</div>
                </div>
                """,
                    unsafe_allow_html=True,
                )

                if preventive_part:
                    st.markdown(
                        f"""
                <div class="card-plain">
                <b> Preventive actions</b>
                <div class="hr"></div>
                <div style="white-space: pre-wrap; font-size: 13.5px; line-height: 1.55;">{preventive_part}</div>
                </div>
                """,
                        unsafe_allow_html=True,
                    )



                # Evidence
                with st.expander(" Evidence used by model", expanded=False):
                    ev = safe_json(r.evidence)
                    if isinstance(ev, dict):
                        # if stored as dict by accident
                        st.json(ev)
                    else:
                        if not ev:
                            st.info("No evidence captured.")
                        else:
                            for item in ev:
                                st.markdown(f"- {item}")

                # RAG cards
                with st.expander(" RAG: Retrieved similar cases", expanded=False):
                    rc = safe_json(r.retrieved_cases)
                    if not rc:
                        st.info("No retrieved cases stored.")
                    else:
                        for hit in rc:
                            sim = float(hit.get("similarity", 0.0))
                            doc_id = hit.get("doc_id") or hit.get("id", "")[:8]
                            source = hit.get("source", "kb")
                            content = hit.get("content", "")

                            st.markdown(
                                f"""
<div class="card-plain">
  <span class="badge">Similarity {sim:.2f}</span>
  <span class="badge">{source}</span>
  <span class="badge">{doc_id}</span>
  <div class="hr"></div>
  <div style="white-space: pre-wrap; font-size: 13.5px; line-height: 1.55;">{content}</div>
</div>
""",
                                unsafe_allow_html=True,
                            )
                            st.markdown(" ")

                # Quick copy
                with st.expander(" Quick copy", expanded=False):
                    st.caption("Click inside and copy (Ctrl+C)")
                    st.code(r.root_cause or "", language="text")
                    st.code(r.recommendation or "", language="text")


# -------------------------
# RAW TAB
# -------------------------
with tab_raw:
    st.subheader("Raw response (debug)")
    if results.empty:
        st.info("No raw response.")
    else:
        latest = results.iloc[0]
        st.json(safe_json(latest.raw_response))
