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
                sub_property_type VARCHAR(255),
                locality_name VARCHAR(255),
                locality_id VARCHAR(50),
                view_trends_url TEXT,
                reviews_link TEXT,
                comp_highest_price VARCHAR(100),
                comp_highest_qoq VARCHAR(50),
                comp_highest_trend VARCHAR(10),
                comp_avg_price VARCHAR(100),
                comp_avg_qoq VARCHAR(50),
                comp_avg_trend VARCHAR(10),
                comp_lowest_price VARCHAR(100),
                comp_lowest_qoq VARCHAR(50),
                comp_lowest_trend VARCHAR(10),
                sale_avg_price VARCHAR(100),
                sale_price VARCHAR(100),
                sale_qoq VARCHAR(50),
                sale_trend_direction VARCHAR(10),
                rent_avg_price VARCHAR(100),
                rent_price VARCHAR(100),
                rent_qoq VARCHAR(50),
                rent_trend_direction VARCHAR(10),
                price_history TEXT,
                nearby_localities TEXT,
                locality_rating VARCHAR(50),
                locality_rating_users VARCHAR(50),
                locality_reviews VARCHAR(50),
                total_props VARCHAR(50),
                props_for_sale VARCHAR(50),
                props_for_rent VARCHAR(50),
                projects_count VARCHAR(50),
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
                    (city_name, sub_property_type, locality_name, locality_id, view_trends_url, reviews_link,
                     comp_highest_price, comp_highest_qoq, comp_highest_trend,
                     comp_avg_price, comp_avg_qoq, comp_avg_trend,
                     comp_lowest_price, comp_lowest_qoq, comp_lowest_trend,
                     sale_avg_price, sale_price, sale_qoq, sale_trend_direction,
                     rent_avg_price, rent_price, rent_qoq, rent_trend_direction,
                     price_history, nearby_localities,
                     locality_rating, locality_rating_users, locality_reviews,
                     total_props, props_for_sale, props_for_rent, projects_count)
                VALUES (%s, %s, %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s,
                        %s, %s, %s,
                        %s, %s, %s, %s)
                """,
                (
                    r.get("city_name", ""), r.get("sub_property_type", ""), r.get("locality_name", ""),
                    r.get("locality_id", ""), r.get("view_trends_url", ""), r.get("reviews_link", ""),
                    r.get("comp_highest_price", ""), r.get("comp_highest_qoq", ""),
                    r.get("comp_highest_trend", ""),
                    r.get("comp_avg_price", ""), r.get("comp_avg_qoq", ""),
                    r.get("comp_avg_trend", ""),
                    r.get("comp_lowest_price", ""), r.get("comp_lowest_qoq", ""),
                    r.get("comp_lowest_trend", ""),
                    r.get("sale_avg_price", ""), r.get("sale_price", ""),
                    r.get("sale_qoq", ""), r.get("sale_trend_direction", ""),
                    r.get("rent_avg_price", ""), r.get("rent_price", ""),
                    r.get("rent_qoq", ""), r.get("rent_trend_direction", ""),
                    r.get("price_history", ""), r.get("nearby_localities", ""),
                    r.get("locality_rating", ""), r.get("locality_rating_users", ""),
                    r.get("locality_reviews", ""),
                    r.get("total_props", ""),
                    r.get("props_for_sale", ""), r.get("props_for_rent", ""),
                    r.get("projects_count", ""),
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
