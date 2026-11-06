"""Blog w trzech językach: /blog/, /es/blog/, /en/blog/ i artykuły pod nimi.

Artykuły to pliki .md w folderze blog/. Jeden temat = do trzech plików z tą samą nazwą i końcówką języka:
    blog/koszty-zakupu.pl.md   blog/koszty-zakupu.es.md   blog/koszty-zakupu.en.md
Przełącznik flag na artykule prowadzi do tego samego artykułu w innym języku (gdy istnieje),
w przeciwnym razie do bloga w tym języku. Plik bez końcówki (np. temat.md) traktowany jest jako polski.

Nagłówek każdego pliku:
    ---
    title: Ile kosztuje zakup mieszkania w Hiszpanii w 2026 roku?
    description: Krótki opis do Google (ok. 150 znaków).
    date: 2026-11-10
    slug: koszty-zakupu-nieruchomosci-w-hiszpanii    (adres artykułu w tym języku)
    image: koszty.jpg              (opcjonalnie – zdjęcie z folderu blog/zdjecia/ albo pełny adres https://)
    share_image: inne.jpg          (opcjonalnie – miniatura przy udostępnianiu, np. na Facebooku/WhatsAppie)
    lead: Krótkie zdanie pod tytułem (opcjonalnie – inaczej pokazuje się description)
    town: Benidorm                 (opcjonalnie – pod artykułem oferty z tej miejscowości)
    draft: true                    (opcjonalnie – szkic, NIE publikuje się)
    ---

Tekst: ## nagłówek, ### podnagłówek, - lista, 1. lista, **pogrubienie**, *kursywa*, [link](/adres/),
> wyróżnienie, tabele | a | b |. Link zaczynający się od "/" prowadzi do podstrony indomitore.com.
Zakładka „Blog” w menu danego języka pojawia się sama, gdy jest tam co najmniej jeden opublikowany artykuł.
"""
import html, json, os, re
from datetime import date

E = html.escape
ROOT = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.join(ROOT, "blog")
LANGS = ("pl", "es", "en")
HUB = {"pl": "blog/", "es": "es/blog/", "en": "en/blog/"}
MONTHS = {
    "pl": ["stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca", "lipca", "sierpnia", "września", "października", "listopada", "grudnia"],
    "es": ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"],
    "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
}
TX = {
    "pl": {"home": "Strona główna", "min": "min czytania", "toc": "Spis treści", "read": "Czytaj dalej", "more": "Przeczytaj też",
           "offers": "Oferty", "hub_eyebrow": "Blog · Nieruchomości w Hiszpanii",
           "hub_h1": "Kupno nieruchomości w Hiszpanii – <em>poradniki</em> po polsku",
           "hub_lead": "Koszty, podatki, kredyt, formalności i najlepsze miejsca na Costa Blanca. Piszę o tym, o co najczęściej pytają mnie klienci z Polski.",
           "hub_title": "Blog o nieruchomościach w Hiszpanii – poradniki dla Polaków",
           "hub_desc": "Poradniki po polsku: koszty zakupu, podatki, kredyt hipoteczny i formalności przy kupnie mieszkania lub domu w Hiszpanii. Blog polskiego biura nieruchomości.",
           "bio": "Agentka nieruchomości",
           "cta_eyebrow": "Polskie biuro nieruchomości w Hiszpanii", "cta_h": "Masz pytania o zakup w Hiszpanii?",
           "cta_p": "Napisz, czego szukasz i jaki masz budżet – odpowiem po polsku i przygotuję wybór ofert dopasowany do Ciebie.",
           "form": "Formularz kontaktowy"},
    "es": {"home": "Inicio", "min": "min de lectura", "toc": "Índice", "read": "Leer más", "more": "Te puede interesar",
           "offers": "Propiedades en", "hub_eyebrow": "Blog · Inmobiliaria en España",
           "hub_h1": "Comprar vivienda en España – <em>guías</em> prácticas",
           "hub_lead": "Costes, impuestos, hipotecas, trámites y las mejores zonas de la Costa Blanca, explicado con claridad.",
           "hub_title": "Blog inmobiliario – guías para comprar vivienda en España",
           "hub_desc": "Guías prácticas sobre costes de compra, impuestos, hipotecas y trámites para comprar un piso o una casa en la Costa Blanca y la Costa Cálida.",
           "bio": "Agente inmobiliaria",
           "cta_eyebrow": "Indómito Real Estate", "cta_h": "¿Tienes preguntas sobre tu compra?",
           "cta_p": "Cuéntame qué buscas y tu presupuesto: te respondo y te preparo una selección de propiedades a tu medida.",
           "form": "Formulario de contacto"},
    "en": {"home": "Home", "min": "min read", "toc": "Contents", "read": "Read more", "more": "You may also like",
           "offers": "Properties in", "hub_eyebrow": "Blog · Property in Spain",
           "hub_h1": "Buying property in Spain – <em>practical</em> guides",
           "hub_lead": "Costs, taxes, mortgages, paperwork and the best areas on the Costa Blanca, explained clearly for international buyers.",
           "hub_title": "Spain property blog – guides for international buyers",
           "hub_desc": "Practical guides for foreign buyers: purchase costs, taxes, mortgages and paperwork when buying an apartment or villa on the Costa Blanca and Costa Cálida.",
           "bio": "Real estate agent",
           "cta_eyebrow": "Indómito Real Estate", "cta_h": "Questions about buying in Spain?",
           "cta_p": "Tell me what you are looking for and your budget – I will reply and send you a hand-picked selection of properties.",
           "form": "Contact form"},
}


