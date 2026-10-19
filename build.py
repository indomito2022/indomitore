#!/usr/bin/env python3
"""
Generator strony indomitore.com (PL / ES / EN)

Źródła:
  1. Feed XML RedSP (nowe budowy)  -> zmienna FEED_URL albo --feed plik.xml
  2. Notion "Nieruchomości" (oferty bezpośrednie) -> NOTION_TOKEN + NOTION_DB (opcjonalnie)

Pliki w repozytorium:
  template.html   strona główna       oferta.html   podstrona oferty
  glowa.html, naglowek.html, stopka.html   wspólne części
  styl.css        wygląd               teksty.json   wszystkie teksty w 3 językach
  wyroznione.txt  oferty wyróżnione

Wynik (folder dist/):
  index.html, es/index.html, en/index.html          strony główne
  oferta/<REF>/, es/propiedad/<REF>/, en/property/<REF>/   podstrony ofert
  404.html, sitemap.xml, robots.txt, CNAME, styl.css, favicon, logo, wideo, portret
  img/                zdjęcia ofert z Notion (pobierane, bo linki Notion wygasają)

Uruchomienie:
  python3 build.py                       # pobiera feed z FEED_URL
  python3 build.py --feed feed.xml       # z pliku
  python3 build.py --sample sample.json  # podgląd lokalny z próbki
Tylko biblioteka standardowa Pythona.
"""
import argparse, html, json, os, re, shutil, sys, urllib.parse, urllib.request, xml.etree.ElementTree as ET
import seo  # podstrony SEO po polsku (seo.py)
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
FEED_URL = os.environ.get("FEED_URL", "")  # ustawiany jako sekret FEED_URL w GitHub
DOMAIN = os.environ.get("SITE_DOMAIN", "indomitore.com")
SITE = f"https://{DOMAIN}/"
WA = "34613152755"

LANGS = ["pl", "es", "en"]
FALLBACK = {"pl": ["pl", "en", "es"], "es": ["es", "en", "pl"], "en": ["en", "es", "pl"]}
HOME = {"pl": "", "es": "es/", "en": "en/"}
OFFER_DIR = {"pl": "oferta/", "es": "es/propiedad/", "en": "en/property/"}
PRIVACY = {"pl": "polityka-prywatnosci/", "es": "es/privacidad/", "en": "en/privacy/"}
FORM_ENDPOINT = os.environ.get("FORM_ENDPOINT", "https://indomito-formularz.klaudia-304.workers.dev/")  # Cloudflare → Notion
T = json.load(open(os.path.join(ROOT, "teksty.json"), encoding="utf-8"))
FLAGS = {  # flagi w przełączniku języka (proste SVG, bez plików)
    "pl": '<svg class="flag" viewBox="0 0 30 20" aria-hidden="true"><rect width="30" height="10" fill="#fff"/><rect y="10" width="30" height="10" fill="#DC143C"/></svg>',
    "es": '<svg class="flag" viewBox="0 0 30 20" aria-hidden="true"><rect width="30" height="20" fill="#AA151B"/><rect y="5" width="30" height="10" fill="#F1BF00"/></svg>',
    "en": '<svg class="flag" viewBox="0 0 60 40" preserveAspectRatio="xMidYMid slice" aria-hidden="true"><clipPath id="ukc"><rect width="60" height="40"/></clipPath>'
          '<g clip-path="url(#ukc)"><rect width="60" height="40" fill="#012169"/><path d="M0,0 60,40M60,0 0,40" stroke="#fff" stroke-width="8"/>'
          '<path d="M0,0 60,40M60,0 0,40" stroke="#C8102E" stroke-width="3"/><path d="M30,0v40M0,20h60" stroke="#fff" stroke-width="12"/>'
          '<path d="M30,0v40M0,20h60" stroke="#C8102E" stroke-width="7"/></g></svg>',
}

KIND = {  # typ z feedu -> grupa do filtra: apt = apartamenty, house = domy, villa = wille
    "Apartment": "apt", "Penthouse": "apt", "Studio": "apt", "Bungalow": "apt", "Duplex": "apt",
    "Town House": "house", "Quad House": "house", "Semi-Detached House": "house", "Villa": "villa",
}


def kind_pl(t):
    """Grupa dla typów z Notion (po polsku)."""
    t = (t or "").lower()
    if "will" in t: return "villa"
    if any(x in t for x in ("dom", "bliźn", "szereg", "quad")): return "house"
    return "apt"


NOTION_TYPES = {  # typ z Notion (pl) -> (pl, es, en)
    "Apartament": ("Apartament", "Apartamento", "Apartment"), "Penthouse": ("Penthouse", "Ático", "Penthouse"),
    "Bungalow": ("Bungalow", "Bungalow", "Bungalow"), "Szeregowiec": ("Dom szeregowy", "Adosado", "Townhouse"),
    "Willa": ("Willa", "Villa", "Villa"), "Działka": ("Działka", "Parcela", "Plot"), "Lokal": ("Lokal", "Local", "Commercial unit"),
}
NOTION_AMEN = {  # udogodnienie z Notion (pl) -> (pl, es, en)
    "Basen prywatny": ("Basen prywatny", "Piscina privada", "Private pool"),
    "Basen wspólny": ("Basen wspólny", "Piscina comunitaria", "Communal pool"),
    "Widok na morze": ("Widok na morze", "Vistas al mar", "Sea views"),
    "Blisko plaży": ("Blisko plaży", "Cerca de la playa", "Close to the beach"),
    "Taras / solarium": ("Taras / solarium", "Terraza / solárium", "Terrace / solarium"),
    "Ogród": ("Ogród", "Jardín", "Garden"), "Garaż / parking": ("Garaż / parking", "Garaje / parking", "Garage / parking"),
    "Klimatyzacja": ("Klimatyzacja", "Aire acondicionado", "Air conditioning"),
    "Pole golfowe": ("Blisko pola golfowego", "Cerca del golf", "Near golf"),
}
MARKET = {"Nowe": "new", "Wtórne": "resale", "Najem": "rent"}  # pole „Rynek” w Notion


