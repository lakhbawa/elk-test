"""
Seed Use Case 1 – Product Catalog (Full-Text Search)
Creates index 'products' with 150 realistic e-commerce products.
"""

import random
from faker import Faker
from elasticsearch import helpers

fake = Faker()

CATEGORIES = [
    "Electronics", "Clothing", "Home & Kitchen", "Sports & Outdoors",
    "Books", "Beauty", "Toys & Games", "Food & Grocery",
]

ELECTRONICS = [
    ("Wireless Bluetooth Headphones", 49, 299, "Noise-cancelling over-ear headphones with 30-hour battery life"),
    ("4K Smart TV", 399, 1299, "Ultra-HD LED television with built-in streaming apps"),
    ("Laptop Pro 15", 799, 2499, "High-performance laptop with Intel Core i7 and 16GB RAM"),
    ("Smartphone X", 699, 1199, "Flagship smartphone with triple camera system"),
    ("Mechanical Keyboard", 59, 249, "RGB backlit mechanical gaming keyboard"),
    ("USB-C Hub", 29, 89, "7-in-1 multiport adapter for USB-C laptops"),
    ("Portable SSD", 49, 199, "Fast external solid-state drive up to 2TB"),
    ("Wireless Earbuds", 39, 179, "True wireless earbuds with active noise cancellation"),
]

CLOTHING = [
    ("Running Shoes", 59, 199, "Lightweight trail running shoes with breathable mesh"),
    ("Merino Wool Sweater", 49, 149, "Premium merino wool pullover for all seasons"),
    ("Yoga Pants", 29, 99, "High-waist compression leggings for yoga and gym"),
    ("Waterproof Hiking Jacket", 89, 299, "3-layer Gore-Tex rain jacket for outdoor adventures"),
    ("Organic Cotton T-Shirt", 14, 49, "Sustainably sourced 100% organic cotton tee"),
]

HOME = [
    ("Coffee Maker Pro", 49, 299, "Programmable drip coffee maker with thermal carafe"),
    ("Air Purifier HEPA", 79, 399, "True HEPA filter air purifier for 500 sq ft rooms"),
    ("Cast Iron Skillet", 29, 89, "Pre-seasoned 12-inch cast iron frying pan"),
    ("Robot Vacuum", 199, 799, "Self-emptying robotic vacuum with smart mapping"),
    ("Bamboo Cutting Board", 19, 59, "Eco-friendly bamboo kitchen cutting board set"),
    ("Instant Pot", 69, 199, "7-in-1 electric pressure cooker and slow cooker"),
]

SPORTS = [
    ("Adjustable Dumbbells", 149, 599, "Space-saving adjustable weight dumbbell set"),
    ("Yoga Mat Premium", 29, 99, "Non-slip eco-friendly yoga and exercise mat"),
    ("Mountain Bike", 399, 1999, "21-speed hardtail mountain bike with disc brakes"),
    ("Tennis Racket Pro", 49, 249, "Graphite composite tennis racket for advanced players"),
    ("Swimming Goggles", 14, 59, "Anti-fog UV-protection swimming goggles"),
]

BOOKS = [
    ("Clean Code", 29, 49, "A handbook of agile software craftsmanship by Robert C. Martin"),
    ("Designing Data-Intensive Applications", 39, 59, "Guide to building reliable and scalable systems"),
    ("The Pragmatic Programmer", 29, 49, "From journeyman to master software development"),
    ("Deep Learning", 49, 79, "Comprehensive textbook on deep learning by Goodfellow"),
]

BEAUTY = [
    ("Vitamin C Serum", 19, 79, "Brightening antioxidant face serum with 20% vitamin C"),
    ("Electric Face Brush", 29, 129, "Silicone sonic face cleansing brush"),
    ("Retinol Night Cream", 24, 89, "Anti-aging night cream with 0.5% retinol"),
    ("Sunscreen SPF 50", 14, 49, "Lightweight daily mineral sunscreen"),
]

PRODUCTS_BY_CAT = {
    "Electronics": ELECTRONICS,
    "Clothing": CLOTHING,
    "Home & Kitchen": HOME,
    "Sports & Outdoors": SPORTS,
    "Books": BOOKS,
    "Beauty": BEAUTY,
    "Toys & Games": [
        ("LEGO Creator Set", 29, 149, "Creative building set with 500+ pieces"),
        ("Board Game Classic", 19, 69, "Strategy board game for 2-6 players"),
        ("Remote Control Car", 29, 99, "High-speed off-road RC truck"),
    ],
    "Food & Grocery": [
        ("Organic Coffee Beans", 14, 49, "Single-origin Colombian organic arabica coffee"),
        ("Whey Protein Powder", 39, 99, "25g protein per serving, chocolate flavor"),
        ("Matcha Green Tea", 19, 59, "Ceremonial grade Japanese matcha powder"),
        ("Himalayan Pink Salt", 9, 29, "Pure Himalayan crystal salt, fine grain"),
    ],
}

