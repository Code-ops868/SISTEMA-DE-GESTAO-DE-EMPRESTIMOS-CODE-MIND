// ============================================
// LOGIN - VALIDAÇÕES E INTERAÇÕES
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('form');
    const emailInput = document.getElementById('email');
    const senhaInput = document.getElementById('senha');
    
    if (emailInput) {
        emailInput.addEventListener('input', function() {
            const emailRegex = /^[^\s@]+@([^\s@]+\.)+[^\s@]+$/;
            if (emailRegex.test(this.value)) {
                this.classList.add('valid');
                this.classList.remove('invalid');
            } else if (this.value.length > 0) {
                this.classList.add('invalid');
                this.classList.remove('valid');
            } else {
                this.classList.remove('valid', 'invalid');
            }
        });
    }
    
    if (senhaInput) {
        senhaInput.addEventListener('input', function() {
            if (this.value.length >= 6) {
                this.classList.add('valid');
                this.classList.remove('invalid');
            } else if (this.value.length > 0) {
                this.classList.add('invalid');
                this.classList.remove('valid');
            } else {
                this.classList.remove('valid', 'invalid');
            }
        });
    }
    
    if (form) {
        form.addEventListener('submit', function(e) {
            const email = emailInput?.value.trim();
            const senha = senhaInput?.value;
            
            if (!email || !senha) {
                e.preventDefault();
                alert('Preencha todos os campos');
            }
        });
    }
});