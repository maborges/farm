const CACHE_NAME = "deepfarms-agro-v5";

const APP_SHELL = [
  "/",
  "/clima",
  "/mercado",
  "/calculadoras",
  "/comunidade",
  "/offline",
  "/logos/deepfarms-logo.svg",
  "/logos/deepfarms-logo-negative.svg",
  "/logos/deepfarms-mark.svg",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
  "/favicon.ico"
];

// Instalação do Service Worker e pré-cache do shell
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => cache.addAll(APP_SHELL))
      .then(() => self.skipWaiting())
  );
});

// Ativação e limpeza de caches antigos da versão anterior
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key.startsWith("deepfarms-agro-") && key !== CACHE_NAME)
          .map((key) => caches.delete(key))
      )
    ).then(() => self.clients.claim())
  );
});

// Interceptação de requisições
self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);

  // Apenas métodos GET na mesma origem
  if (request.method !== "GET" || url.origin !== self.location.origin) {
    return;
  }

  // NUNCA fazer cache de rotas de API ou autenticação
  if (url.pathname.startsWith("/api/")) {
    return;
  }

  // Para navegações de página (HTML)
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (response.status === 200) {
            const copy = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
          }
          return response;
        })
        .catch(() => {
          return caches.match(request).then((cached) => {
            return cached || caches.match("/offline") || caches.match("/");
          });
        })
    );
    return;
  }

  // Bundles do Next precisam ser sempre buscados primeiro. Cache-first aqui
  // mantém componentes antigos ativos após um novo build ou HMR.
  if (url.pathname.startsWith("/_next/")) {
    event.respondWith(
      fetch(request)
        .then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200) {
            const copy = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
          }
          return networkResponse;
        })
        .catch(() => caches.match(request))
    );
    return;
  }

  // Para imagens e demais assets estáticos.
  event.respondWith(
    caches.match(request).then((cachedResponse) => {
      const fetchPromise = fetch(request)
        .then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200) {
            const copy = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
          }
          return networkResponse;
        })
        .catch(() => cachedResponse);

      return cachedResponse || fetchPromise;
    })
  );
});
