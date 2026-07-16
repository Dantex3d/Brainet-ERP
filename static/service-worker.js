// Version cache for update detection
const CACHE_VERSION = 'brainet-erp-v2';
const CACHE_NAME = CACHE_VERSION;
const STATIC_ASSETS = [
  '/',
  '/login',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js'
];

// Check for updates every time service worker activates
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS).catch(() => {
        console.log('Some static assets failed to cache');
      });
    })
  );
  self.skipWaiting(); // Activate new SW immediately
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            console.log('Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  self.clients.claim();
  
  // Check for updates on activation
  self.clients.matchAll().then((clients) => {
    clients.forEach((client) => {
      client.postMessage({ type: 'SW_ACTIVATED', version: CACHE_VERSION });
    });
  });
});

// Check for new versions periodically
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'CHECK_UPDATE') {
    checkForUpdates(event.ports[0]);
  }
});

async function checkForUpdates(port) {
  try {
    const response = await fetch('/manifest.json');
    if (response.ok) {
      port.postMessage({ type: 'UPDATE_AVAILABLE' });
    }
  } catch (error) {
    console.log('Update check failed:', error);
  }
}

// Fetch event - network first, then cache
self.addEventListener('fetch', (event) => {
  // Skip non-GET requests
  if (event.request.method !== 'GET') {
    return;
  }

  // Skip chrome extensions
  if (event.request.url.startsWith('chrome-extension://')) {
    return;
  }

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        // Don't cache non-successful responses
        if (!response || response.status !== 200 || response.type === 'error') {
          return response;
        }

        // Clone the response
        const responseClone = response.clone();

        // Cache the new response
        caches.open(CACHE_NAME).then((cache) => {
          cache.put(event.request, responseClone);
        });

        return response;
      })
      .catch(() => {
        // Return cached version if available
        return caches.match(event.request).then((cached) => {
          if (cached) {
            return cached;
          }
          // Return a fallback page if needed
          return new Response('You are offline. Please check your connection.', {
            status: 503,
            statusText: 'Service Unavailable',
            headers: new Headers({
              'Content-Type': 'text/plain'
            })
          });
        });
      })
  );
});