TYPES = {  # typ z feedu -> (pl, es, en)
    "Villa": ("Willa", "Villa", "Villa"), "Apartment": ("Apartament", "Apartamento", "Apartment"),
    "Penthouse": ("Penthouse", "Ático", "Penthouse"), "Bungalow": ("Bungalow", "Bungalow", "Bungalow"),
    "Town House": ("Dom szeregowy", "Adosado", "Townhouse"), "Quad House": ("Dom typu quad", "Quad", "Quad house"),
    "Semi-Detached House": ("Bliźniak", "Pareado", "Semi-detached house"), "Duplex": ("Dupleks", "Dúplex", "Duplex"),
    "Studio": ("Studio", "Estudio", "Studio"),
}
REGION = {  # costa z feedu -> (grupa, w głębi lądu?)
    "Costa Blanca North": ("cbn", False), "Costa Blanca North - Inland": ("cbn", True),
    "Costa Blanca South": ("cbs", False), "Costa Blanca South - Inland": ("cbs", True),
    "Costa Calida": ("cc", False), "Costa Calida - Inland": ("cc", True),
}
FEATS = {  # cecha z feedu -> (pl, es, en)
    "Gated": ("Osiedle zamknięte", "Urbanización cerrada", "Gated community"),
    "Parking - Space": ("Miejsce parkingowe", "Plaza de aparcamiento", "Parking space"),
    "Near Schools": ("Blisko szkół", "Cerca de colegios", "Near schools"),
    "Garden": ("Ogród", "Jardín", "Garden"),
    "Communal Pool": ("Basen wspólny", "Piscina comunitaria", "Communal pool"),
    "Private Pool": ("Basen prywatny", "Piscina privada", "Private pool"),
    "Elevator/Lift": ("Winda", "Ascensor", "Lift"),
    "Near Commercial Center": ("Blisko centrum handlowego", "Cerca de centro comercial", "Near shopping centre"),
    "Solarium: Yes": ("Solarium", "Solárium", "Solarium"),
    "Near Bus Route": ("Blisko przystanku", "Cerca de parada de autobús", "Near bus route"),
    "Near Golf / Golf Resort Property": ("Blisko pola golfowego", "Cerca de golf", "Near golf"),
    "Furnished": ("Umeblowane", "Amueblado", "Furnished"),
    "Near Childrens Parks": ("Blisko placu zabaw", "Cerca de parques infantiles", "Near playgrounds"),
    "Views: Sea": ("Widok na morze", "Vistas al mar", "Sea views"),
    "Views: Mountain": ("Widok na góry", "Vistas a la montaña", "Mountain views"),
    "Key Ready": ("Gotowe do odbioru kluczy", "Llave en mano", "Key ready"),
    "BBQ": ("Grill", "Barbacoa", "BBQ"),
    "Licensed Tourist Property": ("Licencja turystyczna", "Licencia turística", "Tourist licence"),
    "Near Train Station": ("Blisko dworca", "Cerca de estación de tren", "Near train station"),
    "Air Conditioning": ("Klimatyzacja", "Aire acondicionado", "Air conditioning"),
    "Air Conditioning: Pre-Installed": ("Instalacja pod klimatyzację", "Preinstalación de aire acondicionado", "Air conditioning pre-installed"),
    "Underfloor Heating": ("Ogrzewanie podłogowe", "Suelo radiante", "Underfloor heating"),
    "Storage Room": ("Komórka lokatorska", "Trastero", "Storage room"),
    "Garage": ("Garaż", "Garaje", "Garage"), "Basement": ("Piwnica", "Sótano", "Basement"),
    "Jacuzzi": ("Jacuzzi", "Jacuzzi", "Jacuzzi"), "Gym": ("Siłownia", "Gimnasio", "Gym"), "Spa": ("Spa", "Spa", "Spa"),
    "Domotics": ("Inteligentny dom", "Domótica", "Smart home"), "Patio": ("Patio", "Patio", "Patio"),
}
LOC = {"Rural": ("wiejska", "rural", "rural"), "Urbanisation": ("osiedle", "urbanización", "urbanisation"),
       "Coastal": ("nadmorska", "costera", "coastal"), "Town": ("miejska", "ciudad", "town"), "Village": ("wieś", "pueblo", "village")}
RX = [  # cechy z liczbą
    (r"Terrace: (\d+) Msq", ("Taras {0} m²", "Terraza de {0} m²", "Terrace {0} m²")),
    (r"Number of Parking Spaces: (\d+)", ("Miejsca parkingowe: {0}", "Plazas de aparcamiento: {0}", "Parking spaces: {0}")),
    (r"Useable Build Space: (\d+) Msq", ("Powierzchnia użytkowa {0} m²", "Superficie útil {0} m²", "Usable area {0} m²")),
    (r"Double Bedrooms: (\d+)", ("Sypialnie dwuosobowe: {0}", "Dormitorios dobles: {0}", "Double bedrooms: {0}")),
]


def feat_tr(f):
    """Cecha z feedu -> {pl, es, en} albo None."""
    f = f.strip()
    if f in FEATS:
        return dict(zip(LANGS, FEATS[f]))
    for rx, outs in RX:
        m = re.match(rx, f)
        if m:
            return dict(zip(LANGS, (o.format(m.group(1)) for o in outs)))
    m = re.match(r"Location: (.+)", f)
    if m:
        parts = [x.strip() for x in m.group(1).split(",")]
        heads = ("Lokalizacja", "Ubicación", "Location")
        return {l: f"{heads[i]}: " + ", ".join(LOC.get(x, (x, x, x))[i] for x in parts) for i, l in enumerate(LANGS)}
    if f.startswith("Beach:") or f in ("Space", ""):
        return None  # odległość do plaży pokazujemy osobno
    return {l: f for l in LANGS}


def clean_desc(s):
    s = html.unescape(s or "").replace("\r\n", "\n").replace("\r", "\n")
    paras = [re.sub(r"[ \t]+", " ", p).strip() for p in re.split(r"\n+", s)]
    return [p for p in paras if p]


def by_lang(d, lang):
    for l in FALLBACK[lang]:
        if d.get(l):
            return d[l]
    return next((v for v in d.values() if v), "")


def as_langs(v):
    return v if isinstance(v, dict) else {"pl": v or ""}


