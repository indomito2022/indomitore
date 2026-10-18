#!/usr/bin/env python3
"""
Generator strony indomitore.com

Źródła:
  1. Feed XML RedSP (nowe budowy)  -> zmienna FEED_URL albo --feed plik.xml
  2. Notion "Nieruchomości" (oferty bezpośrednie) -> NOTION_TOKEN + NOTION_DB (opcjonalnie)

Wynik (folder dist/):
  index.html          strona z listą ofert (lekkie dane w środku)
  o/<REF>.json        szczegóły każdej oferty (ładowane po kliknięciu)
  img/                zdjęcia ofert z Notion (pobierane, bo linki Notion wygasają)
  CNAME               domena dla GitHub Pages

Uruchomienie:
  python3 build.py                       # pobiera feed z FEED_URL
  python3 build.py --feed feed.xml       # z pliku
  python3 build.py --sample sample.json --inline   # podgląd lokalny (bez serwera)
Tylko biblioteka standardowa Pythona.
"""
import argparse, html, json, os, re, shutil, sys, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
FEED_URL = os.environ.get("FEED_URL", "")  # ustawiany jako sekret FEED_URL w GitHub
DOMAIN = os.environ.get("SITE_DOMAIN", "indomitore.com")

TYPE_PL = {
    "Villa": "Willa", "Apartment": "Apartament", "Penthouse": "Penthouse",
    "Bungalow": "Bungalow", "Town House": "Dom szeregowy", "Quad House": "Dom typu quad",
    "Semi-Detached House": "Bliźniak", "Duplex": "Dupleks", "Studio": "Studio",
}
REGION = {  # costa z feedu -> (grupa do filtra, opis)
    "Costa Blanca North": ("cbn", "Costa Blanca Północ"),
    "Costa Blanca North - Inland": ("cbn", "Costa Blanca Północ · w głębi lądu"),
    "Costa Blanca South": ("cbs", "Costa Blanca Południe"),
    "Costa Blanca South - Inland": ("cbs", "Costa Blanca Południe · w głębi lądu"),
    "Costa Calida": ("cc", "Costa Cálida"),
    "Costa Calida - Inland": ("cc", "Costa Cálida · w głębi lądu"),
}
FEAT_PL = {
    "Gated": "Osiedle zamknięte", "Parking - Space": "Miejsce parkingowe", "Near Schools": "Blisko szkół",
    "Garden": "Ogród", "Communal Pool": "Basen wspólny", "Private Pool": "Basen prywatny",
    "Elevator/Lift": "Winda", "Near Commercial Center": "Blisko centrum handlowego",
    "Solarium: Yes": "Solarium", "Near Bus Route": "Blisko przystanku",
    "Near Golf / Golf Resort Property": "Blisko pola golfowego", "Furnished": "Umeblowane",
    "Near Childrens Parks": "Blisko placu zabaw", "Views: Sea": "Widok na morze",
    "Views: Mountain": "Widok na góry", "Key Ready": "Gotowe do odbioru kluczy", "BBQ": "Grill",
    "Licensed Tourist Property": "Licencja turystyczna", "Near Train Station": "Blisko dworca",
    "Air Conditioning": "Klimatyzacja", "Underfloor Heating": "Ogrzewanie podłogowe",
    "Storage Room": "Komórka lokatorska", "Garage": "Garaż", "Basement": "Piwnica",
    "Jacuzzi": "Jacuzzi", "Gym": "Siłownia", "Spa": "Spa", "Domotics": "Inteligentny dom",
}
LOC_PL = {"Rural": "wiejska", "Urbanisation": "osiedle", "Coastal": "nadmorska", "Town": "miejska", "Village": "wieś"}


def feat_pl(f):
    if f in FEAT_PL:
        return FEAT_PL[f]
    m = re.match(r"Terrace: (\d+) Msq", f)
    if m: return f"Taras {m.group(1)} m²"
    m = re.match(r"Number of Parking Spaces: (\d+)", f)
    if m: return f"Miejsca parkingowe: {m.group(1)}"
    m = re.match(r"Useable Build Space: (\d+) Msq", f)
    if m: return f"Powierzchnia użytkowa {m.group(1)} m²"
    m = re.match(r"Location: (.+)", f)
    if m: return "Lokalizacja: " + ", ".join(LOC_PL.get(x.strip(), x.strip()) for x in m.group(1).split(","))
    if f.startswith("Beach:") or f.strip() in ("Space", ""):
        return None  # odległość do plaży pokazujemy osobno
    return f


def clean_desc(s):
    s = html.unescape(s or "").replace("\r\n", "\n").replace("\r", "\n")
    paras = [re.sub(r"[ \t]+", " ", p).strip() for p in re.split(r"\n+", s)]
    return [p for p in paras if p]


def norm(rec, source="redsp"):
    """Wspólny format oferty."""
    grp, region = REGION.get(rec.get("c", ""), ("inne", rec.get("c", "")))
    feats = []
    for f in rec.get("f", []):
        t = feat_pl(f)
        if t and t not in feats: feats.append(t)
    pool = bool(rec.get("po")) or any("Basen" in f for f in feats)
    return {
        "ref": rec["r"], "src": source, "price": int(rec.get("p") or 0),
        "type": TYPE_PL.get(rec.get("t", ""), rec.get("t", "")), "town": rec.get("tw", ""),
        "area": rec.get("l", ""), "grp": grp, "region": region,
        "beds": int(rec.get("b") or 0), "baths": int(rec.get("ba") or 0),
        "m2": int(rec.get("m") or 0), "plot": int(rec.get("pl") or 0), "beach": int(rec.get("be") or 0),
        "pool": pool, "lat": rec.get("la"), "lng": rec.get("ln"),
        "title": html.unescape(rec.get("ti", "")).strip(), "desc": clean_desc(rec.get("d", "")),
        "feats": feats, "imgs": rec.get("i", []),
    }


