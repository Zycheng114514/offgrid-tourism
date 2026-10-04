// Keeps the app, the last downloaded listings and the offline assistant's code available with no connection.
const CACHE = "offgrid-v6";          // app files, region pack, config, examples
const CDN_CACHE = "offgrid-cdn-v1";  // transformers.js and the ONNX runtime files it loads, from cdn.jsdelivr.net
const SHELL = ["./", "index.html", "app.css", "app.js", "assistant-worker.js", "manifest.webmanifest", "icon.svg"];
// The assistant's model files (520-790 MB) are kept by assistant-worker.js in the "transformers-cache" cache.
// Only our own "offgrid-" caches are ever deleted here, so a new app version never removes the model.

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys
    .filter(k => k.startsWith("offgrid-") && k !== CACHE && k !== CDN_CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});
self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;  // POST /api/chat and /api/simulate always go to the network and are never stored
  const url = new URL(req.url);
  if (url.origin === "https://cdn.jsdelivr.net") {  // library and runtime: version-pinned URLs, so cache first
    e.respondWith((async () => {
      const c = await caches.open(CDN_CACHE);
      const hit = await c.match(req);
      if (hit) return hit;
      const res = await fetch(req);
      if (res.ok) e.waitUntil(c.put(req, res.clone()));
      return res;
    })());
    return;
  }
  if (url.origin !== location.origin) return;  // e.g. model files from Hugging Face: not stored here
  const cacheable = url.pathname.startsWith("/api/regions/") || url.pathname === "/api/config" ||
                    url.pathname === "/api/examples";
  if (cacheable) {  // network first, fall back to the last copy
    e.respondWith(fetch(req).then(res => {
      const copy = res.clone(); caches.open(CACHE).then(c => c.put(req, copy)); return res;
    }).catch(() => caches.match(req)));
  } else if (url.pathname.startsWith("/app/")) {  // app files: cache first
    e.respondWith(caches.match(req).then(hit => hit || fetch(req)));
  }
});
