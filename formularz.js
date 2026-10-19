// Formularze zapytań (strona główna i podstrony ofert) → pośrednik Cloudflare → baza Klienci w Notion
(function () {
  const C = window.FORM || {};
  const okEmail = s => /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(s);
  const okPhone = s => /^\+?[\d\s().-]{7,}$/.test(s) && s.replace(/\D/g, "").length >= 9;
  document.querySelectorAll("form[data-lead]").forEach(f => {
    const note = f.querySelector("[data-note]"), btn = f.querySelector('button[type="submit"]');
    const say = (t, bad) => { if (note) { note.textContent = t; note.style.color = bad ? "var(--terra)" : ""; } };
    f.addEventListener("submit", async e => {
      e.preventDefault();
      const v = n => (f.elements[n] ? String(f.elements[n].value || "").trim() : "");
      if (!v("name") || !v("phone") || !v("email")) return say(C.err_missing, true);
      if (!okPhone(v("phone"))) { f.elements.phone.focus(); return say(C.err_phone, true); }
      if (!okEmail(v("email"))) { f.elements.email.focus(); return say(C.err_email, true); }
      if (!f.elements.consent.checked) return say(C.err_consent, true);
      const reg = f.elements.region;
      const data = {
        name: v("name"), phone: v("phone"), email: v("email"), budget: v("budget"), region: v("region"),
        regionName: reg && reg.value ? reg.selectedOptions[0].textContent : "", msg: v("msg"),
        offer: f.dataset.offer || "", page: location.href, lang: C.lang,
        consent: true, consent_mkt: !!(f.elements.consent_mkt && f.elements.consent_mkt.checked), website: v("website"),
      };
      btn.disabled = true; say(C.sending);
      try {
        const r = await fetch(C.endpoint, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });
        if (!r.ok) throw new Error(r.status);
        f.reset(); say(C.ok); btn.disabled = false;
        if (window.gtag) gtag("event", "generate_lead");
      } catch (err) {
        say(C.err, true); btn.disabled = false;
      }
    });
  });
  // zapis na newsletter (stopka każdej podstrony)
  document.querySelectorAll("form[data-news]").forEach(f => {
    const note = f.querySelector("[data-note]"), btn = f.querySelector('button[type="submit"]');
    const say = (t, bad) => { note.textContent = t; note.style.color = bad ? "var(--terra)" : ""; };
    f.addEventListener("submit", async e => {
      e.preventDefault();
      const email = f.elements.email.value.trim();
      if (!okEmail(email)) { f.elements.email.focus(); return say(C.err_email, true); }
      if (!f.elements.consent_mkt.checked) return say(C.nl_err_consent, true);
      btn.disabled = true; say(C.sending);
      try {
        const r = await fetch(C.endpoint, { method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ type: "newsletter", name: f.elements.name.value.trim(), email, lang: C.lang,
            page: location.href, consent_mkt: true, website: f.elements.website.value }) });
        if (!r.ok) throw new Error(r.status);
        f.reset(); say(C.nl_ok); mark("done");
        setTimeout(() => { const d = f.closest("dialog"); if (d && d.open) d.close(); }, 3500);
      } catch (err) { say(C.err, true); }
      btn.disabled = false;
    });
  });
  // okienko newslettera: pokazuje się po chwili lub po przewinięciu; „nie teraz” = przerwa 7 dni, zapis = nigdy więcej
  const dlg = document.getElementById("nlPop");
  if (dlg && dlg.showModal) {
    const open = () => { if (!dlg.open) dlg.showModal(); };
    const close = why => { if (dlg.open) dlg.close(); if (why) mark(why); };
    dlg.querySelectorAll("[data-nl-close]").forEach(b => b.addEventListener("click", () => close("later")));
    dlg.addEventListener("cancel", () => mark("later"));
    dlg.addEventListener("click", e => { if (e.target === dlg) close("later"); });
    document.querySelectorAll("[data-nl-open]").forEach(a => a.addEventListener("click", e => { e.preventDefault(); open(); }));
    const st = get();
    const wait = st === "done" || (st && Date.now() - +st < 7 * 864e5);
    let seen = false; try { seen = sessionStorage.getItem("nl_seen") === "1"; } catch (e) {}
    if (/[?&]nl=1/.test(location.search)) open();
    else if (!wait && !seen) {
      let fired = false;
      const busy = () => document.activeElement && /INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName);
      const fire = () => {
        if (fired) return;
        if (busy() || document.querySelector("dialog[open]")) return setTimeout(fire, 8000);
        fired = true; open(); try { sessionStorage.setItem("nl_seen", "1"); } catch (e) {}
        removeEventListener("scroll", onScroll);
      };
      const onScroll = () => { if (scrollY > (document.body.scrollHeight - innerHeight) * 0.45) fire(); };
      setTimeout(fire, 12000);
      addEventListener("scroll", onScroll, { passive: true });
    }
  }
  function get() { try { return localStorage.getItem("indomito_nl"); } catch (e) { return null; } }
  function mark(v) { try { if (get() !== "done") localStorage.setItem("indomito_nl", v === "done" ? "done" : String(Date.now())); } catch (e) {} }
})();
