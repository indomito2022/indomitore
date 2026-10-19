"""Podstrony SEO po polsku: kategorie (Costa Blanca, mieszkania, domy...), miejscowości, polskie biuro i poradnik.

Wywoływane z build.py: seo.build_pages(B, props, stats, ver, dist) -> lista adresów do sitemap.
B to moduł build.py (pomocnicze funkcje: common_ctx, card_html, render, write...).
Teksty stron są tutaj, w słownikach poniżej - można je spokojnie poprawiać.
"""
import html, json, re, unicodedata
from statistics import median

E = html.escape
GUIDE = "poradnik-zakup-nieruchomosci-w-hiszpanii/"
GUIDE_PDF = "poradnik/Indomito-poradnik-zakup-nieruchomosci-w-hiszpanii.pdf"
TOWNS_HUB = "nieruchomosci/"
OFFICE = "polskie-biuro-nieruchomosci-w-hiszpanii/"
MAX_CARDS = 24
MIN_TOWN = 3          # podstrona miejscowości, gdy ma co najmniej tyle ofert
CB = ("cbn", "cbs")
HV = ("house", "villa")

# ---------- miejscowości: ładne nazwy, odmiana „w ...”, krótkie opisy ----------
TOWN_NAME = {
    "Pilar de La Horadada": "Pilar de la Horadada", "Los Alcazares": "Los Alcázares", "Aguilas": "Águilas",
    "Jávea Xàbia": "Jávea", "Moraira_Teulada": "Moraira", "la Nucia": "La Nucia", "Benijofar": "Benijófar",
    "Alhama De Murcia": "Alhama de Murcia", "Hondón de las Nieves": "Hondón de las Nieves",
}
LOC = {  # miejscownik
    "Torrevieja": "w Torreviei", "Benidorm": "w Benidormie", "Altea": "w Altei", "Denia": "w Denii", "Jávea": "w Jávei",
    "Villajoyosa": "w Villajoyosie", "Cartagena": "w Cartagenie", "Santa Pola": "w Santa Poli", "Orihuela Costa": "na Orihuela Costa",
    "Murcia": "w Murcji", "Moraira": "w Morairze",
}
NOTE = {
    "Torrevieja": "Jedno z najpopularniejszych miast Costa Blanca wśród kupujących z zagranicy: kilometry plaż, słone jeziora z różową Laguna Salada i miasto, które żyje przez cały rok. Do lotniska w Alicante jest ok. 40–45 minut.",
    "Pilar de la Horadada": "Spokojniejsza miejscowość na granicy prowincji Alicante i Murcji, z plażami Mil Palmeras i Torre de la Horadada oraz polem golfowym Lo Romero. Dobra baza dla rodzin i na dłuższe pobyty.",
    "Los Alcázares": "Miasteczko nad Mar Menor, płytką i ciepłą laguną, idealną dla rodzin i sportów wodnych. Blisko lotniska Murcja i pól golfowych.",
    "Finestrat": "Miejscowość tuż obok Benidormu: od plaży Cala de Finestrat po wzgórza z widokiem na morze i górę Puig Campana. W okolicy centrum handlowe La Marina, park Terra Mítica i pole golfowe Villaitana.",
    "Benidorm": "Najbardziej znane miasto Costa Blanca: plaże Levante i Poniente, apartamenty z widokiem na morze, sezon przez cały rok i świetna infrastruktura. Tuż obok Finestrat, Polop i La Nucia, gdzie łatwiej o domy i wille.",
    "Guardamar del Segura": "Szerokie, piaszczyste plaże z wydmami i sosnowym parkiem, spokojniej niż w Torreviei. Do lotniska w Alicante jest ok. 30 minut.",
    "San Pedro del Pinatar": "Miasteczko nad Mar Menor, przy parku przyrodniczym Salinas de San Pedro słynącym z kąpieli błotnych. Blisko lotniska Murcja.",
    "Torre Pacheco": "Okolica Mar Menor w regionie Murcji, znana z kompleksów golfowych. Ceny są tu zwykle niższe niż na wybrzeżu Alicante.",
    "Benijófar": "Spokojna miejscowość w głębi lądu, kilkanaście minut od plaż Guardamar i Torreviei. Wille z basenem w dobrej cenie.",
    "San Miguel de Salinas": "Między Torrevieją a Orihuela Costa, blisko pól golfowych Las Colinas, Vistabella i Villamartín.",
    "Villajoyosa": "Kolorowe domy starego miasta, plaże i tradycja wyrobu czekolady. Leży między Benidormem a Alicante.",
    "Pinoso": "Malownicza okolica w głębi lądu, wśród winnic. Przestronne wille z działką w niższej cenie niż na wybrzeżu.",
    "Algorfa": "Kameralna miejscowość z polem golfowym La Finca, kilkanaście minut od plaż Guardamar.",
    "Polop": "Górskie miasteczko nad Benidormem z widokiem na Puig Campana i morze. Ciche wille z basenami, ok. 15 minut do plaż.",
    "Orihuela Costa": "Wybrzeże pełne zatoczek i plaż (Cabo Roig, La Zenia, Playa Flamenca), centrum handlowe La Zenia Boulevard i pola golfowe Villamartín i Las Ramblas.",
    "Rojales": "Miejscowość z dzielnicą Ciudad Quesada i polem golfowym La Marquesa, kilka minut od plaż Guardamar.",
    "Benitachell": "Klify Cumbre del Sol i widoki na morze. Prestiżowa część Costa Blanca Północ, między Jávea a Morairą.",
    "Calpe": "Charakterystyczna skała Peñón de Ifach, piękne plaże i port. Jedno z najładniejszych miasteczek Costa Blanca Północ.",
    "Alicante": "Stolica prowincji: lotnisko, plaża Postiguet tuż przy centrum, zamek Santa Bárbara, marina i miasto, które żyje przez cały rok.",
    "Altea": "Białe stare miasto na wzgórzu, artystyczny klimat i spokojniejsze plaże tuż obok Benidormu.",
    "Denia": "Port z promami na Baleary, zamek nad miastem i długie plaże Les Marines i Les Rotes.",
    "Jávea": "Zatoczki Granadella i Portitxol, góra Montgó nad miastem i klimat, który przyciąga kupujących z całej Europy.",
    "Santa Pola": "Rybackie miasteczko z portem i wyspą Tabarca na wyciągnięcie ręki, ok. 15 minut od lotniska w Alicante.",
    "La Manga del Mar Menor": "Wąski pas lądu między Mar Menor a Morzem Śródziemnym: dwa morza w zasięgu spaceru.",
    "Cartagena": "Historyczne miasto portowe z rzymskim teatrem. W okolicy plaże Mar Menor i park przyrodniczy Calblanque.",
    "Águilas": "Kameralne zatoczki i czysta woda na południu Costa Cálida.",
    "San Javier": "Miasteczko nad Mar Menor z nadmorską Santiago de la Ribera, blisko lotniska Murcja.",
}
REG_PL = {"cbn": "Costa Blanca Północ", "cbs": "Costa Blanca Południe", "cc": "Costa Cálida"}


