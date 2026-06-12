import argparse
import csv
import os
import signal
import sys
import time

from database.db import (
    get_connection, init_tables, count_records,
    get_non_empty_values, upsert_records, load_records,
    init_failed_table, insert_failed, load_failed_records,
    delete_failed_record, count_failed_records,
    STAGE1_TABLE, STAGE2_TABLE, STAGE3_TABLE, STAGE4_TABLE,
    STAGE1_COLUMNS, STAGE1_CONFLICT,
    STAGE2_COLUMNS, STAGE2_CONFLICT,
    STAGE3_COLUMNS, STAGE3_CONFLICT,
    STAGE4_COLUMNS, STAGE4_CONFLICT,
)

from scraper.stage1.scraper import scrape_stage1, generate_filename as gen_filename_s1
from scraper.stage2.scraper import scrape_city, generate_filename as gen_filename_s2
from scraper.stage3.scraper import scrape_locality, generate_filename as gen_filename_s3
from scraper.stage4.scraper import scrape_locality_ratings, generate_filename as gen_filename_s4

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DATA_DIR_S1 = os.path.join(DATA_DIR, "stage1")
DATA_DIR_S2 = os.path.join(DATA_DIR, "stage2")
DATA_DIR_S3 = os.path.join(DATA_DIR, "stage3")
DATA_DIR_S4 = os.path.join(DATA_DIR, "stage4")


def save_csv(records, filename, data_dir):
    if not records:
        return None
    os.makedirs(data_dir, exist_ok=True)
    filepath = os.path.join(data_dir, filename)
    fieldnames = list(records[0].keys())
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
    print(f"  [CSV] Saved {len(records)} rows to {filepath}")
    return filepath


def print_summary(stage, elapsed, total=None, skipped=None, inserted=None, duplicates_ignored=None):
    parts = []
    if total is not None:
        parts.append(f"Total: {total}")
    if skipped is not None and skipped > 0:
        parts.append(f"Skipped: {skipped}")
    if inserted is not None:
        parts.append(f"Inserted: {inserted}")
    if duplicates_ignored is not None and duplicates_ignored > 0:
        parts.append(f"Duplicates ignored: {duplicates_ignored}")
    parts.append(f"Time: {elapsed:.2f}s")
    print(f"  [{stage}] {' | '.join(parts)}")


def run_stage1(conn, export_csv, limit):
    print(f"\n{'=' * 60}")
    print(f"  Stage 1: Scraping city links")
    print(f"{'=' * 60}")
    start = time.time()

    if limit is not None:
        existing = count_records(conn, STAGE1_TABLE)
        if existing > 0:
            print(f"  [Stage 1] Data exists in DB ({existing} records). Skipping HTTP call.")
            records = load_records(conn, STAGE1_TABLE)
            records = records[:limit]
            if export_csv:
                save_csv(records, gen_filename_s1(), DATA_DIR_S1)
            elapsed = time.time() - start
            print_summary("Stage 1", elapsed, total=len(records), skipped=existing, inserted=0)
            return records

    try:
        records = scrape_stage1()
    except Exception as e:
        print(f"  [Stage 1] Fetch failed: {e}")
        existing = count_records(conn, STAGE1_TABLE)
        if existing > 0:
            print(f"  [Stage 1] Falling back to {existing} existing DB records.")
            records = load_records(conn, STAGE1_TABLE)
        else:
            print(f"  [Stage 1] No cached data available. Returning empty.")
            records = []

    if limit is not None:
        records = records[:limit]

    total = len(records)
    if records:
        inserted, dupes = upsert_records(conn, STAGE1_TABLE, records, STAGE1_COLUMNS, STAGE1_CONFLICT)
    else:
        inserted, dupes = 0, 0

    if export_csv and records:
        save_csv(records, gen_filename_s1(), DATA_DIR_S1)

    elapsed = time.time() - start
    print_summary("Stage 1", elapsed, total=total, inserted=inserted, duplicates_ignored=dupes)
    return records


def run_stage2(conn, s1_records, export_csv, limit):
    print(f"\n{'=' * 60}")
    print(f"  Stage 2: Scraping property rate data")
    print(f"{'=' * 60}")
    start = time.time()

    cities_to_scrape = s1_records
    if limit:
        cities_to_scrape = cities_to_scrape[:limit]
        print(f"  [Stage 2] Limit active: processing {len(cities_to_scrape)} of {len(s1_records)} cities")

    existing_count = count_records(conn, STAGE2_TABLE)
    all_new_records = []
    total_inserted = 0
    total_dupes = 0
    total_cities = len(cities_to_scrape)
    for idx, city in enumerate(cities_to_scrape, 1):
        print(f"[{idx}/{total_cities}] Processing {city['city_name']} ({city['property_type']})")
        records = scrape_city(city["city_name"], city["city_url"])
        if records:
            inserted, dupes = upsert_records(conn, STAGE2_TABLE, records, STAGE2_COLUMNS, STAGE2_CONFLICT)
            total_inserted += inserted
            total_dupes += dupes
            all_new_records.extend(records)
            if inserted:
                print(f"  Inserted {inserted} new records for {city['city_name']} ({dupes} duplicates skipped)")

    if export_csv:
        save_csv(all_new_records, gen_filename_s2(), DATA_DIR_S2)

    all_records = load_records(conn, STAGE2_TABLE)
    elapsed = time.time() - start
    print_summary("Stage 2", elapsed, total=len(all_records), inserted=total_inserted, duplicates_ignored=total_dupes)
    return all_records


