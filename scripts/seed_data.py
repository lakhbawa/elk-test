#!/usr/bin/env python3
"""
Master seed script – runs all individual seeders.
Executed automatically on `docker-compose up` via the 'seed' service.
"""

import os
import sys
import time
import logging

from elasticsearch import Elasticsearch, helpers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("seed")

# ─── Elasticsearch connection ─────────────────────────────────────────────────
ES_HOST = os.getenv("ELASTICSEARCH_HOST", "localhost")
ES_PORT = int(os.getenv("ELASTICSEARCH_PORT", "9200"))
ES_USER = os.getenv("ELASTICSEARCH_USERNAME", "elastic")
ES_PASS = os.getenv("ELASTICSEARCH_PASSWORD", "changeme")
ES_SCHEME = os.getenv("ELASTICSEARCH_SCHEME", "http")


def get_es() -> Elasticsearch:
    return Elasticsearch(
        hosts=[{"host": ES_HOST, "port": ES_PORT, "scheme": ES_SCHEME}],
        basic_auth=(ES_USER, ES_PASS),
        verify_certs=False,
        request_timeout=30,
    )


def wait_for_es(es: Elasticsearch, retries: int = 30, delay: int = 5):
    """Wait until ES is accepting requests."""
    for attempt in range(1, retries + 1):
        try:
            health = es.cluster.health(wait_for_status="yellow", timeout="5s")
            log.info("Elasticsearch is ready (status: %s)", health["status"])
            return
        except Exception as exc:
            log.warning("ES not ready (attempt %d/%d): %s", attempt, retries, exc)
            time.sleep(delay)
    log.error("Elasticsearch did not become ready in time. Exiting.")
    sys.exit(1)


# ─── Import seeders ───────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))

from seed_products import seed_products
from seed_logs import seed_logs
from seed_metrics import seed_metrics
from seed_locations import seed_locations
from seed_transactions import seed_transactions
from seed_interactions import seed_interactions


def main():
    es = get_es()
    wait_for_es(es)

    log.info("=" * 60)
    log.info("Starting Elasticsearch Demo Hub data seeding")
    log.info("=" * 60)

    steps = [
        ("Products (Full-Text Search)", seed_products),
        ("Logs (Log Analysis)", seed_logs),
        ("Metrics (Real-Time Analytics)", seed_metrics),
        ("Locations (Geospatial)", seed_locations),
        ("Transactions (Anomaly Detection)", seed_transactions),
        ("Interactions (Recommendations)", seed_interactions),
    ]

    for name, fn in steps:
        try:
            log.info("Seeding: %s", name)
            fn(es)
            log.info("Done: %s", name)
        except Exception as exc:
            log.error("Failed to seed %s: %s", name, exc)

    log.info("=" * 60)
    log.info("Seeding complete!")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
