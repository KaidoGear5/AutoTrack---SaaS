const CACHE_NAME = 'trackmotor-v3';
const STATIC_ASSETS = [
    '/static/manifest.json',
    '/static/icon-192x192.png',
    '/static/icon-512x512.png'
];

// 1. Instala e guarda apenas arquivos estáticos reais (nunca páginas HTML ou redirecionamentos)
self.addEventListener('install', event => {
    self.skipWaiting();
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => {
            return cache.addAll(STATIC_ASSETS);
        })
    );
});

// 2. Apaga automaticamente caches antigos das versões antigas(v1 e v2) assim que ativar
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cache => {
                    if (cache !== CACHE_NAME) {
                        return caches.delete(cache);
                    }
                })
            );
        }).then(() => self.clients.claim())
    );
});

// 3. Intercepta APENAS arquivos estáticos (/static/), preservando 100% dos cookies de sessão e redirecionamentos 302
self.addEventListener('fetch', event => {
    // Nunca intercepta envios de formulário (POST) como login e cadastros
    if (event.request.method !== 'GET') {
        return;
    }

    const url = new URL(event.request.url);

    // Arquivos estáticos (/static/): usa o cache apenas se não houver redirecionamento
    if (url.pathname.startsWith('/static/')) {
        event.respondWith(
            caches.match(event.request).then(cachedResponse => {
                if (cachedResponse && !cachedResponse.redirected) {
                    return cachedResponse;
                }
                return fetch(event.request);
            })
        );
    }
});