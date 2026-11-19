"""Pagine per Google di Ach's Dinners Guide (approvate da Stefano il 17/11/2026).

La guida (index.html) è una pagina sola: Google non vede i singoli ristoranti. Questo programma apre la guida
vera in Chrome, prende le schede e le card che la guida stessa disegna, e le scrive in pagine statiche con lo
STESSO aspetto (stesso foglio di stile, stessi caratteri, stesse schede):

  locale/<id>/index.html      un ristorante segnalato (scheda completa, fonti, «da vedere qui vicino»)
  citta/<comune-pr>/index.html  una città con almeno 3 ristoranti segnalati
  provincia/<pr>/index.html     una provincia
  stile.css, sitemap.xml, sitemap-pagine.xml, robots.txt, pagine.json (elenco delle pagine generate)

Regole:
- solo i ristoranti segnalati (punteggio > 0), nessun dato Google;
- la guida (index.html) non si tocca;
- si riscrive un file solo se il contenuto cambia, così GitHub non si appesantisce a ogni pubblicazione;
- si cancellano solo pagine che questo programma aveva generato (elenco in pagine.json) e che non servono più.

Uso: python3 scripts/pagine.py [--prova N]   (--prova: solo le prime N province, per l'anteprima)
"""
import functools, html, http.server, json, os, re, socketserver, sys, threading, datetime

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITO = "https://achdinners.com"
MIN_CITTA = 3
MAX_ELENCO = 120
CARTELLE = ("locale", "citta", "provincia")


def e(s):
    return html.escape(str(s or ""), quote=True)


