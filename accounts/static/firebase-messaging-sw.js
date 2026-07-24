// static/firebase-messaging-sw.js [سكريبت الخلفية الصامت لإطلاق إشعارات الشاشة المغلقة]
importScripts('https://gstatic.com');
importScripts('https://gstatic.com');

// ⚙️ تهيئة خدمة Firebase بداخل الخلفية (توضع بيانات كونسول Firebase الخاص بك هنا لاحقاً)
firebase.initializeApp({
  apiKey: "YOUR_API_KEY",
  authDomain: "YOUR_PROJECT_://firebaseapp.com",
  projectId: "YOUR_PROJECT_ID",
  storageBucket: "YOUR_PROJECT_://appspot.com",
  messagingSenderId: "YOUR_SENDER_ID",
  appId: "YOUR_APP_ID"
});

const messaging = firebase.messaging();

// 🚀 تفجير الإشعار الجاذب للعين على لوحة الهاتف حتى لو كان المتصفح مغلقاً بالكامل 🚀
messaging.onBackgroundMessage((payload) => {
  console.log('[firebase-messaging-sw.js] Received background message ', payload);
  
  const notificationTitle = payload.data.title || 'طلب خدمة فوري في Otlop ⚡';
  const notificationOptions = {
    body: payload.data.body || 'لديك عرض سعر جديد أو رسالة شات معلقة! ادخل الحين لمطالعته 💵✍️',
    icon: '/static/images/logo1.png', // أيقونة السوبر آب الملوكية ثنائية الألوان
    badge: '/static/images/logo1.png',
    data: { url: payload.data.click_action || '/' } // توجيه اليوزر للرابط فور اللمس
  };

  return self.registration.showNotification(notificationTitle, notificationOptions);
});

// ميكانيكية الطيران بـ اليوزر للمتصفح فور نقر الإشعار بأصبعه
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  event.waitUntil(
    clients.openWindow(event.notification.data.url)
  );
});
