# indomitore.com — strona Indómito Real Estate

Strona z ofertami nowych budów (feed RedSP) i ofertami bezpośrednimi Klaudii (Notion → baza „Nieruchomości”).
Co noc GitHub sam pobiera feed, buduje stronę i publikuje ją pod indomitore.com. Hosting jest darmowy, a limit 1 GB w Nominalii nie ma znaczenia: Nominalia trzyma tylko domenę i pocztę.

## Co jest w środku

| Plik | Do czego |
|---|---|
| `build.py` | Pobiera feed RedSP i oferty z Notion, tłumaczy cechy na polski, składa stronę w `dist/` |
| `template.html` | Wygląd strony (kolory i fonty marki Indómito) |
| `.github/workflows/publikuj.yml` | Codzienna automatyczna aktualizacja i publikacja |

## Uruchomienie (jednorazowo)

1. **Konto GitHub.** Załóż darmowe konto na github.com (najlepiej na info@indomitore.com).
2. **Repozytorium.** Utwórz nowe repozytorium, np. `indomitore`, i wgraj do niego te pliki (przycisk *Add file → Upload files*, razem z folderem `.github`).
3. **Pages.** W repozytorium: *Settings → Pages → Build and deployment → Source: GitHub Actions*.
4. **Link do feedu.** *Settings → Secrets and variables → Actions → New repository secret*: nazwa `FEED_URL`, wartość = Twój link XML z RedSP (jest prywatny, dlatego nie ma go w kodzie).
5. **Pierwsza publikacja.** *Actions → Publikuj stronę indomitore.com → Run workflow*. Po kilku minutach strona działa pod adresem `twojanazwa.github.io/indomitore`.
6. **Domena.** W *Settings → Pages → Custom domain* wpisz `indomitore.com` i zapisz.
7. **DNS w Nominalii.** W panelu: indomitore.com → *Dominio y DNS* → rekordy DNS. **Nie zmieniaj serwerów DNS ani rekordów MX** (od nich zależy poczta).
   - rekord **A** dla `@` (indomitore.com): usuń obecny i dodaj cztery:
     `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`
   - rekord **CNAME** dla `www`: `twojanazwa.github.io`
8. Po 1–24 h wróć do *Settings → Pages* i zaznacz **Enforce HTTPS**.

## Oferty z Notion (opcjonalnie)

Na stronie pojawiają się automatycznie, z czerwonym znaczkiem „Oferta Indómito”, gdy w bazie *Nieruchomości*:
- **Źródło** = „Moja oferta bezpośrednia”,
- **Status** = „Dostępna” albo „Zarezerwowana”,
- dodane są **Zdjęcia**.

Podłączenie:
1. notion.so/my-integrations → *New integration* (w przestrzeni klaudia@indomitorealestate.com, tam gdzie jest Indómito OS) → skopiuj token.
2. W Notion otwórz bazę *Nieruchomości* → ••• → *Connections* → dodaj tę integrację.
3. W GitHub: *Settings → Secrets and variables → Actions*:
   - **Secret** `NOTION_TOKEN` = token z kroku 1,
   - **Variable** `NOTION_DB` = `c2033ff17f9b4c9cb09c1c0a59918261` (ID bazy Nieruchomości).

Dane właściciela i prowizja nie trafiają na stronę. Generator czyta tylko pola oferty: nazwę, cenę, typ, miejscowość, region, metraż, sypialnie, łazienki, opis, udogodnienia i zdjęcia.

## Lokalny podgląd

```
python3 build.py --feed feed.xml --out dist      # z pobranego pliku XML
python3 build.py --sample data/sample.json --inline --out preview   # próbka 36 ofert
```

## Oferty wyróżnione

Sekcja „Oferty wyróżnione” pod wyszukiwarką. Kolejność wyboru:
1. numery ofert z pliku `wyroznione.txt` (np. `N10053`, jeden w linii; edycja na GitHubie → ołówek → Commit),
2. oferty bezpośrednie z Notion (jeśli w bazie dodasz pole wyboru **Wyróżniona**, pokażą się tylko zaznaczone),
3. jeśli brakuje, strona sama dobiera prawdziwe oferty z feedu (basen, do 1 km od plaży, dużo zdjęć).

## Wideo w tle (sekcja otwierająca)

Wgraj do repozytorium (Add file → Upload files):
- `hero.mp4` — wideo poziome 16:9, bez dźwięku, 10–20 s, 1920×1080 lub 1280×720, najlepiej do 8 MB,
- opcjonalnie `hero.webm` (lżejsza wersja), `hero-mobile.mp4` (pionowy/kwadratowy kadr na telefon),
- opcjonalnie `hero.jpg` — kadr z filmu, pokazywany na telefonie i zanim wideo się wczyta.

Bez tych plików w tle jest zdjęcie pierwszej oferty wyróżnionej. Na telefonie domyślnie zdjęcie (szybciej), a wideo tylko gdy jest `hero-mobile.mp4`.

## Zdjęcie w sekcji „O mnie”

Wgraj do repozytorium plik `portret.jpg` (kwadratowe zdjęcie, min. 800×800 px, twarz na środku). Pojawi się w okrągłej złotej ramce. Bez pliku sekcja wyświetla się bez zdjęcia.
