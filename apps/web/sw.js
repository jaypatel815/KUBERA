// T136 — KUBERA service worker: SHELL ONLY, by doctrine.
//
// The shell (page, manifest, icon) is cached so the installed app opens
// instantly and survives a dead server with its own named degradations.
// API responses are NEVER cached — AGENTS.md priority 1: never present
// stale data as current. A cached /portfolio would show old money as
// live money; offline, the panels' existing "broker offline" /
// "unavailable" states ARE the honest answer.

const SHELL_CACHE = "kubera-shell-v1";
const SHELL = ["/", "/manifest.webmanifest", "/icon.svg"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(SHELL_CACHE).then((c) => c.addAll(SHELL)));
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== SHELL_CACHE)
                      .map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  // Financial data is network-ONLY: no cache read, no cache write.
  if (url.pathname.startsWith("/api/") || url.pathname === "/portfolio" ||
      url.pathname === "/health") {
    return; // default browser behavior — straight to the network
  }
  if (e.request.method !== "GET") return;
  // Shell: cache-first, refresh in the background (stale shell is fine;
  // stale MONEY is not — that distinction is this file's whole job).
  e.respondWith(
    caches.match(e.request).then((hit) => {
      const fetched = fetch(e.request).then((res) => {
        if (res.ok && SHELL.includes(url.pathname)) {
          const copy = res.clone();
          caches.open(SHELL_CACHE).then((c) => c.put(e.request, copy));
        }
        return res;
      }).catch(() => hit); // offline: the cached shell, or nothing
      return hit || fetched;
    })
  );
});
