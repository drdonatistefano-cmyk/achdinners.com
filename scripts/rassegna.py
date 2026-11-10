#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rassegna stampa automatica: prepara i candidati, non decide.

GitHub legge i feed delle testate e sorveglia le pagine delle guide, abbina i
nomi ai locali gia' in archivio e scrive un elenco di candidati. La sessione
settimanale di Claude legge solo quei candidati e decide che cosa vale: il
giudizio resta suo, la lettura del web no.

Esce:
  rassegna/candidati.csv   un articolo per riga, con il locale abbinato
  rassegna/sentinella.json stato delle pagine-elenco delle guide
  rassegna/viste.csv       articoli gia' proposti, per non riproporli
  rassegna/RIEPILOGO.md    quanti candidati, per testata e per provincia

Regole prese da coordinamento/food/GUIDE_DA_CERCARE.md:
  - la data e' obbligatoria per articoli, blog e social
  - esclusi TripAdvisor, TheFork, Sluurpy, Restaurant Guru, elenchi anonimi,
    contenuti sponsorizzati o pubbliredazionali
  - oltre 5 anni un riferimento vale 0: qui non si propone nemmeno

Uso:  python3 scripts/rassegna.py [--giorni 45] [--solo feed|sentinella]
"""

import csv
import glob
import hashlib
import html
import json
import os
import re
import socket
import sys
import time
import unicodedata
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTI = os.path.join(RADICE, "scripts", "rassegna_fonti.json")
USCITA = os.path.join(RADICE, "rassegna")
CANDIDATI = os.path.join(USCITA, "candidati.csv")
VISTE = os.path.join(USCITA, "viste.csv")
SENTINELLA = os.path.join(USCITA, "sentinella.json")
RIEPILOGO = os.path.join(USCITA, "RIEPILOGO.md")
REGISTRO = os.path.join(USCITA, "registro-letture.csv")
TESTI = os.path.join(USCITA, "testi")        # il testo degli articoli candidati
ELENCHI = os.path.join(USCITA, "elenchi")    # il testo delle pagine-elenco cambiate

AGENTE = ("Mozilla/5.0 (compatible; AchDinnersBot/1.0; "
          "+https://achdinners.com/ rassegna stampa)")
SCADENZA = 25
ATTESA = 1.0
MAX_BYTE = 6_000_000

COLONNE = ["data", "testata", "codice", "titolo", "url", "id_locale",
           "nome", "prov", "comune", "indizi", "stato", "testo"]

# Da non proporre mai: lo dicono le regole della guida
ESCLUSI = re.compile(
    r"(tripadvisor|thefork|sluurpy|restaurantguru|restaurant-guru|quandoo|"
    r"misterfood|justeat|deliveroo|glovo)", re.I)
PUBBLICITA = re.compile(
    r"(sponsoriz|pubbliredaz|in collaborazione con|advertorial|"
    r"contenuto promozion|publiredaz)", re.I)


def log(m):
    print(f"[{datetime.now():%H:%M:%S}] {m}", flush=True)


def piano(s):
    """Testo ridotto a sole lettere minuscole, senza accenti ne' spazi."""
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", s.lower())


def parole(s):
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return set(re.findall(r"[a-z]{3,}", s.lower()))


# ------------------------------------------------------------ rete

_ultima = {}


def frena(url):
    h = urllib.parse.urlparse(url).netloc if hasattr(urllib, "parse") else ""
    import urllib.parse as up
    h = up.urlparse(url).netloc
    d = time.time() - _ultima.get(h, 0)
    if d < ATTESA:
        time.sleep(ATTESA - d)
    _ultima[h] = time.time()


def leggi(url, tentativi=2):
    """Un secondo tentativo quando la connessione cade a meta': capita con
    alcuni siti che chiudono la prima connessione senza rispondere."""
    ultimo = None
    for i in range(tentativi):
        frena(url)
        req = urllib.request.Request(url, headers={
            "User-Agent": AGENTE,
            "Accept": "application/rss+xml,application/atom+xml,application/xml,"
                      "text/xml,text/html;q=0.8,*/*;q=0.5",
            "Accept-Language": "it,en;q=0.8",
            "Connection": "close"})
        try:
            with urllib.request.urlopen(req, timeout=SCADENZA) as r:
                return r.read(MAX_BYTE), None
        except urllib.error.HTTPError as ex:
            return None, f"HTTP {ex.code}"      # 403 e 404 non migliorano riprovando
        except urllib.error.URLError as ex:
            ultimo = f"rete: {ex.reason}"
        except socket.timeout:
            ultimo = "tempo scaduto"
        except Exception as ex:
            ultimo = f"{type(ex).__name__}: {ex}"
        if i + 1 < tentativi:
            time.sleep(3)
    return None, ultimo


