const CACHE_NAME = 'trackmotor-pwa-v1'; // Nome do cache do PWA

// O que queremos guardar no celular do usuário
const urlsToCache = [
    '/',
];

// Instalação do PWA no dispositivo
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                return cache.addAll(urlsToCache);
            })
    );
});

// Interceta as requisições (Faz o site carregar rápido ou funcionar offline)
self.addEventListener('fetch', event => {
    event.respondWith(
        caches.match(event.request)
            .then(response => {
                // Retorna a resposta do cache ou faz a requisição normalmente na internet se não estiver no cache
                return response || fetch(event.request);
            })
    );
});