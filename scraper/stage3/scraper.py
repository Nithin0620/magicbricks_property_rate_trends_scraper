import json
import re
import time
import urllib.parse
from datetime import datetime
from random import randint

from bs4 import BeautifulSoup
from scraper.fetch import create_session, do_get, do_post

BASE_URL = "https://www.magicbricks.com"
DWR_PATH = "/bricks/dwr"
ORIG_SCRIPT_SESSION_ID = "1F47710CD4AE2F5DB09361C487D16BBD"
REQUEST_DELAY = 1.0

session = create_session()


def fetch_page(url):
    return do_get(session, url, delay=REQUEST_DELAY, label="Req", indent=6)


def extract_city_code(html):
    m = re.search(r"var selectedCity=['\"](\d+)['\"]", html)
    if m:
        return m.group(1)
    m = re.search(r"var cityCodeData\s*=\s*'(\d+)'", html)
    return m.group(1) if m else ""


def extract_locality_id(html):
    m = re.search(r"var localityId\s*=\s*\"(\d+)\"", html)
    return m.group(1) if m else ""


def extract_main_property_type(html):
    m = re.search(r"var mainPropertyType\s*=\s*\"(\d+)\"", html)
    return m.group(1) if m else "9000"


def extract_prop_type_id(html):
    m = re.search(r'value="(\d+)".*?id="currPropertyType"', html)
    if m:
        return m.group(1)
    m = re.search(r'id="currPropertyType".*?value="(\d+)"', html)
    return m.group(1) if m else ""


def extract_sub_type_name(html):
    soup = BeautifulSoup(html, "html.parser")
    el = soup.select_one(".pro-boxHeading strong")
    return el.get_text(strip=True) if el else ""


def extract_locality_name(html):
    m = re.search(r"var locName\s*=\s*'([^']+)'", html)
    return m.group(1) if m else ""


def extract_city_name(html):
    m = re.search(r"var cityName\s*=\s*'([^']+)'", html)
    return m.group(1) if m else ""


def extract_page_url_data(html):
    city_code = extract_city_code(html)
    locality_id = extract_locality_id(html)
    main_property_type = extract_main_property_type(html)
    prop_type_id = extract_prop_type_id(html)
    sub_type_name = extract_sub_type_name(html)
    locality_name = extract_locality_name(html)
    city_name = extract_city_name(html)
    return {
        "city_code": city_code,
        "locality_id": locality_id,
        "main_property_type": main_property_type,
        "prop_type_id": prop_type_id,
        "sub_type_name": sub_type_name,
        "locality_name": locality_name,
        "city_name": city_name,
    }


def extract_locality_metadata(html):
    soup = BeautifulSoup(html, "html.parser")
    result = {
        "rating": "",
        "rating_users": "",
        "reviews": "",
        "total_props": "",
        "props_for_sale": "",
        "props_for_rent": "",
        "projects": "",
    }

    rating_lbl = soup.select_one("#ratingLbl")
    if rating_lbl:
        txt = rating_lbl.get_text(strip=True)
        m = re.search(r"([\d.]+)\s*Rating by (\d+)", txt)
        if m:
            result["rating"] = m.group(1)
            result["rating_users"] = m.group(2)

    review_lbl = soup.select_one("#reviewLbl")
    if review_lbl:
        txt = review_lbl.get_text(strip=True)
        m = re.search(r"(\d+)", txt)
        if m:
            result["reviews"] = m.group(1)

    props_nav = soup.select_one("#localityProperties .navText")
    if props_nav:
        txt = props_nav.get_text(strip=True)
        m = re.search(r"(\d+)\s*Properties", txt)
        if m:
            result["total_props"] = m.group(1)
        m2 = re.search(r"(\d+)\s+for Sale", txt)
        if m2:
            result["props_for_sale"] = m2.group(1)
        m3 = re.search(r"(\d+)\s+for Rent", txt)
        if m3:
            result["props_for_rent"] = m3.group(1)

    proj_nav = soup.select_one("#localityProjects .navText")
    if proj_nav:
        txt = proj_nav.get_text(strip=True)
        m = re.search(r"(\d+)", txt)
        if m:
            result["projects"] = m.group(1)

    return result


