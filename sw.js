/* 15/11/2026 – la guida come un'app: serve ad Android per offrire «Installa».
   Solo la pagina: prima la rete, la copia salvata se la rete manca. Dati, foto e altri siti passano com'è. */
const V = "app-1";
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", e => e.waitUntil((async () => {
  for (const k of await caches.keys()) if (k !== V && k.startsWith("app-")) await caches.delete(k);
  await self.clients.claim();
})()));
self.addEventListener("fetch", e => {
  const r = e.request;
  if (r.method !== "GET" || r.mode !== "navigate") return;
  const u = new URL(r.url);
  e.respondWith((async () => {
    const c = await caches.open(V);
    try { const n = await fetch(r); if (n.ok) c.put(u.pathname, n.clone()); return n; }
    catch (x) { const h = (await c.match(u.pathname)) || (await c.match("/")); if (h) return h; throw x; }
  })());
});