def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def tname(raw):
    return TOWN_NAME.get(raw, raw)


def loc(name):
    return LOC.get(name, f"w {name}")


def pl_num(n, one, few, many):
    if n == 1: return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14: return few
    return many


def offers_word(n):
    return f"{n} " + pl_num(n, "oferta", "oferty", "ofert")


def price_pl(v):
    return f"{v:,}".replace(",", " ") + " €"


# ---------- kategorie ----------
CATS = [
    {
        "slug": "nieruchomosci-costa-blanca/", "nav": "Nieruchomości Costa Blanca",
        "title": "Nieruchomości Costa Blanca – mieszkania, apartamenty i domy na sprzedaż",
        "h1": "Nieruchomości na Costa Blanca",
        "eyebrow": "Costa Blanca · Alicante",
        "lead": "Mieszkania, apartamenty, domy i wille na całym wybrzeżu Costa Blanca – od Denii i Calpe po Torrevieję i Pilar de la Horadada. Z polskim biurem nieruchomości, które przeprowadzi Cię przez cały zakup.",
        "match": lambda p: p["grp"] in CB, "q": {"grp": "cb"},
        "body": """
<h2>Dlaczego Costa Blanca?</h2>
<p>Costa Blanca to ponad 200 km wybrzeża w prowincji Alicante i jeden z najchętniej wybieranych przez Polaków regionów Hiszpanii. Ponad 300 słonecznych dni w roku, łagodna zima, lotnisko w Alicante z bezpośrednimi lotami do kilku polskich miast i ceny, które wciąż są niższe niż na Costa del Sol czy Balearach.</p>
<h2>Costa Blanca Północ czy Południe?</h2>
<p><strong>Costa Blanca Północ</strong> (Benidorm, Finestrat, Altea, Calpe, Jávea, Denia) to góry schodzące do morza, widoki, zatoczki i bardziej prestiżowe lokalizacje. Tu częściej znajdziesz wille z widokiem na morze i apartamenty premium.</p>
<p><strong>Costa Blanca Południe</strong> (Torrevieja, Orihuela Costa, Guardamar, Pilar de la Horadada) to długie, piaszczyste plaże, pola golfowe, spokojniejsze tempo i niższe ceny. Popularny wybór na pierwsze mieszkanie w Hiszpanii i pod wynajem.</p>
<h2>Nowe czy z rynku wtórnego?</h2>
<p>W ofercie masz zarówno nowe inwestycje od deweloperów (często z basenem, ogrodem i solarium, z płatnościami rozłożonymi na etapy budowy), jak i nieruchomości z rynku wtórnego, gotowe do zamieszkania od razu. Różnią się podatkami i procedurą – wszystko wyjaśniam w <a href="{guide}">bezpłatnym poradniku zakupu</a>.</p>
""",
    },
    {
        "slug": "mieszkania-costa-blanca/", "nav": "Mieszkania Costa Blanca",
        "title": "Mieszkania Costa Blanca na sprzedaż – nowe i z rynku wtórnego",
        "h1": "Mieszkania na Costa Blanca",
        "eyebrow": "Mieszkania · apartamenty · penthouse'y",
        "lead": "Mieszkania na sprzedaż na Costa Blanca: apartamenty z tarasem, penthouse'y z solarium i parterowe mieszkania z ogródkiem, w nowych inwestycjach i na rynku wtórnym.",
        "match": lambda p: p["grp"] in CB and p.get("kind") == "apt", "q": {"grp": "cb", "type": "g:apt"},
        "body": """
<h2>Jakie mieszkanie na Costa Blanca wybrać?</h2>
<p>Najczęściej kupowane są mieszkania z 2 sypialniami i 2 łazienkami – wygodne dla rodziny i łatwe do wynajęcia. Hiszpańskie mieszkania typu <strong>planta baja</strong> (parter) mają zwykle własny ogródek, a <strong>ático</strong> (penthouse) – duży taras lub solarium na dachu. W nowych inwestycjach standardem jest basen we wspólnej strefie, klimatyzacja i miejsce parkingowe.</p>
<h2>Ile kosztuje mieszkanie na Costa Blanca?</h2>
<p>Ceny zależą przede wszystkim od odległości od plaży i widoku na morze. Na Costa Blanca Południe (Torrevieja, Guardamar, Orihuela Costa) znajdziesz mieszkania w niższych cenach, na Północy (Benidorm, Finestrat, Calpe, Altea) – droższe, często z panoramicznym widokiem. Do ceny trzeba doliczyć ok. 10–14% kosztów zakupu (podatki, notariusz, prawnik).</p>
<h2>Mieszkanie pod wynajem</h2>
<p>Jeśli myślisz o wynajmie turystycznym, sprawdź przed zakupem, czy w danej miejscowości i we wspólnocie mieszkaniowej można uzyskać licencję turystyczną – zasady w regionie Walencji się zaostrzają. W wyszukiwarce możesz zaznaczyć filtr „Licencja turystyczna”.</p>
""",
    },
    {
        "slug": "apartamenty-costa-blanca/", "nav": "Apartamenty Costa Blanca",
        "title": "Apartamenty Costa Blanca – blisko plaży i z basenem",
        "h1": "Apartamenty na Costa Blanca",
        "eyebrow": "Blisko plaży · z basenem",
        "lead": "Apartamenty na Costa Blanca, które wybierają kupujący na wakacje i pod wynajem: blisko plaży, z basenem, tarasem i widokiem na morze.",
        "match": lambda p: p["grp"] in CB and p.get("kind") == "apt" and (p["pool"] or 0 < p["beach"] <= 1500 or p.get("sea")),
        "q": {"grp": "cb", "type": "g:apt", "sort": "beach"},
        "body": """
<h2>Apartament wakacyjny w Hiszpanii</h2>
<p>Apartament na Costa Blanca to dla wielu Polaków drugi dom: miejsce na urlop, dłuższe zimowanie i inwestycja, która może na siebie zarabiać. Najbardziej poszukiwane są apartamenty <strong>do 1 km od plaży</strong>, w kompleksach ze <strong>wspólnym basenem</strong> i z tarasem lub solarium.</p>
<h2>Na co zwrócić uwagę?</h2>
<p>Sprawdź orientację tarasu (południe = słońce przez cały dzień), opłaty wspólnoty (comunidad), dojazd z lotniska i to, czy okolica żyje także poza sezonem. W nowych kompleksach zwróć uwagę na harmonogram budowy i gwarancję bankową wpłat.</p>
<p>Chcesz zobaczyć mieszkania na całym wybrzeżu, nie tylko przy plaży? Zobacz <a href="{base}mieszkania-costa-blanca/">mieszkania Costa Blanca</a>.</p>
""",
    },
    {
        "slug": "domy-costa-blanca/", "nav": "Domy Costa Blanca",
        "title": "Domy Costa Blanca na sprzedaż – wille, domy szeregowe i bliźniaki",
        "h1": "Domy na Costa Blanca",
        "eyebrow": "Wille · domy szeregowe · bliźniaki",
        "lead": "Domy i wille na sprzedaż na Costa Blanca: z prywatnym basenem, ogrodem i solarium, od kameralnych domów szeregowych po wille z widokiem na morze.",
        "match": lambda p: p["grp"] in CB and p.get("kind") in HV, "q": {"grp": "cb", "type": "g:hv"},
        "body": """
<h2>Rodzaje domów na Costa Blanca</h2>
<p><strong>Villa</strong> to dom wolnostojący na własnej działce, najczęściej z prywatnym basenem. <strong>Adosado</strong> (szeregowiec) i <strong>pareado</strong> (bliźniak) to tańsza alternatywa – zwykle z ogródkiem, tarasem na dachu i dostępem do basenu, czasem prywatnego. <strong>Quad</strong> to cztery domy połączone w jeden budynek, każdy z osobnym wejściem.</p>
<h2>Gdzie szukać domu?</h2>
<p>Wille z widokiem na morze to przede wszystkim Costa Blanca Północ: Finestrat i Sierra Cortina, Polop, Altea, Calpe, Benitachell i Jávea. Domy w lepszej cenie, blisko pól golfowych i plaż, znajdziesz na Costa Blanca Południe: w Rojales, Benijófar, Algorfie, San Miguel de Salinas czy Pilar de la Horadada.</p>
<p>Szukasz domu również poza Costa Blanca? Zobacz <a href="{base}domy-w-hiszpanii/">domy w Hiszpanii</a>, w tym na Costa Cálida.</p>
""",
    },
    {
        "slug": "domy-w-hiszpanii/", "nav": "Domy w Hiszpanii",
        "title": "Domy w Hiszpanii na sprzedaż – wille i domy nad morzem",
        "h1": "Domy w Hiszpanii",
        "eyebrow": "Costa Blanca · Costa Cálida",
        "lead": "Domy i wille w Hiszpanii nad morzem: Costa Blanca i Costa Cálida. Nowe domy od deweloperów i nieruchomości z rynku wtórnego, z pomocą polskiego biura na każdym etapie.",
        "match": lambda p: p.get("kind") in HV, "q": {"type": "g:hv"},
        "body": """
<h2>Dom w Hiszpanii – od czego zacząć?</h2>
<p>Zacznij od regionu i budżetu. <strong>Costa Blanca</strong> (prowincja Alicante) oferuje największy wybór: od willi z widokiem na morze na północy po domy blisko pól golfowych na południu. <strong>Costa Cálida</strong> (region Murcji) przyciąga ciepłą laguną Mar Menor, golfem i niższymi cenami – a także nieco niższym podatkiem przy zakupie z rynku wtórnego.</p>
<h2>Koszty zakupu domu w Hiszpanii</h2>
<p>Przy nowym domu płacisz 10% IVA i podatek od aktu (AJD), przy domu z rynku wtórnego – podatek od przeniesienia własności (ITP): 9% w regionie Walencji i 7,75% w Murcji (stan na 2026 r.). Do tego notariusz, rejestr i prawnik. Szczegóły i przykładowe wyliczenia znajdziesz w <a href="{guide}">poradniku zakupu krok po kroku</a>.</p>
""",
    },
    {
        "slug": "nieruchomosci-costa-calida/", "nav": "Nieruchomości Costa Cálida",
        "title": "Nieruchomości Costa Cálida i Mar Menor – mieszkania i domy na sprzedaż",
        "h1": "Nieruchomości na Costa Cálida",
        "eyebrow": "Murcja · Mar Menor",
        "lead": "Mieszkania, domy i wille na Costa Cálida: nad ciepłą laguną Mar Menor, przy polach golfowych i na spokojnym wybrzeżu regionu Murcji.",
        "match": lambda p: p["grp"] == "cc", "q": {"grp": "cc"},
        "body": """
<h2>Costa Cálida – „gorące wybrzeże”</h2>
<p>Costa Cálida to wybrzeże regionu Murcji, graniczące od północy z Costa Blanca. Jego sercem jest <strong>Mar Menor</strong> – płytka, słona laguna z ciepłą wodą, idealna dla rodzin z dziećmi i sportów wodnych. Region słynie też z kompleksów golfowych i cen niższych niż w prowincji Alicante.</p>
<p>Najpopularniejsze lokalizacje to Los Alcázares, San Pedro del Pinatar, San Javier, Torre Pacheco, La Manga del Mar Menor i Águilas. Najbliższe lotnisko to Murcja (Corvera), a lotnisko w Alicante jest ok. godziny drogi.</p>
""",
    },
    {
        "slug": "inwestycje-w-hiszpanii/", "nav": "Inwestycje w Hiszpanii",
        "title": "Inwestycje w nieruchomości w Hiszpanii – mieszkania pod wynajem",
        "h1": "Inwestycje w nieruchomości w Hiszpanii",
        "eyebrow": "Pod wynajem · blisko plaży",
        "lead": "Nieruchomości w Hiszpanii jako inwestycja: mieszkania i apartamenty blisko plaży, z licencją turystyczną lub w lokalizacjach z popytem na najem przez cały rok.",
        "match": lambda p: p.get("tour") or 0 < p["beach"] <= 800, "q": {"beach": 1},
        "body": """
<h2>Dlaczego Polacy inwestują w Hiszpanii?</h2>
<p>Hiszpania to jeden z najczęściej odwiedzanych krajów świata, a Costa Blanca i Costa Cálida przyciągają turystów i „zimujących” emerytów z całej Europy przez cały rok. Mieszkanie blisko plaży może służyć Tobie na urlop, a w pozostałym czasie przynosić dochód z najmu.</p>
<h2>Na co patrzeć, inwestując?</h2>
<ul>
<li><strong>Lokalizacja:</strong> odległość od plaży, dojazd z lotniska, życie poza sezonem.</li>
<li><strong>Licencja turystyczna:</strong> w regionie Walencji zasady najmu krótkoterminowego się zaostrzają, a wspólnota może go zakazać – sprawdź to przed zakupem.</li>
<li><strong>Koszty stałe:</strong> wspólnota, IBI (podatek od nieruchomości), ubezpieczenie, zarządzanie najmem.</li>
<li><strong>Podatki od najmu:</strong> jako nierezydent rozliczasz w Hiszpanii podatek IRNR od dochodu z najmu (19% dla rezydentów UE, z możliwością odliczenia kosztów).</li>
<li><strong>Nowe czy wtórne:</strong> nowe zwykle wynajmują się lepiej i mają niższe koszty utrzymania; wtórne – są od razu gotowe i często w lepszej lokalizacji.</li>
</ul>
<p>Pomogę policzyć opłacalność konkretnej oferty i sprawdzić możliwość licencji. Zacznij od <a href="{guide}">bezpłatnego poradnika</a> albo napisz do mnie.</p>
""",
    },
]

