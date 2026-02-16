"""
Use Case 6 – Personalization / Recommendations
Index: interactions + products
"""

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter()

INTERACTIONS_INDEX = "interactions"
PRODUCTS_INDEX = "products"


class RecommendRequest(BaseModel):
    user_id: str
    size: Optional[int] = 6


@router.post("/for-user")
async def recommendations_for_user(req: Request, body: RecommendRequest):
    """
    Collaborative filtering lite:
    1. Find products that `user_id` has interacted with.
    2. Find other users who also interacted with those products.
    3. Return products those users interacted with (that our user hasn't seen yet).
    """
    es = req.app.state.es
    try:
        # Step 1: Products this user interacted with
        user_interactions = es.search(
            index=INTERACTIONS_INDEX,
            body={
                "size": 50,
                "query": {"term": {"user_id.keyword": body.user_id}},
                "_source": ["product_id", "event_type"],
            },
        )
        seen_product_ids = list(
            {h["_source"]["product_id"] for h in user_interactions["hits"]["hits"]}
        )

        if not seen_product_ids:
            return {"status": "ok", "data": [], "message": "No interactions found for this user."}

        # Step 2: Other users who interacted with the same products
        similar_users_resp = es.search(
            index=INTERACTIONS_INDEX,
            body={
                "size": 0,
                "query": {
                    "bool": {
                        "must": [{"terms": {"product_id.keyword": seen_product_ids}}],
                        "must_not": [{"term": {"user_id.keyword": body.user_id}}],
                    }
                },
                "aggs": {
                    "similar_users": {
                        "terms": {"field": "user_id.keyword", "size": 20}
                    }
                },
            },
        )
        similar_user_ids = [
            b["key"]
            for b in similar_users_resp["aggregations"]["similar_users"]["buckets"]
        ]

        if not similar_user_ids:
            # Fall back to popular products
            return await popular_products(req, size=body.size, exclude=seen_product_ids)

        # Step 3: Products similar users interacted with (excluding already seen)
        recs_resp = es.search(
            index=INTERACTIONS_INDEX,
            body={
                "size": 0,
                "query": {
                    "bool": {
                        "must": [{"terms": {"user_id.keyword": similar_user_ids}}],
                        "must_not": [{"terms": {"product_id.keyword": seen_product_ids}}],
                    }
                },
                "aggs": {
                    "recommended": {
                        "terms": {"field": "product_id.keyword", "size": body.size}
                    }
                },
            },
        )
        rec_product_ids = [
            b["key"]
            for b in recs_resp["aggregations"]["recommended"]["buckets"]
        ]

        if not rec_product_ids:
            return await popular_products(req, size=body.size, exclude=seen_product_ids)

        # Fetch full product docs
        products = es.search(
            index=PRODUCTS_INDEX,
            body={
                "size": body.size,
                "query": {"terms": {"_id": rec_product_ids}},
            },
        )
        return {
            "status": "ok",
            "user_id": body.user_id,
            "seen_count": len(seen_product_ids),
            "data": [h["_source"] for h in products["hits"]["hits"]],
        }

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/popular")
async def popular_products_endpoint(req: Request, size: int = 6):
    return await popular_products(req, size=size, exclude=[])


async def popular_products(req: Request, size: int = 6, exclude: List[str] = []):
    """Most-interacted products globally."""
    es = req.app.state.es
    must_not = [{"terms": {"product_id.keyword": exclude}}] if exclude else []
    resp = es.search(
        index=INTERACTIONS_INDEX,
        body={
            "size": 0,
            "query": {"bool": {"must": [{"match_all": {}}], "must_not": must_not}},
            "aggs": {
                "popular": {"terms": {"field": "product_id.keyword", "size": size}}
            },
        },
    )
    pop_ids = [b["key"] for b in resp["aggregations"]["popular"]["buckets"]]
    products = es.search(
        index=PRODUCTS_INDEX,
        body={"size": size, "query": {"terms": {"_id": pop_ids}}},
    )
    return {
        "status": "ok",
        "type": "popular",
        "data": [h["_source"] for h in products["hits"]["hits"]],
    }


@router.get("/users")
async def list_users(req: Request):
    """List user IDs that have interaction history."""
    es = req.app.state.es
    try:
        resp = es.search(
            index=INTERACTIONS_INDEX,
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