def norm(rec, source="redsp"):
    """Wspólny format oferty; teksty jako słowniki {pl, es, en}."""
    grp, inland = REGION.get(rec.get("c", ""), ("inne", False))
    feats, seen = [], set()
    for f in rec.get("f", []):
        t = feat_tr(f)
        if t and t["en"] not in seen:
            seen.add(t["en"]); feats.append(t)
    pool = bool(rec.get("po")) or any("pool" in f["en"].lower() for f in feats)
    tr = TYPES.get(rec.get("t", ""))
    return {
        "ref": rec["r"], "src": source, "market": "new", "price": int(float(rec.get("p") or 0)),
        "type": dict(zip(LANGS, tr)) if tr else {l: rec.get("t", "") for l in LANGS},
        "town": rec.get("tw", ""), "area": rec.get("l", ""), "grp": grp, "inland": inland, "costa": rec.get("c", ""),
        "beds": int(rec.get("b") or 0), "baths": int(rec.get("ba") or 0),
        "m2": int(float(rec.get("m") or 0)), "plot": int(float(rec.get("pl") or 0)), "beach": int(float(rec.get("be") or 0)),
        "pool": pool, "lat": rec.get("la"), "lng": rec.get("ln"),
        "kind": KIND.get(rec.get("t", ""), "apt"),
        "tour": any(f["en"] == "Tourist licence" for f in feats),
        "golf": any(f["en"] == "Near golf" for f in feats),
        "sea": any(f["en"] == "Sea views" for f in feats),
        "title": {l: html.unescape(v).strip() for l, v in as_langs(rec.get("ti")).items()},
        "desc": {l: clean_desc(v) for l, v in as_langs(rec.get("d")).items()},
        "feats": feats, "imgs": rec.get("i", []),
    }


def parse_feed(path):
    out, have = [], {l: 0 for l in LANGS}
    def g(p, tag):
        e = p.find(tag); return (e.text or "").strip() if e is not None and e.text else ""
    for _, el in ET.iterparse(path, events=("end",)):
        if el.tag != "property": continue
        p = el
        rec = {
            "r": g(p, "ref"), "p": g(p, "price"), "t": g(p, "type"), "tw": g(p, "town"), "c": g(p, "costa"),
            "l": g(p, "location_detail"), "b": g(p, "beds"), "ba": g(p, "baths"), "po": g(p, "pool") == "1",
            "m": g(p, "surface_area/built"), "pl": g(p, "surface_area/plot"), "be": g(p, "distance_to_beach_m"),
            "la": float(g(p, "location/latitude") or 0) or None, "ln": float(g(p, "location/longitude") or 0) or None,
            "ti": {l: g(p, f"title/{l}") for l in LANGS}, "d": {l: g(p, f"desc/{l}") for l in LANGS},
            "f": [(f.text or "").strip() for f in p.findall("features/feature")],
            "i": [(u.text or "").strip() for u in p.findall("images/image/url")],
        }
        if rec["r"] and rec["i"] and rec["p"]:
            for l in LANGS:
                have[l] += bool(rec["d"][l])
            out.append(norm(rec))
        el.clear()
    print("Opisy w feedzie: " + ", ".join(f"{l.upper()} {n}" for l, n in have.items()))
    print(f"Licencja turystyczna: {sum(p['tour'] for p in out)}, golf w pobliżu: {sum(p['golf'] for p in out)}, widok na morze: {sum(p['sea'] for p in out)}, "
          f"apartamenty/domy/wille: {sum(p['kind']=='apt' for p in out)}/{sum(p['kind']=='house' for p in out)}/{sum(p['kind']=='villa' for p in out)}")
    return out


# ---------- Notion (oferty bezpośrednie) ----------
def notion_req(url, token, body=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"},
        method="POST" if body is not None else "GET")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def fetch_notion(token, db_id, dist):
    """Oferty z bazy Nieruchomości: Źródło = Moja oferta bezpośrednia, Status = Dostępna/Zarezerwowana."""
    flt = {"and": [
        {"property": "Źródło", "select": {"equals": "Moja oferta bezpośrednia"}},
        {"or": [{"property": "Status", "status": {"equals": "Dostępna"}},
                {"property": "Status", "status": {"equals": "Zarezerwowana"}}]},
    ]}
    res, cursor = [], None
    while True:
        body = {"filter": flt, "page_size": 100}
        if cursor: body["start_cursor"] = cursor
        data = notion_req(f"https://api.notion.com/v1/databases/{db_id}/query", token, body)
        res += data["results"]
        if not data.get("has_more"): break
        cursor = data["next_cursor"]
    os.makedirs(os.path.join(dist, "img"), exist_ok=True)
    out = []
    for pg in res:
        pr = pg["properties"]
        txt = lambda k: "".join(t["plain_text"] for t in (pr.get(k, {}).get("rich_text") or pr.get(k, {}).get("title") or []))
        num = lambda k: pr.get(k, {}).get("number") or 0
        sel = lambda k: (pr.get(k, {}).get("select") or {}).get("name", "")
        ref = f"IND-{pr.get('Ref', {}).get('unique_id', {}).get('number', pg['id'][:6])}"
        imgs = []
        for i, f in enumerate((pr.get("Zdjęcia", {}).get("files") or [])[:30]):
            src = (f.get("file") or f.get("external") or {}).get("url")
            if not src: continue
            if f.get("external"):
                imgs.append(src); continue
            ext = os.path.splitext(src.split("?")[0])[1] or ".jpg"
            name = f"img/{ref}-{i+1}{ext}"
            try:
                urllib.request.urlretrieve(src, os.path.join(dist, name)); imgs.append(name)
            except Exception as e:
                print("  ! zdjęcie", ref, e, file=sys.stderr)
        if not imgs:  # zdjęcia jako linki (jeden w linii), np. z MLS Costa
            imgs = [u.strip() for u in re.split(r"[\s,]+", txt("Zdjęcia – linki")) if re.match(r"https?://", u.strip())][:30]
        grp = {"Costa Blanca Norte": "cbn", "Costa Blanca Sur": "cbs", "Costa Cálida": "cc"}.get(sel("Region"), "inne")
        amen = [o["name"] for o in (pr.get("Udogodnienia", {}).get("multi_select") or [])]
        if not imgs: continue
        out.append({
            "ref": ref, "src": "indomito", "market": MARKET.get(sel("Rynek"), "resale"), "price": int(num("Cena")),
            "type": dict(zip(LANGS, NOTION_TYPES.get(sel("Typ"), (sel("Typ"),) * 3))),
            # „Okolica” (np. Sierra Cortina) pokazujemy jako lokalizację, a miejscowość (Finestrat) obok
            "town": txt("Okolica").strip() or sel("Miejscowość"),
            "area": sel("Miejscowość") if txt("Okolica").strip() else "", "grp": grp, "inland": False, "costa": sel("Region"),
            "beds": int(num("Sypialnie")), "baths": int(num("Łazienki")), "m2": int(num("Metraż m²")), "plot": 0,
            "beach": 0, "pool": any("Basen" in a for a in amen), "lat": None, "lng": None,
            "title": {"pl": txt("Nazwa"), "es": txt("Nazwa ES"), "en": txt("Nazwa EN")},
            "desc": {"pl": clean_desc(txt("Opis")), "es": clean_desc(txt("Opis ES")), "en": clean_desc(txt("Opis EN"))},
            "feats": [dict(zip(LANGS, NOTION_AMEN.get(a, (a,) * 3))) for a in amen], "imgs": imgs, "kind": kind_pl(sel("Typ")),
            "tour": any("turyst" in a.lower() for a in amen), "golf": any("golf" in a.lower() for a in amen),
            "sea": any("morze" in a.lower() or "widok na morze" in a.lower() for a in amen),
            "reserved": (pr.get("Status", {}).get("status") or {}).get("name") == "Zarezerwowana",
            "featured": bool(pr.get("Wyróżniona", {}).get("checkbox")),
            "excl": bool(pr.get("Na wyłączność", {}).get("checkbox")),
        })
    return out