def run_stage3(conn, s2_records, export_csv, limit):
    print(f"\n{'=' * 60}")
    print(f"  Stage 3: Scraping locality price trends")
    print(f"{'=' * 60}")
    start = time.time()

    existing_links = get_non_empty_values(conn, STAGE3_TABLE, "view_trends_url")
    seen_links = set()
    seen_composite = set()

    records_to_scrape = []
    skipped = 0
    for rec in s2_records:
        link = rec.get("view_trends_link", "").strip()
        if not link or link in seen_links:
            continue
        seen_links.add(link)
        composite = (rec.get("city_name", ""), rec.get("locality", ""), rec.get("sub_property_type", ""))
        if all(composite) and composite in seen_composite:
            continue
        if all(composite):
            seen_composite.add(composite)
        if link in existing_links:
            skipped += 1
        else:
            records_to_scrape.append(rec)

    print(f"  [Stage 3] New localities: {len(records_to_scrape)}, Already in DB: {skipped}")

    if limit and records_to_scrape:
        records_to_scrape = records_to_scrape[:limit]
        print(f"  [Stage 3] Limit active: scraping {len(records_to_scrape)} localities")

    all_new_records = []
    total_inserted = 0
    total_dupes = 0
    total_localities = len(records_to_scrape)
    for idx, rec in enumerate(records_to_scrape, 1):
        link = rec.get("view_trends_link", "").strip()
        city_name = rec.get("city_name", "")
        sub_type = rec.get("sub_property_type", "")
        locality = rec.get("locality", "")
        print(f"[{idx}/{total_localities}] {city_name} - {locality} ({sub_type})")
        result = scrape_locality(city_name, sub_type, link)
        if result:
            inserted, dupes = upsert_records(conn, STAGE3_TABLE, [result], STAGE3_COLUMNS, STAGE3_CONFLICT)
            total_inserted += inserted
            total_dupes += dupes
            all_new_records.append(result)
        else:
            insert_failed(conn, [{
                "stage": 3,
                "city_name": city_name,
                "locality": locality,
                "sub_property_type": sub_type,
                "view_trends_link": link,
                "reviews_link": "",
                "error": "Scrape failed",
            }])
            print(f"  [Stage 3] Recorded failure in failed table")

    if export_csv:
        save_csv(all_new_records, gen_filename_s3(), DATA_DIR_S3)

    all_records = load_records(conn, STAGE3_TABLE)
    elapsed = time.time() - start
    print_summary("Stage 3", elapsed, total=len(all_records), skipped=skipped, inserted=total_inserted, duplicates_ignored=total_dupes)
    return all_records


def run_stage4(conn, s3_records, export_csv, limit):
    print(f"\n{'=' * 60}")
    print(f"  Stage 4: Scraping ratings & reviews")
    print(f"{'=' * 60}")
    start = time.time()

    existing_links = get_non_empty_values(conn, STAGE4_TABLE, "reviews_url")
    seen = set()

    records_to_scrape = []
    skipped = 0
    for rec in s3_records:
        link = rec.get("reviews_link", "").strip()
        if not link or link in seen:
            continue
        seen.add(link)
        if link in existing_links:
            skipped += 1
        else:
            records_to_scrape.append(rec)

    print(f"  [Stage 4] New localities: {len(records_to_scrape)}, Already in DB: {skipped}")

    if limit and records_to_scrape:
        records_to_scrape = records_to_scrape[:limit]
        print(f"  [Stage 4] Limit active: scraping {len(records_to_scrape)} localities")

    all_new_records = []
    total_inserted = 0
    total_dupes = 0
    total_localities = len(records_to_scrape)
    for idx, rec in enumerate(records_to_scrape, 1):
        link = rec.get("reviews_link", "").strip()
        locality = rec.get("locality_name", "")
        city = rec.get("city_name", "")
        print(f"[{idx}/{total_localities}] {city} - {locality}")
        result = scrape_locality_ratings(link, locality, city)
        if result:
            inserted, dupes = upsert_records(conn, STAGE4_TABLE, [result], STAGE4_COLUMNS, STAGE4_CONFLICT)
            total_inserted += inserted
            total_dupes += dupes
            all_new_records.append(result)
        else:
            insert_failed(conn, [{
                "stage": 4,
                "city_name": city,
                "locality": locality,
                "sub_property_type": "",
                "view_trends_link": "",
                "reviews_link": link,
                "error": "Scrape failed",
            }])
            print(f"  [Stage 4] Recorded failure in failed table")

    if export_csv:
        save_csv(all_new_records, gen_filename_s4(), DATA_DIR_S4)

    all_records = load_records(conn, STAGE4_TABLE)
    elapsed = time.time() - start
    print_summary("Stage 4", elapsed, total=len(all_records), skipped=skipped, inserted=total_inserted, duplicates_ignored=total_dupes)
    return all_records