# ------------------------------------------------------------ locali

def indice_locali():
    """Da d/<PROV>.<impronta>.json: id -> (nome appiattito, prov, comune)."""
    idx = {}
    for f in glob.glob(os.path.join(RADICE, "d", "*.json")):
        try:
            with open(f, encoding="utf-8") as fh:
                righe = json.load(fh)
        except Exception:
            continue
        for r in righe:
            if not isinstance(r, list) or len(r) < 4 or not r[3]:
                continue
            pezzi = r[3].split("-")
            if len(pezzi) < 3:
                continue
            prov, nome, comune = pezzi[0], pezzi[1], "-".join(pezzi[2:])
            if len(nome) < 10:          # nomi corti: troppi falsi abbinamenti
                continue
            idx[r[3]] = (nome, prov, comune)
    return idx


def abbina(testo, idx, comuni_per_nome):
    """Un articolo e' candidato se nel testo compaiono il nome del locale e,
    come conferma, il suo comune. Senza il comune l'abbinamento non si propone:
    meglio perdere un candidato che proporne uno sbagliato."""
    p = piano(testo)
    if len(p) < 40:
        return []
    fuori = []
    for idl, (nome, prov, comune) in idx.items():
        if nome in p:
            if comune and comune[:8] in p:
                fuori.append((idl, nome, prov, comune, "nome e comune"))
            elif len(nome) >= 16:
                fuori.append((idl, nome, prov, comune, "solo nome, da controllare"))
    return fuori[:6]


# ------------------------------------------------------------ feed

def data_di(testo):
    if not testo:
        return None
    testo = testo.strip()
    for f in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z",
              "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d",
              "%a, %d %b %Y %H:%M %z"):
        try:
            d = datetime.strptime(testo.replace("GMT", "+0000"), f)
            return d.date().isoformat()
        except Exception:
            continue
    m = re.search(r"(20\d\d)-(\d\d)-(\d\d)", testo)
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None


def voci_feed(dati):
    """RSS o Atom, senza librerie esterne."""
    try:
        radice = ET.fromstring(dati)
    except Exception:
        return []
    ns = {"a": "http://www.w3.org/2005/Atom"}
    fuori = []
    for it in radice.iter():
        tag = it.tag.split("}")[-1]
        if tag not in ("item", "entry"):
            continue
        def campo(*nomi):
            for n in nomi:
                e = it.find(n) if "}" not in n else None
                if e is None:
                    e = it.find(f"{{http://www.w3.org/2005/Atom}}{n}")
                if e is not None and (e.text or e.get("href")):
                    return (e.text or e.get("href") or "").strip()
            return ""
        titolo = html.unescape(campo("title"))
        link = campo("link", "guid")
        if not link:
            e = it.find("{http://www.w3.org/2005/Atom}link")
            link = e.get("href") if e is not None else ""
        data = data_di(campo("pubDate", "published", "updated", "date"))
        testo = " ".join(filter(None, [
            titolo,
            html.unescape(re.sub(r"<[^>]+>", " ", campo("description") or "")),
            html.unescape(re.sub(r"<[^>]+>", " ", campo("summary", "content") or "")),
        ]))
        if titolo and link:
            fuori.append({"titolo": titolo, "url": link, "data": data,
                          "testo": testo})
    return fuori


def solo_testo(dati):
    t = re.sub(rb"<(script|style|nav|footer|aside)[^>]*>.*?</\1>", b" ", dati,
               flags=re.I | re.S)
    t = re.sub(rb"<[^>]+>", b" ", t)
    try:
        t = t.decode("utf-8", "replace")
    except Exception:
        t = str(t)
    t = html.unescape(t)
    return re.sub(r"[ \t\xa0]+", " ", re.sub(r"\n{3,}", "\n\n", t)).strip()


def salva_testo(cartella, chiave, url, titolo, registro, fonte, tipo):
    """Scarica la pagina e ne salva il testo: cosi' Claude lo legge da file e
    non deve aprire nessun sito (niente finestre di permesso, niente crediti).
    Restituisce il nome del file, o '' se la pagina non si e' aperta."""
    os.makedirs(cartella, exist_ok=True)
    nome = chiave + ".txt"
    dove = os.path.join(cartella, nome)
    if os.path.exists(dove) and os.path.getsize(dove) > 200:
        return nome
    dati, errore = leggi(url)
    registro.append([fonte, url, tipo, errore or "ok",
                     datetime.now().date().isoformat()])
    if errore or not dati:
        return ""
    testo = solo_testo(dati)
    if len(testo) < 200:
        return ""
    with open(dove, "w", encoding="utf-8") as f:
        f.write(f"# {titolo}\n# {url}\n# letto il {datetime.now().date().isoformat()}\n\n")
        f.write(testo[:40000])
    return nome


