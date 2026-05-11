// ============================================
// DASHBOARD - MENU MOBILE
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    
    // ============================================
    // MENU TOGGLE PARA MOBILE
    // ============================================
    const menuToggle = document.getElementById('menuToggle');
    const sidebar = document.getElementById('sidebar');
    
    if (menuToggle) {
        menuToggle.addEventListener('click', function() {
            sidebar.classList.toggle('open');
        });
    }
    
    // Fechar menu ao clicar fora (mobile)
    document.addEventListener('click', function(event) {
        if (window.innerWidth <= 768) {
            if (sidebar && !sidebar.contains(event.target) && !menuToggle.contains(event.target)) {
                sidebar.classList.remove('open');
            }
        }
    });
});