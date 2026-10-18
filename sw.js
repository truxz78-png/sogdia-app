/* Sogdia service worker: network-first.
   Always tries the internet first (fresh content); if offline, shows the last saved copy. */
const CACHE = "sogdia-v1";

self.addEventListener("install", () => self.skipWaiting());

self.addEventListener("activate", (e) => {
  e.waitUntil((async () => {
    for (const k of await caches.keys()) if (k !== CACHE) await caches.delete(k);
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET" || new URL(req.url).origin !== self.location.origin) return;
  e.respondWith((async () => {
    try {
      const res = await fetch(req, { cache: "no-store" });
      if (res && res.ok) {
        const key = req.url.split("?")[0];
        (await caches.open(CACHE)).put(key, res.clone());
      }
      return res;
    } catch (err) {
      const hit = await caches.match(req.url.split("?")[0]) || await caches.match(req, { ignoreSearch: true });
      return hit || Response.error();
    }
  })());
});
