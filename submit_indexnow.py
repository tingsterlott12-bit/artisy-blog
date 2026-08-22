import json, glob, requests, os

BASE = os.path.dirname(os.path.abspath(__file__))
key = open(os.path.join(BASE, "indexnow_key.txt"), encoding="utf-8").read().strip()
BLOG = "https://tingsterlott12-bit.github.io/artisy-blog"
urls = [f"{BLOG}/"]
for f in glob.glob(os.path.join(BASE, "site", "en", "*.html")):
    urls.append(f"{BLOG}/en/" + os.path.basename(f))
# include es
for f in glob.glob(os.path.join(BASE, "site", "es", "*.html")):
    urls.append(f"{BLOG}/es/" + os.path.basename(f))

payload = {"host": "tingsterlott12-bit.github.io", "key": key, "urlList": urls}
H = {"Content-Type": "application/json; charset=utf-8"}
for ep in ["https://api.indexnow.org/indexnow", "https://www.bing.com/indexnow", "https://yandex.com/indexnow"]:
    try:
        r = requests.post(ep, json=payload, headers=H, timeout=20)
        print(ep, r.status_code, r.text[:60])
    except Exception as e:
        print(ep, "err", e)
print(f"Submitted {len(urls)} URLs")
