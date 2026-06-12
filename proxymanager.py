import os

PROXY_FILE = os.path.join(os.path.dirname(__file__), "proxies", "Webshare 10 proxies.txt")

PROXY_URL = None
PROXIES = None
PROXY_TAG = "local"


def _load_proxy():
    global PROXY_URL, PROXIES, PROXY_TAG
    if os.path.exists(PROXY_FILE):
        with open(PROXY_FILE) as f:
            line = f.readline().strip()
            if line:
                PROXY_URL = line
                PROXIES = {"http": PROXY_URL, "https": PROXY_URL}
                PROXY_TAG = "Webshare"


_load_proxy()


if PROXY_URL:
    print(f"[Proxy] Using Webshare rotating IP: {PROXY_URL.split('@')[1]}")
else:
    print(f"[Proxy] No proxy configured. Using local static IP.")
