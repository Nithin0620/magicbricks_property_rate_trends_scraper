import json
import re
import time
from datetime import datetime

from bs4 import BeautifulSoup
from scraper.fetch import create_session, do_get

BASE_URL = "https://www.magicbricks.com"
REQUEST_DELAY = 1.0

session = create_session()


def fetch_page(url):
    return do_get(session, url, delay=REQUEST_DELAY, label="Req", indent=4)


def extract_rating_blocks(soup):
    blocks = {}
    for block in soup.select(".loc-det-rev__rateblock"):
        title_el = block.select_one(".loc-det-rev__rateblock__title")
        value_el = block.select_one(".loc-det-rev__rateblock__value")
        title = title_el.get_text(strip=True) if title_el else ""
        value = value_el.get_text(strip=True) if value_el else ""

        sub_cats = []
        for td in block.select(".loc-det-rev__rateblock__td"):
            txt = td.get_text(strip=True)
            if txt and not txt.endswith("%"):
                sub_cats.append(txt)

        blocks[title] = {
            "rating": value,
            "sub_categories": sub_cats,
        }

        if title == "Overall":
            details_el = block.select_one(".loc-det-rev__rateblock__details-overall")
            if details_el:
                tds = [td.get_text(strip=True) for td in details_el.select(".loc-det-rev__rateblock__td") if td.get_text(strip=True)]
                dist = {}
                for i in range(0, len(tds) - 1, 2):
                    label = tds[i]
                    pct = tds[i + 1]
                    dist[label] = pct
                blocks[title]["distribution"] = dist

    return blocks


def extract_reviews(soup):
    reviews = []
    for review in soup.select(".loc-det-rev__reviewlist"):
        rtitle = review.select_one(".loc-det-rev__rtitle")
        heading_el = review.select_one(".loc-det-rev__rtitle__heading")
        content_el = review.select_one(".loc-det-rev__rtitle__localtxt")

        reviewer_name = ""
        user_type = ""
        review_date = ""
        rating = ""

        if rtitle:
            name_el = rtitle.select_one(".loc-det-rev__rtitle__img_nn, .loc-det__livablityblock__username-name")
            if name_el:
                reviewer_name = name_el.get_text(strip=True)

            block_el = rtitle.select_one(".loc-det-rev__rtitle__block")
            if block_el:
                initial = block_el.get_text(strip=True)
                if initial == "G":
                    user_type = "Guest"
                elif initial == "O":
                    user_type = "Owner"
                elif initial == "A":
                    user_type = "Agent"
                elif initial == "T":
                    user_type = "Tenant"
                elif initial == "I":
                    user_type = "Investor"
                else:
                    user_type = initial

            date_el = rtitle.select_one(".loc-det-rev__rtitle__date")
            if date_el:
                review_date = date_el.get_text(strip=True)

            rating = len(rtitle.select(".loc-det__blocks__smstar.full"))

        heading = heading_el.get_text(strip=True) if heading_el else ""
        content = content_el.get_text(strip=True) if content_el else ""

        if reviewer_name or heading or content:
            reviews.append({
                "reviewer_name": reviewer_name,
                "user_type": user_type,
                "date": review_date,
                "rating": str(rating),
                "title": heading,
                "content": content,
            })

    return reviews


def scrape_locality_ratings(reviews_link, locality_name, city_name):
    print(f"    [Ratings] {locality_name}, {city_name}")

    if not reviews_link:
        print(f"      No reviews link available")
        return None

    try:
        html = fetch_page(reviews_link)
    except Exception as e:
        print(f"      Failed to fetch: {e}")
        return None

    soup = BeautifulSoup(html, "html.parser")

    rating_blocks = extract_rating_blocks(soup)
    reviews = extract_reviews(soup)

    result = {
        "city_name": city_name,
        "locality_name": locality_name,
        "reviews_url": reviews_link,
        "environment_rating": rating_blocks.get("Environment", {}).get("rating", ""),
        "environment_sub_categories": json.dumps(
            rating_blocks.get("Environment", {}).get("sub_categories", []),
            ensure_ascii=False,
        ),
        "commuting_rating": rating_blocks.get("Commuting", {}).get("rating", ""),
        "commuting_sub_categories": json.dumps(
            rating_blocks.get("Commuting", {}).get("sub_categories", []),
            ensure_ascii=False,
        ),
        "places_of_interest_rating": rating_blocks.get("Places of Interest", {}).get("rating", ""),
        "places_of_interest_sub_categories": json.dumps(
            rating_blocks.get("Places of Interest", {}).get("sub_categories", []),
            ensure_ascii=False,
        ),
        "overall_rating_distribution": json.dumps(
            rating_blocks.get("Overall", {}).get("distribution", {}),
            ensure_ascii=False,
        ),
        "total_reviews": str(len(reviews)),
        "reviews_data": json.dumps(reviews, ensure_ascii=False),
    }

    print(
        f"      Ratings: Env={result['environment_rating']}, "
        f"Comm={result['commuting_rating']}, "
        f"POI={result['places_of_interest_rating']}, "
        f"Reviews: {result['total_reviews']}"
    )
    return result


def generate_filename():
    now = datetime.now()
    return now.strftime("magic_brick_property_price_trends_%H_%M_%S_%d_%m_%y.csv")


def scrape_stage4(stage3_records):
    seen = set()
    all_results = []
    total = len(stage3_records)
    for idx, rec in enumerate(stage3_records, 1):
        link = rec.get("reviews_link", "").strip()
        if not link or link in seen:
            continue
        seen.add(link)
        locality = rec.get("locality_name", "")
        city = rec.get("city_name", "")
        print(f"[{idx}/{total}] {city} - {locality}")
        result = scrape_locality_ratings(link, locality, city)
        if result:
            all_results.append(result)
            print(f"  Total so far: {len(all_results)} localities")
    return all_results
