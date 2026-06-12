import os
import psycopg2
import psycopg2.extras


def _load_env():
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, _, value = line.partition('=')
                    os.environ.setdefault(key.strip(), value.strip())


_load_env()
DB_URL = os.getenv("DB_URL", "postgresql://localhost:5432/magicbricks")

STAGE1_TABLE = "magicbrick_stage1"
STAGE2_TABLE = "magicbrick_stage2"
STAGE3_TABLE = "magicbrick_stage3"
STAGE4_TABLE = "magicbrick_stage4"

STAGE1_COLUMNS = ["city_name", "property_type", "city_url"]
STAGE1_CONFLICT = ["city_name", "property_type"]

STAGE2_COLUMNS = [
    "city_name", "property_type", "sub_property_type", "locality",
    "sale_price_range", "sale_average_price", "sale_q_o_q", "view_trends_link",
]
STAGE2_CONFLICT = ["city_name", "locality", "sub_property_type", "view_trends_link"]

STAGE3_COLUMNS = [
    "city_name", "sub_property_type", "locality_name", "locality_id",
    "view_trends_url", "reviews_link",
    "comp_highest_price", "comp_highest_qoq", "comp_highest_trend",
    "comp_avg_price", "comp_avg_qoq", "comp_avg_trend",
    "comp_lowest_price", "comp_lowest_qoq", "comp_lowest_trend",
    "sale_avg_price", "sale_price", "sale_qoq", "sale_trend_direction",
    "rent_avg_price", "rent_price", "rent_qoq", "rent_trend_direction",
    "price_history", "nearby_localities",
    "locality_rating", "locality_rating_users", "locality_reviews",
    "total_props", "props_for_sale", "props_for_rent", "projects_count",
]
STAGE3_CONFLICT = ["view_trends_url"]

STAGE4_COLUMNS = [
    "city_name", "locality_name", "reviews_url",
    "environment_rating", "environment_sub_categories",
    "commuting_rating", "commuting_sub_categories",
    "places_of_interest_rating", "places_of_interest_sub_categories",
    "overall_rating_distribution",
    "total_reviews", "reviews_data",
]
STAGE4_CONFLICT = ["reviews_url"]

FAILED_TABLE = "magicbricks_failed"
FAILED_COLUMNS = ["stage", "city_name", "locality", "sub_property_type", "view_trends_link", "reviews_link", "error"]
FAILED_CONFLICT = ["stage", "city_name", "locality", "sub_property_type"]


def get_connection():
    return psycopg2.connect(DB_URL)


def init_tables(conn):
    with conn.cursor() as cur:
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {STAGE1_TABLE} (
                id SERIAL PRIMARY KEY,
                city_name VARCHAR(255) NOT NULL,
                property_type VARCHAR(50) NOT NULL,
                city_url TEXT NOT NULL,
                scraped_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(city_name, property_type)
            )
        """)
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {STAGE2_TABLE} (
                id SERIAL PRIMARY KEY,
                city_name VARCHAR(255) NOT NULL,
                property_type VARCHAR(50) NOT NULL,
                sub_property_type VARCHAR(255) NOT NULL,
                locality VARCHAR(255) NOT NULL,
                sale_price_range VARCHAR(100),
                sale_average_price VARCHAR(100),
                sale_q_o_q VARCHAR(50),
                view_trends_link TEXT,
                scraped_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(city_name, locality, sub_property_type, view_trends_link)
            )
        """)
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {STAGE3_TABLE} (
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
                scraped_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(view_trends_url)
            )
        """)
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {STAGE4_TABLE} (
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
                scraped_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(reviews_url)
            )
        """)
    conn.commit()


def count_records(conn, table_name):
    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {table_name}")
        return cur.fetchone()[0]


def get_distinct_pairs(conn, table_name, col1, col2):
    with conn.cursor() as cur:
        cur.execute(f"SELECT DISTINCT {col1}, {col2} FROM {table_name}")
        return set(cur.fetchall())


def get_non_empty_values(conn, table_name, column):
    with conn.cursor() as cur:
        cur.execute(f"SELECT DISTINCT {column} FROM {table_name} WHERE {column} IS NOT NULL AND {column} != ''")
        return set(row[0] for row in cur.fetchall())


def upsert_records(conn, table_name, records, columns, conflict_columns):
    if not records:
        return 0, 0

    values = []
    for r in records:
        values.append(tuple(r.get(col, "") for col in columns))

    columns_str = ", ".join(columns)
    conflict_str = ", ".join(conflict_columns)
    sql = f"INSERT INTO {table_name} ({columns_str}) VALUES %s ON CONFLICT ({conflict_str}) DO NOTHING"

    with conn.cursor() as cur:
        psycopg2.extras.execute_values(cur, sql, values, template=None)
        conn.commit()
        inserted = cur.rowcount

    total = len(records)
    duplicates_ignored = max(0, total - inserted)
    return inserted, duplicates_ignored


def init_failed_table(conn):
    with conn.cursor() as cur:
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {FAILED_TABLE} (
                id SERIAL PRIMARY KEY,
                stage INTEGER NOT NULL,
                city_name TEXT NOT NULL DEFAULT '',
                locality TEXT DEFAULT '',
                sub_property_type TEXT DEFAULT '',
                view_trends_link TEXT DEFAULT '',
                reviews_link TEXT DEFAULT '',
                error TEXT DEFAULT '',
                retry_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(stage, city_name, locality, sub_property_type)
            )
        """)
    conn.commit()


def insert_failed(conn, records):
    return upsert_records(conn, FAILED_TABLE, records, FAILED_COLUMNS, FAILED_CONFLICT)


def load_failed_records(conn):
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(f"SELECT * FROM {FAILED_TABLE} ORDER BY created_at")
        return [dict(row) for row in cur.fetchall()]


def delete_failed_record(conn, record_id):
    with conn.cursor() as cur:
        cur.execute(f"DELETE FROM {FAILED_TABLE} WHERE id = %s", (record_id,))
    conn.commit()


def count_failed_records(conn):
    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {FAILED_TABLE}")
        return cur.fetchone()[0]


def load_records(conn, table_name, exclude_columns=None):
    if exclude_columns is None:
        exclude_columns = ["id", "scraped_at"]

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(f"SELECT * FROM {table_name} ORDER BY id")
        rows = cur.fetchall()

    result = []
    for row in rows:
        record = dict(row)
        for col in exclude_columns:
            record.pop(col, None)
        result.append(record)

    return result
