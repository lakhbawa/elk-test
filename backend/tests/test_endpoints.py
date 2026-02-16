"""
Pytest smoke tests for the Elasticsearch Demo Hub backend.

Run with:
    pytest backend/tests/test_endpoints.py -v
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def mock_es():
    """Return a MagicMock that stands in for the Elasticsearch client."""
    es = MagicMock()

    # Generic search response
    es.search.return_value = {
        "hits": {
            "total": {"value": 1},
            "hits": [
                {
                    "_id": "1",
                    "_score": 1.5,
                    "_source": {
                        "title": "Test Product",
                        "description": "A great product",
                        "price": 19.99,
                        "category": "electronics",
                        "location": {"lat": 40.7128, "lon": -74.0060},
                    },
                    "highlight": {"title": ["<mark>Test</mark> Product"]},
                    "fields": {"distance_km": [1.2]},
                }
            ],
        },
        "aggregations": {
            "categories": {"buckets": [{"key": "electronics", "doc_count": 5}]},
            "by_level": {"buckets": [{"key": "ERROR", "doc_count": 10}]},
            "over_time": {
                "buckets": [
                    {
                        "key_as_string": "2024-01-01T00:00:00",
                        "doc_count": 5,
                        "avg_value": {"value": 42.5},
                        "max_value": {"value": 90.0},
                        "min_value": {"value": 10.0},
                        "by_level": {"buckets": [{"key": "INFO", "doc_count": 3}]},
                    }
                ]
            },
            "amount_stats": {
                "avg": 100.0,
                "std_deviation": 20.0,
                "count": 50,
                "min": 10.0,
                "max": 500.0,
            },
            "by_metric": {
                "buckets": [
                    {
                        "key": "cpu",
                        "avg_value": {"value": 55.0},
                        "max_value": {"value": 90.0},
                    }
                ]
            },
            "hosts": {"buckets": [{"key": "server-01"}]},
            "daily": {
                "buckets": [
                    {
                        "key_as_string": "2024-01-01",
                        "total_amount": {"value": 5000.0},
                        "avg_amount": {"value": 100.0},
                        "tx_count": {"value": 50},
                    }
                ]
            },
            "users": {"buckets": [{"key": "user-001"}]},
            "recommended": {"buckets": [{"key": "prod-001"}]},
            "similar_users": {"buckets": [{"key": "user-002"}]},
            "popular": {"buckets": [{"key": "prod-001"}]},
            "by_host": {
                "buckets": [
                    {
                        "key": "web-01",
                        "doc_count": 5,
                        "top_messages": {
                            "buckets": [{"key": "Connection refused", "doc_count": 3}]
                        },
                    }
                ]
            },
            "grid": {"buckets": [{"key": "dr5r", "doc_count": 10}]},
        },
        "suggest": {
            "product-suggest": [
                {
                    "options": [
                        {"_source": {"title": "Test Product"}, "text": "test"}
                    ]
                }
            ]
        },
    }

    es.cluster.health.return_value = {
        "status": "green",
        "cluster_name": "test-cluster",
    }
    es.indices.exists.return_value = True
    es.indices.delete.return_value = {"acknowledged": True}

    return es


@pytest.fixture(scope="module")
def client(mock_es):
    """Create a TestClient with a mocked ES instance."""
    with patch("main.Elasticsearch", return_value=mock_es):
        from main import app
        app.state.es = mock_es
        with TestClient(app) as c:
            yield c


# ─── Health ───────────────────────────────────────────────────────────────────

def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "elasticsearch" in data


# ─── Full-Text Search ─────────────────────────────────────────────────────────

def test_fulltext_search(client):
    resp = client.post("/search/fulltext", json={"query": "test product"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "data" in data
    assert "total" in data


def test_autocomplete(client):
    resp = client.post("/search/autocomplete", json={"prefix": "test"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert isinstance(data["data"], list)


def test_categories(client):
    resp = client.get("/search/categories")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert len(data["data"]) > 0


def test_clear_index(client):
    resp = client.delete("/search/clear")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


# ─── Logs ─────────────────────────────────────────────────────────────────────

def test_log_search(client):
    resp = client.post("/logs/search", json={"keyword": "error", "level": "ERROR"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


def test_level_aggregation(client):
    resp = client.get("/logs/level-aggregation")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


def test_top_errors(client):
    resp = client.get("/logs/top-errors")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


def test_log_timeline(client):
    resp = client.get("/logs/timeline")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


# ─── Analytics ────────────────────────────────────────────────────────────────

def test_timeseries(client):
    resp = client.post("/analytics/timeseries", json={"metric": "cpu"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["metric"] == "cpu"


def test_analytics_hosts(client):
    resp = client.get("/analytics/hosts")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


def test_analytics_summary(client):
    resp = client.get("/analytics/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


# ─── Geospatial ───────────────────────────────────────────────────────────────

def test_nearby(client):
    resp = client.post(
        "/geo/nearby", json={"lat": 40.7128, "lon": -74.0060, "distance": "10km"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


def test_bounding_box(client):
    resp = client.post(
        "/geo/bounding-box",
        json={
            "top_left_lat": 41.0,
            "top_left_lon": -75.0,
            "bottom_right_lat": 40.0,
            "bottom_right_lon": -73.0,
        },
    )
    assert resp.status_code == 200


def test_geo_cluster(client):
    resp = client.get("/geo/cluster")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


# ─── Anomaly Detection ────────────────────────────────────────────────────────

def test_anomaly_detect(client):
    resp = client.post(
        "/ml/detect",
        json={"start_time": "now-7d", "end_time": "now", "z_score_threshold": 2.5},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "anomalies" in data


def test_transaction_summary(client):
    resp = client.get("/ml/transaction-summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


def test_ml_users(client):
    resp = client.get("/ml/users")
    assert resp.status_code == 200


# ─── Recommendations ──────────────────────────────────────────────────────────

def test_recommendations(client):
    resp = client.post("/recs/for-user", json={"user_id": "user-001"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


def test_popular(client):
    resp = client.get("/recs/popular")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


def test_rec_users(client):
    resp = client.get("/recs/users")
    assert resp.status_code == 200
