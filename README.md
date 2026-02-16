# Elasticsearch Demo Hub

A production-ready, multi-use-case demo application showcasing the power of
Elasticsearch. Built with **FastAPI**, **React**, **Logstash**, and orchestrated via
**Docker Compose**.

---

## Architecture

```
┌─────────────┐    ┌──────────────┐    ┌────────────────────┐
│   Browser   │───▶│ React (3000) │───▶│  FastAPI  (8000)   │
└─────────────┘    └──────────────┘    └────────┬───────────┘
                                                │
                   ┌────────────────────────────▼───────────┐
                   │        Elasticsearch (9200)             │
                   │         (single-node, 8.12)             │
                   └────────────────────────────────────────┘
                                    ▲
                   ┌────────────────┴───────────┐
                   │       Logstash (5044)       │
                   │  (Nginx log ingestion)      │
                   └────────────────────────────┘
                   ┌────────────────────────────┐
                   │        Kibana (5601)        │
                   │  (Optional visualization)  │
                   └────────────────────────────┘
```

### Services

| Service         | Port  | Purpose                                         |
|-----------------|-------|-------------------------------------------------|
| `frontend`      | 3000  | React SPA – Demo Hub UI                         |
| `backend`       | 8000  | FastAPI – All use-case endpoints                |
| `elasticsearch` | 9200  | Primary data store for all use cases            |
| `kibana`        | 5601  | Visualization layer (optional embeds)           |
| `logstash`      | 5044  | Nginx log ingestion pipeline                    |
| `seed`          | –     | One-shot data population on startup             |

---

## Prerequisites

| Requirement           | Minimum Version |
|-----------------------|-----------------|
| Docker Engine         | 24+             |
| Docker Compose        | 2.20+           |
| RAM                   | 4 GB            |
| Disk                  | 5 GB free       |

### Increase virtual memory (Linux hosts only)

Elasticsearch requires:
```bash
sudo sysctl -w vm.max_map_count=262144
# Make permanent:
echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf
```

---

## Quick Start

```bash
# 1. Clone and enter the project
git clone <repo-url>
cd elk-test

# 2. (Optional) customise passwords – edit .env
#    Default password: changeme

# 3. Start the full stack
docker-compose up -d

# 4. Wait ~90 seconds for all services to become healthy
docker-compose ps

# 5. Open the demo UI
open http://localhost:3000        # Demo Hub
open http://localhost:5601        # Kibana
open http://localhost:8000/docs   # FastAPI Swagger UI
```

> The `seed` service runs automatically and populates all six indices.
> Check its logs: `docker-compose logs -f seed`

---

## Demo Use Cases

### 1. Full-Text Search – Product Catalog

**Index:** `products` | **Documents:** ~150 e-commerce products

**What it demos:**
- `multi_match` query across `title`, `description`, `category` fields
- `fuzziness: AUTO` for typo-tolerance (`"headphons"` → `"headphones"`)
- Completion suggester for real-time autocomplete
- Result highlighting with `<mark>` tags
- `terms` aggregation for faceted category counts

**Example ES query:**
```json
POST /products/_search
{
  "query": {
    "multi_match": {
      "query": "wireless headphones",
      "fields": ["title^3", "description", "category"],
      "fuzziness": "AUTO"
    }
  },
  "highlight": { "fields": { "title": {}, "description": {} } }
}
```

**Why ES excels:** Inverted index tokenization, BM25 scoring, and native
completion suggesters make sub-millisecond fuzzy full-text search trivial to
implement at scale.

**Docs:** https://www.elastic.co/guide/en/elasticsearch/reference/current/full-text-queries.html

---

### 2. Log & Event Data Analysis

**Index:** `app-logs-YYYY.MM.dd` (daily ILM pattern) | **Documents:** ~2,000 logs

**What it demos:**
- Index template with daily rollover pattern (`app-logs-*`)
- `bool` query with must/filter clauses for keyword + level + date range
- `terms` aggregation for log level distribution (pie chart)
- Nested `terms` aggregation for top error hosts → top messages
- `date_histogram` aggregation for timeline view

**Example ES query (top error hosts):**
```json
POST /app-logs-*/_search
{
  "size": 0,
  "query": { "term": { "level.keyword": "ERROR" } },
  "aggs": {
    "by_host": {
      "terms": { "field": "host.keyword", "size": 5 },
      "aggs": {
        "top_messages": { "terms": { "field": "message.keyword", "size": 3 } }
      }
    }
  }
}
```

**Logstash pipeline:** Parses raw Nginx combined access log format → enriches
with log level based on HTTP status code → ships to daily index.

**Docs:** https://www.elastic.co/guide/en/elasticsearch/reference/current/search-aggregations-bucket-datehistogram-aggregation.html

---

### 3. Real-Time Analytics & Observability

**Index:** `metrics` | **Documents:** ~270,000 data points (6 hosts × 4 metrics × 8 days × 1-min resolution)

