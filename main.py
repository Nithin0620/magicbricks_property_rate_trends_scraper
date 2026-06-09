import os
import sys
import csv

from scraper.stage1.scraper import scrape_stage1, generate_filename as gen_filename_s1
from scraper.stage2.scraper import scrape_stage2, generate_filename as gen_filename_s2

DATA_DIR_S1 = os.path.join(os.path.dirname(__file__), "data", "stage1")
DATA_DIR_S2 = os.path.join(os.path.dirname(__file__), "data", "stage2")


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


def main():
    print("=" * 60)
    print("  MagicBricks Property Rate Trends Scraper")
    print("=" * 60)

    stage = sys.argv[1] if len(sys.argv) > 1 else "all"

    if stage in ("1", "all"):
        cities = run_stage1()
    else:
        csv_files = sorted(
            f for f in os.listdir(DATA_DIR_S1) if f.endswith(".csv") and f.startswith("magic_brick")
        )
        if not csv_files:
            print("[Error] No stage 1 CSV found. Run stage 1 first.")
            return
        with open(os.path.join(DATA_DIR_S1, csv_files[-1]), newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            cities = list(reader)

    if stage in ("2", "all"):
        if not cities:
            print("[Error] No cities data available. Run stage 1 first.")
            return
        run_stage2(cities)

    print("\nDone!")


if __name__ == "__main__":
    main()
