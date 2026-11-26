const CACHE_NAME = 'trackmotor-v2';
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

// 2. Apaga automaticamente o cache da versão 1 (v1) defeituoso assim que ativar
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

// 3. Interceptação segura para Django (preserva redirecionamentos 302 e csrf_token)
self.addEventListener('fetch', event => {
    // Nunca intercepta envios de formulário (POST) como login e cadastros
    if (event.request.method !== 'GET') {
        return;
    }

    const url = new URL(event.request.url);

    // Páginas HTML: busca sempre direto na VPS e exibe aviso amigável apenas se estiver sem internet
    if (event.request.mode === 'navigate') {
        event.respondWith(
            fetch(event.request).catch(() => {
                return new Response(
                    '<!DOCTYPE html><html lang="pt-br"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Sem conexão - Trackmotor</title><style>body{background:#1a1d24;color:#fff;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;text-align:center;padding:20px}h2{color:#f39c12}</style></head><body><div><h2>Você está sem internet</h2><p>Verifique sua conexão e tente novamente.</p></div></body></html>',
                    { headers: { 'Content-Type': 'text/html; charset=utf-8' } }
                );
            })
        );
        return;
    }

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