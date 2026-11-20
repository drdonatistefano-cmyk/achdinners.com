"""Raccolta una tantum di Golosario e Falstaff per Dinners (19/11/2026, decisione di Stefano «ok 1 e 2»).

Legge pagine pubbliche una volta sola (REGOLE 6) e scrive il risultato in out/ (artefatto del giro, tenuto 1 giorno,
poi scaricato nel repository privato e cancellato). Nel repository pubblico non resta nessun testo di pagine altrui.
Modi:
  prova      legge gli indirizzi dati (uno per riga) e salva l'HTML grezzo, per studiare le pagine
  falstaff   (da scrivere dopo la prova)
  golosario  (da scrivere dopo la prova)
"""
import os, sys, time, json, re, hashlib, urllib.request, urllib.error
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36 (+https://achdinners.com/chi-siamo/)"
OUT = "out"
def leggi(url, tentativi=2):
    for t in range(tentativi):
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "it-IT,it;q=0.9"}), timeout=40)
            return r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and t + 1 < tentativi: time.sleep(10); continue
            return e.code, ""
        except Exception as e:
            if t + 1 < tentativi: time.sleep(5); continue
            return 0, str(e)
def prova(indirizzi):
    idx = []
    for u in indirizzi:
        st, h = leggi(u)
        nome = hashlib.md5(u.encode()).hexdigest()[:10] + ".html"
        open(f"{OUT}/{nome}", "w").write(h)
        idx.append({"url": u, "stato": st, "byte": len(h), "file": nome})
        print(st, len(h), u)
        # nel registro solo stato, robots.txt e indirizzi dei link (niente testo delle pagine)
        if "robots.txt" in u: print("  ROBOTS", " | ".join(l for l in h.splitlines() if l.strip())[:900])
        links = sorted(set(re.findall(r'href="((?:https?://www\.ilgolosario\.it)?/[a-z][^"\s#?]*)"', h)))
        ids = re.findall(r'data-id="([0-9a-f]{24})" data-card', h); print("  SCHEDE", len(ids), ids[:2])
        if u.endswith(".js"):
            for k in ("StoreCTA", "data-from", ".data(\"from", "from:", "limit:", "ajax("):
                for m in list(re.finditer(re.escape(k), h))[:3]: print("  JS", k, "::", h[max(0, m.start() - 200):m.start() + 300].replace("\n", " "))
        low = h.lower(); print("  PAROLE", {k: low.count(k) for k in ("corona", "radios", "faccino", "sorriso", "contento", "-ip", "2027", "pagina", "page=")})
        for m in re.finditer(r'(-ip\d+)"', h):
            w = h[m.start():m.start() + 3000]; sim = re.findall(r'(faccino[\w-]*|radios[\w-]*|corona[\w-]*|contento[\w-]*)', w)
            print("  VOCE", m.group(1), sim[:3])
        print("  AJAX", sorted(set(re.findall(r'["\'](/(?:ccm|index\.php|tools|application/tools|mosaic)[^"\'\s]{0,120})["\']', h)))[:40])
        for t in re.findall(r'<[a-z]+[^>]*data-(?:next|limit|from|simboli|card)=[^>]*>', h)[:6]: print("  TAG", re.sub(r"\s+", " ", t)[:500])
        for t in re.findall(r'(?:url|endpoint|action)\s*[:=]\s*["\']([^"\']{3,160})["\']', h)[:30]: print("  URLJS", t)
        print("  SCRIPT", re.findall(r'<script[^>]+src="([^"]+)"', h)[:30])
        print("  DATA", sorted(set(re.findall(r'(data-[a-z-]+)="', h)))[:60])
        print("  LINK", len(links)); [print("   ", l[:140]) for l in links[:150]]
        time.sleep(1.5)
    json.dump(idx, open(f"{OUT}/indice.json", "w"), indent=1)
def michelin():
    """20/11/2026 (Stefano: «ti autorizzo a leggere Michelin»; strada A del 19/11): elenco nazionale dei «Selected Restaurants»
    della Guida Michelin Italia (guide.michelin.com, robots.txt lo permette), una pagina dopo l'altra finché ci sono schede.
    Salva l'HTML grezzo delle pagine-elenco (compresso) per il confronto nel repository privato: qui non resta nulla."""
    import gzip
    base = "https://guide.michelin.com/it/it/ristoranti/the-plate-michelin"
    idx, visti = [], set()
    for n in range(1, 200):
        u = base if n == 1 else f"{base}/page/{n}"
        st, h = leggi(u, 3)
        schede = sorted(set(re.findall(r'href="(/it/it/[^"]+/ristorante/[^"]+)"', h)))
        nuove = [s for s in schede if s not in visti]; visti.update(schede)
        gzip.open(f"{OUT}/pagina-{n:03d}.html.gz", "wt").write(h)
        idx.append({"url": u, "stato": st, "byte": len(h), "schede": len(schede), "nuove": len(nuove)})
        print(st, len(h), "schede", len(schede), "nuove", len(nuove), u)
        if st != 200 or not nuove: break
        time.sleep(2)
    json.dump(idx, open(f"{OUT}/indice.json", "w"), indent=1)
    print("schede in tutto", len(visti))
if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    modo = sys.argv[1]
    if modo == "prova": prova([u.strip() for u in os.environ.get("INDIRIZZI", "").splitlines() if u.strip()])
    elif modo == "michelin": michelin()
    else: sys.exit("modo non ancora pronto: " + modo)
