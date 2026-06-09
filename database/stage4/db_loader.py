import psycopg2
from datetime import datetime
from database.stage1.db_config import DB_CONFIG


def get_table_name():
    now = datetime.now()
    return now.strftime("magic_brick_property_price_trends_%H_%M_%S_%d_%m_%y")


def create_table(conn, table_name):
    with conn.cursor() as cur:
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id SERIAL PRIMARY KEY,
                city_name VARCHAR(255),
                locality_name VARCHAR(255),
                reviews_url TEXT,
                environment_rating VARCHAR(20),
                environment_sub_categories TEXT,
                commuting_rating VARCHAR(20),
                commuting_sub_categories TEXT,
                places_of_interest_rating VARCHAR(20),
                places_of_interest_sub_categories TEXT,
                overall_rating_distribution TEXT,
                total_reviews VARCHAR(20),
                reviews_data TEXT,
                scraped_at TIMESTAMP DEFAULT NOW()
            )
        """)
    conn.commit()
    print(f"[DB] Table '{table_name}' ready.")


def insert_records(conn, table_name, records):
    with conn.cursor() as cur:
        for r in records:
            cur.execute(
                f"""
                INSERT INTO {table_name}
                    (city_name, locality_name, reviews_url,
                     environment_rating, environment_sub_categories,
                     commuting_rating, commuting_sub_categories,
                     places_of_interest_rating, places_of_interest_sub_categories,
                     overall_rating_distribution,
                     total_reviews, reviews_data)
                VALUES (%s, %s, %s,
                        %s, %s,
                        %s, %s,
                        %s, %s,
                        %s,
                        %s, %s)
                """,
                (
                    r.get("city_name", ""), r.get("locality_name", ""), r.get("reviews_url", ""),
                    r.get("environment_rating", ""), r.get("environment_sub_categories", ""),
                    r.get("commuting_rating", ""), r.get("commuting_sub_categories", ""),
                    r.get("places_of_interest_rating", ""), r.get("places_of_interest_sub_categories", ""),
                    r.get("overall_rating_distribution", ""),
                    r.get("total_reviews", ""), r.get("reviews_data", ""),
                ),
            )
    conn.commit()
    print(f"[DB] Inserted {len(records)} rows into '{table_name}'.")


def load_to_db(records):
    if not records:
        print("[DB] No records to insert.")
        return None
    table_name = get_table_name()
    print(f"[DB] Connecting to PostgreSQL at {DB_CONFIG['host']}:{DB_CONFIG['port']}...")
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        create_table(conn, table_name)
        insert_records(conn, table_name, records)
        print(f"[DB] Successfully loaded {len(records)} rows into '{table_name}'.")
    finally:
        conn.close()
    return table_name
