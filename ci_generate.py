import requests, json, os, re, time, glob

BASE = os.path.dirname(os.path.abspath(__file__))
CONTENT = f"{BASE}/content"
os.makedirs(CONTENT, exist_ok=True)

GROQ = os.environ.get("GROQ_API_KEY")
HF = os.environ.get("HF_TOKEN")
DEEPSEEK = os.environ.get("DEEPSEEK_API_KEY")
GEMINI = os.environ.get("GEMINI_API_KEY")
MODEL_GROQ = "qwen/qwen3.6-27b"
MODEL_HF = "Qwen/Qwen3-8B"
MODEL_DS = "deepseek-chat"

def groq_chat(system, user, max_tokens=4000):
    if not GROQ: return None
    for attempt in range(4):
        try:
            r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ}", "Content-Type": "application/json"},
                json={"model": MODEL_GROQ, "messages":[
                    {"role":"system","content":system},
                    {"role":"user","content":user}],
                    "temperature":0.7, "max_tokens":max_tokens}, timeout=120)
            d=r.json()
            if "choices" in d: return d["choices"][0]["message"]["content"]
            if "rate_limit" in str(d): time.sleep(20*(attempt+1)); continue
        except Exception:
            time.sleep(10)
    return None

def hf_chat(system, user):
    if not HF: return None
    url=f"https://api-inference.huggingface.co/models/{MODEL_HF}"
    hdr={"Authorization":f"Bearer {HF}", "Content-Type":"application/json"}
    payload={"inputs": f"{system}\n\n{user}", "parameters":{"max_new_tokens":1500,"return_full_text":False,"temperature":0.7}}
    for attempt in range(3):
        try:
            r=requests.post(url,headers=hdr,json=payload,timeout=120)
            if r.status_code==200:
                out=r.json()
                if isinstance(out,list) and out: return out[0].get("generated_text","")
                if isinstance(out,dict): return out.get("generated_text","")
            if r.status_code==429: time.sleep(20*(attempt+1)); continue
        except Exception:
            time.sleep(10)
    return None

def ds_chat(system, user, max_tokens=4000):
    if not DEEPSEEK: return None
    for attempt in range(4):
        try:
            r=requests.post("https://api.deepseek.com/chat/completions",
                headers={"Authorization":f"Bearer {DEEPSEEK}","Content-Type":"application/json"},
                json={"model":MODEL_DS,"messages":[{"role":"system","content":system},{"role":"user","content":user}],"temperature":0.7,"max_tokens":max_tokens},timeout=120)
            d=r.json()
            if "choices" in d: return d["choices"][0]["message"]["content"]
            if "rate_limit" in str(d): time.sleep(20*(attempt+1)); continue
        except Exception:
            time.sleep(10)
    return None

def gemini_chat(system, user, max_tokens=4000):
    if not GEMINI: return None
    # free tier often 429s; try once
    try:
        url=f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI}"
        payload={"contents":[{"parts":[{"text":f"{system}\n\n{user}"}]}],"generationConfig":{"maxOutputTokens":max_tokens,"temperature":0.7}}
        r=requests.post(url,json=payload,timeout=120)
        if r.status_code==200:
            return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        pass
    return None

def chat(system, user, max_tokens=4000):
    # Free, Grok-independent cascade: Groq -> HF -> DeepSeek -> Gemini
    for fn, name in [(groq_chat,"groq"),(hf_chat,"hf"),(ds_chat,"deepseek"),(gemini_chat,"gemini")]:
        try:
            out = fn(system, user, max_tokens) if name!="hf" else fn(system, user)
            if out: return out, name
        except Exception:
            continue
    return None, None

def extract_json(text):
    if not text: return None
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

TOPICS_EN = [
    ("Phonics vs whole language: what actually works for early readers", "phonics, whole language, teach child to read, early reading"),
    ("5-minute daily reading habit that builds lifelong readers", "reading habit, daily reading, raise a reader, reading routine"),
    ("How audiobooks help struggling readers catch up", "audiobooks for kids, struggling readers, reading fluency, listening comprehension"),
    ("Teaching life skills through stories: a homeschool approach", "life skills for kids, homeschool life lessons, social emotional learning"),
    ("Sight words made simple: a no-tears method", "sight words, high frequency words, kindergarten reading, dolch list"),
]
existing = glob.glob(f"{CONTENT}/article_en*.json")
idx = len(existing)  # next index
ti = (idx-1) % len(TOPICS_EN)
en_topic, en_kw = TOPICS_EN[ti]
print(f"Post #{idx+1}: {en_topic}")

def make_article(lang, topic, kw):
    L = "Spanish" if lang=="es" else "English"
    sys = BRAND + f"\nWrite ONLY in {L}."
    if lang=="es":
        usr = f"""Escribe un articulo de blog SEO completo y original sobre: {topic}
Palabras clave: {kw}
Devuelve SOLO JSON: {{"title":"<60 chars","meta":"<155 chars","h1":"titular","sections":[5x {{"h2":str,"body":str}}],"faq":[3x {{"q":str,"a":str}}]}}"""
    else:
        usr = f"""Write a complete, original, SEO blog article about: {topic}
Keywords: {kw}
Return ONLY JSON: {{"title":"<60 char","meta":"<155 char","h1":"headline","sections":[5x {{"h2":str,"body":str}}],"faq":[3x {{"q":str,"a":str}}]}}"""
    for attempt in range(5):
        out, src = chat(sys, usr)
        if out:
            js = extract_json(out)
            if js:
                try:
                    d=json.loads(js)
                    if is_real_article(d): return d, src
                except: pass
        time.sleep(15)
    return None, None

en_art, src1 = make_article("en", en_topic, en_kw)
if not en_art:
    print("EN failed; exit"); raise SystemExit(1)
json.dump(en_art, open(f"{CONTENT}/article_en_{idx+1}.json","w",encoding="utf-8"), ensure_ascii=False, indent=2)
print("  EN saved via", src1, ":", en_art["title"])

time.sleep(10)
# ES: translate topic then generate
es_topic_raw, _ = chat(BRAND+"\nTranslate ONLY to natural Spanish.", f"Translate to Spanish: {en_topic}")
es_topic = (es_topic_raw or en_topic).strip().strip('"')
es_art, src2 = make_article("es", es_topic, en_kw)
if not es_art:
    print("ES failed; exit"); raise SystemExit(1)
json.dump(es_art, open(f"{CONTENT}/article_es_{idx+1}.json","w",encoding="utf-8"), ensure_ascii=False, indent=2)
print("  ES saved via", src2, ":", es_art["title"])
print("DONE")