def retry_failed(conn, limit):
    for attempt in range(1, 3):
        failed = load_failed_records(conn)
        if not failed:
            if attempt == 1:
                print(f"\n{'=' * 60}")
                print(f"  Retry: No failed items to retry")
                print(f"{'=' * 60}")
            return

        if attempt == 1:
            print(f"\n{'=' * 60}")
            print(f"  Retry phase: {len(failed)} failed items to retry")
            print(f"{'=' * 60}")

        to_scrape = failed[:limit] if limit else failed
        recovered = 0
        for rec in to_scrape:
            fid = rec["id"]
            stage = rec["stage"]
            city = rec["city_name"]
            locality = rec["locality"]
            sub_type = rec["sub_property_type"]
            vt_link = rec["view_trends_link"]
            rv_link = rec["reviews_link"]

            if stage == 3:
                print(f"  [Retry {attempt}/2] Stage 3: {city} - {locality} ({sub_type})")
                result = scrape_locality(city, sub_type, vt_link)
                if result:
                    inserted, dupes = upsert_records(conn, STAGE3_TABLE, [result], STAGE3_COLUMNS, STAGE3_CONFLICT)
                    if inserted:
                        delete_failed_record(conn, fid)
                        recovered += 1
                        print(f"    Recovered and removed from failed table")

            elif stage == 4:
                print(f"  [Retry {attempt}/2] Stage 4: {city} - {locality}")
                result = scrape_locality_ratings(rv_link, locality, city)
                if result:
                    inserted, dupes = upsert_records(conn, STAGE4_TABLE, [result], STAGE4_COLUMNS, STAGE4_CONFLICT)
                    if inserted:
                        delete_failed_record(conn, fid)
                        recovered += 1
                        print(f"    Recovered and removed from failed table")

        remaining = count_failed_records(conn)
        print(f"  [Retry {attempt}/2] Recovered: {recovered}, Remaining: {remaining}")
        if not remaining:
            return


def main():
    parser = argparse.ArgumentParser(description="MagicBricks Property Rate Trends Scraper Pipeline")
    parser.add_argument("--csv", action="store_true", help="Export results to CSV after execution")
    parser.add_argument("--limit", type=int, default=None, help="Process only N records/pages for testing")
    args = parser.parse_args()

    print("=" * 60)
    print("  MagicBricks Property Rate Trends Scraper Pipeline")
    print("=" * 60)

    flags = []
    if args.csv:
        flags.append("CSV export enabled")
    if args.limit:
        flags.append(f"Limit: {args.limit} records")
    if flags:
        print(f"  Flags: {', '.join(flags)}")
    print()

    interrupted = False

    def handle_sigint(sig, frame):
        nonlocal interrupted
        if interrupted:
            sys.exit(1)
        interrupted = True
        print(f"\n\n{'!' * 60}")
        print(f"  Received Ctrl+C. Finishing current request then shutting down...")
        print(f"{'!' * 60}\n")

    signal.signal(signal.SIGINT, handle_sigint)

    conn = get_connection()
    try:
        init_tables(conn)

        init_failed_table(conn)

        s1 = run_stage1(conn, args.csv, args.limit)
        if interrupted:
            s2, s3, s4 = [], [], []
        else:
            s2 = run_stage2(conn, s1, args.csv, args.limit)
        if interrupted:
            s3, s4 = [], []
        else:
            s3 = run_stage3(conn, s2, args.csv, args.limit)
        if interrupted:
            s4 = []
        else:
            s4 = run_stage4(conn, s3, args.csv, args.limit)

        # Retry failed items (2 attempts)
        if not interrupted:
            retry_failed(conn, args.limit)

        # Refresh final record counts
        s1 = load_records(conn, STAGE1_TABLE)
        s2 = load_records(conn, STAGE2_TABLE)
        s3 = load_records(conn, STAGE3_TABLE)
        s4 = load_records(conn, STAGE4_TABLE)
        remaining = count_failed_records(conn)

        print(f"\n{'=' * 60}")
        print(f"  Pipeline {'interrupted' if interrupted else 'complete'}!")
        print(f"  Stage 1: {len(s1)} cities")
        print(f"  Stage 2: {len(s2)} locality records")
        print(f"  Stage 3: {len(s3)} price trend records")
        print(f"  Stage 4: {len(s4)} ratings records")
        if remaining:
            print(f"  Failed: {remaining} items still in failed table")
        print(f"{'=' * 60}")
    except KeyboardInterrupt:
        print(f"\n\n{'!' * 60}")
        print(f"  Pipeline interrupted by user.")
        print(f"{'!' * 60}")
    except Exception as e:
        print(f"\n\n{'!' * 60}")
        print(f"  Pipeline failed: {e}")
        print(f"{'!' * 60}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
