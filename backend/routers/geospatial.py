"""
Use Case 4 – Geospatial Search
Index: locations
"""

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

INDEX = "locations"


class GeoSearchRequest(BaseModel):
    lat: float
    lon: float
    distance: Optional[str] = "50km"
    size: Optional[int] = 20
    category: Optional[str] = None  # restaurant | store | hotel | park


class BoundingBoxRequest(BaseModel):
    top_left_lat: float
    top_left_lon: float
    bottom_right_lat: float
    bottom_right_lon: float
    size: Optional[int] = 50
    category: Optional[str] = None


@router.post("/nearby")
async def nearby_places(req: Request, body: GeoSearchRequest):
    """
    Geo-distance query: find all locations within a given radius.
    """
    es = req.app.state.es
    filter_clauses = [
        {
            "geo_distance": {
                "distance": body.distance,
                "location": {"lat": body.lat, "lon": body.lon},
            }
        }
    ]
    if body.category:
        filter_clauses.append({"term": {"category.keyword": body.category}})

    try:
        resp = es.search(
            index=INDEX,
            body={
                "size": body.size,
                "query": {"bool": {"filter": filter_clauses}},
                "sort": [
                    {
                        "_geo_distance": {
                            "location": {"lat": body.lat, "lon": body.lon},
                            "order": "asc",
                            "unit": "km",
                        }
                    }
                ],
                "script_fields": {
                    "distance_km": {
                        "script": {
                            "source": "doc['location'].arcDistance(params.lat, params.lon) / 1000",
                            "params": {"lat": body.lat, "lon": body.lon},
                        }
                    }
                },
                "_source": True,
            },
        )
        hits = resp["hits"]["hits"]
        return {
            "status": "ok",
            "total": resp["hits"]["total"]["value"],
            "data": [
                {
                    **h["_source"],
                    "distance_km": round(
                        h.get("fields", {}).get("distance_km", [0])[0], 2
                    ),
                }
                for h in hits
            ],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/bounding-box")
async def bounding_box_search(req: Request, body: BoundingBoxRequest):
    """
    Geo bounding-box query: find locations within a rectangular area.
    """
    es = req.app.state.es
    filter_clauses = [
        {
            "geo_bounding_box": {
                "location": {
                    "top_left": {
                        "lat": body.top_left_lat,
                        "lon": body.top_left_lon,
                    },
                    "bottom_right": {
                        "lat": body.bottom_right_lat,
                        "lon": body.bottom_right_lon,
                    },
                }
            }
        }
    ]
    if body.category:
        filter_clauses.append({"term": {"category.keyword": body.category}})

    try:
        resp = es.search(
            index=INDEX,
            body={
                "size": body.size,
                "query": {"bool": {"filter": filter_clauses}},
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


@router.get("/categories")
async def location_categories(req: Request):
    """Aggregation of location categories."""
    es = req.app.state.es
    try:
        resp = es.search(
            index=INDEX,
            body={
                "size": 0,
                "aggs": {
                    "categories": {"terms": {"field": "category.keyword", "size": 20}}
                },
            },
        )
        return {
            "status": "ok",
            "data": [
                {"category": b["key"], "count": b["doc_count"]}
                for b in resp["aggregations"]["categories"]["buckets"]
            ],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/cluster")
async def geo_cluster(req: Request, precision: int = 5):
    """
    Geohash grid aggregation for map clustering.
    """
    es = req.app.state.es
    try:
        resp = es.search(
            index=INDEX,
            body={
                "size": 0,
                "aggs": {
                    "grid": {
                        "geohash_grid": {
                            "field": "location",
                            "precision": precision,
                        }
                    }
                },
            },
        )
        return {
            "status": "ok",
            "data": resp["aggregations"]["grid"]["buckets"],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
