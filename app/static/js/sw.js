const CACHE_NAME = 'gestao-placas-v6';
const urlsToCache = [
  '/',
  '/static/css/style.css',
  '/static/js/app.js',
  '/static/manifest.json'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        return cache.addAll(urlsToCache);
      })
  );
  self.skipWaiting();
});

self.addEventListener('fetch', (event) => {
  // Nunca cachear chamadas de API, auth, uploads ou requisições que não sejam GET
  if (event.request.url.includes('/api/') || 
      event.request.url.includes('/auth/') ||
      event.request.url.includes('/uploads/') ||
      event.request.method !== 'GET') {
    event.respondWith(fetch(event.request));
    return;
  }

  // NUNCA cachear arquivos JavaScript com query strings (ex: conferencias.js?v=123)
  // Isso permite que versões atualizadas sejam carregadas imediatamente
  if (event.request.url.includes('.js?')) {
    event.respondWith(fetch(event.request));
    return;
  }

  event.respondWith(
    caches.match(event.request)
      .then((response) => {
        if (response) {
          return response;
        }
        return fetch(event.request);
      })
  );
});

self.addEventListener('activate', (event) => {
  const cacheWhitelist = [CACHE_NAME];
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheWhitelist.indexOf(cacheName) === -1) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  // Forçar o novo service worker a assumir controle imediatamente
  event.waitUntil(clients.claim());
});
