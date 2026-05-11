// firebase-messaging-sw.js
importScripts('https://www.gstatic.com/firebasejs/12.12.1/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/12.12.1/firebase-messaging-compat.js');

// Sua configuração do Firebase
firebase.initializeApp({
    apiKey: "AIzaSyCmRtDskJ4qkIA3RNmDKwR8XvsazHBic2w",
    authDomain: "codemindmicrocredito-app.firebaseapp.com",
    projectId: "codemindmicrocredito-app",
    storageBucket: "codemindmicrocredito-app.firebasestorage.app",
    messagingSenderId: "319943045295",
    appId: "1:319943045295:web:3da299b2c07580ff82645a",
    measurementId: "G-VC4H0PKTXK"
});

const messaging = firebase.messaging();

// Notificações em background (navegador fechado)
messaging.onBackgroundMessage(function(payload) {
    console.log('[Service Worker] Mensagem em background:', payload);
    
    const notificationTitle = payload.notification?.title || payload.data?.title || '💰 CODE-MIND';
    const notificationOptions = {
        body: payload.notification?.body || payload.data?.body || '',
        icon: '/static/images/logo.png',
        badge: '/static/images/badge.png',
        data: payload.data || {},
        requireInteraction: true,
        vibrate: [200, 100, 200]
    };
    
    self.registration.showNotification(notificationTitle, notificationOptions);
});

// Clicar na notificação
self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    const url = event.notification.data?.url || '/dashboard/';
    event.waitUntil(clients.openWindow(url));
});