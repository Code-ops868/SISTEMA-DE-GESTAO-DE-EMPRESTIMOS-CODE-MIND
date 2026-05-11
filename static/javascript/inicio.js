// ============================================
// PÁGINA INICIAL - ANIMAÇÕES E INTERAÇÕES
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    // Animar cards ao entrar na viewport
    const animatedElements = document.querySelectorAll('.feature-card, .stats-card, .cta-card, .hero-content, .benefits-content');
    
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);
    
    animatedElements.forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(30px)';
        observer.observe(el);
    });
});