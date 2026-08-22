"""
writer.py — Sandbox-native long-form writer for ARTISY blog.
Runs in the Hermes sandbox (has playwright + openai + requests).
Calls free LLMs (DeepSeek/Grok/Groq/OpenAI/HF) to generate full EN+ES articles.
Falls back to Playwright-driven web chat when no API key is present.
"""
import os, json, re, time, glob

ENV_PATH = "C:/abe-workspace/gumroad-audit/.env"

def load_env():
    env = {}
    try:
        for line in open(ENV_PATH, encoding="utf-8"):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    except FileNotFoundError:
        pass
    # override with process env
    for k, v in os.environ.items():
        env[k] = v
    return env

ENV = load_env()

BRAND = """You are Ting Lott, RN, homeschool mom, creator of ARTISY (artistrystore.com).
Voice: warm, practical, encouraging, no fluff. Help parents teach reading/life skills to kids.
Sell homeschool apps, reading tools, audiobooks, coloring books on Gumroad. Write REAL, specific content. Never use "..." or placeholders."""

# Backend config: (name, base_url, api_key_env, model)
BACKENDS = [
    ("deepseek", "https://api.deepseek.com/v1", "DEEPSEEK_API_KEY", "deepseek-chat"),
    ("grok",     "https://api.x.ai/v1",         "GROK_API_KEY",     "grok-3-mini"),
    ("grok2",    "https://api.x.ai/v1",         "GROK_API_KEY_2",   "grok-3-mini"),
    ("groq",     "https://api.groq.com/openai/v1", "GROQ_API_KEY", "qwen/qwen3.6-27b"),
    ("openai",   "https://api.openai.com/v1",   "OPENAI_API_KEY",   "gpt-4o-mini"),
]

def _client_call(base_url, api_key, model, system, user, max_tokens=4000):
    """OpenAI-compatible chat completion. Returns text or None."""
    if not api_key:
        return None
    from openai import OpenAI
    try:
        c = OpenAI(api_key=api_key, base_url=base_url)
        r = c.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            temperature=0.7, max_tokens=max_tokens, timeout=120)
        return r.choices[0].message.content
    except Exception as e:
        return f"__ERR__{e}"

def chat(system, user, max_tokens=4000):
    """Cascade through available backends. Returns (text, backend_name)."""
    for name, base, keyenv, model in BACKENDS:
        ak = ENV.get(keyenv)
        if not ak:
            continue
        out = _client_call(base, ak, model, system, user, max_tokens)
        if out and not out.startswith("__ERR__"):
            return out, name
        time.sleep(3)
    # Final fallback: Playwright web chat (Qwen.ai / DeepSeek web) if a browser session is available
    return None, None

def extract_json(text):
    if not text:
        return None
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    start = text.find("{")
    if start == -1:
        return None
    depth = 0; in_str = False; esc = False
    for i in range(start, len(text)):
        c = text[i]
        if in_str:
            if esc: esc = False
            elif c == "\\": esc = True
            elif c == '"': in_str = False
        else:
            if c == '"': in_str = True
            elif c == '{': depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    return text[start:i+1]
    return None

def is_real_article(d):
    if not d: return False
    if "..." in json.dumps(d).lower(): return False
    if d.get("title") in (None, "", "..."): return False
    if len(d.get("sections", [])) < 5: return False
    if len(d.get("faq", [])) < 3: return False
    return True

TOPICS = [
    ("Phonics vs whole language: what actually works for early readers", "phonics, teach child to read, early reading"),
    ("5-minute daily reading habit that builds lifelong readers", "reading habit, daily reading, raise a reader"),
    ("How audiobooks help struggling readers catch up", "audiobooks for kids, struggling readers, reading fluency"),
    ("Teaching life skills through stories: a homeschool approach", "life skills for kids, homeschool, social emotional learning"),
    ("Sight words made simple: a no-tears method", "sight words, kindergarten reading, dolch list"),
]

def next_index():
    # content dir is the repo-root "content" folder (same as build_site.py uses)
    here = os.path.dirname(os.path.abspath(__file__))
    # writer.py lives at repo root (site/), so content = site/content
    content = os.path.join(here, "content")
    os.makedirs(content, exist_ok=True)
    files = glob.glob(os.path.join(content, "article_en*.json"))
    return len(files)  # 0 -> article_en.json, 1 -> article_en_1.json, etc.

def make_article(lang, topic, kw):
    L = "Spanish" if lang == "es" else "English"
    sys = BRAND + f"\nWrite ONLY in {L}."
    if lang == "es":
        usr = f"""Escribe un articulo de blog SEO completo y original sobre: {topic}
Palabras clave: {kw}
Devuelve SOLO JSON: {{"title":"<60 chars","meta":"<155 chars","h1":"titular","sections":[5x {{"h2":str,"body":str}}],"faq":[3x {{"q":str,"a":str}}]}}"""
    else:
        usr = f"""Write a complete, original, SEO blog article about: {topic}
Keywords: {kw}
Return ONLY JSON: {{"title":"<60 char","meta":"<155 char","h1":"headline","sections":[5x {{"h2":str,"body":str}}],"faq":[3x {{"q":str,"a":str}}]}}"""
    for attempt in range(4):
        out, src = chat(sys, usr)
        if out:
            js = extract_json(out)
            if js:
                try:
                    d = json.loads(js)
                    if is_real_article(d):
                        return d, src
                except Exception:
                    pass
        time.sleep(12)
    return None, None

def generate_pair():
    idx = next_index()
    ti = idx % len(TOPICS)
    en_topic, en_kw = TOPICS[ti]
    print(f"[writer] Post #{idx+1}: {en_topic}")
    en_art, src1 = make_article("en", en_topic, en_kw)
    if not en_art:
        print("[writer] EN failed"); return None
    here = os.path.dirname(os.path.abspath(__file__))
    content = os.path.join(here, "content")
    json.dump(en_art, open(os.path.join(content, f"article_en_{idx+1}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"[writer] EN saved via {src1}: {en_art['title']}")
    time.sleep(8)
    es_topic_raw, _ = chat(BRAND + "\nTranslate ONLY to natural Spanish.", f"Translate to Spanish: {en_topic}")
    es_topic = (es_topic_raw or en_topic).strip().strip('"')
    es_art, src2 = make_article("es", es_topic, en_kw)
    if not es_art:
        print("[writer] ES failed"); return None
    json.dump(es_art, open(os.path.join(content, f"article_es_{idx+1}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"[writer] ES saved via {src2}: {es_art['title']}")
    return idx + 1

if __name__ == "__main__":
    res = generate_pair()
    print("[writer] DONE" if res is not None else "[writer] FAILED")
