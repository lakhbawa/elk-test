"""
Use Case 2 – Log and Event Data Analysis
Index: app-logs-*
"""

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

INDEX = "app-logs-*"


class LogSearchRequest(BaseModel):
    keyword: Optional[str] = None
    level: Optional[str] = None  # ERROR, WARN, INFO, DEBUG
    start_time: Optional[str] = None  # ISO8601
    end_time: Optional[str] = None  # ISO8601
    size: Optional[int] = 50


@router.post("/search")
async def search_logs(req: Request, body: LogSearchRequest):
    """
    Filtered log search with optional keyword, log level, and date range.
    """
    es = req.app.state.es
    must_clauses = []

    if body.keyword:
        must_clauses.append({"match": {"message": {"query": body.keyword, "fuzziness": "AUTO"}}})
    if body.level:
        must_clauses.append({"term": {"level.keyword": body.level.upper()}})

    filter_clauses = []
    if body.start_time or body.end_time:
        range_filter = {"range": {"@timestamp": {}}}
        if body.start_time:
            range_filter["range"]["@timestamp"]["gte"] = body.start_time
        if body.end_time:
            range_filter["range"]["@timestamp"]["lte"] = body.end_time
        filter_clauses.append(range_filter)

    query = {
        "bool": {
            "must": must_clauses if must_clauses else [{"match_all": {}}],
            "filter": filter_clauses,
        }
    }

    try:
        resp = es.search(
            index=INDEX,
            body={
                "size": body.size,
                "query": query,
                "sort": [{"@timestamp": {"order": "desc"}}],
            },
        )
        hits = resp["hits"]["hits"]
        return {
            "status": "ok",
            "total": resp["hits"]["total"]["value"],
            "data": [h["_source"] for h in hits],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/level-aggregation")
async def level_aggregation(req: Request, start_time: Optional[str] = None, end_time: Optional[str] = None):
    """
    Aggregate log counts by level (for pie chart display).
    """
    es = req.app.state.es
    filter_clauses = []
    if start_time or end_time:
        rng = {}
        if start_time:
            rng["gte"] = start_time
        if end_time:
            rng["lte"] = end_time
        filter_clauses.append({"range": {"@timestamp": rng}})

    try:
        resp = es.search(
            index=INDEX,
            body={
                "size": 0,
                "query": {
                    "bool": {
                        "must": [{"match_all": {}}],
                        "filter": filter_clauses,
                    }
                },
                "aggs": {
                    "by_level": {
                        "terms": {"field": "level.keyword", "size": 10}
                    }
                },
            },
        )
        buckets = resp["aggregations"]["by_level"]["buckets"]
        return {
            "status": "ok",
            "data": [{"level": b["key"], "count": b["doc_count"]} for b in buckets],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/top-errors")
async def top_errors(req: Request, size: int = 10):
    """Top error messages grouped by host."""
    es = req.app.state.es
    try:
        resp = es.search(
            index=INDEX,
            body={
                "size": 0,
                "query": {"term": {"level.keyword": "ERROR"}},
                "aggs": {
                    "by_host": {
                        "terms": {"field": "host.keyword", "size": size},
                        "aggs": {
                            "top_messages": {
                                "terms": {"field": "message.keyword", "size": 3}
                            }
                        },
                    }
                },
            },
        )
        buckets = resp["aggregations"]["by_host"]["buckets"]
        return {
            "status": "ok",
            "data": [
                {
                    "host": b["key"],
                    "error_count": b["doc_count"],
                    "top_messages": [
                        {"message": m["key"], "count": m["doc_count"]}
                        for m in b["top_messages"]["buckets"]
                    ],
                }
                for b in buckets
            ],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/timeline")
async def log_timeline(
    req: Request,
    interval: str = "1h",
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
):
    """Date histogram of log events over time."""
    es = req.app.state.es
    filter_clauses = []
    if start_time or end_time:
        rng = {}
        if start_time:
            rng["gte"] = start_time
        if end_time:
            rng["lte"] = end_time
        filter_clauses.append({"range": {"@timestamp": rng}})

    try:
        resp = es.search(
            index=INDEX,
            body={
                "size": 0,
                "query": {"bool": {"must": [{"match_all": {}}], "filter": filter_clauses}},
                "aggs": {
                    "over_time": {
                        "date_histogram": {
                            "field": "@timestamp",
                            "calendar_interval": interval,
                            "min_doc_count": 0,
                        },
                        "aggs": {
                            "by_level": {
                                "terms": {"field": "level.keyword", "size": 5}
                            }
                        },
                    }
                },
            },
        )
        buckets = resp["aggregations"]["over_time"]["buckets"]
        return {
            "status": "ok",
            "data": [
                {
                    "timestamp": b["key_as_string"],
                    "total": b["doc_count"],
                    "by_level": {
                        lvl["key"]: lvl["doc_count"]
                        for lvl in b["by_level"]["buckets"]
                    },
                }
                for b in buckets
            ],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
