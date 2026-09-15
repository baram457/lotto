const CACHE = 'lotto-v2';
const ASSETS = [
  '/lotto/',
  '/lotto/index.html',
  '/lotto/manifest.json',
  '/lotto/icon.svg'
];

self.addEventListener('install', function(e) {
  e.waitUntil(
    caches.open(CACHE).then(function(c) {
      return c.addAll(ASSETS).catch(function() {});
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', function(e) {
  e.waitUntil(
    caches.keys().then(function(keys) {
      return Promise.all(
        keys.filter(function(k) { return k !== CACHE; })
            .map(function(k) { return caches.delete(k); })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', function(e) {
  var req = e.request;
  if (req.method !== 'GET') return;

  if (req.url.indexOf('/data/') !== -1) {
    e.respondWith(
      fetch(req).then(function(r) {
        var copy = r.clone();
        caches.open(CACHE).then(function(c) { c.put(req, copy); });
        return r;
      }).catch(function() {
        return caches.match(req);
      })
    );
    return;
  }

  e.respondWith(
    caches.match(req).then(function(cached) {
      return cached || fetch(req);
    })
  );
});