**What it demos:**
- `date_histogram` with `fixed_interval` for time-series bucketing
- `avg`, `max`, `min` sub-aggregations for statistical rollups
- Multi-host filtering with `term` filter
- Summary cards using `extended_stats` over 24h windows

**Example ES query:**
```json
POST /metrics/_search
{
  "size": 0,
  "query": {
    "bool": {
      "filter": [
        { "term": { "metric.keyword": "cpu" } },
        { "range": { "@timestamp": { "gte": "now-6h" } } }
      ]
    }
  },
  "aggs": {
    "over_time": {
      "date_histogram": { "field": "@timestamp", "fixed_interval": "5m" },
      "aggs": {
        "avg_value": { "avg": { "field": "value" } },
        "max_value": { "max": { "field": "value" } }
      }
    }
  }
}
```

**Why ES excels:** Storing time-series data in ES with date histogram aggregations
gives you millisecond-response OLAP-style rollups without a dedicated TSDB.

**Docs:** https://www.elastic.co/guide/en/elasticsearch/reference/current/search-aggregations-bucket-datehistogram-aggregation.html

---

### 4. Geospatial Search

**Index:** `locations` | **Documents:** ~300 stores, restaurants, hotels, parks worldwide

**What it demos:**
- `geo_point` mapping type
- `geo_distance` filter for radius-based search
- `geo_bounding_box` query for map viewport queries
- `_geo_distance` sort for nearest-first ordering
- `script_fields` for computing distance in km
- `geohash_grid` aggregation for map cluster heatmaps

**Example ES query:**
```json
POST /locations/_search
{
  "query": {
    "bool": {
      "filter": [{
        "geo_distance": {
          "distance": "50km",
          "location": { "lat": 40.7128, "lon": -74.006 }
        }
      }]
    }
  },
  "sort": [{
    "_geo_distance": {
      "location": { "lat": 40.7128, "lon": -74.006 },
      "order": "asc", "unit": "km"
    }
  }]
}
```

**Frontend:** Interactive Leaflet.js map with OpenStreetMap tiles renders the
search radius and result markers.

**Docs:** https://www.elastic.co/guide/en/elasticsearch/reference/current/geo-queries.html

---

### 5. Anomaly Detection – Transaction Analysis

**Index:** `transactions` | **Documents:** ~5,500 (50 users × ~110 transactions)

**What it demos:**
- `extended_stats` aggregation (mean, std deviation, variance)
- Statistical Z-score anomaly flagging server-side using aggregation results
- Deliberate data seeding of anomalies (5–10× normal spend) for visible results
- `date_histogram` for daily transaction volume sparkline

**Detection algorithm:**
```
z = (transaction_amount - global_mean) / global_std_deviation
anomaly = |z| > threshold (default 2.5)
```

**Example ES query (get statistics):**
```json
POST /transactions/_search
{
  "size": 0,
  "aggs": {
    "amount_stats": {
      "extended_stats": { "field": "amount" }
    }
  }
}
```