# ------------------------------------------------------------ giro

def main():
    giorni = 45
    if "--giorni" in sys.argv:
        giorni = int(sys.argv[sys.argv.index("--giorni") + 1])
    solo = sys.argv[sys.argv.index("--solo") + 1] if "--solo" in sys.argv else None

    os.makedirs(USCITA, exist_ok=True)
    with open(FONTI, encoding="utf-8") as f:
        cfg = json.load(f)

    viste = set()
    if os.path.exists(VISTE):
        with open(VISTE, encoding="utf-8", newline="") as f:
            for r in csv.reader(f):
                if r:
                    viste.add(r[0])

    vecchi = {}
    if os.path.exists(CANDIDATI):
        with open(CANDIDATI, encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                vecchi[(r.get("url", ""), r.get("id_locale", ""))] = \
                    [r.get(c, "") for c in COLONNE]

    log("leggo l'archivio dei locali")
    idx = indice_locali()
    log(f"{len(idx)} locali con nome utilizzabile")

    registro = []
    nuovi = 0
    limite = (datetime.now(timezone.utc) - timedelta(days=giorni)).date().isoformat()

    if solo != "sentinella":
        for fo in cfg.get("feed", []):
            if not fo.get("attiva", True):
                continue
            dati, errore = leggi(fo["url"])
            registro.append([fo["id"], fo["url"], "feed", errore or "ok",
                             datetime.now().date().isoformat()])
            if errore:
                log(f"  {fo['id']}: {errore}")
                continue
            voci = voci_feed(dati)
            presi = 0
            for v in voci:
                if not v["data"] or v["data"] < limite:
                    continue
                if v["url"] in viste:
                    continue
                if ESCLUSI.search(v["url"]) or PUBBLICITA.search(v["testo"]):
                    continue
                for idl, nome, prov, comune, indizi in abbina(
                        v["titolo"] + " " + v["testo"], idx, None):
                    chiave = (v["url"], idl)
                    if chiave in vecchi:
                        continue
                    vecchi[chiave] = [v["data"], fo["testata"],
                                      fo.get("codice", "CRIT"),
                                      v["titolo"][:160], v["url"], idl, nome,
                                      prov, comune, indizi, "da valutare", ""]
                    presi += 1
                    nuovi += 1
                viste.add(v["url"])
            log(f"  {fo['id']}: {len(voci)} voci, {presi} candidati")

    # sentinella sulle pagine-elenco delle guide
    stato = {}
    if os.path.exists(SENTINELLA):
        try:
            with open(SENTINELLA, encoding="utf-8") as f:
                stato = json.load(f)
        except Exception:
            stato = {}
    if solo != "feed":
        for s in cfg.get("sentinella", []):
            if not s.get("attiva", True):
                continue
            dati, errore = leggi(s["pagina"])
            registro.append([s["id"], s["pagina"], "sentinella", errore or "ok",
                             datetime.now().date().isoformat()])
            if errore:
                stato.setdefault(s["id"], {})["ultimo_errore"] = errore
                log(f"  sentinella {s['id']}: {errore}")
                continue
            testo = re.sub(rb"<(script|style)[^>]*>.*?</\1>", b" ", dati,
                           flags=re.I | re.S)
            testo = re.sub(rb"<[^>]+>", b" ", testo)
            imp = hashlib.sha256(b" ".join(testo.split())).hexdigest()[:16]
            vecchia = (stato.get(s["id"]) or {}).get("impronta")
            stato[s["id"]] = {
                "pagina": s["pagina"], "nota": s.get("nota", ""),
                "impronta": imp,
                "esito": "nuova" if not vecchia else
                         ("cambiata" if imp != vecchia else "uguale"),
                "visto": datetime.now().date().isoformat(),
            }
            if stato[s["id"]]["esito"] in ("nuova", "cambiata"):
                os.makedirs(ELENCHI, exist_ok=True)
                testo = solo_testo(dati)
                if len(testo) > 200:
                    with open(os.path.join(ELENCHI, s["id"] + ".txt"), "w",
                              encoding="utf-8") as fh:
                        fh.write(f"# {s.get('nota','')}\n# {s['pagina']}\n"
                                 f"# letto il {datetime.now().date().isoformat()}\n\n")
                        fh.write(testo[:60000])
                    stato[s["id"]]["testo"] = s["id"] + ".txt"
            log(f"  sentinella {s['id']}: {stato[s['id']]['esito']}")

    # il testo degli articoli ancora da valutare, salvato su file
    da_leggere = [r for r in vecchi.values()
                  if r[10] == "da valutare" and not r[11]]
    visti_url = {}
    for r in da_leggere[:120]:
        u = r[4]
        if u in visti_url:
            r[11] = visti_url[u]
            continue
        chiave = hashlib.sha1(u.encode()).hexdigest()[:16]
        nome = salva_testo(TESTI, chiave, u, r[3], registro, "articolo", "testo")
        visti_url[u] = nome
        r[11] = nome
    log(f"  testi salvati: {sum(1 for v in visti_url.values() if v)} "
        f"su {len(visti_url)} articoli")

    # pulizia: via i testi degli articoli non piu' in attesa di giudizio
    vivi = {r[11] for r in vecchi.values() if r[10] == "da valutare" and r[11]}
    if os.path.isdir(TESTI):
        for f_ in os.listdir(TESTI):
            if f_ not in vivi:
                try:
                    os.remove(os.path.join(TESTI, f_))
                except Exception:
                    pass

    # scrittura
    righe = sorted(vecchi.values(), key=lambda r: (r[0], r[1]), reverse=True)
    with open(CANDIDATI, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(COLONNE)
        w.writerows(righe)
    with open(VISTE, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        for u in sorted(viste):
            w.writerow([u])
    with open(SENTINELLA, "w", encoding="utf-8") as f:
        json.dump(stato, f, ensure_ascii=False, indent=1)
    nuovo_reg = not os.path.exists(REGISTRO)
    with open(REGISTRO, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if nuovo_reg:
            w.writerow(["fonte", "indirizzo", "tipo", "esito", "data"])
        w.writerows(registro)

    da_valutare = [r for r in righe if r[10] == "da valutare"]
    per_testata = {}
    per_prov = {}
    for r in da_valutare:
        per_testata[r[1]] = per_testata.get(r[1], 0) + 1
        per_prov[r[7]] = per_prov.get(r[7], 0) + 1
    cambiate = [k for k, v in stato.items() if v.get("esito") in ("nuova", "cambiata")]

    with open(RIEPILOGO, "w", encoding="utf-8") as f:
        f.write("# Rassegna stampa: candidati da valutare\n\n")
        f.write(f"Ultimo giro: {datetime.now().date().isoformat()}  \n")
        f.write(f"Candidati in attesa di giudizio: **{len(da_valutare)}** "
                f"(nuovi in questo giro: {nuovi})  \n")
        f.write(f"Pagine-elenco delle guide nuove o cambiate: "
                f"**{len(cambiate)}**"
                + (f" ({', '.join(cambiate)})" if cambiate else "") + "\n\n")
        if per_testata:
            f.write("| Testata | Candidati |\n|---|---:|\n")
            for k, v in sorted(per_testata.items(), key=lambda x: -x[1]):
                f.write(f"| {k} | {v} |\n")
            f.write("\n")
        if per_prov:
            f.write("Province toccate: "
                    + ", ".join(f"{k} ({v})" for k, v in
                                sorted(per_prov.items(), key=lambda x: -x[1])[:20])
                    + "\n\n")
        f.write("Il testo di ogni articolo e' gia' salvato in "
                "`rassegna/testi/<file>.txt` (colonna `testo` del CSV) e quello "
                "delle pagine-elenco nuove o cambiate in "
                "`rassegna/elenchi/<id>.txt`: **non serve aprire nessun sito**, "
                "si leggono da file.\n\n")
        f.write("GitHub prepara i candidati, non decide. La sessione settimanale "
                "legge questo elenco, controlla l'abbinamento e scrive le "
                "citazioni valide nel formato di `GUIDE_DA_CERCARE.md`. Gli "
                "abbinamenti segnati «solo nome, da controllare» vanno "
                "verificati con piu' attenzione: manca la conferma del comune.\n\n")
        f.write("Esclusi per regola: TripAdvisor, TheFork, Sluurpy, Restaurant "
                "Guru e simili, contenuti sponsorizzati o pubbliredazionali, "
                "articoli senza data e articoli di oltre "
                f"{giorni} giorni fa.\n")

    log(f"{len(da_valutare)} candidati da valutare, {nuovi} nuovi; "
        f"{len(cambiate)} pagine-elenco da guardare")


if __name__ == "__main__":
    main()
