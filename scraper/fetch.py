import time
import requests
from proxymanager import PROXIES, PROXY_TAG

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def create_session(use_proxy=True):
    session = requests.Session()
    session.headers.update(HEADERS)
    if use_proxy and PROXIES:
        session.proxies.update(PROXIES)
    return session


def _proxy_clear(session):
    saved = dict(session.proxies)
    session.proxies.clear()
    return saved


def _proxy_restore(session, saved):
    session.proxies.update(saved)


def do_get(session, url, delay=1.0, label="Req", indent=4):
    time.sleep(delay)
    resp = session.get(url, timeout=30)
    fell_back = False
    if resp.status_code == 403 and session.proxies:
        print(f"{' ' * indent}[{label}] {resp.status_code} GET {url} ({PROXY_TAG}) - retrying directly")
        saved = _proxy_clear(session)
        resp = session.get(url, timeout=30)
        _proxy_restore(session, saved)
        fell_back = True
    resp.raise_for_status()
    tag = "direct" if fell_back else PROXY_TAG
    print(f"{' ' * indent}[{label}] {resp.status_code} GET {url} ({tag})")
    return resp.text


def do_post(session, url, data, headers=None, delay=1.0, label="Req", indent=4):
    time.sleep(delay)
    resp = session.post(url, headers=headers, data=data, timeout=30)
    fell_back = False
    if resp.status_code == 403 and session.proxies:
        print(f"{' ' * indent}[{label}] {resp.status_code} POST {url} ({PROXY_TAG}) - retrying directly")
        saved = _proxy_clear(session)
        resp = session.post(url, headers=headers, data=data, timeout=30)
        _proxy_restore(session, saved)
        fell_back = True
    resp.raise_for_status()
    tag = "direct" if fell_back else PROXY_TAG
    print(f"{' ' * indent}[{label}] {resp.status_code} POST {url} ({tag})")
    return resp.text