# ---------- oferty wyróżnione ----------
FEATURED_MAX = 6


def read_featured_refs():
    """wyroznione.txt: jeden numer oferty (REF) w linii, kolejność = kolejność na stronie. # = komentarz."""
    path = os.path.join(ROOT, "wyroznione.txt")
    if not os.path.exists(path):
        return []
    refs = []
    for line in open(path, encoding="utf-8"):
        line = line.split("#", 1)[0].strip()
        if line and line not in refs:
            refs.append(line)
    return refs


def pick_featured(props):
    """Tylko prawdziwe oferty: 1) wyroznione.txt, 2) oferty z Notion (zaznaczone „Wyróżniona” albo wszystkie),
    3) gdy brakuje: najnowsze z basenem do 1 km od plaży, z dużą liczbą zdjęć, każda z innej miejscowości."""
    by_ref = {p["ref"]: p for p in props}
    chosen = []
    def add(p):
        if p and p not in chosen and len(chosen) < FEATURED_MAX:
            chosen.append(p)
    for ref in read_featured_refs():
        if ref not in by_ref:
            print(f"  ! wyroznione.txt: brak oferty {ref} w feedzie (pomijam)", file=sys.stderr)
        add(by_ref.get(ref))
    own = [p for p in props if p["src"] == "indomito" and not p.get("reserved")]
    for p in [p for p in own if p.get("featured")] or own:
        add(p)
    if len(chosen) < 3:
        towns = {p["town"] for p in chosen}
        for p in props:
            if len(chosen) >= FEATURED_MAX: break
            if p["src"] == "redsp" and p["pool"] and 0 < p["beach"] <= 1000 and len(p["imgs"]) >= 12 \
                    and p["price"] and p["town"] not in towns:
                add(p); towns.add(p["town"])
    for i, p in enumerate(chosen, 1):
        p["feat"] = i
    return chosen


# ---------- formatowanie ----------
def nf(n, lang):
    s = f"{n:,}"
    if lang == "pl": return s.replace(",", " ")
    if lang == "es": return s.replace(",", ".")
    return s


def fmt_price(p, lang):
    if not p: return T[lang]["js"]["price_req"]
    return f"€{nf(p, lang)}" if lang == "en" else f"{nf(p, lang)} €"


def fmt_beach(m, lang):
    if not m: return ""
    j = T[lang]["js"]
    if m < 1000: return j["beach_m"].replace("{n}", str(m))
    km = f"{m/1000:.1f}".rstrip("0").rstrip(".")
    return j["beach_km"].replace("{n}", km.replace(".", ",") if lang != "en" else km)


def region_label(p, lang):
    if p["grp"] == "inne": return p.get("costa", "")
    s = T[lang]["reg_" + p["grp"]]
    return f"{s} · {T[lang]['reg_inland']}" if p.get("inland") else s


def headline_count(n):
    """Liczba do nagłówka „Ponad … ofert”: zaokrąglona w dół, nigdy zawyżona."""
    if n >= 1000: return f"{n // 1000 * 1000}"
    if n >= 100: return f"{n // 100 * 100}"
    return str(n)


def safe_ref(ref):
    return re.sub(r"[^\w.-]", "_", ref)


def offer_path(lang, ref):
    return f"{OFFER_DIR[lang]}{safe_ref(ref)}/"


def base_of(page):
    return "../" * page.count("/")


def link(page, target):
    return (base_of(page) + target) or "./"


def src(u, base):
    return u if re.match(r"https?://", u) else base + u


def wa_link(text):
    return f"https://wa.me/{WA}?text={urllib.parse.quote(text)}"


E = lambda s: html.escape(str(s or ""), quote=True)


def render(tpl, ctx):
    def rep(m):
        k = m.group(1)
        if k not in ctx:
            raise KeyError(f"Brak tekstu „{k}”")
        return str(ctx[k])
    return re.sub(r"\{\{(\w+)\}\}", rep, tpl)


def read(name):
    return open(os.path.join(ROOT, name), encoding="utf-8").read()


# ---------- części strony ----------
def common_ctx(lang, page, paths, extra_wa, stats, ver):
    """Wspólny kontekst: teksty języka, linki, przełącznik języka, nagłówek, stopka."""
    base = base_of(page) if page is not None else "/"
    ctx = {k: v for k, v in T[lang].items() if isinstance(v, str)}
    home = (base + HOME[lang]) or "./"
    langs = []
    for l in LANGS:
        href = (base + paths[l]) or "./"
        cur = ' aria-current="true"' if l == lang else ""
        langs.append(f'<a href="{E(href)}" hreflang="{l}" lang="{l}" title="{E(T[l]["lang_name"])}"{cur}>'
                     f'{FLAGS[l]}<span class="lc">{l.upper()}</span></a>')
    alts = "\n".join(f'<link rel="alternate" hreflang="{l}" href="{SITE}{paths[l]}">' for l in LANGS)
    alts += f'\n<link rel="alternate" hreflang="x-default" href="{SITE}{paths["pl"]}">'
    ctx.update({
        "lang": lang, "base": base, "home": home, "ver": ver, "year": datetime.now().year,
        "langs": "".join(langs), "alternates": alts,
        "canonical": SITE + paths[lang], "wa_link": E(wa_link(extra_wa)),
        "footer_offers": T[lang]["footer_offers"].replace("{d}", stats["updated"]),
        "privacy_url": base + PRIVACY[lang],
        "seo_footer": seo.footer_links(base) if lang == "pl" else "",
        "nav_extra": f'<a href="{base}{seo.GUIDE}">Poradnik</a>' if lang == "pl" and seo.GUIDE_ON else "",
    })
    j = T[lang]["js"]
    ctx["form_cfg"] = json.dumps({"lang": lang, "endpoint": FORM_ENDPOINT, "sending": j["f_sending"], "ok": j["f_ok"],
                                  "err": j["f_err"], "err_consent": j["f_err_consent"], "err_missing": j["form_err"],
                                  "err_email": j["f_err_email"], "err_phone": j["f_err_phone"],
                                  "nl_ok": j["nl_ok"], "nl_err_consent": j["nl_err_consent"]},
                                 ensure_ascii=False).replace("</", "<\\/")
    ctx["HEAD"] = render(read("glowa.html"), ctx)
    ctx["HEADER"] = render(read("naglowek.html"), ctx)
    ctx["FOOTER"] = render(read("stopka.html"), ctx)
    return ctx


