# Andromed AI Company - mesin kantor (hanya library bawaan Python)
import json, os, time, random, hashlib, urllib.request, urllib.error, datetime, re

MODEL = os.environ.get("MODEL") or "gemini-3.5-flash-lite"
PAUSE = 6  # detik antar panggilan, supaya aman dari batas per menit

TEAM = {
 "abhiev": ("Abhiev", "CEO", "visi, keputusan strategis, dan arah perusahaan"),
 "meda": ("Meda", "Team Leader", "koordinasi tim, pengawasan pekerjaan, dan laporan kepada CEO"),
 "andro": ("Andro", "Market Research", "riset pasar, kompetitor, tren, dan perilaku konsumen"),
 "cacal": ("Cacal", "Business Analyst", "analisis bisnis, evaluasi performa, dan peluang pengembangan"),
 "dema": ("Dema", "Marketing Manager", "strategi pemasaran, campaign, promosi, dan brand growth"),
 "dorn": ("Dorn", "Creative Director", "konsep kreatif, arah komunikasi, dan supervisi kreativitas"),
 "faqry": ("Faqry", "Art Director", "identitas visual, estetika desain, dan arahan artistik"),
 "mering": ("Mering", "Copywriter", "tagline, campaign messaging, dan storytelling"),
 "glad": ("Glad", "Storyboard Artist", "visualisasi ide, alur cerita, dan perencanaan visual"),
}
STAGES = [
 ("andro", "Riset pasar", "Susun riset singkat: tren pasar, 3 kompetitor utama, dan perilaku konsumen sasaran. Maksimal 150 kata."),
 ("cacal", "Analisis bisnis", "Analisis peluang bisnis, risiko utama, dan 3 KPI yang layak dipantau. Maksimal 130 kata."),
 ("dema", "Strategi pemasaran", "Susun strategi: target audiens, positioning, kanal, ide campaign, dan fase promosi. Maksimal 160 kata."),
 ("dorn", "Konsep kreatif", "Tulis big idea dan arah komunikasi beserta alasannya. Maksimal 130 kata."),
 ("faqry", "Arahan visual", "Tetapkan palet warna, gaya tipografi, mood visual, dan prinsip desain. Maksimal 110 kata."),
 ("mering", "Copy dan storytelling", "Tulis tagline utama, 2 alternatif, headline, dan satu paragraf storytelling. Maksimal 110 kata."),
 ("glad", "Storyboard", "Rancang storyboard 5 adegan untuk video pendek: visual, aksi, dan teks layar. Maksimal 140 kata."),
 ("meda", "Timeline dan rencana eksekusi", "Rangkum status semua divisi untuk CEO, susun timeline 4 minggu dengan penanggung jawab, dan rencana eksekusi minggu pertama. Maksimal 160 kata."),
]

def load():
    try:
        return json.load(open("state.json", encoding="utf-8"))
    except Exception:
        return {"projects": [], "mem": {}, "xp": {}, "journal": [], "brief_hash": "", "updated": ""}

def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")

def persona(S, i):
    n, r, d = TEAM[i]
    p = (f"Kamu adalah {n}, {r} di Andromed Company, perusahaan virtual bidang creative business, marketing, "
         f"strategic development, dan brand communication (CEO: Abhiev; motto: Building Ideas. Creating Impact.). "
         f"Tanggung jawabmu: {d}. Jawab dalam bahasa Indonesia, profesional dan hangat, ringkas, tanpa markdown.")
    m = S["mem"].get(i, [])[-4:]
    if m:
        p += "\nPengalamanmu yang membuatmu makin ahli (pakai bila relevan): " + " | ".join(m)
    return p

LAST = {"p": ""}
G_KEY = os.environ.get("GEMINI_API_KEY", "")
GQ_KEY = os.environ.get("GROQ_API_KEY", "")
OR_KEY = os.environ.get("OPENROUTER_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL") or "llama-3.3-70b-versatile"
OR_MODEL = os.environ.get("OPENROUTER_MODEL") or ""
OA_KEY = os.environ.get("OPENAI_API_KEY", "")
XA_KEY = os.environ.get("XAI_API_KEY", "")
AN_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
OA_MODEL = os.environ.get("OPENAI_MODEL") or "gpt-5-mini"
XA_MODEL = os.environ.get("XAI_MODEL") or "grok-4.3"
AN_MODEL = os.environ.get("ANTHROPIC_MODEL") or "claude-haiku-5-5"
# urutan pilihan model per anggota (otomatis pindah ke berikutnya bila gagal atau kuota habis)
PREF = {"abhiev": ["anthropic", "openai"], "meda": ["anthropic", "gemini"], "andro": ["gemini", "grok"],
        "cacal": ["openai", "gemini"], "dema": ["grok", "openai"], "dorn": ["anthropic", "grok"],
        "faqry": ["gemini", "anthropic"], "mering": ["openai", "anthropic"], "glad": ["grok", "gemini"]}

def post(url, headers, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=dict(headers, **{"Content-Type": "application/json"}))
    return json.load(urllib.request.urlopen(req, timeout=90))

def call_gemini(system, prompt):
    r = post(f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent",
             {"x-goog-api-key": G_KEY},
             {"systemInstruction": {"parts": [{"text": system}]}, "contents": [{"role": "user", "parts": [{"text": prompt}]}],
              "generationConfig": {"maxOutputTokens": 700}})
    return "".join(p.get("text", "") for p in r["candidates"][0]["content"]["parts"] if not p.get("thought")).strip()