def slug(s):
    import unicodedata
    s = unicodedata.normalize("NFD", str(s).lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


# ---------- 1. la guida vera in Chrome: card e schede disegnate dalla guida stessa ----------
def cattura(prova=None):
    from playwright.sync_api import sync_playwright
    class Zitto(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    H = functools.partial(Zitto, directory=RADICE)
    srv = socketserver.TCPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    porta = srv.server_address[1]
    chrome = next((p for p in ("/usr/bin/google-chrome", "/usr/bin/google-chrome-stable") if os.path.exists(p)), None)
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=chrome, args=["--no-sandbox"]) if chrome else p.chromium.launch()
        pg = b.new_page(viewport={"width": 430, "height": 900}, locale="it-IT")
        pg.goto(f"http://127.0.0.1:{porta}/?lang=it#ristoranti")
        pg.wait_for_function('typeof L!=="undefined" && L.length>1000 && document.getElementById("n-tutti").textContent', timeout=120000)
        pg.evaluate("Promise.all([caricaExtra(),caricaAux()])")
        dati = pg.evaluate("""async (prova)=>{
          const tabs={};["rico","piz","altri","altp","tutti"].forEach(k=>tabs[k]=document.getElementById("n-"+k).textContent);
          let sel=L.filter(x=>x.s>0);
          let prov=[...new Set(sel.map(x=>x.p))].sort();
          if(prova)prov=prov.slice(0,prova);
          sel=sel.filter(x=>prov.includes(x.p)).sort((a,b)=>a.pos-b.pos);
          const out=[];
          for(const p of prov){
            await carica(p);
            for(const x of sel.filter(y=>y.p===p)){
              apri(x);
              const sh=document.getElementById("sheet");
              for(let t=0;t<200&&(sh.innerHTML.includes("Carico le fonti")||!document.getElementById("sind"));t++)await new Promise(r=>setTimeout(r,10));
              if(sh.innerHTML.includes("Carico le fonti"))throw new Error("fonti non caricate: "+x.n);
              const id=(DET[p][x.k]||[])[3]||(p+"-"+x.k);
              out.push({id,n:x.n,c:x.c,p:x.p,r:x.r,pos:x.pos,s:x.s,pz:x.pz,g:x.g2,ns:x.ns,nb:x.nb,
                        ind:(DET[p][x.k]||[])[4]||"",sito:(DET[p][x.k]||[])[1]||"",
                        card:card(x,{q:[]}),scheda:document.getElementById("sheet").innerHTML});
            }
          }
          document.getElementById("dlg").close&&document.getElementById("dlg").close();
          return {tabs,locali:out,provn:D.provn,etichette:Object.fromEntries(Object.entries(LEG).map(([k,v])=>[k,v[0]]))};
        }""", prova)
        b.close()
    srv.shutdown()
    return dati


# ---------- 2. pezzi comuni presi da index.html ----------
def pezzi():
    s = open(os.path.join(RADICE, "index.html"), encoding="utf-8").read()
    css = re.findall(r'<style(?: id="([^"]*)")?[^>]*>(.*?)</style>', s, re.S)
    stile = "\n".join(c for i, c in css if i != "en-boot-css") + """
/* pagine statiche (scripts/pagine.py): stesso aspetto della guida */
a.card{color:inherit;text-decoration:none}
.sheet.pagina{position:static;transform:none;left:auto;top:auto;bottom:auto;width:100%;max-height:none;overflow:visible;margin:6px 0 22px;box-shadow:var(--shadow);border:1px solid var(--line)}
a.sx{display:flex;align-items:center;justify-content:center;text-decoration:none;color:inherit}
a.tbtn{text-decoration:none}
h2.sez{font:600 1.25rem/1.2 var(--serif);margin:26px 2px 12px}
.sheet.pagina h1{font:600 1.55rem/1.15 var(--serif);margin:4px 46px 4px 0;letter-spacing:normal;text-wrap:wrap}
.altri{display:flex;flex-wrap:wrap;gap:8px 14px;margin:6px 2px 24px}.altri a{color:var(--acc-ink,inherit)}
"""
    a = s.find('<nav class="tabs"'); b = s.find("</nav>", a) + 6
    tabs = re.sub(r'href="#', f'href="{SITO}/#', s[a:b])
    cerca = re.search(r'<label class="search">(<svg.*?</svg>)', s, re.S).group(1)
    mappa = re.search(r'<a class="tbtn mapbtn".*?</a>', s, re.S).group(0).replace('href="mappa.html"', f'href="{SITO}/mappa.html"')
    filtri = re.search(r'id="mfil">(<svg.*?</svg>)', s, re.S).group(1)
    decl = re.search(r'<p class="decl"[^>]*>(.*?)</p>', s, re.S).group(1)
    return dict(stile=stile, tabs=tabs, cerca=cerca, mappa=mappa, filtri=filtri, decl=decl)


GC = ('<script>const GC="achdinners";if(/(^|\\.)achdinners\\.com$/.test(location.hostname)){try{const s=document.createElement("script");'
      's.async=true;s.dataset.goatcounter=`https://${GC}.goatcounter.com/count`;s.src="https://gc.zgo.at/count.js";document.body.appendChild(s);}catch(_){}}</script>')


def pagina(P, tabs_n, titolo, descr, url, corpo, ld):
    tabs = P["tabs"]
    for k, v in tabs_n.items():
        tabs = tabs.replace(f'<span class="n" id="n-{k}"></span>', f'<span class="n">{e(v)}</span>')
    return f"""<!DOCTYPE html>
<html lang="it" data-stile="C">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{e(titolo)}</title>
<meta name="description" content="{e(descr)}">
<link rel="canonical" href="{SITO}{url}">
<meta property="og:type" content="website"><meta property="og:url" content="{SITO}{url}"><meta property="og:title" content="{e(titolo)}"><meta property="og:description" content="{e(descr)}"><meta property="og:locale" content="it_IT"><meta property="og:image" content="{SITO}/anteprima.png"><meta name="twitter:card" content="summary_large_image">
<link rel="stylesheet" href="/stile.css">
<link rel="apple-touch-icon" href="/icona-180.png">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
</head>
<body>
<div class="wrap">
{tabs}
{corpo}
<p class="legale"><a href="/chi-siamo/">Chi siamo</a> · <a href="/privacy/">Privacy</a> · <a href="/collaborano/">Collaborano con noi</a></p>
</div>
{GC}
</body></html>
"""


def acard(h, href):
    h = re.sub(r'^<button type="button" class="', '<a class="', h)
    h = re.sub(r'" data-i="-?\d+">', f'" href="{href}">', h, count=1)
    return h[: -len("</button>")] + "</a>" if h.endswith("</button>") else h


def guide(places):
    return f"""<nav class="ach-guide" aria-label="Le guide di Ach">
    <a class="ach-guide__btn" href="https://achevents.com/"><span class="ach-guide__ico" aria-hidden="true">🎭</span><span class="ach-guide__txt"><b>Events</b><small>spettacoli, mostre, cinema</small></span><span class="ach-guide__arr" aria-hidden="true">→</span></a>
    <a class="ach-guide__btn" href="{places}"><span class="ach-guide__ico" aria-hidden="true">🏛️</span><span class="ach-guide__txt"><b>Places</b><small>cosa visitare</small></span><span class="ach-guide__arr" aria-hidden="true">→</span></a>
  </nav>"""


def strumenti(P, q):
    return f"""<section id="lista">
  <div class="tools">
    <div class="row">
      <form class="search" action="{SITO}/" onsubmit="location.href='{SITO}/#cerca='+encodeURIComponent(this.q.value);return false">{P['cerca']}<input name="q" type="text" inputmode="search" enterkeyhint="search" autocomplete="off" placeholder="Cerca locale o comune"></form>
      {P['mappa']}
      <a class="tbtn" href="{SITO}/#cerca={e(q)}">{P['filtri']}<span>Filtri</span></a>
    </div>
  </div>"""


def elenco(P, tabs, kick, h1, lede, url, places, q, locali, conta, altri_html, titolo, descr):
    cards = "".join(acard(x["card"], f"/locale/{x['id']}/") for x in locali[:MAX_ELENCO])
    piu = (f'<p class="count" style="margin-top:14px">Gli altri {len(locali) - MAX_ELENCO} sono nella guida: '
           f'<a href="{SITO}/#cerca={e(q)}">vedi tutti</a></p>') if len(locali) > MAX_ELENCO else ""
    corpo = f"""<header class="hero">
  <div class="kick">Ach’s Dinners Guide · {e(kick)}</div>
  <h1>{e(h1)}</h1>
  <p class="lede">{lede}</p>
  <p class="decl">{P['decl']}</p>
  {guide(places)}
</header>
{strumenti(P, q)}
  <div class="ris"><div class="conta"><p class="count">{conta}</p></div>
  <div class="grid">{cards}</div>{piu}</div>
</section>
{altri_html}"""
    ld = {"@context": "https://schema.org", "@type": "ItemList", "name": h1, "numberOfItems": len(locali),
          "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": x["n"], "url": f"{SITO}/locale/{x['id']}/"}
                              for i, x in enumerate(locali[:MAX_ELENCO])]}
    return pagina(P, tabs, titolo, descr, url, corpo, ld)


