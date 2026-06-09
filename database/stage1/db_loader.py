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
                city_name VARCHAR(255) NOT NULL,
                property_type VARCHAR(50) NOT NULL,
                city_url TEXT NOT NULL,
                scraped_at TIMESTAMP DEFAULT NOW()
            )
        """)
    conn.commit()
    print(f"[DB] Table '{table_name}' ready.")


def insert_cities(conn, table_name, cities):
    with conn.cursor() as cur:
        for city in cities:
            cur.execute(
                f"""
                INSERT INTO {table_name} (city_name, property_type, city_url)
                VALUES (%s, %s, %s)
                """,
                (city["city_name"], city["property_type"], city["city_url"]),
            )
    conn.commit()
    print(f"[DB] Inserted {len(cities)} rows into '{table_name}'.")


def load_to_db(cities):
    table_name = get_table_name()
    print(f"[DB] Connecting to PostgreSQL at {DB_CONFIG['host']}:{DB_CONFIG['port']}...")
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        create_table(conn, table_name)
        insert_cities(conn, table_name, cities)
        print(f"[DB] Successfully loaded data into table '{table_name}'.")
    finally:
        conn.close()
    return table_name
