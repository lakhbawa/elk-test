"""
Elasticsearch Demo Hub – FastAPI Backend
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from elasticsearch import Elasticsearch

from config import settings
from routers import search, logs, analytics, geospatial, ml_anomaly, recommendations

app = FastAPI(
    title="Elasticsearch Demo Hub",
    description="Production-ready demos for key Elasticsearch use cases.",
    version="1.0.0",
)

# ─── CORS ────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── ES Client (app-level singleton) ─────────────────────────────────────────
es_client: Elasticsearch = None


@app.on_event("startup")
async def startup_event():
    global es_client
    es_client = Elasticsearch(
        hosts=[
            {
                "host": settings.elasticsearch_host,
                "port": settings.elasticsearch_port,
                "scheme": settings.elasticsearch_scheme,
            }
        ],
        basic_auth=(settings.elasticsearch_username, settings.elasticsearch_password),
        verify_certs=False,
        request_timeout=30,
    )
    # Share the client with routers via app.state
    app.state.es = es_client


@app.on_event("shutdown")
async def shutdown_event():
    if es_client:
        es_client.close()


# ─── Health ───────────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
async def health():
    """Check API and Elasticsearch connectivity."""
    try:
        info = app.state.es.cluster.health()
        return {
            "status": "ok",
            "elasticsearch": info["status"],
            "cluster_name": info.get("cluster_name"),
        }
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


# ─── Routers ──────────────────────────────────────────────────────────────────
app.include_router(search.router, prefix="/search", tags=["Full-Text Search"])
app.include_router(logs.router, prefix="/logs", tags=["Log Analysis"])
app.include_router(analytics.router, prefix="/analytics", tags=["Real-Time Analytics"])
app.include_router(geospatial.router, prefix="/geo", tags=["Geospatial Search"])
app.include_router(ml_anomaly.router, prefix="/ml", tags=["Anomaly Detection"])
app.include_router(recommendations.router, prefix="/recs", tags=["Recommendations"])