# ---------- wczytanie artykułów ----------
def _parse(path):
    raw = open(path, encoding="utf-8").read()
    meta, body = {}, raw
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", raw, re.S)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip().lower()] = v.strip()
        body = m.group(2)
    if not meta.get("title"):
        return None
    name = os.path.splitext(os.path.basename(path))[0]
    key, _, lang = name.rpartition(".")
    if lang not in LANGS:
        key, lang = name, "pl"
    meta.update(key=key, lang=lang, body=body)
    meta["slug"] = re.sub(r"[^a-z0-9-]", "", (meta.get("slug") or key).lower())
    try:
        meta["d"] = date.fromisoformat(meta.get("date", ""))
    except ValueError:
        meta["d"] = date.today()
    meta["draft"] = meta.get("draft", "").lower() in ("true", "tak", "yes", "1")
    meta["url"] = f"{HUB[lang]}{meta['slug']}/"
    return meta


_cache = None
def posts(lang=None):
    """Opublikowane artykuły (od najnowszego). Szkice i daty z przyszłości są pomijane."""
    global _cache
    if _cache is None:
        out = []
        if os.path.isdir(DIR):
            out = [p for p in (_parse(os.path.join(DIR, f)) for f in sorted(os.listdir(DIR)) if f.endswith(".md")) if p]
        _cache = sorted([p for p in out if not p["draft"] and p["d"] <= date.today()], key=lambda p: p["d"], reverse=True)
    return [p for p in _cache if lang is None or p["lang"] == lang]


def nav_link(base, lang):
    return f'<a href="{base}{HUB[lang]}">Blog</a>' if posts(lang) else ""


def footer_item():
    return [("Blog", HUB["pl"])] if posts("pl") else []


def date_txt(d, lang):
    m = MONTHS[lang][d.month - 1]
    return {"pl": f"{d.day} {m} {d.year}", "es": f"{d.day} de {m} de {d.year}", "en": f"{m} {d.day}, {d.year}"}[lang]


# ---------- prosty markdown -> HTML ----------
def _inline(s, base):
    s = E(s, quote=False)
    def link(m):
        t, u = m.group(1), m.group(2)
        if u.startswith("/"):
            return f'<a href="{base}{u[1:]}">{t}</a>'
        return f'<a href="{u}" target="_blank" rel="noopener">{t}</a>'
    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", link, s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", s)
    return s


def _anchor(t):
    t = t.lower()
    for a, b in zip("ąćęłńóśźżáéíóúñü", "acelnoszzaeiounu"):
        t = t.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:60]


def md(text, base):
    out, para, lst, tbl = [], [], None, []

    def flush():
        nonlocal para, lst, tbl
        if para:
            out.append("<p>" + _inline(" ".join(para), base) + "</p>"); para = []
        if lst:
            tag, items = lst
            out.append(f"<{tag}>" + "".join(f"<li>{_inline(i, base)}</li>" for i in items) + f"</{tag}>"); lst = None
        if tbl:
            rows = [[c.strip() for c in r.strip().strip("|").split("|")] for r in tbl if not re.match(r"^\s*\|?[\s:|-]+\|?\s*$", r)]
            if rows:
                head = "".join(f"<th>{_inline(c, base)}</th>" for c in rows[0])
                body = "".join("<tr>" + "".join(f"<td>{_inline(c, base)}</td>" for c in r) + "</tr>" for r in rows[1:])
                out.append(f'<div class="b-table"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>')
            tbl = []

    for line in text.splitlines():
        s = line.strip()
        if not s:
            flush(); continue
        if s.startswith("|"):
            if para or lst: flush()
            tbl.append(s); continue
        elif tbl:
            flush()
        m = re.match(r"^(#{2,3})\s+(.*)$", s)
        if m:
            flush()
            lvl, t = len(m.group(1)), m.group(2)
            out.append(f'<h{lvl} id="{_anchor(t)}">{_inline(t, base)}</h{lvl}>'); continue
        m = re.match(r"^!\[([^\]]*)\]\(([^)\s]+)\)$", s)
        if m:
            flush()
            u = m.group(2)
            if not re.match(r"https?://", u):
                u = base + ("blog/zdjecia/" + u if "/" not in u else u.lstrip("/"))
            alt = E(m.group(1))
            out.append(f'<figure class="b-fig"><img src="{E(u)}" alt="{alt}" loading="lazy"><figcaption>{alt}</figcaption></figure>'); continue
        if s.startswith(">"):
            flush(); out.append(f'<blockquote>{_inline(s.lstrip("> "), base)}</blockquote>'); continue
        m = re.match(r"^(?:[-*]|(\d+)[.)])\s+(.*)$", s)
        if m:
            tag = "ol" if m.group(1) else "ul"
            if para: flush()
            if lst and lst[0] != tag: flush()
            if not lst: lst = (tag, [])
            lst[1].append(m.group(2)); continue
        if lst: flush()
        para.append(s)
    flush()
    return "\n".join(out)


