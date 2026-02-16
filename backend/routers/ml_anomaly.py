"""
Use Case 5 – Anomaly Detection (Statistical approach via ES aggregations)
Index: transactions
"""

import math
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

INDEX = "transactions"


class AnomalyRequest(BaseModel):
    start_time: Optional[str] = "now-7d"
    end_time: Optional[str] = "now"
    z_score_threshold: Optional[float] = 2.5
    user_id: Optional[str] = None


@router.post("/detect")
async def detect_anomalies(req: Request, body: AnomalyRequest):
    """
    Detect anomalous transactions using a Z-score approach:
    1. Compute per-user mean and stddev over the selected period.
    2. Fetch individual transactions.
    3. Flag those with |z-score| > threshold.
    """
    es = req.app.state.es

    filter_clauses = [
        {"range": {"timestamp": {"gte": body.start_time, "lte": body.end_time}}}
    ]
    if body.user_id:
        filter_clauses.append({"term": {"user_id.keyword": body.user_id}})

    try:
        # Step 1: Get global stats
        stats_resp = es.search(
            index=INDEX,
            body={
                "size": 0,
                "query": {"bool": {"filter": filter_clauses}},
                "aggs": {
                    "amount_stats": {"extended_stats": {"field": "amount"}},
                    "by_user": {
                        "terms": {"field": "user_id.keyword", "size": 100},
                        "aggs": {
                            "user_stats": {"extended_stats": {"field": "amount"}}
                        },
                    },
                },
            },
        )

        global_stats = stats_resp["aggregations"]["amount_stats"]
        global_mean = global_stats.get("avg") or 0
        global_std = global_stats.get("std_deviation") or 1

        # Step 2: Fetch all transactions in window
        txn_resp = es.search(
            index=INDEX,
            body={
                "size": 500,
                "query": {"bool": {"filter": filter_clauses}},
                "sort": [{"timestamp": {"order": "desc"}}],
            },
        )

        transactions = [h["_source"] for h in txn_resp["hits"]["hits"]]

        # Step 3: Compute Z-scores and flag anomalies
        anomalies = []
        normal = []
        for txn in transactions:
            amt = txn.get("amount", 0)
            z = (amt - global_mean) / global_std if global_std != 0 else 0
            txn["z_score"] = round(z, 3)
            txn["is_anomaly"] = abs(z) > body.z_score_threshold
            if txn["is_anomaly"]:
                anomalies.append(txn)
            else:
                normal.append(txn)

        return {
            "status": "ok",
            "global_stats": {
                "mean": round(global_mean, 2),
                "std_dev": round(global_std, 2),
                "count": global_stats.get("count", 0),
                "min": round(global_stats.get("min") or 0, 2),
                "max": round(global_stats.get("max") or 0, 2),
            },
            "threshold": body.z_score_threshold,
            "anomaly_count": len(anomalies),
            "normal_count": len(normal),
            "anomalies": anomalies[:50],  # cap at 50
            "sample_normal": normal[:20],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/transaction-summary")
async def transaction_summary(req: Request, days: int = 7):
    """Daily transaction totals for sparkline chart."""
    es = req.app.state.es
    try:
        resp = es.search(
            index=INDEX,
            body={
                "size": 0,
                "query": {"range": {"timestamp": {"gte": f"now-{days}d"}}},
                "aggs": {
                    "daily": {
                        "date_histogram": {
                            "field": "timestamp",
                            "calendar_interval": "1d",
                        },
                        "aggs": {
                            "total_amount": {"sum": {"field": "amount"}},
                            "avg_amount": {"avg": {"field": "amount"}},
                            "tx_count": {"value_count": {"field": "amount"}},
                        },
                    }
                },
            },
        )
        buckets = resp["aggregations"]["daily"]["buckets"]
        return {
            "status": "ok",
            "data": [
                {
                    "date": b["key_as_string"],
                    "total": round(b["total_amount"]["value"] or 0, 2),
                    "avg": round(b["avg_amount"]["value"] or 0, 2),
                    "count": b["tx_count"]["value"],
                }
                for b in buckets
            ],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/users")
async def list_users(req: Request):
    """List distinct user IDs from transactions index."""
    es = req.app.state.es
    try:
        resp = es.search(
            index=INDEX,
            body={
                "size": 0,
                "aggs": {"users": {"terms": {"field": "user_id.keyword", "size": 100}}},
            },
        )
        return {
            "status": "ok",
            "data": [b["key"] for b in resp["aggregations"]["users"]["buckets"]],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