def call_compat(url, key, model, system, prompt):
    r = post(url, {"Authorization": "Bearer " + key},
             {"model": model, "max_tokens": 700, "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]})
    return r["choices"][0]["message"]["content"].strip()

def call_anthropic(system, prompt):
    r = post("https://api.anthropic.com/v1/messages", {"x-api-key": AN_KEY, "anthropic-version": "2023-06-01"},
             {"model": AN_MODEL, "max_tokens": 700, "system": system, "messages": [{"role": "user", "content": prompt}]})
    return "".join(b.get("text", "") for b in r["content"]).strip()

def available():
    a = {}
    if G_KEY: a["gemini"] = lambda s, p: call_gemini(s, p)
    if GQ_KEY: a["groq"] = lambda s, p: call_compat("https://api.groq.com/openai/v1/chat/completions", GQ_KEY, GROQ_MODEL, s, p)
    if OA_KEY: a["openai"] = lambda s, p: call_compat("https://api.openai.com/v1/chat/completions", OA_KEY, OA_MODEL, s, p)
    if XA_KEY: a["grok"] = lambda s, p: call_compat("https://api.x.ai/v1/chat/completions", XA_KEY, XA_MODEL, s, p)
    if AN_KEY: a["anthropic"] = lambda s, p: call_anthropic(s, p)
    if OR_KEY and OR_MODEL: a["openrouter"] = lambda s, p: call_compat("https://openrouter.ai/api/v1/chat/completions", OR_KEY, OR_MODEL, s, p)
    return a

def llm(system, prompt):
    av = available()
    if not av:
        raise RuntimeError("belum ada kunci API yang dipasang")
    m = re.search(r"Kamu adalah (\w+),", system)
    mid = m.group(1).lower() if m else ""
    order = [p for p in PREF.get(mid, []) if p in av] + [p for p in av if p not in PREF.get(mid, [])]
    for prov in order:
        for attempt in range(2):
            try:
                text = av[prov](system, prompt)
                time.sleep(PAUSE)
                if text:
                    LAST["p"] = prov
                    return text
            except urllib.error.HTTPError as e:
                print(prov, "HTTP", e.code, e.read()[:150])
                if e.code in (429, 500, 503) and attempt == 0:
                    time.sleep(25)
                    continue
                break
            except Exception as e:
                print(prov, "ERR", e)
                break
    raise RuntimeError("semua model gagal atau kuota habis")

def grow(S, i, note, xp):
    S["mem"].setdefault(i, []).append(note[:170])
    S["mem"][i] = S["mem"][i][-8:]
    S["xp"][i] = S["xp"].get(i, 0) + xp

def log(S, i, kind, text):
    S["journal"].insert(0, {"id": i, "t": now(), "kind": kind, "txt": text, "via": LAST["p"]})
    S["journal"] = S["journal"][:150]

def run_project(S, brief):
    ctx = "Brief proyek dari CEO Abhiev: " + brief
    stages = []
    for i, title, task in STAGES:
        text = llm(persona(S, i), f"{ctx}\n\nTugasmu sekarang: {task}")
        stages.append({"id": i, "title": title, "text": text})
        ctx += f"\n\nHasil {TEAM[i][0]} ({title}):\n{text[:900]}"
        grow(S, i, f"Proyek '{brief[:40]}': " + " ".join(text.split())[:140], 4)
    S["projects"].insert(0, {"t": now(), "brief": brief, "stages": stages})
    S["projects"] = S["projects"][:10]
    log(S, "meda", "proyek", f"Proyek selesai dikerjakan tim: {brief[:80]}")

def idle_tick(S):
    ids = list(TEAM)
    random.shuffle(ids)
    a, b, c = ids[:3]
    last = S["projects"][0]["brief"] if S["projects"] else "belum ada proyek; pikirkan tren umum di industri kreatif dan pemasaran"
    idea = llm(persona(S, a), f"Konteks: {last}.\nSaat ini CEO sedang tidak ada. Tulis satu ide atau inisiatif baru dari bidangmu (maksimal 50 kata, orang pertama), konkret dan berguna.")
    log(S, a, "ide", idea); grow(S, a, "Ide: " + idea, 3)
    reply = llm(persona(S, b), f"{TEAM[a][0]} ({TEAM[a][1]}) mengusulkan: {idea}\nTanggapi singkat sesuai bidangmu (maksimal 40 kata): dukung, kritik, atau tambahkan.")
    log(S, b, "tanggapan", f"Menanggapi {TEAM[a][0]}: {reply}"); grow(S, b, f"Berdiskusi dengan {TEAM[a][0]}: " + reply, 2)
    refl = llm(persona(S, c), f"Konteks: {last}.\nTulis satu refleksi tentang hal yang baru kamu pelajari atau ingin kamu tingkatkan (maksimal 40 kata, orang pertama).")
    log(S, c, "refleksi", refl); grow(S, c, "Refleksi: " + refl, 3)

def main():
    S = load()
    brief = open("brief.txt", encoding="utf-8").read().strip() if os.path.exists("brief.txt") else ""
    h = hashlib.sha256(brief.encode()).hexdigest()
    try:
        if brief and h != S.get("brief_hash"):
            run_project(S, brief)
            S["brief_hash"] = h
        else:
            idle_tick(S)
    except Exception as e:
        log(S, "meda", "kendala", f"Putaran kantor terhenti: {str(e)[:120]}")
    S["updated"] = now()
    json.dump(S, open("state.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

main()
