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
  var auto = (ios || android) && visite >= 2 && Date.now() >= +(ls("app_no") || 0);   // il riquadro da solo: telefoni, dalla 2ª visita
  addEventListener("beforeinstallprompt", function (e) { e.preventDefault(); richiesta = e; });

  var css = ":host{all:initial}*{box-sizing:border-box;margin:0;padding:0;font-family:inherit}"
    + ".appx{position:fixed;left:10px;right:10px;bottom:calc(12px + env(safe-area-inset-bottom));z-index:99990;display:flex;align-items:center;gap:10px;max-width:460px;margin:0 auto;"
    + "background:#fffdf8;color:#1f1c18;border:1px solid #e3dccd;border-radius:14px;padding:10px 10px 10px 12px;box-shadow:0 10px 28px rgba(0,0,0,.25);font:14px/1.3 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;cursor:pointer;animation:appsu .35s ease-out}"
    + ".appx img{width:40px;height:40px;border-radius:9px;flex:none}.appx div{flex:1;min-width:0}.appx b{display:block;font-size:15px}.appx em{font-style:normal;opacity:.72;font-size:13px}"
    + ".appx .vai{width:30px;height:30px;border-radius:50%;background:" + COL + ";color:#fff;display:grid;place-items:center;font-size:19px;font-weight:700;flex:none}"
    + ".appx .x{border:0;background:none;color:inherit;opacity:.55;font-size:22px;line-height:1;padding:4px 6px;cursor:pointer}"
    + ".appv{position:fixed;inset:0;z-index:99991;background:rgba(0,0,0,.45);animation:appf .2s}"
    + ".appf{position:fixed;left:0;right:0;z-index:99992;max-width:520px;margin:0 auto;background:#fffdf8;color:#1f1c18;padding:16px 16px calc(18px + env(safe-area-inset-bottom));font:15px/1.4 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;box-shadow:0 -8px 30px rgba(0,0,0,.3)}"
    + ".appf.giu{bottom:0;border-radius:18px 18px 0 0}.appf.su{top:0;border-radius:0 0 18px 18px;padding-top:calc(14px + env(safe-area-inset-top))}"
    + ".appf h4{display:flex;align-items:center;gap:10px;margin:0 0 8px;font-size:17px;font-weight:700}.appf h4 img{width:32px;height:32px;border-radius:7px}"
    + ".appf ol{list-style:none;display:block}.appf li{display:flex;gap:12px;align-items:center;padding:10px 0;border-top:1px solid #e3dccd}.appf li:first-child{border-top:0}"
    + ".appf small{font-size:13px;opacity:.75}"
    + ".appf .n{width:24px;height:24px;border-radius:50%;background:" + COL + ";color:#fff;display:grid;place-items:center;font-size:13px;font-weight:700;flex:none}"
    + ".appf .t{display:inline;border:1px solid #d6cdbb;border-radius:6px;padding:1px 6px;font-weight:600;white-space:nowrap}"
    + ".appf .ok{display:block;width:100%;margin-top:12px;border:0;border-radius:10px;padding:11px;background:#efe8da;color:#1f1c18;font:600 15px -apple-system,BlinkMacSystemFont,sans-serif;cursor:pointer}"
    + ".appf .fr{display:block;font-size:26px;line-height:1;color:" + COL + ";animation:apps 1.1s infinite;text-align:center;margin-top:10px}.appf.su .fr{text-align:right;margin:0 4px 4px 0}"
    + ".apptoast{position:fixed;left:50%;top:calc(14px + env(safe-area-inset-top));transform:translateX(-50%);z-index:99993;background:#1f1c18;color:#fff;border-radius:10px;padding:10px 14px;font:600 14px -apple-system,BlinkMacSystemFont,sans-serif;box-shadow:0 8px 24px rgba(0,0,0,.3)}"
    + "@media(prefers-color-scheme:dark){.appx,.appf{background:#24211d;color:#f1ece2;border-color:#3a352e}.appf li{border-color:#3a352e}.appf .t{border-color:#4a443b}.appf .ok{background:#332e28;color:#f1ece2}}"
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
    chip = el('<div class="appx" role="button" aria-label="Metti la guida sul telefono"><img src="' + ICONA + '" alt=""><div><b>Tienila sul telefono</b><em>tocca qui: si apre come un\'app</em></div><span class="vai">›</span><button class="x" aria-label="Chiudi">×</button></div>');
    chip.onclick = function (e) { if (e.target.classList.contains("x")) { chiudi(); basta(90); conta("chiuso", "Riquadro chiuso"); return; } aggiungi(); };
    R.appendChild(chip);
    if (!silenzio) conta("mostrato", "Riquadro mostrato");
  }
  function chiudi() { [chip, velo, foglio].forEach(function (x) { if (x && x.parentNode) x.parentNode.removeChild(x); }); }
  function istruzioni(passi, sopra) {
    radice();
    velo = el('<div class="appv"></div>'); velo.onclick = fatto;
    var fr = '<span class="fr">' + (sopra ? "⬆" : "⬇") + '</span>';
    foglio = el('<div class="appf ' + (sopra ? "su" : "giu") + '">' + (sopra && ios ? fr : "") + '<h4><img src="' + ICONA + '" alt="">Mettila nella schermata Home</h4><ol>'
      + passi.map(function (p, i) { return '<li><span class="n">' + (i + 1) + '</span><span>' + p + '</span></li>'; }).join("")
      + '</ol><button class="ok">Ho capito</button>' + (!sopra ? fr : "") + '</div>');
    foglio.querySelector(".ok").onclick = fatto;
    R.appendChild(velo); R.appendChild(foglio);
  }
  function fatto() { chiudi(); basta(365); }        // ha visto come si fa: non lo rivede per un anno
  function aggiungi() {
    conta("tocco", "Riquadro toccato");
    if (richiesta) {                                 // Android: la finestra vera del telefono
      richiesta.prompt();
      richiesta.userChoice.then(function (r) { if (r.outcome === "accepted") { chiudi(); basta(3650); } richiesta = null; });
      return;
    }
    if (ios && safari) {
      istruzioni(["Tocca <span class='t'>Condividi ⬆︎</span> " + (ipad ? "in alto" : "qui sotto") + "<br><small>(se non lo vedi, tocca prima <span class='t'>•••</span>)</small>",
                  "Scorri e tocca <span class='t'>Aggiungi alla schermata Home</span>",
                  "Tocca <span class='t'>Aggiungi</span> in alto a destra"], ipad);
    } else if (ios) {
      istruzioni(["Tocca <span class='t'>Condividi ⬆︎</span> nella barra dell'indirizzo",
                  "Tocca <span class='t'>Aggiungi alla schermata Home</span>",
                  "Tocca <span class='t'>Aggiungi</span>"], true);
    } else if (!android) {                           // computer: si fa dal telefono
      istruzioni(["Apri questa pagina dal telefono, oppure inquadra il codice QR con la fotocamera", "Poi tocca <span class='t'>Aggiungila al telefono</span>"], false);
    } else {                                         // Android senza la finestra automatica (Firefox, alcuni Samsung)
      istruzioni(["Tocca il menu <span class='t'>⋮</span> in alto a destra",
                  "Tocca <span class='t'>Installa app</span> oppure <span class='t'>Aggiungi a schermata Home</span>",
                  "Conferma con <span class='t'>Installa</span> o <span class='t'>Aggiungi</span>"], true);
    }
  }
  function avviso(t) { radice(); var a = el('<div class="apptoast">' + t + '</div>'); R.appendChild(a); setTimeout(function () { a.remove(); }, 4000); }
  window.achInstalla = function () { mostra(true); aggiungi(); };     // per il bottone della pagina /app
  quando(function () {
    if (!auto) return;
    var parti = function () { setTimeout(function () { if (Date.now() >= +(ls("app_no") || 0)) mostra(); }, 6000); };
    // Android: se la guida è già installata il telefono lo dice (anche se è stata installata in un altro momento)
    if (navigator.getInstalledRelatedApps) navigator.getInstalledRelatedApps().then(function (a) { if (a && a.length) basta(3650); else parti(); }).catch(parti);
    else parti();
  });
})();