BRANDS = {
    "Electronics": ["Sony", "Samsung", "Apple", "Bose", "Logitech", "Anker", "LG"],
    "Clothing": ["Nike", "Adidas", "Patagonia", "Under Armour", "Levi's"],
    "Home & Kitchen": ["Cuisinart", "Vitamix", "Dyson", "iRobot", "KitchenAid"],
    "Sports & Outdoors": ["Garmin", "Coleman", "REI", "Specialized", "Wilson"],
    "Books": ["O'Reilly", "Manning", "MIT Press", "Apress"],
    "Beauty": ["CeraVe", "The Ordinary", "Neutrogena", "L'Oréal", "Drunk Elephant"],
    "Toys & Games": ["LEGO", "Hasbro", "Mattel", "Spin Master"],
    "Food & Grocery": ["Bob's Red Mill", "Thrive Market", "Larabar", "Orgain"],
}

INDEX = "products"


def seed_products(es):
    # Delete + recreate index
    if es.indices.exists(index=INDEX):
        es.indices.delete(index=INDEX)

    es.indices.create(
        index=INDEX,
        body={
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "analysis": {
                    "analyzer": {
                        "product_analyzer": {
                            "type": "standard",
                            "stopwords": "_english_",
                        }
                    }
                },
            },
            "mappings": {
                "properties": {
                    "title": {
                        "type": "text",
                        "analyzer": "product_analyzer",
                        "fields": {
                            "keyword": {"type": "keyword"},
                            "suggest": {"type": "completion"},
                        },
                    },
                    "description": {"type": "text", "analyzer": "product_analyzer"},
                    "category": {"type": "keyword"},
                    "brand": {"type": "keyword"},
                    "price": {"type": "float"},
                    "rating": {"type": "float"},
                    "review_count": {"type": "integer"},
                    "in_stock": {"type": "boolean"},
                    "tags": {"type": "keyword"},
                    "created_at": {"type": "date"},
                }
            },
        },
    )

    docs = []
    doc_id = 1

    for category, product_list in PRODUCTS_BY_CAT.items():
        brands = BRANDS.get(category, ["Generic"])
        for base_name, min_price, max_price, base_desc in product_list:
            # Generate 3-5 variants per base product
            for _ in range(random.randint(3, 5)):
                adjectives = random.choice([
                    "", "Premium ", "Pro ", "Ultra ", "Smart ", "Eco-Friendly ",
                    "Compact ", "Deluxe ", "Lightweight ", "Advanced ",
                ])
                title = f"{adjectives}{base_name}"
                price = round(random.uniform(min_price, max_price), 2)
                extra_detail = fake.sentence(nb_words=random.randint(6, 12))

                docs.append({
                    "_index": INDEX,
                    "_id": str(doc_id),
                    "_source": {
                        "title": title,
                        "description": f"{base_desc}. {extra_detail}",
                        "category": category,
                        "brand": random.choice(brands),
                        "price": price,
                        "rating": round(random.uniform(3.0, 5.0), 1),
                        "review_count": random.randint(5, 5000),
                        "in_stock": random.random() > 0.1,
                        "tags": random.sample(
                            ["sale", "new", "bestseller", "limited", "eco", "premium"],
                            k=random.randint(0, 3),
                        ),
                        "created_at": fake.date_time_this_year().isoformat(),
                    },
                })
                doc_id += 1

    # Ensure at least 150 docs
    while len(docs) < 150:
        cat = random.choice(CATEGORIES)
        docs.append({
            "_index": INDEX,
            "_id": str(doc_id),
            "_source": {
                "title": fake.catch_phrase(),
                "description": fake.paragraph(nb_sentences=3),
                "category": cat,
                "brand": fake.company(),
                "price": round(random.uniform(9.99, 999.99), 2),
                "rating": round(random.uniform(1.0, 5.0), 1),
                "review_count": random.randint(0, 1000),
                "in_stock": True,
                "tags": [],
                "created_at": fake.date_time_this_year().isoformat(),
            },
        })
        doc_id += 1

    helpers.bulk(es, docs)
    es.indices.refresh(index=INDEX)
    print(f"  Seeded {len(docs)} products into '{INDEX}'")
