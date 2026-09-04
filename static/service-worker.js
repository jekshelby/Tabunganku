const CACHE_NAME = 'catatuang-v2';

// Install Event
self.addEventListener('install', (event) => {
  self.skipWaiting();
});

// Activate Event (Hapus cache lama)
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cache) => {
          if (cache !== CACHE_NAME) {
            return caches.delete(cache);
          }
        })
      );
    })
  );
  self.clients.claim();
});

// Fetch Event: Network First (Coba ke Server Dulu, Baru Cache)
self.addEventListener('fetch', (event) => {
  // Hanya proses HTTP/HTTPS request
  if (!event.request.url.startsWith('http')) return;

  event.respondWith(
    fetch(event.request)
      .then((networkResponse) => {
        // Jika berhasil dapat data dari server, simpan salinannya ke cache
        if (networkResponse && networkResponse.status === 200 && event.request.method === 'GET') {
          const responseClone = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseClone);
          });
        }
        return networkResponse;
      })
      .catch(() => {
        // Jika offline / server gagal diakses, baru ambil dari cache
        return caches.match(event.request);
      })
  );
});