FAQ_OFFICE = [
    ("Czy mogę kupić nieruchomość w Hiszpanii bez znajomości hiszpańskiego?",
     "Tak. Prowadzę Cię po polsku przez cały proces, a dokumenty, które podpisujesz, są tłumaczone. Przy akcie notarialnym możesz też mieć tłumacza przysięgłego."),
    ("Czy muszę przyjeżdżać do Hiszpanii, żeby kupić mieszkanie?",
     "Nie zawsze. Mieszkania można obejrzeć na wideo, a do podpisania umów i aktu notarialnego możesz udzielić pełnomocnictwa prawnikowi. Większość klientów przyjeżdża jednak przynajmniej raz, żeby zobaczyć okolicę."),
    ("Ile kosztuje Twoja pomoc przy zakupie?",
     "Przy nowych inwestycjach od deweloperów moje wynagrodzenie płaci zwykle deweloper, więc nie płacisz więcej niż kupując bezpośrednio. Przy innych transakcjach zasady ustalamy na początku, przejrzyście."),
    ("Czy pomagasz w uzyskaniu kredytu?",
     "Tak, współpracuję z doradcami i bankami, które udzielają kredytów nierezydentom. Zwykle bank finansuje do ok. 60–70% wartości nieruchomości."),
]


def guide_body(base):
    """Treść poradnika (strona + PDF). Stawki: stan na październik 2026."""
    return f"""
<p class="g-note">Aktualizacja: październik 2026. Stawki podatków są orientacyjne – każdą transakcję weryfikuje prawnik.</p>

<h2 id="krok-1">1. Ustal budżet razem z kosztami zakupu</h2>
<p>Najczęstszy błąd to liczenie samej ceny mieszkania. W Hiszpanii do ceny trzeba doliczyć <strong>ok. 10–14% kosztów zakupu</strong>. Ich wysokość zależy od tego, czy kupujesz nową nieruchomość od dewelopera, czy z rynku wtórnego, i w którym regionie.</p>
<table class="g-table">
<thead><tr><th></th><th>Rynek wtórny</th><th>Nowa nieruchomość</th></tr></thead>
<tbody>
<tr><th>Podatek główny</th><td>ITP: 9% (region Walencji*), 7,75% (Murcja)</td><td>IVA: 10% (garaż i komórka kupione osobno: 21%)</td></tr>
<tr><th>Podatek od aktu</th><td>–</td><td>AJD: 1,4% (Walencja), 1,5% (Murcja)</td></tr>
<tr><th>Notariusz i rejestr</th><td colspan="2">ok. 0,5–1% ceny</td></tr>
<tr><th>Prawnik</th><td colspan="2">zwykle ok. 1% ceny + 21% IVA</td></tr>
</tbody>
</table>
<p class="small">* W regionie Walencji (prowincja Alicante, czyli Costa Blanca) ITP wynosi 9% od 1 czerwca 2026 r., a dla nieruchomości powyżej 1 000 000 € – 11%. Istnieją stawki obniżone (np. dla rodzin wielodzietnych), ale przy zakupie drugiego domu zwykle nie mają zastosowania.</p>
<p><strong>Przykład:</strong> mieszkanie z rynku wtórnego w Torreviei za 200 000 € to ok. 18 000 € ITP, ok. 1 500 € notariusz i rejestr oraz ok. 2 400 € prawnik – razem ok. 22 000 €. To samo mieszkanie jako nowe od dewelopera: 20 000 € IVA, 2 800 € AJD i podobne opłaty – razem ok. 26 500 €.</p>

<h2 id="krok-2">2. Załatw numer NIE i hiszpańskie konto</h2>
<p><strong>NIE</strong> (Número de Identidad de Extranjero) to numer identyfikacyjny cudzoziemca – bez niego nie kupisz nieruchomości, nie podpiszesz aktu notarialnego ani nie podłączysz mediów. Możesz go uzyskać na policji w Hiszpanii (po wcześniejszym umówieniu wizyty), w konsulacie Hiszpanii w Polsce albo przez prawnika na podstawie pełnomocnictwa.</p>
<p>Przyda się też <strong>konto w hiszpańskim banku</strong>: z niego płacisz cenę, podatki, a później rachunki i opłaty wspólnoty.</p>

<h2 id="krok-3">3. Sprawdź możliwości kredytu</h2>
<p>Hiszpańskie banki udzielają kredytów nierezydentom, zwykle do <strong>ok. 60–70% wartości nieruchomości</strong>. Resztę ceny i koszty zakupu trzeba pokryć z własnych środków. Bank ocenia Twoje dochody w Polsce i zadłużenie, a proces trwa zwykle kilka tygodni. Jeśli planujesz kredyt, załatw wstępną decyzję jeszcze przed rezerwacją.</p>

<h2 id="krok-4">4. Wybierz region i typ nieruchomości</h2>
<p><strong>Costa Blanca Północ</strong> (Benidorm, Finestrat, Altea, Calpe, Jávea) – widoki, góry, prestiżowe lokalizacje. <strong>Costa Blanca Południe</strong> (Torrevieja, Orihuela Costa, Guardamar) – piaszczyste plaże, golf, niższe ceny. <strong>Costa Cálida</strong> (Mar Menor) – ciepła laguna, spokój, niższy ITP. Zastanów się, czy kupujesz dla siebie, pod wynajem, czy jedno i drugie – od tego zależy wybór lokalizacji.</p>
<p>Zobacz oferty: <a href="{base}nieruchomosci-costa-blanca/">nieruchomości Costa Blanca</a>, <a href="{base}mieszkania-costa-blanca/">mieszkania</a>, <a href="{base}domy-costa-blanca/">domy</a> i <a href="{base}nieruchomosci-costa-calida/">Costa Cálida</a>.</p>

<h2 id="krok-5">5. Oglądanie: na miejscu lub online</h2>
<p>Najlepiej przyjechać na 3–4 dni i zobaczyć kilka wybranych wcześniej ofert oraz okolicę o różnych porach dnia. Jeśli nie możesz przyjechać, nieruchomość można obejrzeć na wideo na żywo. Zwróć uwagę na orientację (słońce), hałas, opłaty wspólnoty i to, czy okolica żyje poza sezonem.</p>

<h2 id="krok-6">6. Rezerwacja i umowa przedwstępna (arras)</h2>
<p>Po wyborze nieruchomości wpłacasz <strong>opłatę rezerwacyjną</strong> (zwykle 3 000–10 000 €), która zdejmuje ofertę z rynku. Następnie podpisujesz <strong>umowę przedwstępną</strong> – na rynku wtórnym najczęściej <em>contrato de arras</em> z zadatkiem ok. 10% ceny. Uwaga: jeśli wycofasz się bez uzasadnienia, tracisz zadatek, a jeśli wycofa się sprzedający – zwraca go w podwójnej wysokości.</p>
<p>Przy <strong>nowych inwestycjach</strong> płacisz zwykle w ratach w trakcie budowy (np. 30–50% przed odbiorem). Wpłaty powinny być zabezpieczone <strong>gwarancją bankową lub polisą</strong> – to Twój obowiązkowy parasol ochronny, jeśli deweloper nie dokończy budowy.</p>

<h2 id="krok-7">7. Weryfikacja prawna</h2>
<p>Zanim zapłacisz większą kwotę, niezależny prawnik powinien sprawdzić:</p>
<ul>
<li><strong>nota simple</strong> z rejestru nieruchomości – kto jest właścicielem i czy nie ma hipotek ani obciążeń,</li>
<li>zgodność stanu faktycznego z rejestrem i katastrem (np. dobudowane tarasy czy baseny),</li>
<li>brak zaległości w podatku IBI i opłatach wspólnoty,</li>
<li>przy nowych: pozwolenie na budowę, gwarancje bankowe, a przed odbiorem – licencję na zamieszkanie (LPO / cédula),</li>
<li>certyfikat energetyczny i – jeśli planujesz najem – możliwość uzyskania licencji turystycznej.</li>
</ul>

<h2 id="krok-8">8. Akt notarialny (escritura) i rejestr</h2>
<p>Własność przechodzi na Ciebie przy podpisaniu <strong>aktu notarialnego</strong> u hiszpańskiego notariusza. W tym dniu płacisz resztę ceny (zwykle czekiem bankowym lub przelewem), dostajesz klucze, a prawnik w ciągu kilku tygodni opłaca podatki i wpisuje Cię do <strong>rejestru nieruchomości</strong>. Jeśli nie możesz przyjechać, akt może podpisać Twój pełnomocnik.</p>

<h2 id="krok-9">9. Po zakupie: media i coroczne podatki</h2>
<ul>
<li>przepisanie prądu, wody, internetu i ubezpieczenia (z polecenia przy zakupie zajmuje to kilka dni),</li>
<li><strong>IBI</strong> – roczny podatek od nieruchomości płacony gminie, plus opłata za wywóz śmieci,</li>
<li><strong>IRNR</strong> – podatek dochodowy nierezydentów: płacisz go od mieszkania także wtedy, gdy go nie wynajmujesz (od tzw. dochodu przypisanego), a przy najmie – od dochodu z najmu,</li>
<li>opłaty wspólnoty mieszkaniowej (comunidad), jeśli nieruchomość jest w kompleksie.</li>
</ul>

<h2 id="krok-10">10. Jak pomaga polskie biuro nieruchomości?</h2>
<p>Jako polska agentka z licencją RAICV 4368 przeprowadzam Cię przez cały proces po polsku: dobieram oferty pod Twój budżet, organizuję oglądanie (także online), negocjuję, polecam sprawdzonych prawników i doradców kredytowych, jestem przy notariuszu i pomagam po zakupie. Przy nowych inwestycjach moje wynagrodzenie płaci zwykle deweloper.</p>
"""


