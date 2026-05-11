// ============================================
// CLIENTES - VALIDAÇÕES E INTERAÇÕES
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    
    // Inicializar DataTable
    const table = document.getElementById('clientes-table');
    if (table) {
        $(table).DataTable({
            language: {
                url: '//cdn.datatables.net/plug-ins/1.13.6/i18n/pt-BR.json'
            },
            pageLength: 10,
            responsive: true,
            order: [[0, 'desc']]
        });
    }
    
    // Máscara para telefone
    const telefoneInput = document.getElementById('telefone');
    if (telefoneInput) {
        telefoneInput.addEventListener('input', function(e) {
            let value = e.target.value.replace(/\D/g, '');
            if (value.length > 0) {
                if (value.length <= 2) {
                    value = value;
                } else if (value.length <= 6) {
                    value = value.replace(/(\d{2})(\d{1,4})/, '$1 $2');
                } else {
                    value = value.replace(/(\d{2})(\d{4})(\d{0,4})/, '$1 $2-$3');
                }
            }
            e.target.value = value;
        });
    }
    
    // Formatar renda
    const rendaInput = document.getElementById('renda_mensal');
    if (rendaInput) {
        rendaInput.addEventListener('blur', function() {
            let value = parseFloat(this.value);
            if (!isNaN(value)) {
                this.value = value.toLocaleString('pt-BR', {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2
                });
            }
        });
        
        rendaInput.addEventListener('focus', function() {
            let value = this.value.replace(/\./g, '').replace(',', '.');
            this.value = parseFloat(value) || '';
        });
    }
});

// Função global para confirmar exclusão
function confirmarExclusao(id, nome) {
    if (confirm(`Tem certeza que deseja excluir o cliente "${nome}"?`)) {
        window.location.href = `/clientes/excluir/${id}/`;
    }
}