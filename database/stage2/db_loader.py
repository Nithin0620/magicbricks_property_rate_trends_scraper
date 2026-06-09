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
                sub_property_type VARCHAR(255) NOT NULL,
                locality VARCHAR(255) NOT NULL,
                sale_price_range VARCHAR(100),
                sale_average_price VARCHAR(100),
                sale_q_o_q VARCHAR(50),
                view_trends_link TEXT,
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
                    (city_name, property_type, sub_property_type, locality,
                     sale_price_range, sale_average_price, sale_q_o_q, view_trends_link)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    r["city_name"],
                    r["property_type"],
                    r["sub_property_type"],
                    r["locality"],
                    r["sale_price_range"],
                    r["sale_average_price"],
                    r["sale_q_o_q"],
                    r["view_trends_link"],
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
