// ============================================
// RELATÓRIOS - GRÁFICOS E EXPORTAÇÕES
// REGRA 2 e 5: TODO JS EM ARQUIVO SEPARADO
// ============================================

// Variáveis globais para os gráficos
let chartStatus, chartMensal;

document.addEventListener('DOMContentLoaded', function() {
    
    // Verificar se Chart.js está disponível
    if (typeof Chart === 'undefined') {
        console.error('Chart.js não carregado!');
        return;
    }
    
    // Verificar se os dados foram passados
    if (typeof window.relatoriosData === 'undefined') {
        console.error('Dados dos relatórios não encontrados!');
        return;
    }
    
    const { statusLabels, statusData, monthlyLabels, monthlyData } = window.relatoriosData;
    
    // ============================================
    // GRÁFICO DE STATUS (Doughnut)
    // ============================================
    const ctxStatus = document.getElementById('chartStatus');
    if (ctxStatus && statusLabels && statusData) {
        chartStatus = new Chart(ctxStatus, {
            type: 'doughnut',
            data: {
                labels: statusLabels,
                datasets: [{
                    data: statusData,
                    backgroundColor: ['#88ff66', '#ffa657', '#f85149'],
                    borderWidth: 0,
                    hoverOffset: 10
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: '#e6edf3', font: { size: 12 } }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.raw || 0;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percent = ((value / total) * 100).toFixed(1);
                                return `${label}: ${value} (${percent}%)`;
                            }
                        }
                    }
                }
            }
        });
    }
    
    // ============================================
    // GRÁFICO DE EVOLUÇÃO MENSAL (Line) - SEM GRID
    // ============================================
    const ctxMensal = document.getElementById('chartMensal');
    if (ctxMensal && monthlyLabels && monthlyData) {
        chartMensal = new Chart(ctxMensal, {
            type: 'line',
            data: {
                labels: monthlyLabels,
                datasets: [{
                    label: 'Valor Emprestado (MT)',
                    data: monthlyData,
                    borderColor: '#88ff66',
                    backgroundColor: 'rgba(136, 255, 102, 0.1)',
                    borderWidth: 2,
                    tension: 0.4,
                    fill: true,
                    pointBackgroundColor: '#88ff66',
                    pointBorderColor: '#0a0c10',
                    pointRadius: 4,
                    pointHoverRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: { labels: { color: '#e6edf3' } },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `MT ${context.raw.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        ticks: {
                            color: '#e6edf3',
                            callback: function(value) {
                                return `MT ${value.toLocaleString('pt-BR')}`;
                            }
                        },
                        grid: { display: false }
                    },
                    x: {
                        ticks: { color: '#e6edf3' },
                        grid: { display: false }
                    }
                }
            }
        });
    }
});

// ============================================
// FUNÇÃO PARA CONVERTER CANVAS EM IMAGEM
// ============================================
function captureChartAsImage(canvasId) {
    return new Promise((resolve) => {
        const canvas = document.getElementById(canvasId);
        
        if (!canvas) {
            const div = document.createElement('div');
            div.style.padding = '40px';
            div.style.textAlign = 'center';
            div.style.color = '#8b949e';
            div.style.backgroundColor = '#0d1117';
            div.style.borderRadius = '8px';
            div.innerHTML = 'Gráfico não disponível';
            resolve(div);
            return;
        }
        
        // Aguardar um pouco para garantir que o canvas foi renderizado
        setTimeout(() => {
            try {
                const img = document.createElement('img');
                img.style.width = '100%';
                img.style.maxHeight = '250px';
                img.style.objectFit = 'contain';
                
                // Converter canvas para imagem
                const dataURL = canvas.toDataURL('image/png');
                img.src = dataURL;
                
                img.onload = () => resolve(img);
                img.onerror = () => {
                    const div = document.createElement('div');
                    div.style.padding = '40px';
                    div.style.textAlign = 'center';
                    div.style.color = '#f85149';
                    div.innerHTML = 'Erro ao carregar gráfico';
                    resolve(div);
                };
            } catch (error) {
                console.error('Erro ao capturar gráfico:', error);
                const div = document.createElement('div');
                div.style.padding = '40px';
                div.style.textAlign = 'center';
                div.style.color = '#f85149';
                div.innerHTML = 'Erro ao gerar gráfico';
                resolve(div);
            }
        }, 500);
    });
}

// ============================================
// EXPORTAR PARA PDF
// ============================================
window.exportarPDF = async function() {
    // Mostrar loading
    const btn = event.target.closest('button');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="bi bi-hourglass-split"></i> Gerando PDF...';
    btn.disabled = true;
    
    try {
        // Aguardar um pouco para garantir que os gráficos estão renderizados
        await new Promise(resolve => setTimeout(resolve, 300));
        
        // 1. Converter gráficos para imagens
        const statusImage = await captureChartAsImage('chartStatus');
        const mensalImage = await captureChartAsImage('chartMensal');
        
        // 2. Criar elemento para exportação
        const element = document.createElement('div');
        element.style.padding = '20px';
        element.style.backgroundColor = '#0a0c10';
        element.style.color = '#e6edf3';
        element.style.fontFamily = 'Arial, sans-serif';
        
        // 3. Adicionar cabeçalho
        element.innerHTML = `
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: #88ff66; font-size: 28px; margin: 0;">CODE-MIND</h1>
                <h2 style="color: #e6edf3; font-size: 22px; margin: 10px 0;">Relatório Geral</h2>
                <p style="color: #8b949e;">Data: ${new Date().toLocaleString('pt-BR')}</p>
                <hr style="border-color: #88ff66; margin: 15px 0;">
            </div>
        `;
        
        // 4. Adicionar cards
        const cards = document.querySelector('.stats-grid');
        if (cards) {
            const cardsClone = cards.cloneNode(true);
            cardsClone.style.marginBottom = '30px';
            element.appendChild(cardsClone);
        }
        
        // 5. Adicionar gráficos como imagens
        const chartsSection = document.createElement('div');
        chartsSection.style.display = 'grid';
        chartsSection.style.gridTemplateColumns = '1fr 1fr';
        chartsSection.style.gap = '20px';
        chartsSection.style.marginBottom = '30px';
        
        // Gráfico Status
        const statusDiv = document.createElement('div');
        statusDiv.style.border = '1px solid #88ff66';
        statusDiv.style.borderRadius = '8px';
        statusDiv.style.padding = '15px';
        statusDiv.style.backgroundColor = '#0d1117';
        statusDiv.innerHTML = `<h3 style="color: #88ff66; text-align: center; margin: 0 0 15px 0;">Empréstimos por Status</h3>`;
        statusDiv.appendChild(statusImage);
        chartsSection.appendChild(statusDiv);
        
        // Gráfico Mensal
        const mensalDiv = document.createElement('div');
        mensalDiv.style.border = '1px solid #88ff66';
        mensalDiv.style.borderRadius = '8px';
        mensalDiv.style.padding = '15px';
        mensalDiv.style.backgroundColor = '#0d1117';
        mensalDiv.innerHTML = `<h3 style="color: #88ff66; text-align: center; margin: 0 0 15px 0;">Evolução Mensal</h3>`;
        mensalDiv.appendChild(mensalImage);
        chartsSection.appendChild(mensalDiv);
        
        element.appendChild(chartsSection);
        
        // 6. Adicionar tabelas (percorre TODOS os blocos .tables-row da página,
        // incluindo o de Top Clientes/Resumo e o de Histórico de Pagamentos)
        const tablesRows = document.querySelectorAll('.tables-row');
        tablesRows.forEach(tables => {
            const tablesClone = tables.cloneNode(true);
            tablesClone.style.marginBottom = '20px';
            element.appendChild(tablesClone);
        });
        
        // 7. Adicionar estilos
        const style = document.createElement('style');
        style.textContent = `
            .stat-card {
                background: #0d1117;
                border: 1px solid #88ff66;
                border-radius: 8px;
                padding: 15px;
                display: flex;
                align-items: center;
                gap: 15px;
            }
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-bottom: 30px;
            }
            .stat-icon i { font-size: 32px; color: #88ff66; }
            .stat-label { font-size: 11px; color: #8b949e; text-transform: uppercase; margin: 0; }
            .stat-value { font-size: 24px; font-weight: bold; color: #88ff66; margin: 5px 0 0; }
            .table-card {
                background: #0d1117;
                border: 1px solid #88ff66;
                border-radius: 8px;
                overflow: hidden;
                margin-bottom: 15px;
            }
            .table-header { padding: 12px 15px; border-bottom: 1px solid #88ff66; background: #0d1117; }
            .table-header h3 { margin: 0; color: #88ff66; font-size: 16px; }
            .data-table { width: 100%; border-collapse: collapse; }
            .data-table th { background: #88ff66; color: #0a0c10; padding: 10px; text-align: left; font-weight: bold; }
            .data-table td { padding: 8px 10px; border-bottom: 1px solid #333; color: #e6edf3; }
            .tables-row { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px; }
            .badge-success, .badge-danger, .badge-secondary {
                display: inline-block;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 12px;
            }
            .badge-success { background: #88ff66; color: #0a0c10; }
            .badge-danger { background: #f85149; color: #fff; }
            .badge-secondary { background: #8b949e; color: #fff; }
            .text-center { text-align: center; }
            .text-success { color: #88ff66; }
            .empty-state { text-align: center; padding: 30px; color: #8b949e; }
            @media (max-width: 768px) {
                .tables-row { grid-template-columns: 1fr; }
                .stats-grid { grid-template-columns: 1fr; }
                .chartsSection { grid-template-columns: 1fr; }
            }
        `;
        element.appendChild(style);
        
        // 8. Configurar opções do PDF
        const opt = {
            margin: [0.5, 0.5, 0.5, 0.5],
            filename: `relatorio_${new Date().toISOString().slice(0,19).replace(/:/g, '-')}.pdf`,
            image: { type: 'jpeg', quality: 0.98 },
            html2canvas: { scale: 2, backgroundColor: '#0a0c10', logging: false, useCORS: true },
            jsPDF: { unit: 'in', format: 'a4', orientation: 'landscape' }
        };
        
        // 9. Gerar PDF
        await html2pdf().set(opt).from(element).save();
        
    } catch (error) {
        console.error('Erro ao gerar PDF:', error);
        alert('Erro ao gerar PDF: ' + error.message);
    } finally {
        // Restaurar botão
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
};

// ============================================
// EXPORTAR PARA EXCEL
// ============================================
window.exportarExcel = function() {
    // Coletar dados das tabelas
    const topClientes = [];
    const resumoStatus = [];
    const historicoPagamentos = [];
    
    // Coletar dados da tabela Top Clientes
    document.querySelectorAll('#top-clientes-table tbody tr').forEach(row => {
        const cells = row.querySelectorAll('td');
        if (cells.length === 3 && cells[0].innerText !== 'Nenhum dado disponível') {
            topClientes.push({
                nome: cells[0].innerText,
                emprestimos: cells[1].innerText,
                valor: cells[2].innerText
            });
        }
    });
    
    // Coletar dados da tabela Resumo por Status
    document.querySelectorAll('#resumo-status-table tbody tr').forEach(row => {
        const cells = row.querySelectorAll('td');
        if (cells.length === 4 && cells[0].innerText !== 'Nenhum dado disponível') {
            resumoStatus.push({
                status: cells[0].innerText,
                quantidade: cells[1].innerText,
                valor: cells[2].innerText,
                percentual: cells[3].innerText
            });
        }
    });
    
    // Coletar dados da tabela Histórico de Pagamentos
    document.querySelectorAll('#historico-pagamentos-table tbody tr').forEach(row => {
        const cells = row.querySelectorAll('td');
        if (cells.length === 5 && cells[0].innerText !== 'Nenhum pagamento registado') {
            historicoPagamentos.push({
                data: cells[0].innerText,
                cliente: cells[1].innerText,
                parcela: cells[2].innerText,
                forma: cells[3].innerText,
                valor: cells[4].innerText
            });
        }
    });
    
    // Criar planilha
    const wsData = [
        ['RELATÓRIO GERAL - CODE-MIND'],
        ['Data:', new Date().toLocaleString('pt-BR')],
        [],
        ['RESUMO GERAL'],
        ['Total de Clientes', document.querySelector('.stat-card:first-child .stat-value')?.innerText || '0'],
        ['Total de Empréstimos', document.querySelector('.stat-card:nth-child(2) .stat-value')?.innerText || '0'],
        ['Valor Total Emprestado', document.querySelector('.stat-card:nth-child(3) .stat-value')?.innerText || '0'],
        ['Taxa de Inadimplência', document.querySelector('.stat-card:nth-child(4) .stat-value')?.innerText || '0%'],
        [],
        ['TOP CLIENTES'],
        ['Cliente', 'Empréstimos', 'Valor Total']
    ];
    
    topClientes.forEach(c => {
        wsData.push([c.nome, c.emprestimos, c.valor]);
    });
    
    if (topClientes.length === 0) {
        wsData.push(['Nenhum cliente cadastrado', '', '']);
    }
    
    wsData.push([], ['RESUMO POR STATUS']);
    wsData.push(['Status', 'Quantidade', 'Valor', '%']);
    
    resumoStatus.forEach(s => {
        wsData.push([s.status, s.quantidade, s.valor, s.percentual]);
    });
    
    if (resumoStatus.length === 0) {
        wsData.push(['Nenhum dado disponível', '', '', '']);
    }
    
    wsData.push([], ['HISTÓRICO DE PAGAMENTOS']);
    wsData.push(['Data', 'Cliente', 'Parcela', 'Forma de Pagamento', 'Valor']);
    
    historicoPagamentos.forEach(h => {
        wsData.push([h.data, h.cliente, h.parcela, h.forma, h.valor]);
    });
    
    if (historicoPagamentos.length === 0) {
        wsData.push(['Nenhum pagamento registado', '', '', '', '']);
    }
    
    // Criar workbook
    const ws = XLSX.utils.aoa_to_sheet(wsData);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Relatorio');
    
    // Ajustar largura das colunas
    ws['!cols'] = [{wch:30}, {wch:15}, {wch:20}, {wch:12}];
    
    // Baixar arquivo
    XLSX.writeFile(wb, `relatorio_${new Date().toISOString().slice(0,19).replace(/:/g, '-')}.xlsx`);
};