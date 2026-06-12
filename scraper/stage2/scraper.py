import math
from bs4 import BeautifulSoup
import re
import time
import urllib.parse
from datetime import datetime
from random import randint
from scraper.fetch import create_session, do_get, do_post

BASE_URL = "https://www.magicbricks.com"
DWR_PATH = "/bricks/dwr"
ORIG_SCRIPT_SESSION_ID = "1F47710CD4AE2F5DB09361C487D16BBD"
REQUEST_DELAY = 1.5

session = create_session()


def fetch_page(url):
    return do_get(session, url, delay=REQUEST_DELAY, label="Req", indent=4)


def dwr_call(city_code, prop_type_id, page_num, main_tab, page_url):
    time.sleep(REQUEST_DELAY)
    jsessionid = session.cookies.get("JSESSIONID", "")
    script_session_id = ORIG_SCRIPT_SESSION_ID + str(randint(0, 999))

    body = (
        "callCount=1\n"
        "page=" + page_url + "\n"
        "httpSessionId=" + jsessionid + "\n"
        "scriptSessionId=" + script_session_id + "\n"
        "c0-scriptName=ajaxService\n"
        "c0-methodName=getPropertyRates\n"
        "c0-id=0\n"
        "c0-param0=string:" + city_code + "\n"
        "c0-param1=string:" + prop_type_id + "\n"
        "c0-param2=string:\n"
        "c0-param3=string:\n"
        "c0-param4=number:" + str(page_num) + "\n"
        "c0-param5=number:" + str(main_tab) + "\n"
        "c0-param6=boolean:false\n"
        "c0-param7=boolean:false\n"
        "batchId=0\n"
    )

    return do_post(
        session,
        BASE_URL + DWR_PATH + "/call/plaincall/ajaxService.getPropertyRates.dwr",
        data=body,
        headers={"Content-Type": "text/plain", "Referer": BASE_URL + page_url},
        delay=0,
        label="Req",
        indent=4,
    )


def _parse_dwr_val(val):
    val = val.strip().rstrip(";")
    if val.startswith('"') and val.endswith('"'):
        return val[1:-1]
    if val == "null":
        return None
    if val == "true":
        return True
    if val == "false":
        return False
    return val


def parse_dwr_response(text):
    if "//#DWR-REPLY" in text:
        text = text[text.find("//#DWR-REPLY"):]

    m = re.search(r"_remoteHandleCallback\('[^']+','[^']+',\{(.+)\}\);", text, re.DOTALL)
    if not m:
        return []

    objs = {}
    arrays = {}

    for statement in text.replace("\n", " ").split(";"):
        statement = statement.strip()
        if not statement:
            continue
        if statement.startswith("var ") and "=" in statement:
            parts = statement.split("=", 1)
            var_name = parts[0].replace("var ", "").strip()
            var_val = parts[1].strip()
            if var_val.startswith("{"):
                objs[var_name] = {}
            elif var_val.startswith("["):
                arrays[var_name] = []
            else:
                objs[var_name] = _parse_dwr_val(var_val)
        elif "=" in statement:
            key, val = statement.split("=", 1)
            key = key.strip()
            val = _parse_dwr_val(val)
            if "[" in key and key.endswith("]"):
                arr_name = key[: key.index("[")]
                idx_str = key[key.index("[") + 1 : key.index("]")]
                if idx_str.isdigit():
                    idx = int(idx_str)
                    if arr_name not in arrays:
                        arrays[arr_name] = []
                    while len(arrays[arr_name]) <= idx:
                        arrays[arr_name].append(None)
                    arrays[arr_name][idx] = val
            elif "." in key:
                dot = key.index(".")
                obj_name = key[:dot]
                attr = key[dot + 1 :]
                if obj_name in objs:
                    objs[obj_name][attr] = val
                elif obj_name in arrays:
                    if not isinstance(arrays[obj_name], dict):
                        arrays[obj_name] = {}
                    arrays[obj_name][attr] = val

    cb = m.group(1)
    m2 = re.search(r"rates:(\w+)", cb)
    rates_var = m2.group(1) if m2 else None

    m3 = re.search(r'propertTypeSelected:"([^"]*)"', cb)
    sub_type = m3.group(1) if m3 else ""

    results = []
    if rates_var and rates_var in arrays:
        for ref in arrays[rates_var]:
            if not ref or not (isinstance(ref, str) and ref.startswith("s") and ref[1:].isdigit()):
                continue
            rate = objs.get(ref, {})
            locality = rate.get("locality", "")
            trend_link = rate.get("trendLink", "")
            row_list_ref = rate.get("rowList", "")

            if isinstance(row_list_ref, str) and row_list_ref in arrays:
                for row_ref in arrays[row_list_ref]:
                    if not row_ref or not (isinstance(row_ref, str) and row_ref.startswith("s") and row_ref[1:].isdigit()):
                        continue
                    row = objs.get(row_ref, {})
                    sale_ref = row.get("sale", "")
                    if isinstance(sale_ref, str) and sale_ref in objs:
                        sale = objs[sale_ref]
                        price_range = sale.get("priceRange", "")
                        avg_price = sale.get("avgPrice", "")
                        qoq_raw = sale.get("qoq", "")
                        qoq = qoq_raw.replace("%", "").strip() if qoq_raw else ""

                        results.append({
                            "city_name": "",
                            "property_type": "",
                            "sub_property_type": sub_type,
                            "locality": locality,
                            "sale_price_range": price_range,
                            "sale_average_price": avg_price,
                            "sale_q_o_q": qoq,
                            "view_trends_link": trend_link,
                        })

    return results