def card_html(p, lang, base, eager=False):
    """Karta oferty w HTML (tak jak w JS na stronie głównej)."""
    j = T[lang]["js"]
    if p["src"] == "indomito":
        left = f'<span class="tag own{" excl" if p.get("excl") and not p.get("reserved") else ""}">{E(j["tag_res"] if p.get("reserved") else j["tag_excl"] if p.get("excl") else j["tag_own"])}</span>'
    elif p.get("market") == "resale":
        left = f'<span class="tag dark">{E(j["tag_resale"])}</span>'
    elif 0 < p["beach"] <= 1000:
        left = f'<span class="tag dark">{E(j["tag_beach"])}</span>'
    else:
        left = f'<span class="tag dark">{E(j["tag_new"])}</span>'
    right = "".join(f'<span class="tag">{E(j[k])}</span>' for k, on in (("tag_sea", p.get("sea")), ("tag_pool", p["pool"])) if on)
    right = f'<span class="tags-r">{right}</span>'
    params = "".join(x for x in (
        f'<span><b class="num">{p["beds"]}</b> {E(j["beds_short"])}</span>' if p["beds"] else "",
        f'<span><b class="num">{p["baths"]}</b> {E(j["baths_short"])}</span>' if p["baths"] else "",
        f'<span><b class="num">{p["m2"]}</b> m²</span>' if p["m2"] else ""))
    loc = f'{p["town"]} · {by_lang(p["type"], lang)}' + (f' · {fmt_beach(p["beach"], lang)}' if p["beach"] else "")
    return (f'<a class="card" href="{E(base + offer_path(lang, p["ref"]))}">'
            f'<div class="ph"><img src="{E(src(p["imgs"][0], base))}" alt="{E(by_lang(p["title"], lang) or p["town"])}" loading="{"eager" if eager else "lazy"}" decoding="async" referrerpolicy="no-referrer">'
            f'<div class="tags">{left}{right}</div><span class="n">{len(p["imgs"])} {E(j["photos"])}</span></div>'
            f'<div class="cb"><div class="loc">{E(loc)}</div><div class="ttl">{E(by_lang(p["title"], lang))}</div>'
            f'<div class="c-foot"><span class="price num">{E(fmt_price(p["price"], lang))}</span>'
            + (f'<span class="params">{params}</span>' if params else "") + '</div></div></a>')


def similar(p, props, k=3):
    """Podobne oferty: ten sam region, najpierw ta sama miejscowość, najbliższa cena."""
    pool = [q for q in props if q is not p and q["grp"] == p["grp"] and q["price"]]
    price = p["price"] or 1
    pool.sort(key=lambda q: (q["town"] != p["town"], abs(q["price"] - price) / price))
    out, titles = [], set()
    for q in pool:
        t = by_lang(q["title"], "pl")
        if t in titles: continue  # bez kilku wariantów tej samej inwestycji
        titles.add(t); out.append(q)
        if len(out) >= k: break
    return out


