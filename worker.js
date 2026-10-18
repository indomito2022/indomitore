// Cloudflare Worker "indomito-formularz": formularz ze strony indomitore.com → baza Klienci w Notion.
// Sekret NOTION_TOKEN ustawiony w Cloudflare (Settings → Variables and Secrets). Kodu nie trzeba ruszać.
const DB = "5b40305f6b6d43fc942249cdb8b67893";
const ORIGINS = ["https://indomitore.com", "https://www.indomitore.com", "https://indomito2022.github.io"];
const LANG = { pl: "Polski", es: "Hiszpański", en: "Angielski" };
const BUDGET = { b1: [null, 250000], b2: [250000, 400000], b3: [400000, 700000], b4: [700000, null] };

const cors = o => ({
  "Access-Control-Allow-Origin": ORIGINS.includes(o) ? o : ORIGINS[0],
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
  "Vary": "Origin",
});
const txt = s => [{ type: "text", text: { content: String(s).slice(0, 1900) } }];
const clean = (s, n = 500) => String(s || "").trim().slice(0, n);

export default {
  async fetch(req, env) {
    const origin = req.headers.get("Origin") || "";
    const h = cors(origin);
    const out = (status, body) => new Response(JSON.stringify(body), { status, headers: { ...h, "Content-Type": "application/json" } });
    if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: h });
    if (req.method !== "POST") return out(405, { ok: false });
    if (!ORIGINS.includes(origin)) return out(403, { ok: false });

    let d;
    try { d = await req.json(); } catch { return out(400, { ok: false }); }
    if (d.website) return out(200, { ok: true }); // pułapka na boty

    const name = clean(d.name, 120), phone = clean(d.phone, 40), email = clean(d.email, 120);
    if (!name || !phone || !email || !/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email) || phone.replace(/\D/g, "").length < 9)
      return out(400, { ok: false, error: "missing" });
    if (d.consent !== true) return out(400, { ok: false, error: "consent" });

    const today = new Date().toISOString().slice(0, 10);
    const notes = [
      d.msg && `Wiadomość: ${clean(d.msg, 1200)}`,
      d.regionName && `Region: ${clean(d.regionName, 80)}`,
      d.offer && `Oferta: ${clean(d.offer, 40)}`,
      d.page && `Strona: ${clean(d.page, 300)}`,
      `Zgoda RODO (odpowiedź na zapytanie): tak (${today})`,
      `Zgoda na otrzymywanie ofert (e-mail, telefon, WhatsApp): ${d.consent_mkt === true ? `tak (${today})` : "nie"}`,
    ].filter(Boolean).join("\n");

    const p = {
      "Imię i nazwisko": { title: txt(name) },
      "Telefon / WhatsApp": { phone_number: phone },
      "Email": { email },
      "Źródło leada": { select: { name: "Strona / formularz" } },
      "Etap": { status: { name: "Nowy lead" } },
      "Szuka – rynek": { multi_select: [{ name: "Nowe" }] },
      "Ostatni kontakt": { date: { start: today } },
      "Data następnego kroku": { date: { start: today } },
      "Następny krok": { rich_text: txt("Odpowiedzieć na zapytanie ze strony") },
      "Notatki": { rich_text: txt(notes) },
      "Zgoda na oferty": { checkbox: d.consent_mkt === true },
    };
    if (LANG[d.lang]) p["Język"] = { select: { name: LANG[d.lang] } };
    const b = BUDGET[d.budget];
    if (b) { if (b[0] != null) p["Budżet od"] = { number: b[0] }; if (b[1] != null) p["Budżet do"] = { number: b[1] }; }
    if (d.region === "cc") p["Szuka – lokalizacje"] = { multi_select: [{ name: "Costa Cálida" }] };

    const r = await fetch("https://api.notion.com/v1/pages", {
      method: "POST",
      headers: { Authorization: `Bearer ${env.NOTION_TOKEN}`, "Notion-Version": "2022-06-28", "Content-Type": "application/json" },
      body: JSON.stringify({ parent: { database_id: DB }, properties: p }),
    });
    if (!r.ok) { console.log("Notion error", r.status, await r.text()); return out(502, { ok: false }); }
    return out(200, { ok: true });
  },
};
