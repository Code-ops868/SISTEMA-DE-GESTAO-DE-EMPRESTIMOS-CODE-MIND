// ============================================
// PLANOS - FUNÇÕES E INTERAÇÕES
// REGRA 2 e 5: TODO JS EM ARQUIVO SEPARADO
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    // Função para escolher plano
    window.escolherPlano = function(plano, valor) {
        if (confirm(`Deseja assinar o plano ${plano.toUpperCase()} no valor de ${valor} MT?`)) {
            window.location.href = `/pagamento-plano/${plano}/`;
        }
    };
});