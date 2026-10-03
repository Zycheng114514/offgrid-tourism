// Keeps the app and the last downloaded listings available with no connection.
const CACHE = "offgrid-v1";
const SHELL = ["./", "index.html", "app.css", "app.js", "manifest.webmanifest", "icon.svg"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});
self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;
  const cacheable = url.pathname.startsWith("/api/regions/") || url.pathname === "/api/config" ||
                    url.pathname === "/api/examples";
  if (cacheable) {  // network first, fall back to the last copy
    e.respondWith(fetch(e.request).then(res => {
      const copy = res.clone(); caches.open(CACHE).then(c => c.put(e.request, copy)); return res;
    }).catch(() => caches.match(e.request)));
  } else if (url.pathname.startsWith("/app/")) {  // app files: cache first
    e.respondWith(caches.match(e.request).then(hit => hit || fetch(e.request)));
  }
});
