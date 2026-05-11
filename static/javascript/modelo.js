// ============================================
// MODELO - FUNÇÕES GLOBAIS
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    // Fechar alertas automaticamente após 5 segundos
    setTimeout(function() {
        document.querySelectorAll('.alert').forEach(function(alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);
});