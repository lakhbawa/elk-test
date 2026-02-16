"""
Seed Use Case 2 – Application Logs (Log Analysis)
Creates index 'app-logs-YYYY.MM.dd' with simulated Nginx/app log entries.
"""

import random
from datetime import datetime, timedelta
from faker import Faker
from elasticsearch import helpers

fake = Faker()

LOG_LEVELS = ["DEBUG", "INFO", "INFO", "INFO", "WARN", "ERROR", "ERROR"]
HOSTS = [f"web-{i:02d}" for i in range(1, 8)] + [f"app-{i:02d}" for i in range(1, 5)]
LOG_SOURCES = ["nginx", "django", "flask", "nodejs", "java-app"]

HTTP_METHODS = ["GET", "POST", "PUT", "DELETE", "PATCH"]
PATHS = [
    "/api/users", "/api/products", "/api/orders", "/api/auth/login",
    "/api/search", "/api/checkout", "/api/recommendations", "/health",
    "/static/app.js", "/static/styles.css",
]

ERROR_MESSAGES = [
    "Connection refused to database host",
    "Timeout waiting for upstream service",
    "NullPointerException in ProductService",
    "Authentication token expired",
    "Rate limit exceeded for IP",
    "Disk space below 10% threshold",
    "Failed to parse JSON request body",
    "SSL certificate validation failed",
    "Max connection pool size reached",
    "Cache miss on critical path",
]

WARN_MESSAGES = [
    "Slow query detected: {duration}ms",
    "Memory usage at {pct}%",
    "Retry attempt {n} for external API",
    "Deprecated endpoint called: {path}",
    "Large request payload: {size}MB",
]

INFO_MESSAGES = [
    "Request processed in {duration}ms",
    "User {uid} logged in successfully",
    "Cache hit for key: {key}",
    "Scheduled job completed: {job}",
    "New order placed: order-{oid}",
    "Product search returned {n} results",
    "Background task queued: {task}",
]

DEBUG_MESSAGES = [
    "SQL query: SELECT * FROM users WHERE id={id}",
    "Cache set for key: {key} TTL={ttl}s",
    "HTTP {method} {path} -> {status}",
    "Request headers: {headers}",
]

INDEX_PREFIX = "app-logs"


def _random_message(level: str) -> str:
    if level == "ERROR":
        return random.choice(ERROR_MESSAGES)
    elif level == "WARN" or level == "WARNING":
        tmpl = random.choice(WARN_MESSAGES)
        return tmpl.format(
            duration=random.randint(5000, 30000),
            pct=random.randint(85, 99),
            n=random.randint(1, 5),
            path=random.choice(PATHS),
            size=round(random.uniform(10, 50), 1),
        )
    elif level == "DEBUG":
        tmpl = random.choice(DEBUG_MESSAGES)
        return tmpl.format(
            id=random.randint(1000, 9999),
            key=f"prod:{random.randint(1, 500)}",
            ttl=random.randint(60, 3600),
            method=random.choice(HTTP_METHODS),
            path=random.choice(PATHS),
            status=random.choice([200, 200, 200, 301, 404, 500]),
            headers="Accept: application/json",
        )
    else:
        tmpl = random.choice(INFO_MESSAGES)
        return tmpl.format(
            duration=random.randint(5, 800),
            uid=f"user-{random.randint(1000, 9999)}",
            key=f"session:{random.randint(100, 999)}",
            job=random.choice(["cleanup", "report", "backup"]),
            oid=random.randint(10000, 99999),
            n=random.randint(0, 200),
            task=random.choice(["email-send", "pdf-gen", "resize-img"]),
        )


def seed_logs(es):
    now = datetime.utcnow()
    docs = []

    for i in range(2000):
        ts = now - timedelta(
            days=random.randint(0, 13),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59),
        )
        level = random.choice(LOG_LEVELS)
        host = random.choice(HOSTS)
        source = random.choice(LOG_SOURCES)
        index_name = f"{INDEX_PREFIX}-{ts.strftime('%Y.%m.%d')}"

        doc = {
            "@timestamp": ts.isoformat() + "Z",
            "level": level,
            "host": host,
            "source": source,
            "message": _random_message(level),
            "http_method": random.choice(HTTP_METHODS),
            "path": random.choice(PATHS),
            "status_code": random.choice([200, 200, 200, 201, 204, 301, 400, 401, 403, 404, 500, 503]),
            "response_time_ms": random.randint(1, 15000),
            "client_ip": fake.ipv4_public(),
            "user_agent": fake.user_agent(),
            "request_id": fake.uuid4(),
        }

        # Delete + create index per day (idempotent)
        docs.append({
            "_index": index_name,
            "_source": doc,
        })

    # Create index template so all app-logs-* indices have correct mapping
    es.indices.put_index_template(
        name="app-logs-template",
        body={
            "index_patterns": ["app-logs-*"],
            "template": {
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                },
                "mappings": {
                    "properties": {
                        "@timestamp": {"type": "date"},
                        "level": {"type": "keyword"},
                        "host": {"type": "keyword"},
                        "source": {"type": "keyword"},
                        "message": {
                            "type": "text",
                            "fields": {"keyword": {"type": "keyword", "ignore_above": 512}},
                        },
                        "http_method": {"type": "keyword"},
                        "path": {"type": "keyword"},
                        "status_code": {"type": "integer"},
                        "response_time_ms": {"type": "long"},
                        "client_ip": {"type": "ip"},
                        "user_agent": {"type": "text"},
                        "request_id": {"type": "keyword"},
                    }
                },
            },
        },
    )

    helpers.bulk(es, docs)
    es.indices.refresh(index="app-logs-*")
    print(f"  Seeded {len(docs)} log entries into '{INDEX_PREFIX}-*' indices")
