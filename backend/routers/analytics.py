"""
Use Case 3 – Real-Time Analytics & Observability
Index: metrics
"""

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

INDEX = "metrics"


class MetricsRequest(BaseModel):
    metric: Optional[str] = "cpu"  # cpu | memory | disk | network
    host: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    interval: Optional[str] = "5m"


@router.post("/timeseries")
async def get_timeseries(req: Request, body: MetricsRequest):
    """
    Date histogram aggregation with average and max values.
    Powers the line chart in the frontend.
    """
    es = req.app.state.es
    filter_clauses = [{"term": {"metric.keyword": body.metric}}]

    if body.host:
        filter_clauses.append({"term": {"host.keyword": body.host}})

    if body.start_time or body.end_time:
        rng = {}
        if body.start_time:
            rng["gte"] = body.start_time
        if body.end_time:
            rng["lte"] = body.end_time
        filter_clauses.append({"range": {"@timestamp": rng}})

    try:
        resp = es.search(
            index=INDEX,
            body={
                "size": 0,
                "query": {"bool": {"filter": filter_clauses}},
                "aggs": {
                    "over_time": {
                        "date_histogram": {
                            "field": "@timestamp",
                            "fixed_interval": body.interval,
                            "min_doc_count": 0,
                        },
                        "aggs": {
                            "avg_value": {"avg": {"field": "value"}},
                            "max_value": {"max": {"field": "value"}},
                            "min_value": {"min": {"field": "value"}},
                        },
                    }
                },
            },
        )
        buckets = resp["aggregations"]["over_time"]["buckets"]
        return {
            "status": "ok",
            "metric": body.metric,
            "data": [
                {
                    "timestamp": b["key_as_string"],
                    "avg": round(b["avg_value"]["value"] or 0, 2),
                    "max": round(b["max_value"]["value"] or 0, 2),
                    "min": round(b["min_value"]["value"] or 0, 2),
                }
                for b in buckets
            ],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/hosts")
async def list_hosts(req: Request):
    """List all monitored hosts."""
    es = req.app.state.es
    try:
        resp = es.search(
            index=INDEX,
            body={
                "size": 0,
                "aggs": {"hosts": {"terms": {"field": "host.keyword", "size": 50}}},
            },
        )
        return {
            "status": "ok",
            "data": [b["key"] for b in resp["aggregations"]["hosts"]["buckets"]],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/summary")
async def metrics_summary(req: Request, host: Optional[str] = None):
    """
    Per-metric average over the last 24 hours for a dashboard summary card.
    """
    es = req.app.state.es
    filter_clauses = [{"range": {"@timestamp": {"gte": "now-24h"}}}]
    if host:
        filter_clauses.append({"term": {"host.keyword": host}})

    try:
        resp = es.search(
            index=INDEX,
            body={
                "size": 0,
                "query": {"bool": {"filter": filter_clauses}},
                "aggs": {
                    "by_metric": {
                        "terms": {"field": "metric.keyword", "size": 10},
                        "aggs": {
                            "avg_value": {"avg": {"field": "value"}},
                            "max_value": {"max": {"field": "value"}},
                        },
                    }
                },
            },
        )
        buckets = resp["aggregations"]["by_metric"]["buckets"]
        return {
            "status": "ok",
            "data": [
                {
                    "metric": b["key"],
                    "avg_24h": round(b["avg_value"]["value"] or 0, 2),
                    "max_24h": round(b["max_value"]["value"] or 0, 2),
                }
                for b in buckets
            ],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
