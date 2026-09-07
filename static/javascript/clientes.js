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
        rendaInput.addEventListener('input', function(e) {
            let value = e.target.value.replace(/[^\d,]/g, '');
            e.target.value = value;
        });
        
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

    // ============================================
    // VALIDAÇÃO DE DOCUMENTOS
    // ============================================
    
    /**
     * Valida BI, DIRE ou Passaporte moçambicano pelo formato estrutural:
     * - BI: 12 dígitos + 1 letra (ex: 110101234567A)
     * - DIRE: 8 dígitos + 1 letra (ex: 00012345A)
     * - Passaporte: 2 letras + 7 dígitos (ex: AB1234567)
     */
    function validarDocumento(value) {
        if (!value) {
            return { valid: true, message: '', tipo: null };
        }
        
        const cleaned = value.replace(/\s/g, '').toUpperCase();
        if (cleaned.length === 0) {
            return { valid: true, message: '', tipo: null };
        }
        
        // BI: 12 dígitos + 1 letra
        if (/^[0-9]{12}[A-Z]$/.test(cleaned)) {
            return { valid: true, message: '✓ BI válido', tipo: 'BI' };
        }
        
        // DIRE: 8 dígitos + 1 letra
        if (/^[0-9]{8}[A-Z]$/.test(cleaned)) {
            return { valid: true, message: '✓ DIRE válido', tipo: 'DIRE' };
        }
        
        // Passaporte: 2 letras + 7 dígitos
        if (/^[A-Z]{2}[0-9]{7}$/.test(cleaned)) {
            return { valid: true, message: '✓ Passaporte válido', tipo: 'Passaporte' };
        }
        
        return { 
            valid: false, 
            message: '✕ Use BI (12 dígitos + letra), DIRE (8 dígitos + letra) ou Passaporte (2 letras + 7 dígitos)',
            tipo: null 
        };
    }

    // ============================================
    // VALIDAÇÃO NUIT/NUIB
    // ============================================
    
    function validarNUIT(value) {
        if (!value) return { valid: true, message: '' };
        const cleaned = value.replace(/\D/g, '');
        if (cleaned.length === 0) return { valid: true, message: '' };
        if (cleaned.length !== 9) {
            return { valid: false, message: 'NUIT deve ter exatamente 9 dígitos numéricos.' };
        }
        return { valid: true, message: '' };
    }
    
    function validarNUIB(value) {
        if (!value) return { valid: true, message: '' };
        const cleaned = value.replace(/\D/g, '');
        if (cleaned.length === 0) return { valid: true, message: '' };
        if (cleaned.length !== 9) {
            return { valid: false, message: 'NUIB deve ter exatamente 9 dígitos numéricos.' };
        }
        return { valid: true, message: '' };
    }

    // ============================================
    // LIMPAR ENTRADA (APENAS DÍGITOS)
    // ============================================
    
    function limparEntrada(input) {
        if (!input) return;
        input.addEventListener('input', function() {
            this.value = this.value.replace(/\D/g, '').slice(0, 9);
        });
    }

    // Elementos do formulário
    const nuitInput = document.getElementById('nuit');
    const nuibInput = document.getElementById('nuib');
    const biInput = document.getElementById('bi_passaporte');
    const tipoDocumentoButtons = document.querySelectorAll('.tipo-documento-select .btn-doc');

    if (nuitInput) limparEntrada(nuitInput);
    if (nuibInput) limparEntrada(nuibInput);

    // ============================================
    // VALIDAÇÃO NUIT EM TEMPO REAL
    // ============================================
    
    if (nuitInput) {
        nuitInput.addEventListener('input', function() {
            const result = validarNUIT(this.value);
            const errorEl = document.getElementById('nuit-error');
            const validEl = document.getElementById('nuit-valid');
            this.classList.remove('documento-validado', 'documento-invalido');
            if (errorEl) errorEl.classList.remove('show');
            if (validEl) validEl.classList.remove('show');
            
            if (this.value && !result.valid) {
                this.classList.add('documento-invalido');
                if (errorEl) {
                    errorEl.textContent = '✕ ' + result.message;
                    errorEl.classList.add('show');
                }
            } else if (this.value && result.valid) {
                this.classList.add('documento-validado');
                if (validEl) {
                    validEl.textContent = '✓ NUIT válido';
                    validEl.classList.add('show');
                }
            }
        });
    }

    // ============================================
    // VALIDAÇÃO NUIB EM TEMPO REAL
    // ============================================
    
    if (nuibInput) {
        nuibInput.addEventListener('input', function() {
            const result = validarNUIB(this.value);
            const errorEl = document.getElementById('nuib-error');
            const validEl = document.getElementById('nuib-valid');
            this.classList.remove('documento-validado', 'documento-invalido');
            if (errorEl) errorEl.classList.remove('show');
            if (validEl) validEl.classList.remove('show');
            
            if (this.value && !result.valid) {
                this.classList.add('documento-invalido');
                if (errorEl) {
                    errorEl.textContent = '✕ ' + result.message;
                    errorEl.classList.add('show');
                }
            } else if (this.value && result.valid) {
                this.classList.add('documento-validado');
                if (validEl) {
                    validEl.textContent = '✓ NUIB válido';
                    validEl.classList.add('show');
                }
            }
        });
    }

    // ============================================
    // VALIDAÇÃO BI/PASSAPORTE/DIRE EM TEMPO REAL
    // ============================================
    
    if (biInput) {
        biInput.addEventListener('input', function() {
            const result = validarDocumento(this.value);
            const errorEl = document.getElementById('bi-error');
            const validEl = document.getElementById('bi-valid');
            
            this.classList.remove('documento-validado', 'documento-invalido');
            if (errorEl) errorEl.classList.remove('show');
            if (validEl) validEl.classList.remove('show');
            
            if (this.value && !result.valid) {
                this.classList.add('documento-invalido');
                if (errorEl) {
                    errorEl.textContent = '✕ ' + result.message;
                    errorEl.classList.add('show');
                }
            } else if (this.value && result.valid) {
                this.classList.add('documento-validado');
                if (validEl) {
                    validEl.textContent = '✓ Documento válido';
                    validEl.classList.add('show');
                }
                if (result.tipo) {
                    this.setAttribute('data-tipo', result.tipo);
                }
            }
        });
    }

    // ============================================
    // BOTÕES DE TIPO DE DOCUMENTO
    // ============================================
    
    if (tipoDocumentoButtons) {
        tipoDocumentoButtons.forEach(btn => {
            btn.addEventListener('click', function() {
                tipoDocumentoButtons.forEach(b => b.classList.remove('active'));
                this.classList.add('active');
                const tipo = this.dataset.tipo;
                
                if (biInput) {
                    if (tipo === 'BI') {
                        biInput.placeholder = 'Ex: 110101234567A (12 dígitos + letra)';
                    } else if (tipo === 'DIRE') {
                        biInput.placeholder = 'Ex: 00012345A (8 dígitos + letra)';
                    } else if (tipo === 'Passaporte') {
                        biInput.placeholder = 'Ex: AB1234567 (2 letras + 7 dígitos)';
                    }
                    
                    biInput.focus();
                    biInput.classList.remove('documento-validado', 'documento-invalido');
                    const errorEl = document.getElementById('bi-error');
                    const validEl = document.getElementById('bi-valid');
                    if (errorEl) errorEl.classList.remove('show');
                    if (validEl) validEl.classList.remove('show');
                }
            });
        });
    }

    // ============================================
    // VALIDAÇÃO DO FORMULÁRIO NO SUBMIT
    // ============================================
    
    const form = document.getElementById('cliente-form');
    if (form) {
        form.addEventListener('submit', function(e) {
            let isValid = true;
            let primeiroErro = null;
            
            // Validar Nome
            const nomeInput = document.getElementById('nome');
            const nomeError = document.getElementById('nome-error');
            if (!nomeInput || !nomeInput.value.trim()) {
                if (nomeError) nomeError.classList.add('show');
                if (nomeInput) nomeInput.classList.add('documento-invalido');
                isValid = false;
                if (!primeiroErro && nomeInput) primeiroErro = nomeInput;
            } else {
                if (nomeError) nomeError.classList.remove('show');
                if (nomeInput) nomeInput.classList.remove('documento-invalido');
            }
            
            // Validar Telefone
            const telefoneInput = document.getElementById('telefone');
            const telefoneError = document.getElementById('telefone-error');
            if (!telefoneInput || !telefoneInput.value.trim()) {
                if (telefoneError) telefoneError.classList.add('show');
                if (telefoneInput) telefoneInput.classList.add('documento-invalido');
                isValid = false;
                if (!primeiroErro && telefoneInput) primeiroErro = telefoneInput;
            } else {
                if (telefoneError) telefoneError.classList.remove('show');
                if (telefoneInput) telefoneInput.classList.remove('documento-invalido');
            }
            
            // Validar NUIT se preenchido
            if (nuitInput && nuitInput.value) {
                const nuitResult = validarNUIT(nuitInput.value);
                const nuitError = document.getElementById('nuit-error');
                if (!nuitResult.valid) {
                    if (nuitError) {
                        nuitError.textContent = '✕ ' + nuitResult.message;
                        nuitError.classList.add('show');
                    }
                    nuitInput.classList.add('documento-invalido');
                    isValid = false;
                    if (!primeiroErro) primeiroErro = nuitInput;
                }
            }
            
            // Validar NUIB se preenchido
            if (nuibInput && nuibInput.value) {
                const nuibResult = validarNUIB(nuibInput.value);
                const nuibError = document.getElementById('nuib-error');
                if (!nuibResult.valid) {
                    if (nuibError) {
                        nuibError.textContent = '✕ ' + nuibResult.message;
                        nuibError.classList.add('show');
                    }
                    nuibInput.classList.add('documento-invalido');
                    isValid = false;
                    if (!primeiroErro) primeiroErro = nuibInput;
                }
            }
            
            // Validar BI/Passaporte/DIRE se preenchido
            if (biInput && biInput.value) {
                const biResult = validarDocumento(biInput.value);
                const biError = document.getElementById('bi-error');
                if (!biResult.valid) {
                    if (biError) {
                        biError.textContent = '✕ ' + biResult.message;
                        biError.classList.add('show');
                    }
                    biInput.classList.add('documento-invalido');
                    isValid = false;
                    if (!primeiroErro) primeiroErro = biInput;
                }
            }
            
            if (!isValid) {
                e.preventDefault();
                if (primeiroErro) {
                    primeiroErro.focus();
                    primeiroErro.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }
        });
    }
    
    // ============================================
    // REMOVER MENSAGENS DE ERRO AO DIGITAR
    // ============================================
    
    document.querySelectorAll('input, textarea').forEach(el => {
        el.addEventListener('input', function() {
            this.classList.remove('documento-invalido');
            const errorId = this.id + '-error';
            const errorEl = document.getElementById(errorId);
            if (errorEl) {
                errorEl.classList.remove('show');
            }
        });
    });
});