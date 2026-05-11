// ============================================
// M-PESA - FUNÇÕES E INTERAÇÕES
// REGRA 2 e 5: TODO JS EM ARQUIVO SEPARADO
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
                    value = value.replace(/(\d{2})(\d{4})(\d{0,4})/, '$1 $2 $3');
                }
            }
            e.target.value = value;
        });
    }
    
    // Validação do formulário
    const form = document.getElementById('formPagamentoMpesa');
    if (form) {
        form.addEventListener('submit', function(e) {
            const telefone = document.getElementById('telefone').value;
            const telefoneLimpo = telefone.replace(/\D/g, '');
            
            if (telefoneLimpo.length < 9) {
                e.preventDefault();
                alert('Por favor, insira um número de telefone válido (ex: 84 1234567)');
                return false;
            }
            
            return true;
        });
    }
});