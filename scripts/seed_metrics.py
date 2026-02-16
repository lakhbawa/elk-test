"""
Seed Use Case 3 – System Metrics (Real-Time Analytics)
Creates index 'metrics' with simulated CPU/memory/disk/network readings.
"""

import random
import math
from datetime import datetime, timedelta
from elasticsearch import helpers

INDEX = "metrics"
HOSTS = [f"server-{i:02d}" for i in range(1, 7)]
METRICS = ["cpu", "memory", "disk", "network"]


def _simulate_value(metric: str, hour: int, noise: float = 0.0) -> float:
    """Generate a realistic metric value with daily seasonality."""
    base = {"cpu": 30, "memory": 55, "disk": 40, "network": 20}[metric]
    # Sinusoidal daily pattern peaking around 14:00
    seasonal = 20 * math.sin(math.pi * (hour - 6) / 12) if 6 <= hour <= 22 else 0
    # Random spikes
    spike = random.choice([0] * 9 + [random.uniform(20, 40)])
    value = base + seasonal + spike + noise + random.uniform(-5, 5)
    return max(0.0, min(100.0, round(value, 2)))


def seed_metrics(es):
    if es.indices.exists(index=INDEX):
        es.indices.delete(index=INDEX)

    es.indices.create(
        index=INDEX,
        body={
            "settings": {"number_of_shards": 1, "number_of_replicas": 0},
            "mappings": {
                "properties": {
                    "@timestamp": {"type": "date"},
                    "host": {"type": "keyword"},
                    "metric": {"type": "keyword"},
                    "value": {"type": "float"},
                    "unit": {"type": "keyword"},
                }
            },
        },
    )

    now = datetime.utcnow()
    docs = []

    for host_idx, host in enumerate(HOSTS):
        # Each host has a slightly different baseline noise
        host_noise = random.uniform(-10, 10)

        for days_back in range(8):  # 8 days of data
            for hour in range(0, 24):
                for minute in range(0, 60, 1):  # 1-minute resolution
                    ts = now - timedelta(
                        days=days_back,
                        hours=(23 - hour),
                        minutes=minute,
                        seconds=random.randint(0, 59),
                    )
                    for metric in METRICS:
                        val = _simulate_value(metric, ts.hour, noise=host_noise)
                        docs.append({
                            "_index": INDEX,
                            "_source": {
                                "@timestamp": ts.isoformat() + "Z",
                                "host": host,
                                "metric": metric,
                                "value": val,
                                "unit": "percent",
                            },
                        })

    # Bulk index in chunks
    chunk_size = 5000
    for i in range(0, len(docs), chunk_size):
        helpers.bulk(es, docs[i : i + chunk_size])

    es.indices.refresh(index=INDEX)
    print(f"  Seeded {len(docs)} metric data points into '{INDEX}'")
