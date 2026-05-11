// ============================================
// MODAL FUNCIONAL - JAVASCRIPT
// REGRA 2 e 5: TODO JS EM ARQUIVO SEPARADO
// ============================================

// Formatar moeda
function formatarMoeda(valor) {
    if (isNaN(valor)) valor = 0;
    return valor.toLocaleString('pt-BR', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

// Abrir modal de pagamento (pendente)
window.abrirModalPagamento = function(id, valor, cliente, numero) {
    console.log('Abrindo modal pagamento:', { id, valor, cliente, numero });
    
    const modal = document.getElementById('modalPagamentoFuncional');
    if (!modal) {
        console.error('Modal não encontrado!');
        return;
    }
    
    document.getElementById('funcional_parcela_id').value = id;
    document.getElementById('funcional_cliente_nome').value = cliente;
    document.getElementById('funcional_parcela_numero').value = numero;
    document.getElementById('funcional_valor').value = formatarMoeda(valor);
    
    // Limpar seleções
    document.querySelectorAll('input[name="forma_pagamento"]').forEach(radio => radio.checked = false);
    document.getElementById('funcional_comprovante').value = '';
    document.getElementById('funcional_observacoes').value = '';
    
    document.querySelectorAll('.funcional-payment-option').forEach(opt => opt.classList.remove('selected'));
    
    modal.style.display = 'flex';
};

// Abrir modal de pagamento (atrasado)
window.abrirModalPagamentoAtrasado = function(id, valorTotal, cliente, numero) {
    console.log('Abrindo modal atrasado:', { id, valorTotal, cliente, numero });
    
    const modal = document.getElementById('modalPagamentoFuncional');
    if (!modal) {
        console.error('Modal não encontrado!');
        return;
    }
    
    document.getElementById('funcional_parcela_id').value = id;
    document.getElementById('funcional_cliente_nome').value = cliente;
    document.getElementById('funcional_parcela_numero').value = numero + ' (em atraso)';
    document.getElementById('funcional_valor').value = formatarMoeda(valorTotal);
    
    document.querySelectorAll('input[name="forma_pagamento"]').forEach(radio => radio.checked = false);
    document.getElementById('funcional_comprovante').value = '';
    document.getElementById('funcional_observacoes').value = '';
    
    document.querySelectorAll('.funcional-payment-option').forEach(opt => opt.classList.remove('selected'));
    
    modal.style.display = 'flex';
};

// Fechar modal
window.fecharModalPagamento = function() {
    const modal = document.getElementById('modalPagamentoFuncional');
    if (modal) {
        modal.style.display = 'none';
    }
};

// Simular juros
window.simularJuros = function(id) {
    console.log('Simular juros:', id);
    fetch(`/simular-juros/${id}/`)
        .then(response => response.json())
        .then(data => {
            alert('Simulação:\n' +
                'Valor Original: MT ' + formatarMoeda(data.valor_original) + '\n' +
                'Dias Atraso: ' + data.dias_atraso + '\n' +
                'Multa: MT ' + formatarMoeda(data.multa) + '\n' +
                'Juros: MT ' + formatarMoeda(data.juros_mora) + '\n' +
                'Total: MT ' + formatarMoeda(data.valor_total));
        });
};

// Ver comprovante
window.verComprovante = function(url) {
    if (url) window.open(url, '_blank');
};

// Inicialização
document.addEventListener('DOMContentLoaded', function() {
    
    // Botão fechar
    const btnFechar = document.getElementById('btnFecharModal');
    const btnCancelar = document.getElementById('btnCancelarModal');
    const overlay = document.querySelector('#modalPagamentoFuncional .modal-funcional-overlay');
    
    if (btnFechar) btnFechar.addEventListener('click', fecharModalPagamento);
    if (btnCancelar) btnCancelar.addEventListener('click', fecharModalPagamento);
    if (overlay) overlay.addEventListener('click', fecharModalPagamento);
    
    // Fechar com ESC
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') fecharModalPagamento();
    });
    
    // Selecionar opção de pagamento
    document.querySelectorAll('.funcional-payment-option').forEach(opt => {
        opt.addEventListener('click', function() {
            const radio = this.querySelector('input[type="radio"]');
            if (radio) {
                radio.checked = true;
                document.querySelectorAll('.funcional-payment-option').forEach(o => o.classList.remove('selected'));
                this.classList.add('selected');
            }
        });
    });
    
    // Formatação do valor
    const valorInput = document.getElementById('funcional_valor');
    if (valorInput) {
        valorInput.addEventListener('blur', function() {
            let valor = parseFloat(this.value.replace(/\./g, '').replace(',', '.'));
            if (!isNaN(valor) && valor > 0) this.value = formatarMoeda(valor);
        });
        valorInput.addEventListener('focus', function() {
            let valor = parseFloat(this.value.replace(/\./g, '').replace(',', '.'));
            if (!isNaN(valor) && valor > 0) this.value = valor;
        });
    }
    
    console.log('✅ Modal funcional inicializado');
});