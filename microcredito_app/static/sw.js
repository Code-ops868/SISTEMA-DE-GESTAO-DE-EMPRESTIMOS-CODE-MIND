/* ============================================
   SERVICE WORKER - GESTÃO DE EMPRÉSTIMOS
   ============================================ */

const CACHE_NAME = 'gestao-v7';
const OFFLINE_URL = '/offline/';

// Arquivos para cache offline
const urlsToCache = [
    '/',
    '/static/css/modelo.css',
    '/static/css/clientes.css',
    '/static/css/emprestimos.css',
    '/static/css/dashboard.css',
    '/static/img/logo.svg',
    '/static/img/icon-192.png',
    '/static/img/icon-512.png',
    '/static/img/icon-maskable-192.png',
    '/static/img/icon-maskable-512.png',
    '/static/manifest.json',
    '/static/bootstrap/css/bootstrap.css',
    '/static/bootstrap_icons/bootstrap-icons.min.css',
    '/static/javascript/jquery-3.7.0.min.js',
    '/static/bootstrap/js/bootstrap.bundle.js'
];

// ============================================
// INSTALAÇÃO
// ============================================

self.addEventListener('install', event => {
    console.log('📦 Service Worker: Instalando...');
    
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('✅ Cache aberto:', CACHE_NAME);
                return cache.addAll(urlsToCache);
            })
            .then(() => {
                console.log('✅ Todos os arquivos foram cacheados');
                self.skipWaiting();
            })
            .catch(err => {
                console.error('❌ Erro ao adicionar arquivos ao cache:', err);
            })
    );
});

// ============================================
// ATIVAÇÃO
// ============================================

self.addEventListener('activate', event => {
    console.log('🚀 Service Worker: Ativando...');
    
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cacheName => {
                    if (cacheName !== CACHE_NAME) {
                        console.log('🗑️ Removendo cache antigo:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        })
        .then(() => {
            console.log('✅ Cache limpo, Service Worker ativado');
            return self.clients.claim();
        })
    );
});

// ============================================
// INTERCEPTAÇÃO DE REQUISIÇÕES (FETCH)
// ============================================

self.addEventListener('fetch', event => {
    const url = new URL(event.request.url);
    
    if (url.origin !== self.location.origin) {
        return;
    }
    
    if (url.pathname.includes('analytics') || url.pathname.includes('firebase')) {
        return;
    }
    
    event.respondWith(
        caches.match(event.request)
            .then(response => {
                if (response) {
                    return response;
                }
                
                return fetch(event.request)
                    .then(response => {
                        if (response && response.status === 200) {
                            const responseToCache = response.clone();
                            caches.open(CACHE_NAME)
                                .then(cache => {
                                    cache.put(event.request, responseToCache);
                                });
                        }
                        return response;
                    })
                    .catch(() => {
                        if (event.request.headers.get('accept').includes('text/html')) {
                            return caches.match(OFFLINE_URL);
                        }
                        return new Response('Offline', { status: 503 });
                    });
            })
    );
});

// ============================================
// MENSAGENS DO SERVICE WORKER
// ============================================

self.addEventListener('message', event => {
    console.log('📨 Mensagem recebida no Service Worker:', event.data);
    
    if (event.data === 'SKIP_WAITING') {
        self.skipWaiting();
    }
});

// ============================================
// NOTIFICAÇÕES PUSH
// ============================================

self.addEventListener('push', event => {
    console.log('🔔 Push recebido:', event);
    
    let data = {
        title: 'Gestão de Empréstimos',
        body: 'Nova notificação',
        icon: '/static/img/icon-192.png',
        badge: '/static/img/icon-192.png',
        vibrate: [200, 100, 200],
        data: { url: '/' }
    };
    
    if (event.data) {
        try {
            data = event.data.json();
        } catch (e) {
            data.body = event.data.text();
        }
    }
    
    event.waitUntil(
        self.registration.showNotification(data.title, {
            body: data.body,
            icon: data.icon || '/static/img/icon-192.png',
            badge: data.badge || '/static/img/icon-192.png',
            vibrate: data.vibrate || [200, 100, 200],
            data: data.data || { url: '/' },
            actions: data.actions || [
                { action: 'open', title: 'Abrir' },
                { action: 'close', title: 'Fechar' }
            ]
        })
    );
});

// ============================================
// CLIQUE NA NOTIFICAÇÃO
// ============================================

self.addEventListener('notificationclick', event => {
    console.log('🔔 Clique na notificação:', event);
    
    event.notification.close();
    
    const url = event.notification.data?.url || '/';
    
    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true })
            .then(windowClients => {
                for (let client of windowClients) {
                    if (client.url === url && 'focus' in client) {
                        return client.focus();
                    }
                }
                if (clients.openWindow) {
                    return clients.openWindow(url);
                }
            })
    );
});