def offer_page(p, lang, props, stats, ver, tpl):
    paths = {l: offer_path(l, p["ref"]) for l in LANGS}
    page = paths[lang]
    t, j = T[lang], T[lang]["js"]
    title = by_lang(p["title"], lang) or f'{by_lang(p["type"], lang)} {p["town"]}'
    price = fmt_price(p["price"], lang)
    msg = t["o_wa"].format(ref=p["ref"], title=title, town=p["town"], price=price)
    ctx = common_ctx(lang, page, paths, msg, stats, ver)
    base = ctx["base"]
    region = region_label(p, lang)
    desc = by_lang(p["desc"], lang)
    beach = fmt_beach(p["beach"], lang)
    beach_short = re.sub(r"\s*(do plaży|de la playa|to the beach)$", "", beach)
    town_full = p["town"] + (f', {p["area"]}' if p.get("area") and p["area"] != p["town"] else "")
    specs = [(t["sp_beds"], p["beds"] or "", 1), (t["sp_baths"], p["baths"] or "", 1),
             (t["sp_area"], f'{p["m2"]} m²' if p["m2"] else "", 1),
             (t["sp_plot"], f'{p["plot"]} m²', 1) if p["plot"] else (t["sp_beach"], beach_short, 1),
             (t["sp_type"], by_lang(p["type"], lang), 0), (t["sp_market"], t["mk_" + p.get("market", "new")], 0),
             (t["sp_town"], town_full, 0),
             (t["sp_region"], region, 0), (t["sp_beach"], beach_short, 0) if p["plot"] else ("", "", 0)]
    specs_html = "".join(f'<li class="{"k" if big else ""}"><span>{E(k)}</span><b class="{"num" if big else ""}">{E(v)}</b></li>'
                         for k, v, big in specs if v not in ("", None))
    imgs = p["imgs"]
    n = len(imgs)
    show = imgs[:5] if n >= 5 else imgs[:1]
    mosaic = "".join(f'<button type="button" data-open="{i}" aria-label="{E(t["o_photo"].format(i=i+1, n=n))}">'
                     f'<img src="{E(src(u, base))}" alt="{E(title)} – {E(t["o_photo"].format(i=i+1, n=n))}" loading="{"eager" if i == 0 else "lazy"}" referrerpolicy="no-referrer"></button>'
                     for i, u in enumerate(show))
    mosaic += f'<button type="button" class="all" data-open="0">{E(t["o_photos"])} ({n})</button>'
    lb = "".join(f'<figure><img data-src="{E(src(u, base))}" alt="{E(t["o_photo"].format(i=i+1, n=n))}" referrerpolicy="no-referrer"></figure>'
                 for i, u in enumerate(imgs))
    desc_block = (f'<h2>{E(t["o_desc"])}</h2><div class="desc">' + "".join(f"<p>{E(x)}</p>" for x in desc) + "</div>") if desc else ""
    feats = [by_lang(f, lang) for f in p["feats"]]
    feats_block = (f'<h2>{E(t["o_feats"])}</h2><ul class="chips">' + "".join(f"<li>{E(f)}</li>" for f in feats) + "</ul>") if feats else ""
    map_block = ""
    if p.get("lat") and p.get("lng"):
        q = f'{p["lat"]:.5f},{p["lng"]:.5f}'
        map_block = (f'<h2>{E(t["o_loc"])}</h2><div class="map"><iframe src="https://maps.google.com/maps?q={q}&amp;z=13&amp;hl={lang}&amp;output=embed" '
                     f'loading="lazy" title="{E(t["o_loc"])}" referrerpolicy="no-referrer-when-downgrade"></iframe></div>'
                     f'<a class="maplink" href="https://www.google.com/maps?q={q}" target="_blank" rel="noopener">{E(t["o_map_link"])}</a>')
    sim = similar(p, props)
    similar_block = (f'<section class="similar"><h2>{E(t["o_similar"])}</h2><div class="grid">'
                     + "".join(card_html(q, lang, base) for q in sim) + "</div></section>") if sim else ""
    meta = (" ".join(desc)[:155].rsplit(" ", 1)[0] + "…") if desc else f"{title}, {p['town']}, {region}."
    ctx.update({
        "o_title": E(title), "o_price": E(price), "o_refno": E(p["ref"]), "o_region": E(region), "o_town": E(p["town"]),
        "o_loc": E(f'{town_full} · {region}' + (f" · {beach}" if beach else "")),
        "o_meta": E(meta), "o_img": E(imgs[0] if re.match(r"https?://", imgs[0]) else SITE + imgs[0]),
        "o_nphotos": E(f'{n} {j["photos"]}'), "o_wa": E(wa_link(msg)),
        "o_mail_subj": urllib.parse.quote(f'{t["o_ref"]} {p["ref"]}'),
        "o_badge": f'<span class="tag own excl op-badge">{E(j["tag_excl"])}</span>' if p.get("excl") else "",
        "mosaic": mosaic, "mosaic_cls": "" if n >= 5 else " few", "lb_imgs": lb, "specs": specs_html,
        "desc_block": desc_block, "feats_block": feats_block, "map_block": map_block, "similar_block": similar_block,
    })
    out = render(tpl, ctx)
    ld = [{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
              {"@type": "ListItem", "position": 1, "name": "Indómito", "item": SITE + HOME[lang]},
              {"@type": "ListItem", "position": 2, "name": region, "item": SITE + HOME[lang] + "#oferty"},
              {"@type": "ListItem", "position": 3, "name": title, "item": SITE + page}]},
          {"@context": "https://schema.org", "@type": "RealEstateListing", "name": title, "url": SITE + page,
           "description": meta, "inLanguage": lang,
           "image": [u if re.match(r"https?://", u) else SITE + u for u in imgs[:6]],
           "offers": {"@type": "Offer", "price": p["price"], "priceCurrency": "EUR", "availability": "https://schema.org/InStock"},
           "about": {"@type": "Accommodation", "numberOfBedrooms": p["beds"] or None, "numberOfBathroomsTotal": p["baths"] or None,
                     "floorSize": {"@type": "QuantitativeValue", "value": p["m2"], "unitCode": "MTK"} if p["m2"] else None,
                     "address": {"@type": "PostalAddress", "addressLocality": p.get("area") or p["town"], "addressRegion": region, "addressCountry": "ES"}}}]
    def prune(o):
        if isinstance(o, dict): return {k: prune(v) for k, v in o.items() if v is not None}
        if isinstance(o, list): return [prune(v) for v in o]
        return o
    tag = "".join('<script type="application/ld+json">' + json.dumps(prune(x), ensure_ascii=False).replace("</", "<\\/") + "</script>" for x in ld)
    out = out.replace("</head>", tag + "</head>", 1)
    return page, out


def summary(p, lang):
    s = {k: p[k] for k in ("ref", "src", "price", "town", "grp", "beds", "baths", "m2", "beach", "pool")}
    s.update({"type": by_lang(p["type"], lang), "region": region_label(p, lang), "title": by_lang(p["title"], lang),
              "img": p["imgs"][0], "n": len(p["imgs"])})
    s["k"] = p.get("kind", "apt")
    s["mk"] = p.get("market", "new")
    if p.get("tour"): s["tl"] = 1
    if p.get("golf"): s["gf"] = 1
    if p.get("sea"): s["sv"] = 1
    if p.get("reserved"): s["reserved"] = True
    if p.get("excl"): s["ex"] = 1
    if p.get("feat"): s["feat"] = p["feat"]
    return s


