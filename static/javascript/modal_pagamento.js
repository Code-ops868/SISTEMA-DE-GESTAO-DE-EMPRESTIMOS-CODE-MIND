// ============================================
// MODAL_PAGAMENTO.JS - FUNÇÕES GLOBAIS
// ============================================

function formatarMoeda(valor) {
    if (isNaN(valor)) valor = 0;
    return valor.toLocaleString('pt-BR', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

// ============================================
// ABRIR MODAL (PAGAMENTO NORMAL)
// ============================================
window.abrirModalPagamento = function(id, valor, cliente, parcela) {
    console.log('🔵 Abrindo modal pagamento:', { id, valor, cliente, parcela });
    
    document.getElementById('modal_parcela_id').value = id;
    document.getElementById('modal_cliente_nome').value = cliente || '';
    document.getElementById('modal_parcela_numero').value = parcela || '';
    document.getElementById('modal_valor').value = formatarMoeda(valor);
    document.getElementById('modal_forma_pagamento').value = '';
    document.getElementById('modal_comprovante').value = '';
    document.getElementById('modal_observacoes').value = '';
    
    var modal = new bootstrap.Modal(document.getElementById('modalPagamento'));
    modal.show();
};

// ============================================
// ABRIR MODAL (PAGAMENTO ATRASADO)
// ============================================
window.abrirModalPagamentoAtrasado = function(id, valorTotal, cliente, parcela) {
    console.log('🔴 Abrindo modal atrasado:', { id, valorTotal, cliente, parcela });
    
    document.getElementById('modal_parcela_id').value = id;
    document.getElementById('modal_cliente_nome').value = cliente || '';
    document.getElementById('modal_parcela_numero').value = parcela + ' (em atraso)';
    document.getElementById('modal_valor').value = formatarMoeda(valorTotal);
    document.getElementById('modal_forma_pagamento').value = '';
    document.getElementById('modal_comprovante').value = '';
    document.getElementById('modal_observacoes').value = '';
    
    var modal = new bootstrap.Modal(document.getElementById('modalPagamento'));
    modal.show();
};

// ============================================
// SIMULAR JUROS
// ============================================
window.simularJuros = function(id) {
    console.log('📊 Simular juros para parcela:', id);
    
    fetch(`/simular-juros/${id}/`)
        .then(response => response.json())
        .then(data => {
            alert('📊 SIMULAÇÃO DE JUROS\n\n' +
                'Valor Original: MT ' + formatarMoeda(data.valor_original) + '\n' +
                'Dias em Atraso: ' + data.dias_atraso + '\n' +
                'Multa (2%): MT ' + formatarMoeda(data.multa) + '\n' +
                'Juros (0.033%/dia): MT ' + formatarMoeda(data.juros_mora) + '\n' +
                '━━━━━━━━━━━━━━━━━━━━━━\n' +
                'Total a Pagar: MT ' + formatarMoeda(data.valor_total));
        })
        .catch(error => {
            console.error('Erro:', error);
            alert('❌ Erro ao simular juros.');
        });
};

// ============================================
// VER COMPROVANTE
// ============================================
window.verComprovante = function(url) {
    if (url) {
        window.open(url, '_blank');
    }
};

// ============================================
// REGISTRAR PAGAMENTO VIA AJAX
// ============================================
window.registrarPagamento = function() {
    console.log('💰 Confirmando pagamento...');
    
    var parcelaId = document.getElementById('modal_parcela_id').value;
    var valorTexto = document.getElementById('modal_valor').value;
    var forma = document.getElementById('modal_forma_pagamento').value;
    var comprovante = document.getElementById('modal_comprovante').files[0];
    var observacoes = document.getElementById('modal_observacoes').value;
    
    if (!parcelaId || !forma) {
        alert('❌ Preencha a forma de pagamento!');
        return;
    }
    
    var valorNum = parseFloat(valorTexto.replace(/\./g, '').replace(',', '.'));
    
    var formData = new FormData();
    formData.append('parcela_id', parcelaId);
    formData.append('valor', valorNum);
    formData.append('forma_pagamento', forma);
    if (comprovante) formData.append('comprovante', comprovante);
    if (observacoes) formData.append('observacoes', observacoes);
    
    fetch('/registrar-pagamento/', {
        method: 'POST',
        body: formData,
        headers: { 'X-CSRFToken': getCookie('csrftoken') }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('✅ ' + (data.message || 'Pagamento registrado!'));
            location.reload();
        } else {
            alert('❌ ' + (data.error || 'Erro desconhecido'));
        }
    })
    .catch(error => {
        console.error('Erro:', error);
        alert('❌ Erro ao registrar pagamento.');
    });
};

// ============================================
// FUNÇÃO AUXILIAR CSRF
// ============================================
function getCookie(name) {
    var v = document.cookie.match('(^|;) ?' + name + '=([^;]*)(;|$)');
    return v ? v[2] : null;
}

console.log('✅ modal_pagamento.js carregado com sucesso!');