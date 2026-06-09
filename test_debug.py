import requests, time, re
from random import randint

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0"})

r = session.get("https://www.magicbricks.com/Property-Rates-Trends/ALL-RESIDENTIAL-rates-in-New-Delhi", timeout=30)
jsessionid = session.cookies.get("JSESSIONID", "")
orig_ssid = "1F47710CD4AE2F5DB09361C487D16BBD"
scriptSessionId = orig_ssid + str(randint(0, 999))
page_url = "/Property-Rates-Trends/ALL-RESIDENTIAL-rates-in-New-Delhi"

body = (
    "callCount=1\n"
    "page=" + page_url + "\n"
    "httpSessionId=" + jsessionid + "\n"
    "scriptSessionId=" + scriptSessionId + "\n"
    "c0-scriptName=ajaxService\n"
    "c0-methodName=getPropertyRates\n"
    "c0-id=0\n"
    "c0-param0=string:2624\n"
    "c0-param1=string:10002\n"
    "c0-param2=string:\n"
    "c0-param3=string:\n"
    "c0-param4=number:1\n"
    "c0-param5=number:9000\n"
    "c0-param6=boolean:false\n"
    "c0-param7=boolean:false\n"
    "batchId=0\n"
)

time.sleep(1)
r = session.post(
    "https://www.magicbricks.com/bricks/dwr/call/plaincall/ajaxService.getPropertyRates.dwr",
    headers={"Content-Type": "text/plain", "Referer": "https://www.magicbricks.com" + page_url},
    data=body,
    timeout=30,
)
text = r.text

if "//#DWR-REPLY" in text:
    text = text[text.find("//#DWR-REPLY"):]

m = re.search(r"_remoteHandleCallback\('[^']+','[^']+',\{(.+)\}\);", text, re.DOTALL)
print(f"Callback found: {m is not None}")
if not m:
    print("No callback found. Text last 500 chars:")
    print(text[-500:])
    exit()

objs = {}
arrays = {}
for line in text.split("\n"):
    line = line.strip()
    if not line or line.startswith("//"):
        continue
    if line.startswith("var ") and "=" in line:
        parts = line.split("=", 1)
        var_name = parts[0].replace("var ", "").strip()
        var_val = parts[1].strip().rstrip(";")
        if var_val.startswith("{"):
            objs[var_name] = {}
        elif var_val.startswith("["):
            arrays[var_name] = []

for line in text.split("\n"):
    line = line.strip()
    if not line:
        continue
    for part in line.split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        key, val = part.split("=", 1)
        key = key.strip()
        val = val.strip().rstrip(";")
        if val.startswith('"') and val.endswith('"'):
            val = val[1:-1]
        elif val == "null":
            val = None
        elif val == "true":
            val = True
        elif val == "false":
            val = False

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

print(f"Objs count: {len(objs)}")
print(f"Arrays count: {len(arrays)}")
print(f"s0 in arrays: {'s0' in arrays}")
if "s0" in arrays:
    print(f"s0 type: {type(arrays['s0'])}")
    print(f"s0 first 3: {arrays['s0'][:3]}")
print(f"s1 in objs: {'s1' in objs}")
if "s1" in objs:
    print(f"s1: {objs['s1']}")
print(f"s16 in arrays: {'s16' in arrays}")
if "s16" in arrays:
    print(f"s16: {arrays['s16']}")
print(f"s17 in objs: {'s17' in objs}")
if "s17" in objs:
    print(f"s17: {objs['s17']}")
print(f"s19 in objs: {'s19' in objs}")
if "s19" in objs:
    print(f"s19: {objs['s19']}")