def home_page(lang, props, featured, stats, hero, files, ver, tpl):
    paths = dict(HOME)
    page = HOME[lang]
    t = T[lang]
    ctx = common_ctx(lang, page, paths, t["js"]["wa_hello"], stats, ver)
    base = ctx["base"]
    dev = stats["dev"]
    head = headline_count(dev)
    prices = [150000, 200000, 250000, 300000, 400000, 500000, 750000, 1000000, 1500000]
    portrait = files.get("portret")
    reel = files.get("reel")
    media = []
    if portrait:
        media.append(f'<div class="reel photo"><img src="{base}{portrait}?v={ver}" alt="{E(t["about_alt"])}" loading="lazy" width="900" height="1600"></div>')
    if reel:
        media.append(f'<div class="reel"><video src="{base}{reel}?v={ver}" controls playsinline preload="metadata"'
                     + (f' poster="{base}{files["reel_poster"]}?v={ver}"' if files.get("reel_poster") else "")
                     + f' aria-label="{E(t["about_video"])}"></video></div>')
    about_media = (f'<div class="about-media{" two" if len(media) == 2 else ""}">' + "".join(media) + "</div>") if media else ""
    ig_block = ""
    if files.get("ig"):
        fid, prof = files["ig"]
        follow = f'<a class="btn" href="{E(prof)}" target="_blank" rel="noopener">{E(t["ig_follow"])}</a>' if prof else ""
        ig_block = (f'<section class="sec rule" id="instagram"><div class="wrap"><div class="sec-top"><div class="sec-head">'
                    f'<div class="eyebrow">Instagram</div><h2>{E(t["ig_h2"])}</h2></div>{follow}</div>'
                    f'<div class="ig"><behold-widget feed-id="{E(fid)}"></behold-widget></div></div></section>'
                    '<script type="module" src="https://w.behold.so/widget.js"></script>')
    ctx.update({
        "meta_title": E(t["meta_title"].replace("{n}", head)), "meta_desc": E(t["meta_desc"].replace("{n}", head)),
        "devcount": head, "all_n": nf(len(props), lang),
        "st_dev_n": f"{head}+" if dev >= 100 else str(dev), "st_towns_n": str(stats["towns"]),
        "st_min_n": E(fmt_price(stats["minPrice"], lang)),
        "price_options": "".join(f'<option value="{v}">{E(fmt_price(v, lang))}</option>' for v in prices),
        "price_from_options": "".join(f'<option value="{v}">{E(fmt_price(v, lang))}</option>' for v in [100000] + prices[:-1]),
        "about_cls": "" if (portrait or reel) else " noimg",
        "portrait": about_media,
        "ig_block": ig_block,
        "og_image": E(featured[0]["imgs"][0]) if featured and re.match(r"https?://", featured[0]["imgs"][0]) else SITE + "logo-pelne.png",
        "locale": t["locale"], "offer_path": OFFER_DIR[lang][len(HOME[lang]):],
    })
    js = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    h = dict(hero)
    h["video"] = [[base + a, b] for a, b in hero["video"]]
    h["mobile"] = [[base + a, b] for a, b in hero["mobile"]]
    if h.get("poster"): h["poster"] = src(h["poster"], base)
    data = [summary(p, lang) for p in props]
    for d in data:
        d["img"] = src(d["img"], base)
    out = render(tpl, ctx)
    out = (out.replace("/*__DATA__*/[]", js(data)).replace("/*__HERO__*/{}", js(h)).replace("/*__T__*/{}", js(t["js"])))
    agent = {"@context": "https://schema.org", "@type": "RealEstateAgent", "@id": SITE + "#indomito", "name": "Indómito Real Estate",
             "alternateName": ["Indomito Real Estate", "Indómito", "Indomito", "Indómito Real Estate – Klaudia Szafran"], "url": SITE + page,
             "logo": SITE + "logo-pelne.png", "image": SITE + "portret.jpg", "telephone": "+34 613 15 27 55", "email": "info@indomitore.com",
             "founder": {"@type": "Person", "@id": SITE + "#klaudia", "name": "Klaudia Szafran", "alternateName": "Claudia Szafran",
                         "jobTitle": "Agentka nieruchomości (RAICV 4368)", "image": SITE + "portret.jpg", "url": SITE,
                         "worksFor": {"@id": SITE + "#indomito"}, "sameAs": ["https://www.instagram.com/indomitore/"]}, "priceRange": "€€",
             "address": {"@type": "PostalAddress", "streetAddress": "Calle Marqués de Sotelo 5, bajo 5", "postalCode": "46002", "addressLocality": "Valencia", "addressCountry": "ES"},
             "areaServed": ["Costa Blanca", "Costa Cálida"], "knowsLanguage": ["pl", "es", "en"], "sameAs": ["https://www.instagram.com/indomitore/"]}
    site = {"@context": "https://schema.org", "@type": "WebSite", "name": "Indómito Real Estate", "url": SITE, "inLanguage": lang}
    out = out.replace("</head>", "".join('<script type="application/ld+json">' + js(x) + "</script>" for x in (agent, site)) + "</head>", 1)
    return page, out


def privacy_page(lang, stats, ver):
    page = PRIVACY[lang]
    ctx = common_ctx(lang, page, dict(PRIVACY), T[lang]["js"]["wa_hello"], stats, ver)
    t = T[lang]
    body = f'<main class="wrap legal"><div class="eyebrow">Indómito Real Estate</div><h1>{E(t["pp_title"])}</h1>{t["pp_body"]}</main>'
    return page, (f'<!doctype html><html lang="{lang}"><head>{ctx["HEAD"]}<title>{E(t["pp_title"])} | Indómito</title>'
                  f'<link rel="canonical" href="{SITE}{page}"></head><body>{ctx["HEADER"]}{body}{ctx["FOOTER"]}</body></html>')


def not_found_page(stats, ver):
    lang = "pl"
    paths = dict(HOME)
    ctx = common_ctx(lang, None, paths, T[lang]["js"]["wa_hello"], stats, ver)
    other = " ".join(f'<a class="more-link" href="/{HOME[l]}" lang="{l}">{E(T[l]["nf_btn"])}</a>' for l in ("es", "en"))
    body = (f'<main class="wrap nf"><div class="eyebrow">404</div><h1>{E(T[lang]["nf_title"])}</h1><p>{E(T[lang]["nf_p"])}</p>'
            f'<a class="btn gold" href="/#oferty">{E(T[lang]["nf_btn"])}</a><p>{E(T["es"]["nf_title"])} · {E(T["en"]["nf_title"])}</p>'
            f'<div style="display:flex;gap:24px;flex-wrap:wrap;justify-content:center">{other}</div></main>')
    return (f'<!doctype html><html lang="pl"><head>{ctx["HEAD"]}<title>{E(T[lang]["nf_title"])} | Indómito</title>'
            f'<meta name="robots" content="noindex"></head><body>{ctx["HEADER"]}{body}{ctx["FOOTER"]}</body></html>')


# ---------- pliki statyczne ----------
def asset(n):
    return next((p for p in (os.path.join(ROOT, "assets", n), os.path.join(ROOT, n)) if os.path.exists(p)), "")