def dwr_fetch_price_trend(city_code, prop_type_id, main_property_type, locality_id, sale_or_rent, page_url):
    time.sleep(REQUEST_DELAY)
    jsessionid = session.cookies.get("JSESSIONID", "")
    script_session_id = ORIG_SCRIPT_SESSION_ID + str(randint(0, 999))
    page_path = urllib.parse.urlparse(page_url).path

    body = (
        "callCount=1\n"
        "page=" + page_path + "\n"
        "httpSessionId=" + jsessionid + "\n"
        "scriptSessionId=" + script_session_id + "\n"
        "c0-scriptName=ajaxService\n"
        "c0-methodName=fetchPriceTrendDetails\n"
        "c0-id=0\n"
        "c0-param0=string:" + city_code + "\n"
        "c0-param1=string:" + prop_type_id + "\n"
        "c0-param2=string:" + main_property_type + "\n"
        "c0-param3=string:" + locality_id + "\n"
        "c0-param4=string:" + sale_or_rent + "\n"
        "c0-param5=boolean:false\n"
        "c0-param6=boolean:false\n"
        "batchId=0\n"
    )

    return do_post(
        session,
        BASE_URL + DWR_PATH + "/call/plaincall/ajaxService.fetchPriceTrendDetails.dwr",
        data=body,
        headers={"Content-Type": "text/plain", "Referer": BASE_URL + page_path},
        delay=0,
        label="Req",
        indent=6,
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


def resolve_nearby_rates(nearby_obj, objs, arrays):
    rates = []
    rates_ref = nearby_obj.get("rates", "")
    if isinstance(rates_ref, str) and rates_ref in arrays:
        for ref in arrays[rates_ref]:
            if not ref:
                continue
            rate_key = ref if isinstance(ref, str) else ""
            rate_obj = objs.get(rate_key, {})
            if not rate_obj:
                continue
            locality = rate_obj.get("locality", "")
            trend_link = rate_obj.get("trendLink", "")
            row_list_ref = rate_obj.get("rowList", "")
            sale_data = {}
            if isinstance(row_list_ref, str) and row_list_ref in arrays:
                for row_ref in arrays[row_list_ref]:
                    if not row_ref:
                        continue
                    row_key = row_ref if isinstance(row_ref, str) else ""
                    row = objs.get(row_key, {})
                    sale_ref = row.get("sale", "")
                    if isinstance(sale_ref, str) and sale_ref in objs:
                        sale = objs[sale_ref]
                        sale_data = {
                            "priceRange": sale.get("priceRange", ""),
                            "avgPrice": sale.get("avgPrice", ""),
                            "qoq": sale.get("qoq", ""),
                            "up": sale.get("up", ""),
                            "qoqPresent": sale.get("qoqPresent", ""),
                        }
            rates.append({
                "locality": locality,
                "priceRange": sale_data.get("priceRange", ""),
                "avgPrice": sale_data.get("avgPrice", ""),
                "qoq": sale_data.get("qoq", ""),
                "up": sale_data.get("up", ""),
                "trendLink": trend_link,
            })
    return rates


def resolve_graph_data(graph_obj, arrays):
    result = {}
    for field in ["lowerRangeValues", "upperRangeValues", "averageRangeValues", "quarterValues", "quarterValuesMob"]:
        ref = graph_obj.get(field, "")
        if isinstance(ref, str) and ref in arrays:
            result[field] = arrays[ref]
        else:
            result[field] = []
    for field in ["pu", "upOrDown", "upOrdownValue", "quarterValuesLast", "averageRangeValuesLast",
                   "quarterValuesSecondLast", "averageRangeValuesSecondLast"]:
        val = graph_obj.get(field, "")
        result[field] = val
    return result


def parse_price_trend_response_full(text):
    if "//#DWR-REPLY" in text:
        text = text[text.find("//#DWR-REPLY"):]

    m = re.search(r"_remoteHandleCallback\('[^']+','[^']+',\{(.+)\}\);", text, re.DOTALL)
    if not m:
        return None

    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    clean_lines = []
    for line in lines:
        line = line.strip()
        if line and not line.startswith("//"):
            clean_lines.append(line)
    clean = " ".join(clean_lines)

    objs = {}
    arrays = {}

    for statement in clean.split(";"):
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
                arr_name = key[:key.index("[")]
                idx_str = key[key.index("[") + 1:key.index("]")]
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
                attr = key[dot + 1:]
                if obj_name in objs:
                    objs[obj_name][attr] = val
                elif obj_name in arrays:
                    if not isinstance(arrays[obj_name], dict):
                        arrays[obj_name] = {}
                    arrays[obj_name][attr] = val

    cb_body = m.group(1)

    prop_type_desc = ""
    m_desc = re.search(r'propTypeDesc:"([^"]*)"', cb_body)
    if m_desc:
        prop_type_desc = m_desc.group(1)

    pu = ""
    m_pu = re.search(r'pu:"([^"]+)"', cb_body)
    if m_pu:
        pu = m_pu.group(1)

    price_rate = {}
    price_compare = {}
    graph_data = {}
    nearby_rates = []
    nearby_obj = None

    refs = re.findall(r'(\w+):(s\d+)', cb_body)
    for field, ref in refs:
        if ref in objs:
            if field == "priceRate":
                price_rate = objs[ref]
            elif field == "priceCompare":
                price_compare = objs[ref]
            elif field == "graphData":
                graph_data = resolve_graph_data(objs[ref], arrays)
            elif field == "nearByPriceRate":
                nearby_obj = objs[ref]

    if nearby_obj:
        nearby_rates = resolve_nearby_rates(nearby_obj, objs, arrays)

    return {
        "propTypeDesc": prop_type_desc,
        "pu": pu,
        "priceRate": price_rate,
        "priceCompare": price_compare,
        "graphData": graph_data,
        "nearbyRates": nearby_rates,
    }


def build_price_history(graph_data):
    quarters = graph_data.get("quarterValues", [])
    lowers = graph_data.get("lowerRangeValues", [])
    uppers = graph_data.get("upperRangeValues", [])
    avgs = graph_data.get("averageRangeValues", [])
    history = []
    for i in range(len(quarters)):
        history.append({
            "quarter": quarters[i] if i < len(quarters) else "",
            "lower": lowers[i] if i < len(lowers) else "",
            "upper": uppers[i] if i < len(uppers) else "",
            "average": avgs[i] if i < len(avgs) else "",
        })
    return history


def scrape_locality(city_name, sub_property_type, view_trends_link):
    print(f"    [Locality] {city_name} - {sub_property_type}")
    
    try:
        html = fetch_page(view_trends_link)
    except Exception as e:
        print(f"      Failed to fetch: {e}")
        return None
    page_data = extract_page_url_data(html)
    metadata = extract_locality_metadata(html)

    city_code = page_data.get("city_code", "")
    locality_id = page_data.get("locality_id", "")
    main_property_type = page_data.get("main_property_type", "9000")
    prop_type_id = page_data.get("prop_type_id", "")
    loc_name = page_data.get("locality_name", "")

    if not city_code or not locality_id or not prop_type_id:
        print(f"      Missing page data: city={city_code}, loc={locality_id}, prop={prop_type_id}")
        return None

    reviews_link = derive_reviews_link(view_trends_link)

    result = {
        "city_name": city_name or page_data.get("city_name", ""),
        "sub_property_type": sub_property_type or page_data.get("sub_type_name", ""),
        "locality_name": loc_name,
        "locality_id": locality_id,
        "view_trends_url": view_trends_link,
        "reviews_link": reviews_link,
    }

    # Fetch Sale data
    sale_resp = dwr_fetch_price_trend(city_code, prop_type_id, main_property_type, locality_id, "S", view_trends_link)
    sale_data = parse_price_trend_response_full(sale_resp)
    
    # Fetch Rent data
    rent_resp = dwr_fetch_price_trend(city_code, prop_type_id, main_property_type, locality_id, "R", view_trends_link)
    rent_data = parse_price_trend_response_full(rent_resp)

    # Price compare (from sale data)
    pc = (sale_data or {}).get("priceCompare", {})
    result.update({
        "comp_highest_price": pc.get("max", ""),
        "comp_highest_qoq": pc.get("maxQoq", ""),
        "comp_highest_trend": "up" if pc.get("maxUp") else ("down" if pc.get("maxUp") is False else ""),
        "comp_avg_price": pc.get("avg", ""),
        "comp_avg_qoq": pc.get("avgQoq", ""),
        "comp_avg_trend": "up" if pc.get("avgUp") else ("down" if pc.get("avgUp") is False else ""),
        "comp_lowest_price": pc.get("min", ""),
        "comp_lowest_qoq": pc.get("minQoq", ""),
        "comp_lowest_trend": "up" if pc.get("minUp") else ("down" if pc.get("minUp") is False else ""),
    })

    # Sale price rate
    pr = (sale_data or {}).get("priceRate", {})
    result.update({
        "sale_avg_price": pr.get("avg", ""),
        "sale_price": pr.get("price", ""),
        "sale_qoq": pr.get("qoq", ""),
        "sale_trend_direction": "up" if pr.get("up") else ("down" if pr.get("up") is False else ""),
    })

    # Rent price rate
    rpr = (rent_data or {}).get("priceRate", {})
    result.update({
        "rent_avg_price": rpr.get("avg", ""),
        "rent_price": rpr.get("price", ""),
        "rent_qoq": rpr.get("qoq", ""),
        "rent_trend_direction": "up" if rpr.get("up") else ("down" if rpr.get("up") is False else ""),
    })

    # Sale graph data
    gd = (sale_data or {}).get("graphData", {})
    price_history = build_price_history(gd)
    result["price_history"] = json.dumps(price_history, ensure_ascii=False)

    # Nearby localities (from sale data)
    nearby = (sale_data or {}).get("nearbyRates", [])
    result["nearby_localities"] = json.dumps(nearby, ensure_ascii=False) if nearby else "[]"

    # Locality metadata
    result.update({
        "locality_rating": metadata.get("rating", ""),
        "locality_rating_users": metadata.get("rating_users", ""),
        "locality_reviews": metadata.get("reviews", ""),
        "total_props": metadata.get("total_props", ""),
        "props_for_sale": metadata.get("props_for_sale", ""),
        "props_for_rent": metadata.get("props_for_rent", ""),
        "projects_count": metadata.get("projects", ""),
    })

    print(f"      Sale price: {result['sale_avg_price']}, Rent: {result['rent_avg_price']}, Nearby: {len(nearby)} localities, History: {len(price_history)} quarters")
    return result


def derive_reviews_link(view_trends_url):
    m = re.search(r'rates-(.+?)-in-(.+)$', view_trends_url)
    if m:
        locality = m.group(1)
        city = m.group(2)
        return f"https://www.magicbricks.com/real-estate-property-reviews/{locality}-in-{city}?widgetName=localityRatings"
    return ""


def generate_filename():
    now = datetime.now()
    return now.strftime("magic_brick_property_price_trends_%H_%M_%S_%d_%m_%y.csv")


def scrape_stage3(stage2_records):
    seen = set()
    all_results = []
    total = len(stage2_records)
    for idx, rec in enumerate(stage2_records, 1):
        link = rec.get("view_trends_link", "").strip()
        if not link or link in seen:
            continue
        seen.add(link)
        city_name = rec.get("city_name", "")
        sub_type = rec.get("sub_property_type", "")
        print(f"[{idx}/{total}] {city_name} - {sub_type}")
        result = scrape_locality(city_name, sub_type, link)
        if result:
            all_results.append(result)
            print(f"  Total so far: {len(all_results)} localities")
    return all_results
