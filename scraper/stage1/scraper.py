import requests
from bs4 import BeautifulSoup
from datetime import datetime


BASE_URL = "https://www.magicbricks.com"
TARGET_URL = "https://www.magicbricks.com/bricks/propertyRates.html?%20fromSite=mb"


def fetch_page(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.text


def parse_cities(html):
    soup = BeautifulSoup(html, "html.parser")
    results = []

    residential_div = soup.find("div", id="rateTrandsResidential")
    commercial_div = soup.find("div", id="rateTrandsCommercial")

    if residential_div:
        for a in residential_div.find_all("a", href=True):
            name = a.get_text(strip=True)
            href = a["href"]
            full_url = BASE_URL + href if href.startswith("/") else href
            results.append({
                "city_name": name,
                "property_type": "Residential",
                "city_url": full_url,
            })

    if commercial_div:
        for a in commercial_div.find_all("a", href=True):
            name = a.get_text(strip=True)
            href = a["href"]
            full_url = BASE_URL + href if href.startswith("/") else href
            results.append({
                "city_name": name,
                "property_type": "Commercial",
                "city_url": full_url,
            })

    return results


def generate_filename():
    now = datetime.now()
    return now.strftime("magic_brick_property_price_trends_%H_%M_%S_%d_%m_%y.csv")


def scrape_stage1():
    print(f"[Stage 1] Fetching: {TARGET_URL}")
    html = fetch_page(TARGET_URL)
    print("[Stage 1] Parsing city data...")
    cities = parse_cities(html)
    print(f"[Stage 1] Found {len(cities)} cities ({sum(1 for c in cities if c['property_type']=='Residential')} residential, {sum(1 for c in cities if c['property_type']=='Commercial')} commercial)")
    return cities
