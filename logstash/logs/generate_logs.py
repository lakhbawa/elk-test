#!/usr/bin/env python3
"""
Generate sample Nginx access logs for Logstash to ingest.
Run locally: python generate_logs.py > nginx-access.log
"""

import random
from datetime import datetime, timedelta

PATHS = [
    "/api/users", "/api/products", "/api/orders", "/api/auth/login",
    "/api/search?q=laptop", "/api/checkout", "/api/recommendations",
    "/health", "/static/app.js", "/static/styles.css",
    "/api/products/123", "/api/orders/456", "/favicon.ico",
]

METHODS = ["GET", "GET", "GET", "POST", "PUT", "DELETE"]
STATUS_CODES = [200, 200, 200, 200, 201, 204, 301, 400, 401, 403, 404, 500, 503]
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
    "Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36 Chrome/120.0",
    "python-requests/2.31.0",
    "curl/7.81.0",
]

IPS = [f"192.168.1.{i}" for i in range(1, 50)] + \
      [f"10.0.0.{i}" for i in range(1, 20)] + \
      ["203.0.113.1", "198.51.100.1", "8.8.8.8", "1.1.1.1"]


def generate_log_line(ts: datetime) -> str:
    ip = random.choice(IPS)
    method = random.choice(METHODS)
    path = random.choice(PATHS)
    status = random.choice(STATUS_CODES)
    size = random.randint(100, 50000)
    ua = random.choice(USER_AGENTS)
    ts_str = ts.strftime("%d/%b/%Y:%H:%M:%S +0000")
    return f'{ip} - - [{ts_str}] "{method} {path} HTTP/1.1" {status} {size} "-" "{ua}"'


if __name__ == "__main__":
    now = datetime.utcnow()
    for i in range(500):
        ts = now - timedelta(
            days=random.randint(0, 7),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59),
        )
        print(generate_log_line(ts))