def corto(t, n=160):
    """Descrizione entro i ~160 caratteri che Google mostra, tagliata a fine parola."""
    return t if len(t) <= n else t[:n].rsplit(" ", 1)[0].rstrip(",;:–-") + "…"


def n_it(n):
    return f"{n:,}".replace(",", ".")


def places_comune(c, p):
    """Pagina del comune su Ach's Places, se esiste (si controlla la mappa del sito pubblica di Places)."""
    global _PLACES
    if _PLACES is None:
        _PLACES = set()
        try:
            import urllib.request
            locale_ = os.path.join(RADICE, "..", "achplaces", "sitemap-1.xml")
            for n in ("sitemap-1.xml",):
                t = (open(locale_, encoding="utf-8").read() if os.path.exists(locale_)
                     else urllib.request.urlopen(f"https://achplaces.com/{n}", timeout=30).read().decode())
                _PLACES |= set(re.findall(r"achplaces\.com/comune/([a-z0-9-]+)/", t))
        except Exception as ex:
            print("mappa del sito di Places non letta:", ex)
    s = f"{slug(c)}-{p.lower()}"
    return f"https://achplaces.com/comune/{s}/" if s in _PLACES else "https://achplaces.com/"


_PLACES = None


def costruisci(dati, P):
    L = dati["locali"]
    # indirizzo leggibile e stabile: nome-comune (es. ristorante-san-domenico-imola); a parità si aggiunge la provincia
    visti = {}
    for x in sorted(L, key=lambda y: (y["pos"], y["id"])):
        n, c = slug(x["n"])[:60].strip("-"), slug(x["c"])
        base = n if n.endswith(c) else f"{n}-{c}"
        if base in visti:
            base = f"{base}-{x['p'].lower()}"
        while base in visti:
            base += "-2"
        visti[base] = 1
        x["id"] = base
    provn, et = dati["provn"], dati["etichette"]
    tabs = dati["tabs"]
    per_citta, per_prov = {}, {}
    for x in L:
        per_citta.setdefault((x["c"], x["p"]), []).append(x)
        per_prov.setdefault(x["p"], []).append(x)
    citta = {k: v for k, v in per_citta.items() if len(v) >= MIN_CITTA}
    url_citta = {k: f"/citta/{slug(k[0])}-{k[1].lower()}/" for k in citta}
    url_prov = {p: f"/provincia/{p.lower()}/" for p in per_prov}
    pagine = {}
    # --- ristoranti
    for x in L:
        k = (x["c"], x["p"])
        su = url_citta.get(k) or url_prov[x["p"]]
        dove = x["c"] if k in citta else f"provincia di {provn.get(x['p'], x['p'])}"
        sch = x["scheda"].replace('<div class="grab"></div>', "")
        sch = re.sub(r'<button class="sx" type="button" aria-label="Chiudi" id="sx">×</button>',
                     f'<a class="sx" href="{su}" aria-label="Torna ai ristoranti: {e(dove)}">×</a>', sch)
        sch = re.sub(r"<h2>(.*?)</h2>", r"<h1>\1</h1>", sch, count=1, flags=re.S)
        sch = sch.replace(' id="sind"', "").replace(' id="sazioni"', "").replace(' id="snear"', "")
        vicini = [y for y in (citta.get(k) or per_prov[x["p"]]) if y is not x][:6]
        altri = "".join(acard(y["card"], f"/locale/{y['id']}/") for y in vicini)
        ric = [et.get(g, g) for g in x["g"]]
        corpo = (f'<div class="sheet pagina" role="main">{sch}</div>'
                 + (f'<h2 class="sez">Altri ristoranti segnalati: {e(dove)}</h2><div class="grid">{altri}</div>' if altri else "")
                 + f'<p class="altri"><a href="{su}">Tutti i ristoranti segnalati: {e(dove)}</a>'
                 + (f' · <a href="{url_prov[x["p"]]}">Provincia di {e(provn.get(x["p"], x["p"]))}</a>' if k in citta else "") + "</p>")
        tipo = "Pizzeria" if x["pz"] else "Ristorante"
        titolo = x['n'] if slug(x['c']) in slug(x['n']) else f"{x['n']} a {x['c']}"
        if ric and len(titolo) + len(ric[0]) < 52:
            titolo += f": {ric[0]}"
        titolo += " | Ach’s Dinners"
        descr = (f"{x['n']} ({x['c']}, {x['p']}): " + (", ".join(ric[:3]) + ". " if ric else "")
                 + f"{x['pos']}° su {n_it(len(L))} secondo guide e stampa, con tutte le fonti.")
        ld = {"@context": "https://schema.org", "@type": "Restaurant", "name": x["n"], "url": f"{SITO}/locale/{x['id']}/",
              "address": {"@type": "PostalAddress", "streetAddress": x["ind"], "addressLocality": x["c"], "addressRegion": x["p"], "addressCountry": "IT"}}
        if x["sito"]:
            ld["sameAs"] = x["sito"]
        if ric:
            ld["award"] = ric
        pagine[f"locale/{x['id']}/index.html"] = pagina(P, tabs, titolo, corto(descr), f"/locale/{x['id']}/", corpo, ld)
    # --- città
    for k, v in citta.items():
        c, p = k
        altre = sorted([kk for kk in citta if kk[1] == p and kk != k], key=lambda kk: -len(citta[kk]))
        alt = "".join(f'<a href="{url_citta[kk]}">{e(kk[0])}</a>' for kk in altre[:30])
        altri_html = (f'<h2 class="sez">Altre città in provincia di {e(provn.get(p, p))}</h2><p class="altri">{alt}'
                      f'<a href="{url_prov[p]}">Tutta la provincia</a></p>') if alt else f'<p class="altri"><a href="{url_prov[p]}">Tutta la provincia di {e(provn.get(p, p))}</a></p>'
        n = len(v)
        pagine[url_citta[k].strip("/") + "/index.html"] = elenco(
            P, tabs, c, f"Ristoranti a {c}", f"<b>{n}</b> ristoranti segnalati da guide e stampa a {e(c)}.", url_citta[k],
            places_comune(c, p), c, v,
            f"<b>{n}</b> ristoranti segnalati a {e(c)} · ordinati per citazioni", altri_html,
            f"Ristoranti a {c}: i {n} migliori | Ach’s Dinners",
            f"I {n} ristoranti di {c} segnalati da guide, stampa e altre fonti online. Gratuita e senza pubblicità.")
    # --- province
    for p, v in per_prov.items():
        nome = provn.get(p, p)
        cc = sorted([kk for kk in citta if kk[1] == p], key=lambda kk: -len(citta[kk]))
        alt = "".join(f'<a href="{url_citta[kk]}">{e(kk[0])}</a>' for kk in cc)
        altri_html = f'<h2 class="sez">Le città</h2><p class="altri">{alt}</p>' if alt else ""
        n = len(v)
        pagine[url_prov[p].strip("/") + "/index.html"] = elenco(
            P, tabs, f"Provincia di {nome}", f"Ristoranti in provincia di {nome}",
            f"<b>{n}</b> ristoranti segnalati da guide e stampa in provincia di {e(nome)}.", url_prov[p],
            "https://achplaces.com/", nome, v, f"<b>{n}</b> ristoranti segnalati in provincia di {e(nome)} · ordinati per citazioni",
            altri_html, f"Ristoranti in provincia di {nome}: i {n} migliori | Ach’s Dinners",
            f"I {n} ristoranti della provincia di {nome} segnalati da guide, stampa e altre fonti online. Gratuita e senza pubblicità.")
    return pagine


