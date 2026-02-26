import json
from sentence_transformers import SentenceTransformer

_EMB_MODEL = None

def embed_text(text: str) -> list[float]:
    global _EMB_MODEL
    if _EMB_MODEL is None:
        _EMB_MODEL = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")
    vec = _EMB_MODEL.encode([text], normalize_embeddings=True)[0]
    return vec.tolist()

def retrieve_rag_hits(c, incident_text: str, top_k: int = 4):
    emb = embed_text(incident_text)

    with c.cursor() as cur:
        cur.execute("""
            SELECT id, source, doc_id, chunk_id, content,
                   1 - (embedding <=> %s::vector) AS similarity
            FROM rca_knowledge
            ORDER BY embedding <=> %s::vector
            LIMIT %s;
        """, (emb, emb, top_k))
        rows = cur.fetchall()

    hits = []
    for rid, source, doc_id, chunk_id, content, sim in rows:
        hits.append({
            "id": str(rid),
            "source": source,
            "doc_id": doc_id,
            "chunk_id": chunk_id,
            "similarity": float(sim),
            "content": content[:1200],
        })

    return hits, emb
