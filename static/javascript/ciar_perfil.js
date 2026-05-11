// ============================================
// PERFIS - FUNÇÕES E INTERAÇÕES
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    const provinciaSelect = document.getElementById('provincia');
    const cidadeSelect = document.getElementById('cidade');
    const distritoSelect = document.getElementById('distrito');
    
    // Guardar opções originais
    let cidadesOriginais = [];
    let distritosOriginais = [];
    
    if (cidadeSelect) {
        for (let i = 0; i < cidadeSelect.options.length; i++) {
            cidadesOriginais.push({
                value: cidadeSelect.options[i].value,
                text: cidadeSelect.options[i].text,
                provincia: cidadeSelect.options[i].getAttribute('data-provincia')
            });
        }
    }
    
    if (distritoSelect) {
        for (let i = 0; i < distritoSelect.options.length; i++) {
            distritosOriginais.push({
                value: distritoSelect.options[i].value,
                text: distritoSelect.options[i].text,
                provincia: distritoSelect.options[i].getAttribute('data-provincia')
            });
        }
    }
    
    function filtrarPorProvincia() {
        const provinciaId = provinciaSelect.value;
        
        // Filtrar cidades
        if (cidadeSelect) {
            cidadeSelect.innerHTML = '<option value="">Selecione uma cidade</option>';
            cidadesOriginais.forEach(cidade => {
                if (!provinciaId || cidade.provincia === provinciaId) {
                    const option = document.createElement('option');
                    option.value = cidade.value;
                    option.textContent = cidade.text;
                    option.setAttribute('data-provincia', cidade.provincia);
                    cidadeSelect.appendChild(option);
                }
            });
        }
        
        // Filtrar distritos
        if (distritoSelect) {
            distritoSelect.innerHTML = '<option value="">Selecione um distrito</option>';
            distritosOriginais.forEach(distrito => {
                if (!provinciaId || distrito.provincia === provinciaId) {
                    const option = document.createElement('option');
                    option.value = distrito.value;
                    option.textContent = distrito.text;
                    option.setAttribute('data-provincia', distrito.provincia);
                    distritoSelect.appendChild(option);
                }
            });
        }
    }
    
    if (provinciaSelect) {
        provinciaSelect.addEventListener('change', filtrarPorProvincia);
        filtrarPorProvincia();
    }
});

function confirmarExclusao(id) {
    if (confirm('Tem certeza que deseja excluir este perfil?')) {
        window.location.href = `/perfis/excluir/${id}/`;
    }
}