def scrivi(pagine, P):
    oggi = datetime.date.today().isoformat()
    fisse = {"stile.css": P["stile"]}
    urls = [f"{SITO}/"] + [f"{SITO}/{k[:-len('index.html')]}" for k in sorted(pagine)]
    fisse["sitemap-pagine.xml"] = ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                   + "".join(f"<url><loc>{u}</loc></url>\n" for u in urls) + "</urlset>\n")
    fisse["sitemap.xml"] = ('<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                            f"<sitemap><loc>{SITO}/sitemap-pagine.xml</loc></sitemap>\n</sitemapindex>\n")
    fisse["robots.txt"] = f"User-agent: *\nAllow: /\n\nSitemap: {SITO}/sitemap.xml\n"
    tutte = dict(pagine, **fisse)
    scritti = 0
    for rel, testo in tutte.items():
        f = os.path.join(RADICE, rel)
        if os.path.exists(f) and open(f, encoding="utf-8").read() == testo:
            continue
        os.makedirs(os.path.dirname(f) or RADICE, exist_ok=True)
        open(f, "w", encoding="utf-8").write(testo)
        scritti += 1
    # togliere solo le pagine generate da qui in passato e non più servite
    elenco_f = os.path.join(RADICE, "pagine.json")
    prima = set(json.load(open(elenco_f))["pagine"]) if os.path.exists(elenco_f) else set()
    via = sorted(prima - set(pagine))
    for rel in via:
        if rel.split("/")[0] in CARTELLE and os.path.exists(os.path.join(RADICE, rel)):
            os.remove(os.path.join(RADICE, rel))
            try:
                os.rmdir(os.path.dirname(os.path.join(RADICE, rel)))
            except OSError:
                pass
    nuovo = json.dumps({"pagine": sorted(pagine)}, ensure_ascii=False, indent=0)
    if not os.path.exists(elenco_f) or open(elenco_f).read() != nuovo:
        open(elenco_f, "w").write(nuovo)
    print(f"pagine: {len(pagine)} (scritte o cambiate: {scritti}, tolte: {len(via)}) · {oggi}")
    return scritti, via


def controlli(pagine):
    """Prima di salvare: niente dati Google, ogni pagina ha titolo, descrizione e contenuto."""
    vietati = re.compile(r'"place_id"|googleusercontent|maps\.googleapis|"recensioni"|"rating"')
    for rel, t in pagine.items():
        assert not vietati.search(t), f"dati Google in {rel}"
        assert "<title>" in t and 'name="description"' in t, f"titolo o descrizione mancante in {rel}"
        assert 'class="card' in t or 'class="sheet pagina"' in t, f"pagina vuota: {rel}"


if __name__ == "__main__":
    prova = int(sys.argv[sys.argv.index("--prova") + 1]) if "--prova" in sys.argv else None
    P = pezzi()
    dati = cattura(prova)
    assert len(dati["locali"]) > (5 if prova else 2500), f"troppo pochi locali: {len(dati['locali'])}"
    pagine = costruisci(dati, P)
    controlli(pagine)
    scrivi(pagine, P)
