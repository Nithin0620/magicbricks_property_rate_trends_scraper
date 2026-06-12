import time
import requests
from proxymanager import PROXIES, PROXY_TAG

PERMANENT_404 = "__PERMANENT_404__"
OOPS_STAGE3 = "The page you are looking cannot be found"
OOPS_STAGE4 = "Oops... something is missing"

BREAK_INTERVAL = 600
BREAK_DURATION = 600
_request_count = 0


def _check_break(indent=0):
    global _request_count
    _request_count += 1
    if _request_count >= BREAK_INTERVAL:
        _request_count = 0
        print(f"{' ' * indent}[Break] {BREAK_INTERVAL} requests done. Sleeping {BREAK_DURATION // 60} min...")
        time.sleep(BREAK_DURATION)
        print(f"{' ' * indent}[Break] Resuming.")


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


def _retry_direct(method, session, url, reason, label, indent, **kwargs):
    print(f"{' ' * indent}[{label}] {reason} {url} - retrying directly")
    saved = _proxy_clear(session)
    try:
        resp = method(url, **kwargs)
    except requests.exceptions.ConnectionError:
        _proxy_restore(session, saved)
        raise
    _proxy_restore(session, saved)
    return resp, True


def do_get(session, url, delay=1.0, label="Req", indent=4):
    time.sleep(delay)
    fell_back = False
    try:
        resp = session.get(url, timeout=30)
    except requests.exceptions.ConnectionError:
        if not session.proxies:
            raise
        resp, fell_back = _retry_direct(
            session.get, session, url, "ProxyError GET", label, indent, timeout=30
        )

    if not fell_back and resp.status_code == 403 and session.proxies:
        resp, fell_back = _retry_direct(
            session.get, session, url, f"{resp.status_code} GET ({PROXY_TAG})", label, indent, timeout=30
        )

    resp.raise_for_status()
    _check_break(indent)
    tag = "direct" if fell_back else PROXY_TAG
    print(f"{' ' * indent}[{label}] {resp.status_code} GET {url} ({tag})")
    return resp.text


def do_post(session, url, data, headers=None, delay=1.0, label="Req", indent=4):
    time.sleep(delay)
    fell_back = False
    try:
        resp = session.post(url, headers=headers, data=data, timeout=30)
    except requests.exceptions.ConnectionError:
        if not session.proxies:
            raise
        resp, fell_back = _retry_direct(
            session.post, session, url, "ProxyError POST", label, indent,
            headers=headers, data=data, timeout=30
        )

    if not fell_back and resp.status_code == 403 and session.proxies:
        resp, fell_back = _retry_direct(
            session.post, session, url, f"{resp.status_code} POST ({PROXY_TAG})", label, indent,
            headers=headers, data=data, timeout=30
        )

    resp.raise_for_status()
    _check_break(indent)
    tag = "direct" if fell_back else PROXY_TAG
    print(f"{' ' * indent}[{label}] {resp.status_code} POST {url} ({tag})")
    return resp.text
