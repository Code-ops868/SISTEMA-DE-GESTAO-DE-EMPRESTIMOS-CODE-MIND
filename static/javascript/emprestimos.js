// REGRA 2: JS SEPARADO DO HTML
document.addEventListener('DOMContentLoaded', function() {
    
    const valorInput = document.getElementById('valor');
    const taxaInput = document.getElementById('taxa_juros');
    const parcelasInput = document.getElementById('quantidade_parcelas');
    const tipoInput = document.getElementById('tipo_juros');
    const simulacaoCard = document.getElementById('simulacao-card');
    const valorParcelaSpan = document.getElementById('valor-parcela');
    const totalPagarSpan = document.getElementById('total-pagar');
    const totalJurosSpan = document.getElementById('total-juros');
    const btnSubmit = document.getElementById('btn-submit');
    
    // Converte string para número (aceita vírgula)
    function parseValor(valor) {
        if (!valor) return 0;
        let cleaned = valor.toString().replace(/\./g, '').replace(',', '.');
        return parseFloat(cleaned) || 0;
    }
    
    // Formata número para moeda
    function formatarMoeda(valor) {
        return valor.toLocaleString('pt-BR', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }
    
    // Simular empréstimo
    function simular() {
        let valor = parseValor(valorInput.value);
        let taxa = parseFloat(taxaInput.value) || 0;
        let parcelas = parseInt(parcelasInput.value) || 0;
        let tipo = tipoInput.value;
        
        if (valor <= 0 || taxa < 0 || parcelas <= 0) {
            simulacaoCard.style.display = 'none';
            if (btnSubmit) btnSubmit.disabled = true;
            return;
        }
        
        if (btnSubmit) btnSubmit.disabled = false;
        
        let parcela, total, juros;
        
        if (tipo === 'simples') {
            juros = valor * (taxa / 100) * parcelas;
            total = valor + juros;
            parcela = total / parcelas;
        } else {
            let taxaMensal = taxa / 100;
            if (taxaMensal === 0) {
                parcela = valor / parcelas;
            } else {
                let fator = Math.pow(1 + taxaMensal, parcelas);
                parcela = valor * (taxaMensal * fator) / (fator - 1);
            }
            total = parcela * parcelas;
            juros = total - valor;
        }
        
        valorParcelaSpan.textContent = `MT ${formatarMoeda(parcela)}`;
        totalPagarSpan.textContent = `MT ${formatarMoeda(total)}`;
        totalJurosSpan.textContent = `MT ${formatarMoeda(juros)}`;
        
        simulacaoCard.style.display = 'block';
    }
    
    // Eventos
    if (valorInput) {
        valorInput.addEventListener('input', simular);
        valorInput.addEventListener('blur', function() {
            let valor = parseValor(this.value);
            if (valor > 0) {
                this.value = formatarMoeda(valor);
            } else {
                this.value = '';
            }
        });
        valorInput.addEventListener('focus', function() {
            let valor = parseValor(this.value);
            if (valor > 0) {
                this.value = valor.toString();
            }
        });
    }
    
    if (taxaInput) taxaInput.addEventListener('input', simular);
    if (parcelasInput) parcelasInput.addEventListener('input', simular);
    if (tipoInput) tipoInput.addEventListener('change', simular);
});

// ============================================
// FUNÇÃO PARA BAIXAR EMPRÉSTIMO
// ============================================

function baixarEmprestimo(emprestimoId) {
    if (confirm('⚠️ Tem certeza que deseja baixar este empréstimo?\n\nEsta ação marcará todas as parcelas como pagas.')) {
        fetch(`/emprestimo/baixar/${emprestimoId}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('✅ Empréstimo baixado com sucesso!');
                location.reload();
            } else {
                alert('❌ Erro: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Erro:', error);
            alert('Erro ao baixar empréstimo.');
        });
    }
}

// Função auxiliar para obter o cookie CSRF
function getCookie(name) {
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