def parse_feed(path):
    out = []
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
            "ti": g(p, "title/pl") or g(p, "title/en"), "d": g(p, "desc/pl") or g(p, "desc/en"),
            "f": [ (f.text or "").strip() for f in p.findall("features/feature") ],
            "i": [ (u.text or "").strip() for u in p.findall("images/image/url") ],
        }
        if rec["r"] and rec["i"] and rec["p"]:
            out.append(norm(rec))
        el.clear()
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
        for i, f in enumerate((pr.get("Zdjęcia", {}).get("files") or [])[:20]):
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
        reg = sel("Region")
        grp = {"Costa Blanca Norte": "cbn", "Costa Blanca Sur": "cbs", "Costa Cálida": "cc"}.get(reg, "inne")
        amen = [o["name"] for o in (pr.get("Udogodnienia", {}).get("multi_select") or [])]
        if not imgs: continue
        out.append({
            "ref": ref, "src": "indomito", "price": int(num("Cena")), "type": sel("Typ"),
            "town": sel("Miejscowość"), "area": "", "grp": grp, "region": reg.replace("Norte", "Północ").replace("Sur", "Południe"),
            "beds": int(num("Sypialnie")), "baths": int(num("Łazienki")), "m2": int(num("Metraż m²")), "plot": 0,
            "beach": 0, "pool": any("Basen" in a for a in amen), "lat": None, "lng": None,
            "title": txt("Nazwa"), "desc": clean_desc(txt("Opis")), "feats": amen, "imgs": imgs,
            "reserved": (pr.get("Status", {}).get("status") or {}).get("name") == "Zarezerwowana",
        })
    return out


# ---------- składanie strony ----------
def summary(p):
    s = {k: p[k] for k in ("ref", "src", "price", "type", "town", "grp", "region", "beds", "baths", "m2", "beach", "pool")}
    s["title"] = p["title"]; s["img"] = p["imgs"][0]; s["n"] = len(p["imgs"])
    if p.get("reserved"): s["reserved"] = True
    return s


def detail(p):
    return {k: p[k] for k in ("ref", "area", "plot", "lat", "lng", "desc", "feats", "imgs")}


def build(props, dist, inline=False):
    if os.path.isdir(dist): shutil.rmtree(dist)
    os.makedirs(os.path.join(dist, "o"), exist_ok=True)
    # oferty Indómito na początek, potem najtańsze nowości wg daty z feedu (kolejność feedu)
    props.sort(key=lambda p: 0 if p["src"] == "indomito" else 1)
    feed = [p for p in props if p["src"] == "redsp"]
    stats = {
        "count": len(props), "minPrice": min((p["price"] for p in props if p["price"]), default=0),
        "towns": len({p["town"] for p in props}),
        "updated": datetime.now(timezone.utc).astimezone().strftime("%d.%m.%Y"),
        "beach1km": sum(1 for p in feed if 0 < p["beach"] <= 1000),
    }
    details = {p["ref"]: detail(p) for p in props}
    if not inline:
        for ref, d in details.items():
            with open(os.path.join(dist, "o", re.sub(r"[^\w.-]", "_", ref) + ".json"), "w", encoding="utf-8") as f:
                json.dump(d, f, ensure_ascii=False, separators=(",", ":"))
    tpl = open(os.path.join(ROOT, "template.html"), encoding="utf-8").read()
    js = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    page = (tpl.replace("/*__DATA__*/[]", js([summary(p) for p in props]))
               .replace("/*__STATS__*/{}", js(stats))
               .replace("/*__DETAILS__*/null", js(details) if inline else "null"))
    import base64
    asset = lambda n: next((p for p in (os.path.join(ROOT, "assets", n), os.path.join(ROOT, n)) if os.path.exists(p)), "")
    logo = asset("logo-kon.png")
    if logo:
        page = page.replace("__LOGO__", "data:image/png;base64," + base64.b64encode(open(logo, "rb").read()).decode())
    logo_full = asset("logo-pelne.png")
    if logo_full:
        page = page.replace("__LOGOFULL__", "data:image/png;base64," + base64.b64encode(open(logo_full, "rb").read()).decode())
    with open(os.path.join(dist, "index.html"), "w", encoding="utf-8") as f:
        f.write(page)
    with open(os.path.join(dist, "CNAME"), "w") as f:
        f.write(DOMAIN + "\n")
    print(f"OK: {len(props)} ofert -> {dist}/index.html ({os.path.getsize(os.path.join(dist,'index.html'))//1024} KB)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--feed", help="lokalny plik XML zamiast pobierania")
    ap.add_argument("--sample", help="próbka JSON (format skrócony) do podglądu")
    ap.add_argument("--inline", action="store_true", help="szczegóły w jednym pliku (podgląd bez serwera)")
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
    os.makedirs(a.out, exist_ok=True)
    own = []
    if tok and db:
        try:
            own = fetch_notion(tok, db, a.out + "_tmp")
            print(f"Notion: {len(own)} ofert bezpośrednich")
        except Exception as e:
            print("! Notion niedostępny, buduję bez ofert bezpośrednich:", e, file=sys.stderr)
    build(own + props, a.out, inline=a.inline)
    tmp = a.out + "_tmp"
    if os.path.isdir(os.path.join(tmp, "img")):
        shutil.copytree(os.path.join(tmp, "img"), os.path.join(a.out, "img"), dirs_exist_ok=True)
        shutil.rmtree(tmp)


if __name__ == "__main__":
    main()