def extract_city_code(html):
    m = re.search(r"var selectedCity=['\"](\d+)['\"]", html)
    return m.group(1) if m else ""


def extract_main_tab(html):
    m = re.search(r"var mainTab=(\d+)", html)
    return int(m.group(1)) if m else 9000


def extract_sub_types(html):
    soup = BeautifulSoup(html, "html.parser")
    types = []
    pro_div = soup.find("div", class_="proTrends-btn")
    if not pro_div:
        return types
    for span in pro_div.find_all("span", onclick=True):
        name = span.get_text(strip=True)
        onclick = span.get("onclick", "")
        m = re.search(r"fetchpropertyRates\('(\d+)','(\d+)','([^']+)'\)", onclick)
        if m and name:
            types.append({
                "name": name,
                "type_id": m.group(1),
                "count": m.group(2),
                "tab_id": m.group(3),
            })
    return types


def generate_filename():
    now = datetime.now()
    return now.strftime("magic_brick_property_price_trends_%H_%M_%S_%d_%m_%y.csv")


def scrape_city(city_name, city_url):
    print(f"  [City] {city_name} ({city_url})")
    property_type = "Residential" if "RESIDENTIAL" in city_url else "Commercial"

    html = fetch_page(city_url)
    city_code = extract_city_code(html)
    main_tab = extract_main_tab(html)
    sub_types = extract_sub_types(html)

    if not city_code:
        print(f"    No city code found!")
        return []
    if not sub_types:
        print(f"    No sub-property types found!")
        return []

    all_results = []
    for st in sub_types:
        total_pages = math.ceil(int(st["count"]) / 20)
        page_path = urllib.parse.urlparse(city_url).path
        for page_num in range(1, total_pages + 1):
            print(f"    [Sub-type] {st['name']} (page {page_num}/{total_pages})")
            resp_text = dwr_call(
                city_code, st["type_id"], page_num, main_tab, page_path
            )
            records = parse_dwr_response(resp_text)
            for r in records:
                r["city_name"] = city_name
                r["property_type"] = property_type
                r["sub_property_type"] = st["name"]
            all_results.extend(records)
            print(f"      -> {len(records)} localities on this page")

    return all_results


def scrape_stage2(cities):
    all_results = []
    total = len(cities)
    for idx, city in enumerate(cities, 1):
        print(f"[{idx}/{total}] Processing {city['city_name']} ({city['property_type']})")
        records = scrape_city(city["city_name"], city["city_url"])
        all_results.extend(records)
        print(f"  Total so far: {len(all_results)} records")
    return all_results
