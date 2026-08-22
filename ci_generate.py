import requests, json, os, re, time, glob, random

MODEL = "qwen/qwen3.6-27b"
GROQ = os.environ.get("GROQ_API_KEY")
if not GROQ:
    raise SystemExit("GROQ_API_KEY env not set")

BASE = os.path.dirname(os.path.abspath(__file__))
CONTENT = f"{BASE}/content"
os.makedirs(CONTENT, exist_ok=True)

TOPICS_EN = [
    ("Phonics vs whole language: what actually works for early readers", "phonics, whole language, teach child to read, early reading"),
    ("5-minute daily reading habit that builds lifelong readers", "reading habit, daily reading, raise a reader, reading routine"),
    ("How audiobooks help struggling readers catch up", "audiobooks for kids, struggling readers, reading fluency, listening comprehension"),
    ("Teaching life skills through stories: a homeschool approach", "life skills for kids, homeschool life lessons, social emotional learning"),
    ("Sight words made simple: a no-tears method", "sight words, high frequency words, kindergarten reading, dolch list"),
    ("Reading comprehension questions that actually help", "comprehension questions, ask about reading, recall, inference"),
    ("How to pick the right books for your child's reading level", "reading level, book selection, lexile, guided reading"),
    ("Dyslexia-friendly reading strategies for home", "dyslexia, reading difficulty, multisensory reading, Orton-Gillingham"),
    ("Summer reading without the battle", "summer reading, prevent slide, fun reading, library challenge"),
    ("Using drawing and art to boost reading comprehension", "drawing comprehension, visual reading, art and literacy"),
]
TOPICS_ES = [(t[0], t[1]) for t in TOPICS_EN]  # we regenerate ES via translation prompt

def groq(system, user, max_tokens=4000):
    for attempt in range(8):
        r = requests.post("https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ}", "Content-Type": "application/json"},
            json={"model": MODEL, "messages":[
                {"role":"system","content":system},
                {"role":"user","content":user}],
                "temperature":0.7, "max_tokens":max_tokens}, timeout=180)
        data = r.json()
        if "choices" in data:
            return data["choices"][0]["message"]["content"]
        msg = data.get("error",{}).get("message","")
        if "rate_limit" in msg or r.status_code == 429:
            wait = 25*(attempt+1)
            print(f"  [rate-limit] retry {attempt+1} in {wait}s")
            time.sleep(wait); continue
        raise RuntimeError(f"Groq {r.status_code}: {data}")
    raise RuntimeError("rate-limited")

def extract_json(text):
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    start = text.find("{")
    if start == -1: return None
    depth=0; in_str=False; esc=False
    for i in range(start, len(text)):
        c=text[i]
        if in_str:
            if esc: esc=False
            elif c=="\\": esc=True
            elif c=='"': in_str=False
        else:
            if c=='"': in_str=True
            elif c=='{': depth+=1
            elif c=='}':
                depth-=1
                if depth==0: return text[start:i+1]
    return None

def is_real_article(d):
    if not d: return False
    s=json.dumps(d).lower()
    if "..." in s: return False
    if d.get("title") in (None,"","..."): return False
    if len(d.get("sections",[])) < 5: return False
    if len(d.get("faq",[])) < 3: return False
    return True

BRAND = """You are Ting Lott, RN, homeschool mom, creator of ARTISY (artistrystore.com).
Voice: warm, practical, encouraging, no fluff. Help parents teach reading/life skills to kids.
Sell homeschool apps, reading tools, audiobooks, coloring books on Gumroad. Write REAL, specific content. Never use "..." or placeholders."""

# pick a topic we haven't done yet
existing = [os.path.basename(f) for f in glob.glob(f"{CONTENT}/article_en*.json")]
idx = len(existing) - 1  # we have article_en.json (idx 0) and article_en_<n>.json
topic_idx = idx % len(TOPICS_EN)
en_topic, en_kw = TOPICS_EN[topic_idx]
# translate topic to Spanish
es_topic = groq(BRAND+"\nTranslate ONLY to Spanish.", f"Translate this to natural Spanish: {en_topic}")
es_topic = es_topic.strip().strip('"')

print(f"Generating post #{idx+1}: {en_topic}")

# EN article
en_art=None
for attempt in range(4):
    sys = BRAND + "\nWrite ONLY in English."
    usr = f"""Write a complete, original, SEO blog article about: {en_topic}
Keywords: {en_kw}
Return ONLY JSON (no prose):
{{"title":"<60 char SEO title","meta":"<155 char meta","h1":"headline","sections":[5x {{"h2":str,"body":str}}],"faq":[3x {{"q":str,"a":str}}]}}"""
    js = extract_json(groq(sys, usr))
    if js:
        try:
            d=json.loads(js)
            if is_real_article(d): en_art=d; break
        except: pass
    time.sleep(20)
if not en_art:
    print("EN article failed; exiting"); raise SystemExit(1)
json.dump(en_art, open(f"{CONTENT}/article_en_{idx+1}.json","w",encoding="utf-8"), ensure_ascii=False, indent=2)
print("  EN saved:", en_art["title"])

time.sleep(10)

# ES article (translate + localize)
es_art=None
for attempt in range(4):
    sys = BRAND + "\nWrite ONLY in Spanish."
    usr = f"""Escribe un articulo de blog SEO completo y original sobre: {es_topic}
Palabras clave: {en_kw}
Devuelve SOLO JSON (sin texto extra):
{{"title":"titulo SEO <60 chars","meta":"meta <155 chars","h1":"titular","sections":[5x {{"h2":str,"body":str}}],"faq":[3x {{"q":str,"a":str}}]}}"""
    js = extract_json(groq(sys, usr))
    if js:
        try:
            d=json.loads(js)
            if is_real_article(d): es_art=d; break
        except: pass
    time.sleep(20)
if not es_art:
    print("ES article failed; exiting"); raise SystemExit(1)
json.dump(es_art, open(f"{CONTENT}/article_es_{idx+1}.json","w",encoding="utf-8"), ensure_ascii=False, indent=2)
print("  ES saved:", es_art["title"])

print("DONE generating")
