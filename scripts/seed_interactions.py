"""
Seed Use Case 6 – User Interactions (Recommendations)
Creates index 'interactions' with simulated user-product interaction history.
"""

import random
from datetime import datetime, timedelta
from faker import Faker
from elasticsearch import helpers

fake = Faker()

INDEX = "interactions"
EVENT_TYPES = ["view", "view", "view", "like", "purchase", "add_to_cart"]
NUM_USERS = 40
NUM_PRODUCTS = 150  # Must match products index


def seed_interactions(es):
    if es.indices.exists(index=INDEX):
        es.indices.delete(index=INDEX)

    es.indices.create(
        index=INDEX,
        body={
            "settings": {"number_of_shards": 1, "number_of_replicas": 0},
            "mappings": {
                "properties": {
                    "user_id": {"type": "keyword"},
                    "product_id": {"type": "keyword"},
                    "event_type": {"type": "keyword"},
                    "timestamp": {"type": "date"},
                    "session_id": {"type": "keyword"},
                    "duration_seconds": {"type": "integer"},
                }
            },
        },
    )

    now = datetime.utcnow()
    docs = []
    doc_id = 1

    # Create user clusters (users in same cluster prefer same categories of products)
    # Cluster A: products 1-50, Cluster B: products 51-100, Cluster C: 101-150
    user_clusters = {
        f"user-{i:03d}": random.randint(0, 2) for i in range(1, NUM_USERS + 1)
    }
    cluster_products = {
        0: list(range(1, 51)),
        1: list(range(51, 101)),
        2: list(range(101, 151)),
    }

    for user_id, cluster in user_clusters.items():
        primary_products = cluster_products[cluster]
        # Occasional cross-cluster interactions for diversity
        all_products = list(range(1, NUM_PRODUCTS + 1))

        # 20-60 interactions per user
        num_interactions = random.randint(20, 60)
        viewed_products = set()

        for _ in range(num_interactions):
            # 80% chance of interacting with cluster products
            if random.random() < 0.8:
                product_id = f"{random.choice(primary_products)}"
            else:
                product_id = f"{random.choice(all_products)}"

            viewed_products.add(product_id)

            event = random.choice(EVENT_TYPES)
            ts = now - timedelta(
                days=random.randint(0, 60),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59),
            )

            docs.append({
                "_index": INDEX,
                "_id": str(doc_id),
                "_source": {
                    "user_id": user_id,
                    "product_id": product_id,
                    "event_type": event,
                    "timestamp": ts.isoformat() + "Z",
                    "session_id": fake.uuid4(),
                    "duration_seconds": random.randint(5, 600) if event == "view" else 0,
                },
            })
            doc_id += 1

    helpers.bulk(es, docs)
    es.indices.refresh(index=INDEX)
    print(f"  Seeded {len(docs)} interactions into '{INDEX}'")
