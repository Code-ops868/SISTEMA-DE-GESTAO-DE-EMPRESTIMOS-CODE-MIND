// ============================================
// CLIENTES - VALIDAÇÕES E INTERAÇÕES
// REGRA 2: JS SEPARADO DO HTML
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    
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
    
    // Campo renda mensal
    const rendaInput = document.getElementById('renda_mensal');
    if (rendaInput) {
        // Ao digitar, apenas números
        rendaInput.addEventListener('input', function(e) {
            let value = e.target.value.replace(/[^\d,]/g, '');
            e.target.value = value;
        });
        
        // Ao perder o foco, formata para exibição
        rendaInput.addEventListener('blur', function() {
            let value = this.value.replace(/\./g, '').replace(',', '.');
            let num = parseFloat(value);
            if (!isNaN(num) && num > 0) {
                this.value = num.toLocaleString('pt-BR', {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2
                });
            } else if (this.value === '') {
                this.value = '';
            } else {
                this.value = '0,00';
            }
        });
        
        // Ao ganhar foco, converte para número
        rendaInput.addEventListener('focus', function() {
            let value = this.value.replace(/\./g, '').replace(',', '.');
            let num = parseFloat(value);
            if (!isNaN(num) && num > 0) {
                this.value = num;
            } else {
                this.value = '';
            }
        });
    }
});