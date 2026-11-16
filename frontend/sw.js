// Minimal offline shell: cache static files, always go to the network for the API.
const CACHE = "saagi-shell-v4";
const SHELL = ["/", "/index.html", "/submit.html", "/track.html", "/feed.html", "/cabinet.html", "/privacy.html", "/staff.html", "/app.css", "/common.js", "/home.js", "/submit.js", "/track.js", "/feed.js", "/cabinet.js", "/cabinet-data.json", "/privacy.js", "/staff.js", "/manifest.json", "/assets/isbat-logo.png", "/icon.svg"];
self.addEventListener("install", (e) => e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL))));
self.addEventListener("activate", (e) => e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k))))));
self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (url.pathname.startsWith("/api") || e.request.method !== "GET") return;
  e.respondWith(fetch(e.request).catch(() => caches.match(e.request)));
});