**Note:** For production ML anomaly detection, use the
[Elasticsearch ML jobs API](https://www.elastic.co/guide/en/machine-learning/current/ml-jobs.html)
(requires the ML node role and an appropriate license).

---

### 6. Personalization & Recommendations (Bonus)

**Indices:** `interactions` + `products` | **Documents:** ~2,000 interactions

**What it demos:**
- Collaborative filtering using pure ES aggregations (no ML needed)
- `terms` aggregation cascade: user → products → similar users → unseen products
- Fallback to globally popular products when insufficient interaction history
- Cluster-aware data seeding to make recommendations meaningful

**Algorithm:**
```
1. Find all products user X has interacted with
2. Find other users who also interacted with those products
3. Find products those users liked but user X hasn't seen
4. Return as recommendations
```

**Docs:** https://www.elastic.co/guide/en/elasticsearch/reference/current/search-aggregations-bucket-terms-aggregation.html

---

## API Reference

Full Swagger UI available at `http://localhost:8000/docs`

| Method | Endpoint                    | Description                             |
|--------|-----------------------------|-----------------------------------------|
| GET    | `/health`                   | ES cluster health check                 |
| POST   | `/search/fulltext`          | Multi-match search with highlighting    |
| POST   | `/search/autocomplete`      | Completion suggester                    |
| GET    | `/search/categories`        | Product category aggregation            |
| DELETE | `/search/clear`             | Reset products index                    |
| POST   | `/logs/search`              | Filter log entries                      |
| GET    | `/logs/level-aggregation`   | Log level pie chart data                |
| GET    | `/logs/top-errors`          | Top error hosts                         |
| GET    | `/logs/timeline`            | Log timeline histogram                  |
| POST   | `/analytics/timeseries`     | Metric time-series data                 |
| GET    | `/analytics/hosts`          | List monitored hosts                    |
| GET    | `/analytics/summary`        | 24h metric summary                      |
| POST   | `/geo/nearby`               | Geo-distance search                     |
| POST   | `/geo/bounding-box`         | Bounding box search                     |
| GET    | `/geo/cluster`              | Geohash grid aggregation                |
| POST   | `/ml/detect`                | Z-score anomaly detection               |
| GET    | `/ml/transaction-summary`   | Daily transaction rollup                |
| POST   | `/recs/for-user`            | Collaborative filtering recommendations |
| GET    | `/recs/popular`             | Popular products                        |

---

## Development

### Run backend tests

```bash
# From project root
pip install -r backend/requirements.txt
pytest backend/tests/test_endpoints.py -v
```

### Reseed data

```bash
docker-compose run --rm seed
```

### Re-seed a single use case

```bash
docker-compose run --rm -v $(pwd)/scripts:/app/scripts seed \
  python /app/scripts/seed_products.py
```

### View live logs

```bash
docker-compose logs -f backend
docker-compose logs -f seed
docker-compose logs -f logstash
```

### Hot-reload backend

The `backend` service mounts `./backend` as a volume and runs Uvicorn with
`--reload`. Edit any Python file and changes apply immediately.

---

## Project Structure

```
elk-test/
├── docker-compose.yml          # Full stack orchestration
├── .env                        # Environment variables
├── README.md
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                 # FastAPI app + CORS + health endpoint
│   ├── config.py               # Pydantic settings (env vars)
│   ├── routers/
│   │   ├── search.py           # Use case 1: Full-text search
│   │   ├── logs.py             # Use case 2: Log analysis
│   │   ├── analytics.py        # Use case 3: Real-time analytics
│   │   ├── geospatial.py       # Use case 4: Geospatial search
│   │   ├── ml_anomaly.py       # Use case 5: Anomaly detection
│   │   └── recommendations.py  # Use case 6: Recommendations
│   └── tests/
│       └── test_endpoints.py   # Pytest smoke tests (mocked ES)
│
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── public/index.html
│   └── src/
│       ├── App.js              # Main layout, tab navigation, health chip
│       ├── index.js
│       └── components/
│           ├── FullTextSearch.js
│           ├── LogAnalysis.js
│           ├── RealTimeAnalytics.js
│           ├── GeospatialSearch.js
│           ├── AnomalyDetection.js
│           └── Recommendations.js
│
├── scripts/
│   ├── seed_data.py            # Master seeder (runs all below)
│   ├── seed_products.py        # 150+ e-commerce products
│   ├── seed_logs.py            # 2000 application logs
│   ├── seed_metrics.py         # ~270k metric data points
│   ├── seed_locations.py       # ~300 geo locations worldwide
│   ├── seed_transactions.py    # ~5500 transactions (with anomalies)
│   └── seed_interactions.py    # ~2000 user-product interactions
│
└── logstash/
    ├── config/logstash.yml
    ├── pipeline/logstash.conf  # Nginx log parser → ES
    └── logs/
        ├── generate_logs.py    # Sample log generator
        └── nginx-access.log    # Pre-generated sample logs
```

---

## Scaling to Production

This demo runs a single-node Elasticsearch cluster suitable for development and
demos. For production deployments, consider:

### Multi-Node Cluster
```yaml
# docker-compose.yml additions
es-node-2:
  image: docker.elastic.co/elasticsearch/elasticsearch:8.12.0
  environment:
    - cluster.initial_master_nodes=es-node-1,es-node-2,es-node-3
    - discovery.seed_hosts=es-node-1,es-node-2,es-node-3
    - node.roles=[data,ingest]
```

### Index Lifecycle Management (ILM)
Configure ILM policies to automatically roll over, shrink, and delete old
log indices:
```bash
PUT _ilm/policy/logs-policy
{
  "policy": {
    "phases": {
      "hot": { "actions": { "rollover": { "max_size": "50gb" } } },
      "warm": { "min_age": "7d", "actions": { "shrink": { "number_of_shards": 1 } } },
      "delete": { "min_age": "30d", "actions": { "delete": {} } }
    }
  }
}
```

### Security Hardening
- Enable TLS (`xpack.security.http.ssl.enabled=true`)
- Create dedicated API keys per service (not `elastic` superuser)
- Use Kibana Spaces for multi-tenancy
- Enable audit logging (`xpack.security.audit.enabled=true`)

### Kubernetes
Use the [Elastic Cloud on Kubernetes (ECK)](https://www.elastic.co/guide/en/cloud-on-k8s/current/k8s-quickstart.html)
operator for production Kubernetes deployments with automated lifecycle management.

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| ES container exits immediately | Insufficient `vm.max_map_count` | `sudo sysctl -w vm.max_map_count=262144` |
| Frontend shows "ES: error" | ES not yet healthy | Wait 60-90s; `docker-compose ps` to check |
| Seed fails with ConnectionError | ES not ready | Re-run: `docker-compose run --rm seed` |
| Empty search results | Seed didn't run | `docker-compose logs seed` to diagnose |
| Port 9200 already in use | Local ES running | `sudo systemctl stop elasticsearch` |
| Maps not loading | No internet access | OSM tiles require internet; swap for offline tiles |

---

## License

MIT. Feel free to use this project as a starting point for demos, workshops,
and production POCs.