GUIDE_FAQ = [
    ("Ile wynoszą koszty zakupu nieruchomości w Hiszpanii?",
     "Zwykle 10–14% ceny. Na rynku wtórnym w regionie Walencji to głównie podatek ITP 9%, w Murcji 7,75%. Przy nowej nieruchomości płacisz 10% IVA i 1,4–1,5% AJD. Do tego notariusz, rejestr i prawnik."),
    ("Czy Polak może kupić nieruchomość w Hiszpanii?",
     "Tak. Obywatele UE kupują nieruchomości w Hiszpanii bez ograniczeń. Potrzebny jest numer NIE i najlepiej konto w hiszpańskim banku."),
    ("Jak długo trwa zakup nieruchomości w Hiszpanii?",
     "Przy rynku wtórnym zwykle 4–8 tygodni od rezerwacji do aktu notarialnego. Przy nowej inwestycji – do zakończenia budowy, z płatnościami rozłożonymi na etapy."),
    ("Czy hiszpański bank da kredyt Polakowi?",
     "Tak, banki udzielają kredytów nierezydentom, zwykle do ok. 60–70% wartości nieruchomości, po ocenie dochodów."),
]


# ---------- budowa stron ----------
def build_pages(B, props, stats, ver, dist):
    urls = []
    by_town = {}
    for p in props:
        if p["town"]:
            by_town.setdefault(tname(p["town"]), []).append(p)
    towns = {n: ps for n, ps in by_town.items() if len(ps) >= MIN_TOWN}
    town_url = lambda n: f"{TOWNS_HUB}{slug(n)}/"
    top_towns = sorted(towns, key=lambda n: -len(towns[n]))

    def sort_props(ps):
        return sorted(ps, key=lambda p: (p["src"] != "indomito", p.get("market") != "resale", p["price"] or 9e9))

    def cards(ps, base):
        return "".join(B.card_html(p, "pl", base) for p in sort_props(ps)[:MAX_CARDS])

    def more_link(base, q, n):
        if n <= MAX_CARDS: return ""
        qs = "&".join(f"{k}={B.urllib.parse.quote(str(v))}" for k, v in q.items())
        return f'<div class="seo-more"><a class="btn" href="{base}?{qs}#oferty">Zobacz wszystkie {offers_word(n)} w wyszukiwarce</a></div>'

    def facts(ps):
        prices = [p["price"] for p in ps if p["price"]]
        out = [f'<span><b class="num">{len(ps)}</b> {pl_num(len(ps), "oferta", "oferty", "ofert")}</span>']
        if prices:
            out.append(f'<span>od <b class="num">{price_pl(min(prices))}</b></span>')
        tw = len({p["town"] for p in ps})
        if tw > 1:
            out.append(f'<span><b class="num">{tw}</b> {pl_num(tw, "miejscowość", "miejscowości", "miejscowości")}</span>')
        return '<div class="seo-facts">' + "".join(out) + "</div>"

    def ld(obj):
        return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False).replace("</", "<\\/") + "</script>"

    def crumbs_ld(items):
        return ld({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": n, "item": B.SITE + u} for i, (n, u) in enumerate(items)]})

    def itemlist_ld(ps):
        return ld({"@context": "https://schema.org", "@type": "ItemList", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "url": B.SITE + B.offer_path("pl", p["ref"])}
            for i, p in enumerate(sort_props(ps)[:MAX_CARDS])]})

    guide_banner = lambda base: (
        f'<aside class="seo-lm"><div><div class="eyebrow">Bezpłatny poradnik PDF</div>'
        f'<h2>Zakup nieruchomości w Hiszpanii krok po kroku</h2>'
        f'<p>Koszty i podatki w 2026 r., NIE, kredyt, umowy i lista kontrolna – wszystko po polsku, w jednym pliku.</p></div>'
        f'<a class="btn gold" href="{base}{GUIDE}#pobierz">Pobierz poradnik</a></aside>')

    def related(base, current):
        cats = "".join(f'<li><a href="{base}{c["slug"]}">{E(c["nav"])}</a></li>' for c in CATS if c["slug"] != current)
        tw = "".join(f'<li><a href="{base}{town_url(n)}">{E(n)}</a></li>' for n in top_towns[:18] if town_url(n) != current)
        return (f'<section class="seo-rel"><div><h2>Szukaj dalej</h2><ul>{cats}<li><a href="{base}{OFFICE}">Polskie biuro nieruchomości w Hiszpanii</a></li>'
                f'<li><a href="{base}{GUIDE}">Poradnik: zakup krok po kroku</a></li></ul></div>'
                f'<div><h2>Popularne miejscowości</h2><ul>{tw}<li><a href="{base}{TOWNS_HUB}">Wszystkie miejscowości</a></li></ul></div></section>')

    def contact_cta(ctx):
        return (f'<section class="seo-cta"><div class="eyebrow">Polskie biuro nieruchomości w Hiszpanii</div>'
                f'<h2>Porozmawiajmy o Twoim budżecie i planach</h2>'
                f'<p>Napisz, czego szukasz – w ciągu 24 godzin przygotuję wybór ofert dopasowany do Ciebie.</p>'
                f'<div class="seo-btns"><a class="btn gold" href="{ctx["wa_link"]}" target="_blank" rel="noopener">{E(B.T["pl"]["wa_btn"])}</a>'
                f'<a class="btn" href="{ctx["home"]}#kontakt">Formularz kontaktowy</a></div></section>')

    def faq_html(faq):
        items = "".join(f"<details><summary>{E(q)}</summary><p>{E(a)}</p></details>" for q, a in faq)
        return f'<section class="seo-faq"><h2>Najczęstsze pytania</h2>{items}</section>' + ld({
            "@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
                {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]})

    def page_html(page, title, desc, h1, eyebrow, lead, crumbs, body, og_img=None, extra_head=""):
        paths = {"pl": page, "es": B.HOME["es"], "en": B.HOME["en"]}
        ctx = B.common_ctx("pl", page, paths, B.T["pl"]["js"]["wa_hello"], stats, ver)
        ctx["alternates"] = f'<link rel="alternate" hreflang="pl" href="{B.SITE}{page}">'
        ctx["HEAD"] = B.render(B.read("glowa.html"), ctx)
        base = ctx["base"]
        cr = "".join(f'<a href="{base}{u}">{E(n)}</a><span aria-hidden="true">/</span>' for n, u in crumbs[:-1]) + f"<span>{E(crumbs[-1][0])}</span>"
        img = og_img or B.SITE + "logo-pelne.png"
        body = body(ctx, base) if callable(body) else body
        out = (f'<!doctype html><html lang="pl"><head>{ctx["HEAD"]}<title>{E(title)} | Indómito</title>'
               f'<meta name="description" content="{E(desc)}"><meta property="og:type" content="website">'
               f'<meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}">'
               f'<meta property="og:image" content="{E(img)}"><meta property="og:url" content="{B.SITE}{page}">'
               f'<link rel="canonical" href="{B.SITE}{page}">{crumbs_ld([("Strona główna", "")] + crumbs)}{extra_head}</head>'
               f'<body>{ctx["HEADER"]}<main class="seo"><div class="wrap">'
               f'<nav class="crumbs" aria-label="breadcrumb"><a href="{ctx["home"]}">Strona główna</a><span aria-hidden="true">/</span>{cr}</nav>'
               f'<header class="seo-hero"><div class="eyebrow">{E(eyebrow)}</div><h1>{E(h1)}</h1><p class="lead">{E(lead)}</p></header>'
               f'{body}</div></main>{ctx["FOOTER"]}</body></html>')
        B.write(dist, page, out)
        urls.append(page)

    def og_of(ps):
        for p in sort_props(ps):
            if p["imgs"] and re.match(r"https?://", p["imgs"][0]):
                return p["imgs"][0]

    # kategorie
    for c in CATS:
        ps = [p for p in props if c["match"](p)]
        if not ps: continue
        def body(ctx, base, c=c, ps=ps):
            text = c["body"].replace("{guide}", base + GUIDE).replace("{base}", base)
            return (facts(ps) + f'<div class="seo-grid"><article class="seo-text">{text}</article>{guide_banner(base)}</div>'
                    f'<section class="seo-list"><h2>{E(c["h1"])}: wybrane oferty</h2><div class="grid">{cards(ps, base)}</div>'
                    f'{more_link(base, c["q"], len(ps))}</section>{related(base, c["slug"])}{contact_cta(ctx)}')
        desc = f'{c["lead"][:120].rsplit(" ", 1)[0]}… {offers_word(len(ps)).capitalize()}, ceny od {price_pl(min([p["price"] for p in ps if p["price"]] or [0]))}.'
        page_html(c["slug"], c["title"], desc, c["h1"], c["eyebrow"], c["lead"], [(c["nav"], c["slug"])], body,
                  og_of(ps), itemlist_ld(ps))

    # miejscowości
    for n in top_towns:
        ps = towns[n]
        page = town_url(n)
        grp = max({"cbn", "cbs", "cc"}, key=lambda g: sum(p["grp"] == g for p in ps))
        reg = REG_PL[grp]
        kinds = {k: sum(p.get("kind") == k for p in ps) for k in ("apt", "house", "villa")}
        prices = sorted(p["price"] for p in ps if p["price"])
        near = [q for q in props if q["grp"] == grp and tname(q["town"]) != n]
        near_towns = sorted({tname(q["town"]) for q in near if tname(q["town"]) in towns}, key=lambda t: -len(towns[t]))[:6]
        L = loc(n)
        parts = []
        if kinds["apt"]: parts.append(f'{kinds["apt"]} {pl_num(kinds["apt"], "mieszkanie lub apartament", "mieszkania i apartamenty", "mieszkań i apartamentów")}')
        if kinds["house"]: parts.append(f'{kinds["house"]} {pl_num(kinds["house"], "dom", "domy", "domów")}')
        if kinds["villa"]: parts.append(f'{kinds["villa"]} {pl_num(kinds["villa"], "willa", "wille", "willi")}')
        resale = sum(p.get("market") == "resale" for p in ps)
        h1 = f"Nieruchomości {L}"
        title = f"Nieruchomości {n} – mieszkania i domy na sprzedaż {L}"
        lead = f"Mieszkania, apartamenty i domy na sprzedaż {L} ({reg}). Aktualne oferty od deweloperów" + (" i z rynku wtórnego" if resale else "") + " – z pomocą polskiego biura nieruchomości."
        intro = f"<h2>Kupno nieruchomości {L}</h2><p>{E(NOTE.get(n, f'{n} leży w regionie {reg}.'))}</p>"
        intro += (f"<p>Obecnie mam tu {offers_word(len(ps))}: " + ", ".join(parts) + "."
                  + (f" Ceny zaczynają się od {price_pl(prices[0])}, a połowa ofert kosztuje mniej niż {price_pl(int(median(prices)) // 1000 * 1000)}." if prices else "")
                  + "</p>")
        intro += f'<p>Sprawdź też, ile wynoszą podatki i koszty zakupu – wszystko opisałam w <a href="{{guide}}">poradniku zakupu nieruchomości w Hiszpanii</a>.</p>'
        q = {"town": n}
        def body(ctx, base, ps=ps, intro=intro, near=near, near_towns=near_towns, q=q, page=page, n=n, L=L):
            near_block = ""
            if near_towns:
                near_ps = [x for t in near_towns for x in sort_props(towns[t])[:2]][:6]
                links = " · ".join(f'<a href="{base}{town_url(t)}">{E(t)}</a>' for t in near_towns)
                near_block = (f'<section class="seo-list"><h2>W okolicy</h2><p class="seo-near">{links}</p>'
                              f'<div class="grid">{"".join(B.card_html(x, "pl", base) for x in near_ps)}</div></section>')
            return (facts(ps) + f'<div class="seo-grid"><article class="seo-text">{intro.replace("{guide}", base + GUIDE)}</article>{guide_banner(base)}</div>'
                    f'<section class="seo-list"><h2>Oferty {E(L)}</h2><div class="grid">{cards(ps, base)}</div>{more_link(base, q, len(ps))}</section>'
                    f'{near_block}{related(base, page)}{contact_cta(ctx)}')
        desc = f'{offers_word(len(ps)).capitalize()} {L}: ' + ", ".join(parts) + (f". Ceny od {price_pl(prices[0])}." if prices else ".") + " Polskie biuro nieruchomości."
        page_html(page, title, desc, h1, reg, lead, [("Miejscowości", TOWNS_HUB), (n, page)], body, og_of(ps), itemlist_ld(ps))

    # lista miejscowości
    def hub(ctx, base):
        out = ""
        for g in ("cbn", "cbs", "cc"):
            ts = sorted((t for t in towns if max({"cbn", "cbs", "cc"}, key=lambda x: sum(p["grp"] == x for p in towns[t])) == g), key=lambda t: t)
            if not ts: continue
            li = "".join(f'<li><a href="{base}{town_url(t)}">{E(t)}</a><span class="num">{len(towns[t])}</span></li>' for t in ts)
            out += f'<section class="seo-towns"><h2>{REG_PL[g]}</h2><ul>{li}</ul></section>'
        return out + guide_banner(base) + contact_cta(ctx)
    page_html(TOWNS_HUB, "Nieruchomości w Hiszpanii według miejscowości – Costa Blanca i Costa Cálida",
              f"Mieszkania i domy na sprzedaż w {len(towns)} miejscowościach Costa Blanca i Costa Cálida: Torrevieja, Benidorm, Finestrat, Alicante i inne.",
              "Nieruchomości według miejscowości", "Costa Blanca · Costa Cálida",
              "Wybierz miejscowość, żeby zobaczyć aktualne mieszkania, apartamenty i domy na sprzedaż oraz krótki opis okolicy.",
              [("Miejscowości", TOWNS_HUB)], hub)

    # polskie biuro nieruchomości
    own = [p for p in props if p["src"] == "indomito"]
    agent_ld = ld({
        "@context": "https://schema.org", "@type": "RealEstateAgent", "name": "Indómito Real Estate – Klaudia Szafran",
        "url": B.SITE + OFFICE, "image": B.SITE + "portret.jpg", "logo": B.SITE + "logo-pelne.png",
        "telephone": "+34 613 15 27 55", "email": "info@indomitore.com", "priceRange": "€€",
        "address": {"@type": "PostalAddress", "streetAddress": "Calle Marqués de Sotelo 5, bajo 5", "postalCode": "46002",
                    "addressLocality": "Valencia", "addressCountry": "ES"},
        "areaServed": ["Costa Blanca", "Costa Cálida", "Alicante", "Murcia"], "knowsLanguage": ["pl", "es", "en"],
        "sameAs": ["https://www.instagram.com/indomitore/"]})
    def office(ctx, base):
        text = f"""
<h2>Kim jestem?</h2>
<p>Nazywam się <strong>Klaudia Szafran</strong> i prowadzę <strong>Indómito Real Estate</strong> – polskie biuro nieruchomości w Hiszpanii z licencją agenta nieruchomości RAICV 4368. Mieszkam na Costa Blanca i na co dzień pomagam Polakom kupić mieszkanie, apartament lub dom nad morzem: na własne potrzeby, na emeryturę albo jako inwestycję.</p>
<h2>W czym pomagam?</h2>
<ul>
<li><strong>Wybór ofert</strong> pod Twój budżet: ponad {B.headline_count(stats["dev"])} nowych inwestycji od deweloperów i wybrane nieruchomości z rynku wtórnego.</li>
<li><strong>Oglądanie</strong> na miejscu lub online, na wideo na żywo.</li>
<li><strong>Negocjacje</strong> ceny i warunków.</li>
<li><strong>Formalności:</strong> NIE, konto w banku, sprawdzony prawnik, doradca kredytowy, tłumacz u notariusza.</li>
<li><strong>Po zakupie:</strong> media, ubezpieczenie, wyposażenie, zarządzanie najmem.</li>
</ul>
<h2>Dlaczego polskie biuro?</h2>
<p>Zakup w obcym kraju to inne prawo, inne podatki i dokumenty w obcym języku. Ze mną rozmawiasz po polsku, rozumiesz każdy krok i każdy koszt, zanim cokolwiek podpiszesz. Przy nowych inwestycjach moje wynagrodzenie płaci zwykle deweloper.</p>
<p>Zacznij od <a href="{base}{GUIDE}">poradnika zakupu krok po kroku</a> albo napisz do mnie – przygotuję wybór ofert dla Ciebie.</p>
"""
        lst = f'<section class="seo-list"><h2>Moje oferty</h2><div class="grid">{"".join(B.card_html(p, "pl", base) for p in own[:6])}</div></section>' if own else ""
        return (f'<div class="seo-grid"><article class="seo-text">{text}</article>{guide_banner(base)}</div>{lst}'
                f'{faq_html(FAQ_OFFICE)}{related(base, OFFICE)}{contact_cta(ctx)}')
    page_html(OFFICE, "Polskie biuro nieruchomości w Hiszpanii – Costa Blanca",
              "Polskie biuro nieruchomości w Hiszpanii: Klaudia Szafran, Indómito Real Estate (RAICV 4368). Mieszkania i domy na Costa Blanca i Costa Cálida, pomoc w zakupie po polsku.",
              "Polskie biuro nieruchomości w Hiszpanii", "Indómito Real Estate · Klaudia Szafran",
              "Kupujesz mieszkanie lub dom w Hiszpanii? Przeprowadzę Cię przez cały zakup po polsku – od wyboru oferty po akt notarialny i klucze.",
              [("Polskie biuro nieruchomości w Hiszpanii", OFFICE)], office, B.SITE + "portret.jpg", agent_ld)

    # poradnik + lead magnet
    article_ld = ld({"@context": "https://schema.org", "@type": "Article",
                     "headline": "Zakup nieruchomości w Hiszpanii krok po kroku – poradnik 2026",
                     "author": {"@type": "Person", "name": "Klaudia Szafran"},
                     "publisher": {"@type": "Organization", "name": "Indómito Real Estate", "logo": {"@type": "ImageObject", "url": B.SITE + "logo-pelne.png"}},
                     "dateModified": "2026-10-19", "inLanguage": "pl", "mainEntityOfPage": B.SITE + GUIDE})
    def guide(ctx, base):
        form = (f'<aside class="lm-box" id="pobierz"><div class="eyebrow">Bezpłatny PDF</div>'
                f'<h2>Pobierz poradnik w PDF</h2>'
                f'<p>Cały poradnik + <strong>lista kontrolna zakupu</strong> i tabela kosztów do wydrukowania. Wyślę Ci też najciekawsze oferty – możesz zrezygnować w każdej chwili.</p>'
                f'<form class="lm-form" data-guide novalidate>'
                f'<input name="name" autocomplete="given-name" placeholder="Imię" aria-label="Imię">'
                f'<input name="email" type="email" autocomplete="email" placeholder="Twój e-mail" aria-label="Twój e-mail" required>'
                f'<input class="hp" name="website" tabindex="-1" autocomplete="off" aria-hidden="true">'
                f'<label class="consent"><input type="checkbox" name="consent_mkt" required> <span>Chcę otrzymać poradnik i oferty nieruchomości e-mailem. Mogę zrezygnować w każdej chwili. <a href="{ctx["privacy_url"]}">{E(B.T["pl"]["priv"])}</a></span></label>'
                f'<button class="btn gold" type="submit">Pobierz bezpłatnie</button><p class="note" data-note></p></form>'
                f'<div class="lm-ok" hidden><p><strong>Dziękuję!</strong> Twój poradnik jest gotowy:</p>'
                f'<a class="btn gold" href="{base}{GUIDE_PDF}" download>Pobierz PDF</a></div></aside>')
        toc = "".join(f'<li><a href="#{a}">{E(t)}</a></li>' for a, t in re.findall(r'<h2 id="([^"]+)">([^<]+)</h2>', guide_body(base)))
        script = """<script>
(function(){
  const f = document.querySelector("form[data-guide]"); if (!f) return;
  const box = f.closest(".lm-box"), note = f.querySelector("[data-note]");
  const say = (m, bad) => { note.textContent = m; note.classList.toggle("bad", !!bad); };
  f.addEventListener("submit", async e => {
    e.preventDefault();
    if (f.elements.website.value) return;
    const email = f.elements.email.value.trim();
    if (!/^[^\\s@]+@[^\\s@]+\\.[^\\s@]{2,}$/.test(email)) return say("Wpisz poprawny adres e-mail.", true);
    if (!f.elements.consent_mkt.checked) return say("Zaznacz zgodę, żeby otrzymać poradnik.", true);
    say("Wysyłam…");
    try {
      const r = await fetch(window.FORM.endpoint, {method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({type: "newsletter", name: f.elements.name.value.trim(), email, lang: "pl", consent_mkt: true,
          page: "Poradnik PDF – zakup nieruchomości w Hiszpanii (" + location.href + ")"})});
      if (!r.ok) throw 0;
      f.hidden = true; box.querySelector(".lm-ok").hidden = false;
      try { localStorage.setItem("indomito_nl", "done"); } catch (e) {}
      if (window.gtag) gtag("event", "generate_lead", {method: "poradnik"});
    } catch (e) { say("Coś poszło nie tak. Spróbuj ponownie albo napisz na info@indomitore.com.", true); }
  });
})();
</script>"""
        return (f'<div class="g-wrap"><article class="seo-text guide"><nav class="g-toc"><b>Spis treści</b><ul>{toc}</ul></nav>{guide_body(base)}</article>'
                f'<div class="g-side">{form}</div></div>{faq_html(GUIDE_FAQ)}{related(base, GUIDE)}{contact_cta(ctx)}{script}')
    page_html(GUIDE, "Zakup nieruchomości w Hiszpanii krok po kroku – poradnik 2026",
              "Jak kupić mieszkanie lub dom w Hiszpanii? Koszty i podatki 2026 (ITP, IVA, AJD), NIE, kredyt, umowa arras, notariusz. Bezpłatny poradnik PDF od polskiego biura nieruchomości.",
              "Zakup nieruchomości w Hiszpanii krok po kroku", "Poradnik 2026 · bezpłatny PDF",
              "Wszystko, co musisz wiedzieć, zanim kupisz mieszkanie lub dom w Hiszpanii: koszty, podatki, formalności i pułapki – w 10 krokach, po polsku.",
              [("Poradnik zakupu", GUIDE)], guide, None, article_ld)
    return urls


def footer_links(base):
    """Linki SEO w stopce (tylko po polsku)."""
    items = [(c["nav"], c["slug"]) for c in CATS] + [("Polskie biuro nieruchomości w Hiszpanii", OFFICE),
                                                    ("Poradnik: zakup krok po kroku", GUIDE), ("Miejscowości", TOWNS_HUB)]
    return '<nav class="f-seo" aria-label="Popularne wyszukiwania">' + "".join(f'<a href="{base}{u}">{E(n)}</a>' for n, u in items) + "</nav>"