def _reading_min(text):
    return max(1, round(len(re.findall(r"\w+", text)) / 200))


def _img(u, base, B):
    """Adres zdjęcia na stronie i pełny adres do Google/Facebooka."""
    if not u:
        return None, None
    if re.match(r"https?://", u):
        return u, u
    u = u.lstrip("/")
    if "/" not in u:  # sama nazwa pliku -> folder blog/zdjecia/
        u = "blog/zdjecia/" + u
    return base + u, B.SITE + u


# ---------- strony ----------
def build_pages(B, props, stats, ver, dist):
    urls = []
    pics = os.path.join(DIR, "zdjecia")
    if os.path.isdir(pics):
        import shutil
        shutil.copytree(pics, os.path.join(dist, "blog", "zdjecia"), dirs_exist_ok=True)

    def ld(obj):
        return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False).replace("</", "<\\/") + "</script>"

    def page(lang, url, paths, title, desc, crumbs, inner, og_img=None, extra_head="", og_type="website"):
        tx = TX[lang]
        ctx = B.common_ctx(lang, url, paths, B.T[lang]["js"]["wa_hello"], stats, ver)
        alts = [f'<link rel="alternate" hreflang="{l}" href="{B.SITE}{paths[l]}">' for l in LANGS if l in paths and paths[l] != B.HOME[l]]
        ctx["alternates"] = "".join(alts) or f'<link rel="alternate" hreflang="{lang}" href="{B.SITE}{url}">'
        ctx["HEAD"] = B.render(B.read("glowa.html"), ctx)
        base = ctx["base"]
        cr = "".join(f'<a href="{base}{u}">{E(n)}</a><span aria-hidden="true">/</span>' for n, u in crumbs[:-1]) + f"<span>{E(crumbs[-1][0])}</span>"
        crumbs_ld = ld({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": n, "item": B.SITE + u}
            for i, (n, u) in enumerate([(tx["home"], B.HOME[lang])] + crumbs)]})
        img = og_img or B.SITE + "logo-pelne.png"
        out = (f'<!doctype html><html lang="{lang}"><head>{ctx["HEAD"]}<title>{E(title)} | Indómito</title>'
               f'<meta name="description" content="{E(desc)}"><meta property="og:type" content="{og_type}">'
               f'<meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}">'
               f'<meta property="og:image" content="{E(img)}"><meta property="og:url" content="{B.SITE}{url}">'
               f'<link rel="canonical" href="{B.SITE}{url}">{crumbs_ld}{extra_head}</head>'
               f'<body>{ctx["HEADER"]}<main class="seo blog"><div class="wrap">'
               f'<nav class="crumbs" aria-label="breadcrumb"><a href="{ctx["home"]}">{E(tx["home"])}</a><span aria-hidden="true">/</span>{cr}</nav>'
               f'{inner(ctx, base)}</div></main>{ctx["FOOTER"]}</body></html>')
        B.write(dist, url, out)
        urls.append(url)

    def cta(ctx, lang):
        tx = TX[lang]
        return (f'<section class="seo-cta"><div class="eyebrow">{E(tx["cta_eyebrow"])}</div>'
                f'<h2>{E(tx["cta_h"])}</h2><p>{E(tx["cta_p"])}</p>'
                f'<div class="seo-btns"><a class="btn gold" href="{ctx["wa_link"]}" target="_blank" rel="noopener">{E(B.T[lang]["wa_btn"])}</a>'
                f'<a class="btn" href="{ctx["home"]}#kontakt">{E(tx["form"])}</a></div></section>')

    def card(p, base):
        tx = TX[p["lang"]]
        src, _ = _img(p.get("image"), base, B)
        img = f'<div class="b-img"><img src="{E(src)}" alt="" loading="lazy"></div>' if src else ""
        return (f'<a class="b-card" href="{base}{p["url"]}">{img}<div class="b-meta">{date_txt(p["d"], p["lang"])} · {_reading_min(p["body"])} {tx["min"]}</div>'
                f'<h2>{E(p["title"])}</h2><p>{E(p.get("description", ""))}</p><span class="more-link">{tx["read"]}</span></a>')

    hub_paths = {l: (HUB[l] if posts(l) else B.HOME[l]) for l in LANGS}
    for lang in LANGS:
        ps = posts(lang)
        if not ps:
            continue
        tx = TX[lang]

        def hub(ctx, base, ps=ps, lang=lang, tx=tx):
            return (f'<header class="seo-hero"><div class="eyebrow">{E(tx["hub_eyebrow"])}</div>'
                    f'<h1>{tx["hub_h1"]}</h1><p class="lead">{E(tx["hub_lead"])}</p></header>'
                    f'<div class="b-grid">{"".join(card(p, base) for p in ps)}</div>{cta(ctx, lang)}')
        page(lang, HUB[lang], hub_paths, tx["hub_title"], tx["hub_desc"], [("Blog", HUB[lang])], hub)

        for p in ps:
            trans = {o["lang"]: o["url"] for o in posts() if o["key"] == p["key"]}
            paths = {l: trans.get(l, hub_paths[l]) for l in LANGS}

            def art(ctx, base, p=p, ps=ps, lang=lang, tx=tx):
                body = md(p["body"], base)
                toc_items = re.findall(r'<h2 id="([^"]+)">(.*?)</h2>', body)
                toc = (f'<nav class="g-toc"><b>{tx["toc"]}</b><ul>' + "".join(f'<li><a href="#{a}">{t}</a></li>' for a, t in toc_items)
                       + '</ul></nav>') if len(toc_items) >= 3 else ""
                author = (f'<div class="b-author"><img src="{base}portret.jpg" alt="Klaudia Szafran" width="56" height="56" loading="lazy">'
                          f'<div><b>Klaudia Szafran</b><span>{E(tx["bio"])}</span></div></div>')
                offers = ""
                if p.get("town"):
                    tw = p["town"].lower()
                    sel = [x for x in props if (x.get("town") or "").lower() == tw][:3]
                    if sel:
                        offers = (f'<section class="seo-list"><h2>{tx["offers"]}{":" if lang == "pl" else ""} {E(p["town"])}</h2><div class="grid">'
                                  + "".join(B.card_html(x, lang, base) for x in sel) + "</div></section>")
                others = [o for o in ps if o is not p][:3]
                more = (f'<section class="b-more"><h2>{tx["more"]}</h2><div class="b-grid">{"".join(card(o, base) for o in others)}</div></section>') if others else ""
                src, _ = _img(p.get("image"), base, B)
                hero_img = f'<img class="b-hero" src="{E(src)}" alt="{E(p["title"])}">' if src else ""
                return (f'<article class="b-art"><header class="seo-hero"><div class="eyebrow">Blog · {date_txt(p["d"], lang)} · {_reading_min(p["body"])} {tx["min"]}</div>'
                        f'<h1>{E(p["title"])}</h1>' + (f'<p class="lead">{E(p.get("lead") or p["description"])}</p>' if p.get("lead") or p.get("description") else "") + '</header>'
                        f'{hero_img}{author}{toc}<div class="seo-text">{body}</div></article>{offers}{cta(ctx, lang)}{more}')

            _, full_img = _img(p.get("share_image") or p.get("image"), "", B)
            art_ld = ld({"@context": "https://schema.org", "@type": "BlogPosting", "headline": p["title"],
                         "description": p.get("description", ""), "datePublished": p["d"].isoformat(),
                         "dateModified": p.get("updated", p["d"].isoformat()), "inLanguage": lang,
                         "image": full_img or B.SITE + "logo-pelne.png",
                         "author": {"@type": "Person", "name": "Klaudia Szafran", "url": B.SITE + "polskie-biuro-nieruchomosci-w-hiszpanii/"},
                         "publisher": {"@type": "Organization", "name": "Indómito Real Estate",
                                       "logo": {"@type": "ImageObject", "url": B.SITE + "logo-pelne.png"}},
                         "mainEntityOfPage": B.SITE + p["url"]})
            page(lang, p["url"], paths, p["title"], p.get("description", p["title"]), [("Blog", HUB[lang]), (p["title"], p["url"])],
                 art, full_img, art_ld, "article")
    return urls
