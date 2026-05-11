// ============================================
// ALERTAS PERSONALIZADOS - VERSÃO ESTÁVEL
// REGRA 2 e 5
// ============================================

class AlertaManager {
    constructor() {
        this.container = document.getElementById('alerta-container');
        if (!this.container) {
            this.criarContainer();
        }
        this.timeouts = new Map();
        this.duracaoPadrao = 8000; // 8 segundos (era 5, agora aumentado)
    }
    
    criarContainer() {
        const container = document.createElement('div');
        container.id = 'alerta-container';
        container.className = 'alerta-container';
        document.body.appendChild(container);
        this.container = container;
    }
    
    mostrar(mensagem, tipo = 'info', titulo = null, duracao = null) {
        const duracaoFinal = duracao !== null ? duracao : this.duracaoPadrao;
        
        const titulos = {
            success: 'Sucesso!',
            error: 'Erro!',
            warning: 'Atenção!',
            info: 'Informação'
        };
        
        const tituloFinal = titulo || titulos[tipo] || 'Info';
        
        const icones = {
            success: 'bi-check-circle-fill',
            error: 'bi-exclamation-triangle-fill',
            warning: 'bi-exclamation-circle-fill',
            info: 'bi-info-circle-fill'
        };
        
        const alerta = document.createElement('div');
        alerta.className = `alerta alerta-${tipo}`;
        
        alerta.innerHTML = `
            <div class="alerta-icon">
                <i class="bi ${icones[tipo] || icones.info}"></i>
            </div>
            <div class="alerta-content">
                <div class="alerta-title">${this.escapeHtml(tituloFinal)}</div>
                <div class="alerta-message">${this.escapeHtml(mensagem)}</div>
            </div>
            <button class="alerta-close" aria-label="Fechar">
                <i class="bi bi-x-lg"></i>
            </button>
        `;
        
        this.container.appendChild(alerta);
        
        const closeBtn = alerta.querySelector('.alerta-close');
        closeBtn.addEventListener('click', () => this.fechar(alerta));
        
        const timeoutId = setTimeout(() => this.fechar(alerta), duracaoFinal);
        this.timeouts.set(alerta, timeoutId);
        
        alerta.addEventListener('click', (e) => {
            if (e.target === closeBtn || closeBtn.contains(e.target)) return;
            this.fechar(alerta);
        });
        
        return alerta;
    }
    
    fechar(alerta) {
        const timeoutId = this.timeouts.get(alerta);
        if (timeoutId) {
            clearTimeout(timeoutId);
            this.timeouts.delete(alerta);
        }
        
        alerta.classList.add('alerta-exit');
        
        setTimeout(() => {
            if (alerta.parentNode) {
                alerta.remove();
            }
        }, 300);
    }
    
    sucesso(mensagem, titulo = null, duracao = null) {
        return this.mostrar(mensagem, 'success', titulo, duracao);
    }
    
    erro(mensagem, titulo = null, duracao = null) {
        return this.mostrar(mensagem, 'error', titulo, duracao);
    }
    
    aviso(mensagem, titulo = null, duracao = null) {
        return this.mostrar(mensagem, 'warning', titulo, duracao);
    }
    
    info(mensagem, titulo = null, duracao = null) {
        return this.mostrar(mensagem, 'info', titulo, duracao);
    }
    
    escapeHtml(texto) {
        const div = document.createElement('div');
        div.textContent = texto;
        return div.innerHTML;
    }
}

const alertas = new AlertaManager();