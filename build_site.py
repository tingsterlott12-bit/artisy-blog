import json, os, html, re, glob

# Repo root = this script's directory (the GitHub Pages source)
ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = ROOT  # build output goes to repo root
CONTENT = f"{ROOT}/content"
os.makedirs(f"{SITE}/en", exist_ok=True)
os.makedirs(f"{SITE}/es", exist_ok=True)

STORE = "https://shop.artistrystore.com"
APP = "https://abe-reads-comprehension-jg69t2pkr-tingsterlott12-5519s-projects.vercel.app"
BLOG = "https://tingsterlott12-bit.github.io/artisy-blog"

def esc(s): return html.escape(str(s))

def slugify(s):
    s = s.lower()
    s = re.sub(r"[^a-z0-9áéíóúñü]+", "-", s)
    return s.strip("-")

def article_html(d, lang, url):
    secs = "".join(f'<section><h2>{esc(s["h2"])}</h2><p>{esc(s["body"])}</p></section>' for s in d["sections"])
    faq = "".join(f'<div class="faq"><h3>{esc(f["q"])}</h3><p>{esc(f["a"])}</p></div>' for f in d["faq"])
    return f'''<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(d["title"])}</title>
<meta name="description" content="{esc(d["meta"])}">
<link rel="canonical" href="{url}">
<link rel="alternate" hreflang="en" href="{BLOG}/en/">
<link rel="alternate" hreflang="es" href="{BLOG}/es/">
<meta property="og:type" content="article">
<meta property="og:title" content="{esc(d["title"])}">
<meta property="og:description" content="{esc(d["meta"])}">
<meta property="og:url" content="{url}">
<meta property="og:site_name" content="ARTISY by Ting Lott">
<meta property="og:locale" content="{'en_US' if lang=='en' else 'es_ES'}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(d["title"])}">
<meta name="twitter:description" content="{esc(d["meta"])}">
<style>
body{{font-family:system-ui,Arial,sans-serif;max-width:760px;margin:0 auto;padding:24px;line-height:1.6;color:#1f2937;background:#fffdf7}}
h1{{font-size:2rem;color:#b45309}} h2{{color:#92400e;margin-top:2rem}} a{{color:#b45309}}
header,footer{{text-align:center;padding:16px;background:#fff3e0;border-radius:8px;margin-bottom:24px}}
.cta{{display:inline-block;background:#b45309;color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none;margin:8px}}
.faq{{background:#fff7ed;padding:12px;border-radius:8px;margin:12px 0}}
</style>
</head>
<body>
<header>
<h1>ARTISY by Ting Lott</h1>
<p>Helping parents teach reading & life skills — homeschool apps, audiobooks, coloring books.</p>
<a class="cta" href="{STORE}">Visit the Shop</a>
<a class="cta" href="{APP}">Free Reading App</a>
</header>
<h1>{esc(d["h1"])}</h1>
{secs}
<h2>Frequently Asked Questions</h2>
{faq}
<footer>
<p>More free help at <a href="{STORE}">shop.artistrystore.com</a> · Reading practice on our <a href="{APP}">free app</a></p>
</footer>
</body></html>'''

# Discover all article pairs (en + es share a base name)
en_files = glob.glob(f"{CONTENT}/article_en*.json")
posts = []  # (en_dict, es_dict, base, en_slug, es_slug)
for ef in en_files:
    esf = ef.replace("article_en", "article_es")
    if not os.path.exists(esf):
        print(f"skip {ef} (no ES pair)"); continue
    en = json.load(open(ef, encoding="utf-8"))
    es = json.load(open(esf, encoding="utf-8"))
    en_slug = slugify(en["title"])
    es_slug = slugify(es["title"])
    open(f"{SITE}/en/{en_slug}.html","w",encoding="utf-8").write(article_html(en,"en",f"{BLOG}/en/{en_slug}.html"))
    open(f"{SITE}/es/{es_slug}.html","w",encoding="utf-8").write(article_html(es,"es",f"{BLOG}/es/{es_slug}.html"))
    posts.append((en, es, en_slug, es_slug))
    print(f"built: {en_slug} / {es_slug}")

# Homepage (lists all posts)
post_cards = ""
for en, es, en_slug, es_slug in posts:
    post_cards += f'<div class="post"><h2><a href="en/{en_slug}.html">{esc(en["title"])}</a></h2><p>{esc(en["meta"])}</p>'
    post_cards += f'<p><a href="es/{es_slug}.html">Leer en español</a></p></div>\n'
home = f'''<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ARTISY Blog — Reading & Homeschool Help by Ting Lott, RN</title>
<meta name="description" content="Free homeschool reading tips, comprehension strategies, and kids learning resources from a nurse & homeschool mom.">
<style>body{{font-family:system-ui,Arial,sans-serif;max-width:760px;margin:0 auto;padding:24px;line-height:1.6;color:#1f2937;background:#fffdf7}}h1{{color:#b45309}}a{{color:#b45309}}header,footer{{text-align:center;padding:16px;background:#fff3e0;border-radius:8px;margin-bottom:24px}}.post{{background:#fff7ed;padding:16px;border-radius:8px;margin:16px 0}}.cta{{display:inline-block;background:#b45309;color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none}}</style>
</head>
<body>
<header><h1>ARTISY Blog</h1><p>by Ting Lott, RN — homeschool mom & reading-app creator</p>
<a class="cta" href="{STORE}">Shop</a> <a class="cta" href="{APP}">Free Reading App</a></header>
{post_cards}
<footer><p>&copy; ARTISY · <a href="{STORE}">shop.artistrystore.com</a></p></footer>
</body></html>'''
open(f"{SITE}/index.html","w",encoding="utf-8").write(home)

# Sitemap (all posts)
urls = f"<url><loc>{BLOG}/</loc></url>\n"
for en, es, en_slug, es_slug in posts:
    urls += f"<url><loc>{BLOG}/en/{en_slug}.html</loc></url>\n"
    urls += f"<url><loc>{BLOG}/es/{es_slug}.html</loc></url>\n"
sitemap = f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{urls}</urlset>'''
open(f"{SITE}/sitemap.xml","w",encoding="utf-8").write(sitemap)

# robots.txt
open(f"{SITE}/robots.txt","w",encoding="utf-8").write(f"User-agent: *\nAllow: /\nSitemap: {BLOG}/sitemap.xml\n")

print(f"Built {len(posts)} post pairs + index + sitemap + robots.txt")
