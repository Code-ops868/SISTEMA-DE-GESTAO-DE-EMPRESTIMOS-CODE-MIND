// Service Worker para notificações push
self.addEventListener('push', function(event) {
    const data = event.data.json();
    
    const options = {
        body: data.body,
        icon: '/static/images/logo.png',
        badge: '/static/images/badge.png',
        vibrate: [200, 100, 200],
        data: {
            url: data.url || '/',
            notificacao_id: data.notificacao_id
        },
        actions: [
            {
                action: 'ver',
                title: '🔍 Ver agora'
            },
            {
                action: 'fechar',
                title: '❌ Fechar'
            }
        ]
    };
    
    event.waitUntil(
        self.registration.showNotification(data.title, options)
    );
});

// Quando clicar na notificação
self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    
    if (event.action === 'fechar') {
        return;
    }
    
    const urlToOpen = event.notification.data.url;
    
    event.waitUntil(
        clients.openWindow(urlToOpen)
    );
});