def copy_static(dist, featured):
    """Style, favicon, ikona na telefon, logo i (jeśli są w repo) portret i wideo do sekcji otwierającej."""
    out = {}
    for name, dst in (("styl.css", "styl.css"), ("formularz.js", "formularz.js"), ("logo-kon.png", "favicon.png"), ("apple-touch-icon.png", "apple-touch-icon.png"),
                      ("logo-pelne.png", "logo-pelne.png"), ("newsletter.jpg", "newsletter.jpg")):
        s = asset(name)
        if s:
            shutil.copyfile(s, os.path.join(dist, dst)); out[name] = dst
    for name in ("portret.jpg", "portret.webp", "portret.png"):
        s = asset(name)
        if s:
            shutil.copyfile(s, os.path.join(dist, name)); out["portret"] = name; break
    # pionowe wideo do sekcji „O mnie” (wystarczy wgrać o-mnie.mp4, opcjonalnie okładkę o-mnie.jpg)
    for name, key in (("o-mnie.mp4", "reel"), ("o-mnie.jpg", "reel_poster")):
        s = asset(name)
        if s:
            shutil.copyfile(s, os.path.join(dist, name)); out[key] = name
    # poradnik PDF (lead magnet): plik w głównym folderze repo -> dist/poradnik/
    pdf = os.path.basename(seo.GUIDE_PDF)
    if seo.GUIDE_ON and asset(pdf):
        os.makedirs(os.path.join(dist, "poradnik"), exist_ok=True)
        shutil.copyfile(asset(pdf), os.path.join(dist, seo.GUIDE_PDF)); out["pdf"] = seo.GUIDE_PDF
    elif seo.GUIDE_ON:
        print(f"! brak pliku {pdf} – link do poradnika PDF nie zadziała", file=sys.stderr)
    # Instagram (Behold.so): instagram.txt → 1. linia ID feedu, 2. linia (opcjonalnie) link do profilu
    s = asset("instagram.txt")
    if s:
        lines = [l.strip() for l in open(s, encoding="utf-8").read().splitlines() if l.strip() and not l.strip().startswith("#")]
        if lines and re.fullmatch(r"[A-Za-z0-9_-]{6,64}", lines[0]):
            out["ig"] = (lines[0], lines[1] if len(lines) > 1 and re.match(r"https://(www\.)?instagram\.com/", lines[1]) else "")
    hero = {"video": [], "mobile": []}
    for name, typ, key in (("hero.webm", "video/webm", "video"), ("hero.mp4", "video/mp4", "video"),
                           ("hero-mobile.mp4", "video/mp4", "mobile")):
        s = asset(name)
        if s:
            shutil.copyfile(s, os.path.join(dist, name)); hero[key].append([name, typ])
    for name in ("hero.jpg", "hero.webp", "hero.png"):
        s = asset(name)
        if s:
            shutil.copyfile(s, os.path.join(dist, name)); hero["poster"] = name; break
    if "poster" not in hero and featured:
        hero["poster"] = featured[0]["imgs"][0]
    return out, hero


def write(dist, page, content):
    path = os.path.join(dist, page, "index.html") if page.endswith("/") or page == "" else os.path.join(dist, page)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def build(props, dist):
    if os.path.isdir(dist): shutil.rmtree(dist)
    os.makedirs(dist, exist_ok=True)
    props.sort(key=lambda p: 0 if p["src"] == "indomito" else 1)  # oferty Indómito na początek
    feed = [p for p in props if p["src"] == "redsp"]
    featured = pick_featured(props)
    stats = {
        "dev": len(feed), "minPrice": min((p["price"] for p in props if p["price"]), default=0),
        "towns": len({p["town"] for p in props}),
        "updated": datetime.now(timezone.utc).astimezone().strftime("%d.%m.%Y"),
    }
    files, hero = copy_static(dist, featured)
    ver = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
    tpl_home, tpl_offer = read("template.html"), read("oferta.html")
    urls = []
    for lang in LANGS:
        page, out = home_page(lang, props, featured, stats, hero, files, ver, tpl_home)
        write(dist, page, out); urls.append(page)
        for p in props:
            page, out = offer_page(p, lang, props, stats, ver, tpl_offer)
            write(dist, page, out); urls.append(page)
    for lang in LANGS:
        page, out = privacy_page(lang, stats, ver)
        write(dist, page, out); urls.append(page)
    urls += seo.build_pages(sys.modules[__name__], props, stats, ver, dist)
    write(dist, "404.html", not_found_page(stats, ver))
    with open(os.path.join(dist, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        f.writelines(f"<url><loc>{SITE}{u}</loc></url>\n" for u in urls)
        f.write("</urlset>\n")
    with open(os.path.join(dist, "robots.txt"), "w") as f:
        f.write(f"User-agent: *\nAllow: /\nDisallow: /poradnik/\nSitemap: {SITE}sitemap.xml\n")
    with open(os.path.join(dist, "CNAME"), "w") as f:
        f.write(DOMAIN + "\n")
    size = sum(os.path.getsize(os.path.join(r, n)) for r, _, fs in os.walk(dist) for n in fs)
    print(f"Wyróżnione: {', '.join(p['ref'] for p in featured) or 'brak'}; wideo: {'tak' if hero['video'] else 'nie'}; "
          f"portret: {'tak' if files.get('portret') else 'nie'}; wideo o mnie: {'tak' if files.get('reel') else 'nie'}; instagram: {'tak' if files.get('ig') else 'nie'}")
    print(f"OK: {len(props)} ofert × {len(LANGS)} języki = {len(urls)} stron -> {dist}/ ({size // 1024 // 1024} MB)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--feed", help="lokalny plik XML zamiast pobierania")
    ap.add_argument("--sample", help="próbka JSON (format skrócony) do podglądu")
    ap.add_argument("--inline", action="store_true", help="(niepotrzebne, zostawione dla zgodności)")
    ap.add_argument("--out", default=os.path.join(ROOT, "dist"))
    a = ap.parse_args()
    if a.sample:
        props = [norm(r) for r in json.load(open(a.sample, encoding="utf-8"))]
    else:
        path = a.feed
        if not path:
            path = os.path.join(ROOT, "feed.xml")
            if not FEED_URL:
                sys.exit("Brak FEED_URL: ustaw sekret FEED_URL w GitHub (Settings → Secrets → Actions)")
            print("Pobieram feed RedSP…")
            urllib.request.urlretrieve(FEED_URL, path)
        props = parse_feed(path)
    tok, db = os.environ.get("NOTION_TOKEN"), os.environ.get("NOTION_DB")
    own = []
    tmp = a.out + "_tmp"
    if tok and db:
        try:
            own = fetch_notion(tok, db, tmp)
            print(f"Notion: {len(own)} ofert bezpośrednich (" + ", ".join(f"{p['ref']} {p['market']}" for p in own) + ")")
        except Exception as e:
            print("! Notion niedostępny, buduję bez ofert bezpośrednich:", e, file=sys.stderr)
    build(own + props, a.out)
    if os.path.isdir(os.path.join(tmp, "img")):
        shutil.copytree(os.path.join(tmp, "img"), os.path.join(a.out, "img"), dirs_exist_ok=True)
    if os.path.isdir(tmp):
        shutil.rmtree(tmp)


if __name__ == "__main__":
    main()
