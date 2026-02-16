"""
Seed Use Case 4 – Location Data (Geospatial Search)
Creates index 'locations' with store/restaurant/hotel/park locations worldwide.
"""

import random
from faker import Faker
from elasticsearch import helpers

fake = Faker()

INDEX = "locations"

CATEGORIES = ["restaurant", "store", "hotel", "park", "cafe", "gym", "hospital", "museum"]

# Major world cities with approximate lat/lon bounding boxes
CITY_BOUNDS = [
    ("New York", "US", (40.49, -74.26), (40.92, -73.70)),
    ("London", "GB", (51.28, -0.51), (51.69, 0.33)),
    ("Tokyo", "JP", (35.52, 139.37), (35.82, 139.92)),
    ("Sydney", "AU", (-34.17, 150.52), (-33.57, 151.34)),
    ("Paris", "FR", (48.71, 2.23), (48.91, 2.47)),
    ("Berlin", "DE", (52.34, 13.17), (52.68, 13.76)),
    ("Dubai", "AE", (25.00, 55.07), (25.36, 55.57)),
    ("Singapore", "SG", (1.20, 103.60), (1.47, 104.01)),
    ("Toronto", "CA", (43.57, -79.64), (43.85, -79.11)),
    ("Mumbai", "IN", (18.88, 72.77), (19.27, 73.05)),
    ("São Paulo", "BR", (-23.68, -46.83), (-23.43, -46.36)),
    ("Cape Town", "ZA", (-34.18, 18.33), (-33.77, 18.74)),
]

RESTAURANT_NAMES = [
    "The Golden Spoon", "Sakura Garden", "La Piazza", "Spice Route",
    "The Blue Whale", "Ember & Oak", "Zen Kitchen", "Casa Mexicana",
    "The French Press", "Urban Bites",
]

STORE_NAMES = [
    "Market Square", "City Fresh", "TechStop", "The Book Nook",
    "Sports World", "Fashion Hub", "HomeSense", "Pet Paradise",
]

HOTEL_NAMES = [
    "Grand Palace Hotel", "The Riverside Inn", "Sky Tower Suites",
    "Garden View Resort", "Central Boutique Hotel", "Harbor Lights Hotel",
]


def _random_name(category: str) -> str:
    if category == "restaurant":
        return f"{random.choice(RESTAURANT_NAMES)} {fake.last_name()}"
    elif category == "store":
        return f"{random.choice(STORE_NAMES)}"
    elif category == "hotel":
        return random.choice(HOTEL_NAMES)
    elif category == "park":
        return f"{fake.last_name()} {random.choice(['Park', 'Gardens', 'Green', 'Reserve'])}"
    elif category == "cafe":
        return f"{fake.first_name()}'s {random.choice(['Coffee', 'Café', 'Brew Bar'])}"
    elif category == "gym":
        return f"{random.choice(['FitLife', 'IronClad', 'Peak', 'CoreFit'])} Gym"
    elif category == "hospital":
        return f"{fake.last_name()} {random.choice(['Medical Center', 'Hospital', 'Clinic'])}"
    else:  # museum
        return f"{fake.last_name()} Museum of {random.choice(['Art', 'History', 'Science', 'Natural History'])}"


def seed_locations(es):
    if es.indices.exists(index=INDEX):
        es.indices.delete(index=INDEX)

    es.indices.create(
        index=INDEX,
        body={
            "settings": {"number_of_shards": 1, "number_of_replicas": 0},
            "mappings": {
                "properties": {
                    "name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                    "category": {"type": "keyword"},
                    "location": {"type": "geo_point"},
                    "address": {"type": "text"},
                    "city": {"type": "keyword"},
                    "country": {"type": "keyword"},
                    "rating": {"type": "float"},
                    "review_count": {"type": "integer"},
                    "price_range": {"type": "keyword"},
                    "phone": {"type": "keyword"},
                    "open_now": {"type": "boolean"},
                }
            },
        },
    )

    docs = []
    doc_id = 1

    for city, country, (lat_min, lon_min), (lat_max, lon_max) in CITY_BOUNDS:
        # 15-25 locations per city
        for _ in range(random.randint(15, 25)):
            lat = round(random.uniform(lat_min, lat_max), 6)
            lon = round(random.uniform(lon_min, lon_max), 6)
            category = random.choice(CATEGORIES)

            docs.append({
                "_index": INDEX,
                "_id": str(doc_id),
                "_source": {
                    "name": _random_name(category),
                    "category": category,
                    "location": {"lat": lat, "lon": lon},
                    "address": fake.street_address(),
                    "city": city,
                    "country": country,
                    "rating": round(random.uniform(2.5, 5.0), 1),
                    "review_count": random.randint(10, 10000),
                    "price_range": random.choice(["$", "$$", "$$$", "$$$$"]),
                    "phone": fake.phone_number(),
                    "open_now": random.random() > 0.2,
                },
            })
            doc_id += 1

    helpers.bulk(es, docs)
    es.indices.refresh(index=INDEX)
    print(f"  Seeded {len(docs)} locations into '{INDEX}'")
