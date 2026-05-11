// Sistema de Notificações Push
const pushNotifications = {
    
    // Chave pública VAPID (do settings.py)
    vapidPublicKey: 'BEgA49KYbULfkVvwLyjx4xpdGMo0OWBamEsr8SmhDv6zv-dsXe3GtHHBA5nAWHuukKhWKgDzyK0Trts9npgL4X8',
    
    // Verificar se o navegador suporta push
    isSupported: function() {
        return 'serviceWorker' in navigator && 'PushManager' in window;
    },
    
    // Solicitar permissão
    solicitarPermissao: async function() {
        if (!this.isSupported()) {
            console.log('❌ Push não suportado neste navegador');
            alert('Seu navegador não suporta notificações push.');
            return false;
        }
        
        try {
            const permissao = await Notification.requestPermission();
            
            if (permissao === 'granted') {
                console.log('✅ Permissão concedida');
                await this.inscreverUsuario();
                return true;
            } else {
                console.log('❌ Permissão negada');
                return false;
            }
        } catch (error) {
            console.error('Erro ao solicitar permissão:', error);
            return false;
        }
    },
    
    // Inscrever usuário
    inscreverUsuario: async function() {
        try {
            const registration = await navigator.serviceWorker.register('/static/javascript/service_worker.js');
            console.log('✅ Service Worker registrado');
            
            const subscription = await registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: this.urlBase64ToUint8Array(this.vapidPublicKey)
            });
            
            const resultado = await this.enviarInscricao(subscription);
            
            if (resultado.success) {
                console.log('✅ Inscrição salva no servidor');
            }
            
            return subscription;
        } catch (error) {
            console.error('Erro ao inscrever:', error);
        }
    },
    
    // Enviar inscrição para o servidor
    enviarInscricao: async function(subscription) {
        const response = await fetch('/notificacoes/inscrever_push/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCookie('csrftoken')
            },
            body: JSON.stringify({ subscription: subscription })
        });
        
        return response.json();
    },
    
    // Converter VAPID key
    urlBase64ToUint8Array: function(base64String) {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
        const rawData = window.atob(base64);
        const outputArray = new Uint8Array(rawData.length);
        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }
        return outputArray;
    },
    
    // Obter cookie CSRF
    getCookie: function(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
};

// Inicializar
document.addEventListener('DOMContentLoaded', function() {
    // Verificar se o usuário está logado via cookie ou elemento no DOM
    const userAuthenticated = document.body.dataset.userAuthenticated === 'true';
    
    if (!userAuthenticated) {
        console.log('⏳ Usuário não autenticado. Push notifications serão registradas após login.');
        return;
    }
    
    if (Notification.permission === 'granted') {
        pushNotifications.inscreverUsuario();
    }
    
    const btnAtivar = document.getElementById('ativar-notificacoes');
    if (btnAtivar) {
        btnAtivar.addEventListener('click', () => pushNotifications.solicitarPermissao());
    }
});