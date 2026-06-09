import os
import sys
import csv

from scraper.stage1.scraper import scrape_stage1, generate_filename as gen_filename_s1
from scraper.stage2.scraper import scrape_stage2, generate_filename as gen_filename_s2
from scraper.stage3.scraper import scrape_stage3, generate_filename as gen_filename_s3
from scraper.stage4.scraper import scrape_stage4, generate_filename as gen_filename_s4

DATA_DIR_S1 = os.path.join(os.path.dirname(__file__), "data", "stage1")
DATA_DIR_S2 = os.path.join(os.path.dirname(__file__), "data", "stage2")
DATA_DIR_S3 = os.path.join(os.path.dirname(__file__), "data", "stage3")
DATA_DIR_S4 = os.path.join(os.path.dirname(__file__), "data", "stage4")


def save_csv(records, filename, data_dir):
    os.makedirs(data_dir, exist_ok=True)
    filepath = os.path.join(data_dir, filename)
    if not records:
        print(f"[CSV] No records to write.")
        return filepath
    fieldnames = list(records[0].keys())
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
    print(f"[CSV] Saved {len(records)} rows to {filepath}")
    return filepath


def run_stage1():
    print("\n" + "=" * 60)
    print("  Stage 1: Scraping city links from main page")
    print("=" * 60)
    cities = scrape_stage1()
    filename = gen_filename_s1()
    save_csv(cities, filename, DATA_DIR_S1)

    try:
        from database.stage1.db_loader import load_to_db
        load_to_db(cities)
    except Exception as e:
        print(f"[DB] Skipping DB load: {e}")

    return cities


def run_stage2(cities):
    print("\n" + "=" * 60)
    print("  Stage 2: Scraping property rate data for all cities")
    print("=" * 60)
    records = scrape_stage2(cities)
    filename = gen_filename_s2()
    save_csv(records, filename, DATA_DIR_S2)

    try:
        from database.stage2.db_loader import load_to_db
        load_to_db(records)
    except Exception as e:
        print(f"[DB] Skipping DB load: {e}")

    return records


def run_stage3(stage2_records):
    print("\n" + "=" * 60)
    print("  Stage 3: Scraping locality detail pages (view trends)")
    print("=" * 60)
    records = scrape_stage3(stage2_records)
    filename = gen_filename_s3()
    save_csv(records, filename, DATA_DIR_S3)

    try:
        from database.stage3.db_loader import load_to_db
        load_to_db(records)
    except Exception as e:
        print(f"[DB] Skipping DB load: {e}")

    return records


def run_stage4(stage3_records):
    print("\n" + "=" * 60)
    print("  Stage 4: Scraping locality ratings & reviews")
    print("=" * 60)
    records = scrape_stage4(stage3_records)
    filename = gen_filename_s4()
    save_csv(records, filename, DATA_DIR_S4)

    try:
        from database.stage4.db_loader import load_to_db
        load_to_db(records)
    except Exception as e:
        print(f"[DB] Skipping DB load: {e}")

    return records


def load_csv(data_dir, prefix):
    try:
        files = [f for f in os.listdir(data_dir) if f.endswith(".csv") and f.startswith(prefix)]
    except FileNotFoundError:
        return None
    if not files:
        return None
    files.sort(key=lambda f: os.path.getmtime(os.path.join(data_dir, f)))
    with open(os.path.join(data_dir, files[-1]), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    print("=" * 60)
    print("  MagicBricks Property Rate Trends Scraper")
    print("=" * 60)

    stage = sys.argv[1] if len(sys.argv) > 1 else "all"
    cities = None
    stage2_records = None
    stage3_records = None

    if stage in ("1", "all"):
        cities = run_stage1()
    else:
        cities = load_csv(DATA_DIR_S1, "magic_brick")
        if cities is None:
            print("[Error] No stage 1 CSV found. Run stage 1 first.")
            return

    if stage in ("2", "all"):
        if stage == "all":
            stage2_records = run_stage2(cities)
        else:
            stage2_records = run_stage2(cities)

    if stage in ("3", "all"):
        if stage == "3":
            stage2_records = load_csv(DATA_DIR_S2, "magic_brick")
        if stage2_records is None:
            print("[Error] No stage 2 data. Run stage 2 first.")
            return
        stage3_records = run_stage3(stage2_records)

    if stage in ("4", "all"):
        if stage == "4":
            stage3_records = load_csv(DATA_DIR_S3, "magic_brick")
        if stage3_records is None:
            print("[Error] No stage 3 data. Run stage 3 first.")
            return
        run_stage4(stage3_records)

    print("\nDone!")


if __name__ == "__main__":
    main()
