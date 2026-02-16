"""
Seed Use Case 5 – Transaction Data (Anomaly Detection)
Creates index 'transactions' with realistic payment data including deliberate anomalies.
"""

import random
from datetime import datetime, timedelta
from faker import Faker
from elasticsearch import helpers

fake = Faker()

INDEX = "transactions"

CATEGORIES = [
    "Food & Dining", "Shopping", "Transportation", "Entertainment",
    "Healthcare", "Utilities", "Travel", "Groceries",
]

TX_STATUS = ["completed", "completed", "completed", "pending", "failed", "refunded"]

# User profiles with spending bands
USERS = [
    {"id": f"user-{i:03d}", "avg": random.uniform(30, 150), "std": random.uniform(10, 50)}
    for i in range(1, 51)
]


def _normal_amount(avg: float, std: float) -> float:
    """Box-Muller transform to generate normally distributed amounts."""
    import math
    u1 = random.random() or 1e-10
    u2 = random.random()
    z = math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)
    return max(0.01, round(avg + std * z, 2))


def seed_transactions(es):
    if es.indices.exists(index=INDEX):
        es.indices.delete(index=INDEX)

    es.indices.create(
        index=INDEX,
        body={
            "settings": {"number_of_shards": 1, "number_of_replicas": 0},
            "mappings": {
                "properties": {
                    "transaction_id": {"type": "keyword"},
                    "user_id": {"type": "keyword"},
                    "amount": {"type": "float"},
                    "category": {"type": "keyword"},
                    "merchant": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                    "status": {"type": "keyword"},
                    "timestamp": {"type": "date"},
                    "currency": {"type": "keyword"},
                    "country": {"type": "keyword"},
                    "is_anomaly_label": {"type": "boolean"},  # ground truth for demo
                }
            },
        },
    )

    now = datetime.utcnow()
    docs = []
    doc_id = 1

    for user in USERS:
        uid = user["id"]
        avg_spend = user["avg"]
        std_spend = user["std"]

        # 80-120 normal transactions per user
        for _ in range(random.randint(80, 120)):
            ts = now - timedelta(
                days=random.randint(0, 30),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59),
            )
            docs.append({
                "_index": INDEX,
                "_id": str(doc_id),
                "_source": {
                    "transaction_id": f"tx-{doc_id:06d}",
                    "user_id": uid,
                    "amount": _normal_amount(avg_spend, std_spend),
                    "category": random.choice(CATEGORIES),
                    "merchant": fake.company(),
                    "status": random.choice(TX_STATUS),
                    "timestamp": ts.isoformat() + "Z",
                    "currency": "USD",
                    "country": fake.country_code(),
                    "is_anomaly_label": False,
                },
            })
            doc_id += 1

        # 2-4 deliberate anomalies per user (extreme amounts)
        for _ in range(random.randint(2, 4)):
            ts = now - timedelta(
                days=random.randint(0, 30),
                hours=random.randint(0, 23),
            )
            # Anomaly is either 5-10x normal or near-zero
            if random.random() > 0.3:
                anomaly_amount = round(avg_spend * random.uniform(5, 10), 2)
            else:
                anomaly_amount = round(random.uniform(0.01, 1.0), 2)

            docs.append({
                "_index": INDEX,
                "_id": str(doc_id),
                "_source": {
                    "transaction_id": f"tx-{doc_id:06d}",
                    "user_id": uid,
                    "amount": anomaly_amount,
                    "category": random.choice(CATEGORIES),
                    "merchant": fake.company(),
                    "status": "completed",
                    "timestamp": ts.isoformat() + "Z",
                    "currency": "USD",
                    "country": fake.country_code(),
                    "is_anomaly_label": True,
                },
            })
            doc_id += 1

    # Shuffle to mix anomalies naturally
    random.shuffle(docs)

    chunk_size = 2000
    for i in range(0, len(docs), chunk_size):
        helpers.bulk(es, docs[i : i + chunk_size])

    es.indices.refresh(index=INDEX)
    print(f"  Seeded {len(docs)} transactions into '{INDEX}'")
