const CACHE_NAME = 'otlop-cache-v1';
// الملفات الأساسية الشاملة لحماية الواجهة من الانهيار الأوفلاين
const ASSETS_TO_CACHE = [
  '/',
  '/static/manifest.json'
];

// تثبيت السيرفس وركر وحفظ الملفات الثابتة في كاش الهاتف
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS_TO_CACHE);
    })
  );
});

// استراتيجية النتوورك أولاً ثم الكاش (Network-first, falling back to cache)
// وهي الاستراتيجية الأقوى لمنصات التواصل؛ يجلب الجديد وإذا فصل النت يحقن القديم فوراً
self.addEventListener('fetch', (event) => {
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        // إذا كان الإنترنت يعمل، قم بتحديث الكاش بالمنشورات الجديدة
        if (event.request.method === 'GET' && response.status === 200) {
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseClone);
          });
        }
        return response;
      })
      .catch(() => {
        // ⚠️ الإنترنت فاصل! قم بسحب وحقن آخر تايم لاين تم حفظه تلقائياً لمنع الشاشة البيضاء
        return caches.match(event.request).then((cachedResponse) => {
          if (cachedResponse) {
            return cachedResponse;
          }
        });
      })
  );
});
