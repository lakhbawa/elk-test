"""
Use Case 1 – Full-Text Search
Index: products
"""

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter()

INDEX = "products"


class SearchRequest(BaseModel):
    query: str
    fields: Optional[List[str]] = ["title", "description", "category"]
    size: Optional[int] = 10
    from_: Optional[int] = 0


class AutocompleteRequest(BaseModel):
    prefix: str
    size: Optional[int] = 5


@router.post("/fulltext")
async def full_text_search(req: Request, body: SearchRequest):
    """
    Multi-match query with fuzzy matching and result highlighting.
    """
    es = req.app.state.es
    try:
        resp = es.search(
            index=INDEX,
            body={
                "from": body.from_,
                "size": body.size,
                "query": {
                    "multi_match": {
                        "query": body.query,
                        "fields": body.fields,
                        "type": "best_fields",
                        "fuzziness": "AUTO",
                        "operator": "or",
                    }
                },
                "highlight": {
                    "fields": {f: {} for f in body.fields},
                    "pre_tags": ["<mark>"],
                    "post_tags": ["</mark>"],
                },
                "sort": ["_score"],
            },
        )
        hits = resp["hits"]["hits"]
        return {
            "status": "ok",
            "total": resp["hits"]["total"]["value"],
            "data": [
                {
                    "id": h["_id"],
                    "score": h["_score"],
                    "source": h["_source"],
                    "highlights": h.get("highlight", {}),
                }
                for h in hits
            ],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/autocomplete")
async def autocomplete(req: Request, body: AutocompleteRequest):
    """
    Prefix-based autocomplete on the title.suggest field.
    """
    es = req.app.state.es
    try:
        resp = es.search(
            index=INDEX,
            body={
                "size": 0,
                "suggest": {
                    "product-suggest": {
                        "prefix": body.prefix,
                        "completion": {
                            "field": "title.suggest",
                            "size": body.size,
                            "skip_duplicates": True,
                        },
                    }
                },
            },
        )
        suggestions = resp["suggest"]["product-suggest"][0]["options"]
        return {
            "status": "ok",
            "data": [s["_source"]["title"] for s in suggestions],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/categories")
async def list_categories(req: Request):
    """Aggregation of product categories."""
    es = req.app.state.es
    try:
        resp = es.search(
            index=INDEX,
            body={
                "size": 0,
                "aggs": {
                    "categories": {
                        "terms": {"field": "category.keyword", "size": 20}
                    }
                },
            },
        )
        buckets = resp["aggregations"]["categories"]["buckets"]
        return {
            "status": "ok",
            "data": [{"category": b["key"], "count": b["doc_count"]} for b in buckets],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/clear")
async def clear_index(req: Request):
    """Delete and recreate the products index (reset demo)."""
    es = req.app.state.es
    try:
        if es.indices.exists(index=INDEX):
            es.indices.delete(index=INDEX)
        return {"status": "ok", "message": f"Index '{INDEX}' cleared."}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
