/* 15/11/2026 – «Tienila sul telefono»: aiuta a mettere la guida nella schermata Home, come un'app.
   Stesso file nelle tre guide; nome, colore e icona li dà il tag <script> (data-nome, data-colore, data-icona, data-sw).
   - Android (Chrome, Edge, Samsung): la finestra «Installa» del telefono; se non c'è, istruzioni dal menu ⋮.
   - iPhone/iPad: Apple non permette di farlo in automatico → 3 istruzioni con la freccia verso Condividi.
   - Compare solo sui telefoni, dalla 2ª visita, dopo qualche secondo.
   - Sparisce per sempre a chi l'ha installata: aperta dall'icona; installata (Android lo dice, e lo controlla anche dopo);
     su iPhone Apple non lo dice, quindi chi segue le istruzioni e tocca «Ho capito» non lo rivede per un anno. La × lo nasconde 90 giorni.
   - Conta su GoatCounter: app/mostrato, app/tocco, app/installata, app/aperta-dall-icona.
   Il riquadro vive in un Shadow DOM: gli stili della guida non lo toccano e i suoi non toccano la guida. */
(function () {
  var S = document.currentScript || {}, D = S.dataset || {};
  var COL = D.colore || "#3d5f7d", ICONA = D.icona || "/icona-192.png", SW = D.sw || "";
  var ua = navigator.userAgent || "";
  var standalone = (window.matchMedia && matchMedia("(display-mode: standalone)").matches) || navigator.standalone === true;
  var ios = /iPhone|iPad|iPod/.test(ua) || (/Macintosh/.test(ua) && navigator.maxTouchPoints > 1);
  var ipad = /iPad/.test(ua) || (/Macintosh/.test(ua) && navigator.maxTouchPoints > 1);
  var android = /Android/.test(ua);
  var safari = ios && !/CriOS|FxiOS|EdgiOS|OPiOS|GSA\//.test(ua);
  var richiesta = null, chip, velo, foglio, R;
  function ls(k, v) { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch (_) { return null; } }
  function basta(giorni) { ls("app_no", Date.now() + giorni * 864e5); }
  function conta(p, t) { try { if (window.goatcounter && goatcounter.count) goatcounter.count({ path: "app/" + p, title: t || p, event: true }); } catch (_) {} }
  function quando(f) { if (document.readyState === "complete") f(); else addEventListener("load", f); }
  if (SW && "serviceWorker" in navigator) quando(function () { navigator.serviceWorker.register(SW).catch(function () {}); });
  if (standalone) {                                   // aperta dall'icona: niente riquadro, e lo ricorda
    basta(3650);
    window.achInstalla = function () { alert("È già sul telefono: la stai usando come app."); };
    if (/[?&]app=1/.test(location.search)) quando(function () { setTimeout(function () { conta("aperta-dall-icona", "Aperta dall'icona"); }, 1500); });
    return;
  }
  addEventListener("appinstalled", function () { basta(3650); chiudi(); avviso("✓ Fatto: la trovi nella schermata Home"); conta("installata", "Installata"); });
  var visite = +(ls("app_visite") || 0) + 1; ls("app_visite", visite);
  var forza = /[?&]installa=1/.test(location.search) || D.prova === "1";   // per provarlo subito: indirizzo con ?installa=1 (anche dalla 1ª visita, anche dopo la ×)
  var auto = forza || ((ios || android) && visite >= 2 && Date.now() >= +(ls("app_no") || 0));   // il riquadro da solo: telefoni, dalla 2ª visita
  addEventListener("beforeinstallprompt", function (e) { e.preventDefault(); richiesta = e; });

  var css = ":host{all:initial}*{box-sizing:border-box;margin:0;padding:0;font-family:inherit}"
    + ".appx{position:fixed;left:10px;right:10px;bottom:calc(12px + env(safe-area-inset-bottom));z-index:99990;display:flex;align-items:center;gap:10px;max-width:460px;margin:0 auto;"
    + "background:#fffdf8;color:#1f1c18;border:1px solid #e3dccd;border-radius:14px;padding:10px 10px 10px 12px;box-shadow:0 10px 28px rgba(0,0,0,.25);font:14px/1.3 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;cursor:pointer;animation:appsu .35s ease-out}"
    + ".appx img{width:40px;height:40px;border-radius:9px;flex:none}.appx div{flex:1;min-width:0}.appx b{display:block;font-size:15px}.appx em{font-style:normal;opacity:.72;font-size:13px}"
    + ".appx .vai{width:30px;height:30px;border-radius:50%;background:" + COL + ";color:#fff;display:grid;place-items:center;font-size:19px;font-weight:700;flex:none}"
    + ".appx .x{border:0;background:none;color:inherit;opacity:.55;font-size:22px;line-height:1;padding:4px 6px;cursor:pointer}"
    + ".appv{position:fixed;inset:0;z-index:99991;background:rgba(0,0,0,.45);animation:appf .2s}"
    + ".appf{position:fixed;left:0;right:0;z-index:99992;max-width:520px;margin:0 auto;background:#fffdf8;color:#1f1c18;padding:16px 16px calc(18px + env(safe-area-inset-bottom));font:15px/1.4 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;box-shadow:0 -8px 30px rgba(0,0,0,.3)}"
    + ".appf.giu{bottom:0;border-radius:18px 18px 0 0}.appf.su{top:0;border-radius:0 0 18px 18px;padding-top:calc(14px + env(safe-area-inset-top))}.appf{max-height:92vh;overflow:auto}"
    + ".appf h4{display:flex;align-items:center;gap:10px;margin:0 0 8px;font-size:17px;font-weight:700}.appf h4 img{width:32px;height:32px;border-radius:7px}"
    + ".appf ol{list-style:none;display:block}.appf li{display:flex;gap:12px;align-items:center;padding:10px 0;border-top:1px solid #e3dccd}.appf li:first-child{border-top:0}"
    + ".appf small{font-size:13px;opacity:.75}.appf .tx{flex:1;min-width:0}.appf b{font-weight:700}"
    + ".appf .fg{width:112px;height:67px;flex:none;display:block}.appf .sf{fill:#f1ece2;stroke:#e3dccd}.appf .bar{fill:#fff;stroke:#ddd5c5}.appf .gr{fill:#d9d1c1}"
    + ".appf .tg{font:7px -apple-system,BlinkMacSystemFont,sans-serif;fill:#6b6358}.appf .tw{font:600 7px -apple-system,BlinkMacSystemFont,sans-serif;fill:#fff}"
    + ".appf .pu{animation:pul 1.4s ease-in-out infinite;transform-box:fill-box;transform-origin:center}@keyframes pul{50%{transform:scale(1.35);opacity:.05}}"
    + ".appf .cp{display:block;width:100%;margin-top:12px;border:0;border-radius:10px;padding:12px;background:" + COL + ";color:#fff;font:600 15px -apple-system,BlinkMacSystemFont,sans-serif;cursor:pointer}"
    + ".appf .n{width:24px;height:24px;border-radius:50%;background:" + COL + ";color:#fff;display:grid;place-items:center;font-size:13px;font-weight:700;flex:none}"
    + ".appf .t{display:inline;border:1px solid #d6cdbb;border-radius:6px;padding:1px 6px;font-weight:600;white-space:nowrap}"
    + ".appf .ok{display:block;width:100%;margin-top:12px;border:0;border-radius:10px;padding:11px;background:#efe8da;color:#1f1c18;font:600 15px -apple-system,BlinkMacSystemFont,sans-serif;cursor:pointer}"
    + ".appf .fr{display:block;font:700 15px -apple-system,BlinkMacSystemFont,sans-serif;color:" + COL + ";animation:apps 1.1s infinite;text-align:center;margin:10px 0 0}.appf.giu .fr{margin:0 0 8px}"
    + ".apptoast{position:fixed;left:50%;top:calc(14px + env(safe-area-inset-top));transform:translateX(-50%);z-index:99993;background:#1f1c18;color:#fff;border-radius:10px;padding:10px 14px;font:600 14px -apple-system,BlinkMacSystemFont,sans-serif;box-shadow:0 8px 24px rgba(0,0,0,.3)}"
    + "@media(prefers-color-scheme:dark){.appf .sf{fill:#2e2a25;stroke:#3a352e}.appf .bar{fill:#3a352e;stroke:#4a443b}.appf .gr{fill:#4a443b}.appf .tg{fill:#c9c0b2}.appx,.appf{background:#24211d;color:#f1ece2;border-color:#3a352e}.appf li{border-color:#3a352e}.appf .t{border-color:#4a443b}.appf .ok{background:#332e28;color:#f1ece2}}"
    + "@keyframes appsu{from{transform:translateY(30px);opacity:0}}@keyframes appf{from{opacity:0}}@keyframes apps{50%{transform:translateY(6px)}}";

  function el(h) { var d = document.createElement("div"); d.innerHTML = h; return d.firstChild; }
  function radice() {
    if (R) return R;
    var o = document.createElement("div"); o.id = "ach-installa"; o.style.cssText = "all:initial;position:static";
    document.body.appendChild(o);
    R = o.attachShadow ? o.attachShadow({ mode: "open" }) : o;
    var st = document.createElement("style"); st.textContent = css; R.appendChild(st);
    return R;
  }
  function mostra(silenzio) {
    if (chip && chip.parentNode) return;
    radice();
    chip = el('<div class="appx" role="button" aria-label="Metti la guida sul telefono"><img src="' + ICONA + '" alt=""><div><b>Mettila sul telefono, come un\'app</b><em>gratis · tocca qui e ti mostro come</em></div><span class="vai">›</span><button class="x" aria-label="Chiudi">×</button></div>');
    chip.onclick = function (e) { if (e.target.classList.contains("x")) { chiudi(); basta(90); conta("chiuso", "Riquadro chiuso"); return; } aggiungi(); };
    R.appendChild(chip);
    if (!silenzio) conta("mostrato", "Riquadro mostrato");
  }
  function chiudi() { [chip, velo, foglio].forEach(function (x) { if (x && x.parentNode) x.parentNode.removeChild(x); }); }
  // --- figure dei passi: disegni semplici di quello che si vede sul telefono (il tasto da toccare è colorato e pulsa)
  var C = COL;
  function fig(c) { return '<svg viewBox="0 0 120 72" class="fg" aria-hidden="true"><rect x="1" y="1" width="118" height="70" rx="10" class="sf"/>' + c + '</svg>'; }
  var tasto = function (x, y, r) { return '<circle cx="' + x + '" cy="' + y + '" r="' + (r + 5) + '" fill="' + C + '" opacity=".22" class="pu"/><circle cx="' + x + '" cy="' + y + '" r="' + r + '" fill="' + C + '"/>'; };
  var riga = function (y, w, on, t) { return on ? '<rect x="10" y="' + y + '" width="100" height="14" rx="4" fill="' + C + '"/><text x="16" y="' + (y + 10) + '" class="tw">' + t + '</text>'
      : '<rect x="10" y="' + y + '" width="' + w + '" height="6" rx="3" class="gr"/>'; };
  var FIG = {
    tre_punti: fig('<rect x="8" y="48" width="104" height="16" rx="8" class="bar"/><text x="18" y="59" class="tg">achevents.com</text>' + tasto(100, 56, 7) + '<text x="100" y="58.5" class="tw" text-anchor="middle">•••</text>'),
    condividi_menu: fig(riga(10, 70) + riga(22, 60) + riga(34, 0, 1, "⬆︎  Condividi") + riga(54, 50)),
    condividi_barra: fig('<rect x="8" y="48" width="104" height="16" rx="4" class="bar"/><text x="18" y="60" class="tg">‹    ›</text>' + tasto(60, 56, 7) + '<path d="M60 52v7M57 55l3-3 3 3" stroke="#fff" stroke-width="1.6" fill="none"/><text x="86" y="60" class="tg">⧉</text>'),
    condividi_alto: fig('<rect x="8" y="8" width="104" height="16" rx="4" class="bar"/><text x="16" y="19" class="tg">achevents.com</text>' + tasto(100, 16, 7) + '<path d="M100 12v7M97 15l3-3 3 3" stroke="#fff" stroke-width="1.6" fill="none"/>'),
    home: fig(riga(8, 80) + riga(18, 60) + riga(28, 0, 1, "⊞  Aggiungi alla schermata Home") + riga(48, 70) + riga(58, 50)),
    aggiungi: fig('<text x="10" y="16" class="tg">Annulla</text><rect x="80" y="6" width="32" height="14" rx="7" fill="' + C + '"/><text x="96" y="16" class="tw" text-anchor="middle">Aggiungi</text><image href="' + ICONA + '" x="10" y="27" width="20" height="20"/><rect x="36" y="31" width="50" height="6" rx="3" class="gr"/><text x="10" y="63" class="tg">Apri come app web</text><rect x="92" y="54" width="20" height="12" rx="6" fill="#34c759"/><circle cx="106" cy="60" r="4.5" fill="#fff"/>'),
    menu_android: fig('<rect x="8" y="8" width="104" height="16" rx="8" class="bar"/><text x="16" y="19" class="tg">achevents.com</text>' + tasto(104, 16, 7) + '<text x="104" y="19" class="tw" text-anchor="middle">⋮</text>'),
    installa_menu: fig(riga(8, 70) + riga(18, 60) + riga(28, 0, 1, "⊕  Aggiungi a schermata Home") + riga(48, 70) + riga(58, 40)),
    installa_ok: fig('<text x="60" y="22" class="tg" text-anchor="middle">Installare l\'app?</text><image href="' + ICONA + '" x="50" y="27" width="20" height="20"/><text x="30" y="62" class="tg">Annulla</text><rect x="70" y="52" width="40" height="14" rx="7" fill="' + C + '"/><text x="90" y="62" class="tw" text-anchor="middle">Installa</text>'),
    browser: fig('<rect x="8" y="8" width="104" height="16" rx="4" class="bar"/>' + tasto(104, 16, 7) + '<text x="104" y="19" class="tw" text-anchor="middle">•••</text>' + riga(32, 0, 1, "Apri nel browser") + riga(54, 60))
  };
  var NOME_SITO = location.hostname.replace(/^www\./, "");
  function passiGiusti() {
    var inApp = /FBAN|FBAV|FB_IAB|Instagram|LinkedInApp|Line\/|Twitter|TikTok|Snapchat|GSA\/|; wv\)/.test(ua);
    var safari26 = ios && safari && +((ua.match(/Version\/(\d+)/) || [])[1] || 0) >= 26;
    if (inApp) return { titolo: "Prima aprila nel browser", sopra: false, copia: true, passi: [
      [FIG.browser, "Tocca <b>•••</b> (o <b>⋮</b>) in alto e scegli <b>Apri nel browser</b> " + (ios ? "(Safari)" : "(Chrome)")],
      [null, "Oppure copia il link qui sotto e incollalo in " + (ios ? "Safari" : "Chrome") + ": lì comparirà questo riquadro"]] };
    if (ios && safari26 && !ipad) return { titolo: "Aggiungila in 4 tocchi", sopra: true, freccia: "⬇︎ i tasti sono qui sotto", passi: [
      [FIG.tre_punti, "Tocca <b>•••</b> in basso a destra, accanto all'indirizzo"],
      [FIG.condividi_menu, "Tocca <b>Condividi</b>"],
      [FIG.home, "Scorri e tocca <b>Aggiungi alla schermata Home</b><br><small>se non c'è, tocca prima <b>Mostra altro</b></small>"],
      [FIG.aggiungi, "Lascia acceso <b>Apri come app web</b> e tocca <b>Aggiungi</b>"]] };
    if (ios && safari) return { titolo: "Aggiungila in 3 tocchi", sopra: !ipad, freccia: ipad ? "⬆︎ il tasto è in alto" : "⬇︎ il tasto è qui sotto", passi: [
      [ipad ? FIG.condividi_alto : FIG.condividi_barra, "Tocca <b>Condividi</b> " + (ipad ? "in alto a destra" : "in basso, al centro") + "<br><small>se vedi solo <b>•••</b>, tocca quello e poi Condividi</small>"],
      [FIG.home, "Scorri e tocca <b>Aggiungi alla schermata Home</b>"],
      [FIG.aggiungi, "Tocca <b>Aggiungi</b> in alto a destra"]] };
    if (ios) return { titolo: "Aggiungila in 3 tocchi", sopra: false, freccia: "⬆︎ il tasto è nella barra dell'indirizzo", passi: [
      [FIG.condividi_alto, "Tocca <b>Condividi</b> nella barra dell'indirizzo"],
      [FIG.home, "Tocca <b>Aggiungi alla schermata Home</b>"],
      [FIG.aggiungi, "Tocca <b>Aggiungi</b>"]] };
    if (android) return { titolo: "Aggiungila in 3 tocchi", sopra: false, freccia: "⬆︎ il menu è in alto a destra", passi: [
      [FIG.menu_android, "Tocca il menu <b>⋮</b> in alto a destra"],
      [FIG.installa_menu, "Tocca <b>Aggiungi a schermata Home</b> oppure <b>Installa app</b>"],
      [FIG.installa_ok, "Conferma con <b>Installa</b> o <b>Aggiungi</b>"]] };
    return { titolo: "Si mette sul telefono", sopra: false, passi: [[null, "Apri questa pagina dal telefono, oppure inquadra il codice QR con la fotocamera"], [null, "Poi tocca <b>Aggiungila al telefono</b> e segui i passi"]] };
  }
  function istruzioni() {
    radice();
    var g = passiGiusti();
    velo = el('<div class="appv"></div>'); velo.onclick = fatto;
    var fr = g.freccia ? '<div class="fr">' + g.freccia + '</div>' : "";
    foglio = el('<div class="appf ' + (g.sopra ? "su" : "giu") + '">' + (!g.sopra ? fr : "")
      + '<h4><img src="' + ICONA + '" alt="">' + g.titolo + '</h4><ol>'
      + g.passi.map(function (p, i) { return '<li><span class="n">' + (i + 1) + '</span>' + (p[0] || "") + '<span class="tx">' + p[1] + '</span></li>'; }).join("")
      + '</ol>' + (g.copia ? '<button class="cp">Copia il link</button>' : "") + '<button class="ok">' + (g.copia ? "Chiudi" : "Ho capito") + '</button>' + (g.sopra ? fr : "") + '</div>');
    foglio.querySelector(".ok").onclick = fatto;
    var cp = foglio.querySelector(".cp");
    if (cp) cp.onclick = function () {
      var u = location.origin + "/?installa=1";
      (navigator.clipboard ? navigator.clipboard.writeText(u) : Promise.reject()).then(function () { cp.textContent = "✓ Copiato: ora incollalo nel browser"; },
        function () { prompt("Copia questo link e incollalo nel browser:", u); });
    };
    R.appendChild(velo); R.appendChild(foglio);
  }
  function fatto() { chiudi(); basta(365); }        // ha visto come si fa: non lo rivede per un anno
  function aggiungi() {
    conta("tocco", "Riquadro toccato");
    if (richiesta) {                                 // Android: la finestra vera del telefono
      richiesta.prompt();
      richiesta.userChoice.then(function (r) { if (r.outcome === "accepted") { chiudi(); basta(3650); } else istruzioni(); richiesta = null; });
      return;
    }
    istruzioni();
  }
  function avviso(t) { radice(); var a = el('<div class="apptoast">' + t + '</div>'); R.appendChild(a); setTimeout(function () { a.remove(); }, 4000); }
  window.achInstalla = function () { mostra(true); aggiungi(); };     // per il bottone della pagina /app
  quando(function () {
    if (!auto) return;
    var parti = function () { setTimeout(function () { if (forza || Date.now() >= +(ls("app_no") || 0)) mostra(); }, forza ? 1000 : 6000); };
    // Android: se la guida è già installata il telefono lo dice (anche se è stata installata in un altro momento)
    if (navigator.getInstalledRelatedApps && !forza) navigator.getInstalledRelatedApps().then(function (a) { if (a && a.length) basta(3650); else parti(); }).catch(parti);
    else parti();
  });
})();
