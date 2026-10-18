// Formularze zapytań (strona główna i podstrony ofert) → pośrednik Cloudflare → baza Klienci w Notion
(function () {
  const C = window.FORM || {};
  document.querySelectorAll("form[data-lead]").forEach(f => {
    const note = f.querySelector("[data-note]"), btn = f.querySelector('button[type="submit"]');
    const say = (t, bad) => { if (note) { note.textContent = t; note.style.color = bad ? "var(--terra)" : ""; } };
    f.addEventListener("submit", async e => {
      e.preventDefault();
      const v = n => (f.elements[n] ? String(f.elements[n].value || "").trim() : "");
      if (!v("name") || !v("contact")) return say(C.err_missing, true);
      if (!f.elements.consent.checked) return say(C.err_consent, true);
      const reg = f.elements.region;
      const data = {
        name: v("name"), contact: v("contact"), budget: v("budget"), region: v("region"),
        regionName: reg && reg.value ? reg.selectedOptions[0].textContent : "", msg: v("msg"),
        offer: f.dataset.offer || "", page: location.href, lang: C.lang, consent: true, website: v("website"),
      };
      btn.disabled = true; say(C.sending);
      try {
        const r = await fetch(C.endpoint, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });
        if (!r.ok) throw new Error(r.status);
        f.reset(); say(C.ok);
        if (window.gtag) gtag("event", "generate_lead");
      } catch (err) {
        say(C.err, true); btn.disabled = false;
      }
    });
  });
})();
