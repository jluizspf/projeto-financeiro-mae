const API_URL = 'http://127.0.0.1:5000/api';
let tipoTransacaoAtual = 'despesa';
let dataVisualizacao = new Date();

document.addEventListener('DOMContentLoaded', async () => {
    iniciarRelogio()
    if (document.getElementById('saldo-atual')) {
        atualizarTituloMes();
        await carregarDadosFinanceiros();
        await carregarAlertas();
    }
});

// --- NAVEGAÇÃO ---
function atualizarTituloMes() {
    const titulo = document.getElementById('titulo-mes');
    titulo.innerText = dataVisualizacao.toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' });
}

function mudarMes(direcao) {
    dataVisualizacao.setMonth(dataVisualizacao.getMonth() + direcao);
    atualizarTituloMes();
    carregarDadosFinanceiros();
}

// --- DASHBOARD (Saldo e Transações) ---
async function carregarDadosFinanceiros() {
    try {
        const mes = dataVisualizacao.getMonth() + 1;
        const ano = dataVisualizacao.getFullYear();
        const resposta = await fetch(`${API_URL}/transacoes?mes=${mes}&ano=${ano}`);
        const transacoes = await resposta.json();

        let saldo = 0;
        const listaElemento = document.getElementById('lista-transacoes');
        listaElemento.innerHTML = '';

        transacoes.forEach(t => {
            if (t.tipo === 'receita') saldo += t.valor;
            else saldo -= t.valor;

            const item = document.createElement('li');
            item.className = 'transacao-item';
            const valorFmt = t.valor.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
            const classeCor = t.tipo === 'receita' ? 't-valor-positivo' : 't-valor-negativo';
            const icone = t.tipo === 'receita' ? 'arrow_upward' : 'arrow_downward';

            item.innerHTML = `
                <div style="display: flex; align-items: center;">
                    <span class="material-icons ${classeCor}" style="margin-right: 10px;">${icone}</span>
                    <span class="t-desc">${t.descricao}</span>
                </div>
                <div style="display: flex; align-items: center;">
                    <span class="${classeCor}" style="margin-right: 15px; font-weight: bold;">${valorFmt}</span>
                    <button onclick="deletarTransacao(${t.id})" style="border:none; background:none; cursor:pointer; color:#999;">
                        <span class="material-icons" style="font-size: 1.2rem;">delete</span>
                    </button>
                </div>`;
            listaElemento.appendChild(item);
        });

        const saldoEl = document.getElementById('saldo-atual');
        saldoEl.innerText = saldo.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
        saldoEl.style.color = saldo < 0 ? '#C62828' : '#333333';

        // Chama o cálculo do saldo estimado passando o saldo atual
        calcularSaldoEstimado(saldo);

    } catch (erro) {
        console.error("Erro dados:", erro);
        document.getElementById('saldo-atual').innerText = "Erro";
    }
}

// --- ESTIMATIVA (Bola de Cristal) ---
async function calcularSaldoEstimado(saldoAtual) {
    try {
        const resposta = await fetch(`${API_URL}/contas-recorrentes`);
        const agendamentos = await resposta.json();
        const diaHoje = new Date().getDate();
        let saldoPrevisto = saldoAtual;

        const listaEl = document.getElementById('lista-estimativa');
        if (listaEl) {
            listaEl.innerHTML = `<li style="margin-bottom: 5px;">Saldo Hoje: <strong>${saldoAtual.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}</strong></li>`;
        }

        agendamentos.forEach(item => {
            const valorFmt = item.valor_estimado.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
            let linhaHTML = '';
            let classeTexto = '';
            let sinal = '';

            // Define cores e sinais
            if (item.dia_vencimento > diaHoje) {
                // É Futuro: Calcula
                if (item.tipo === 'receita') {
                    saldoPrevisto += item.valor_estimado;
                    classeTexto = 'est-receita';
                    sinal = '+';
                } else {
                    saldoPrevisto -= item.valor_estimado;
                    classeTexto = 'est-despesa';
                    sinal = '-';
                }
            } else {
                // É Passado: Riscado
                classeTexto = 'est-ignorado';
                sinal = ''; // Sem sinal pois foi ignorado
            }

            // Monta a linha com a Lixeira
            // Usamos display:flex para alinhar texto à esquerda e lixeira à direita
            linhaHTML = `
                <li class="${classeTexto}" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                    <span>${sinal} ${valorFmt} (${item.descricao}, dia ${item.dia_vencimento})</span>
                    
                    <button onclick="deletarContaRecorrente(${item.id})" title="Excluir Agendamento" style="border:none; background:none; cursor:pointer; color:#999; margin-left: 5px;">
                        <span class="material-icons" style="font-size: 1rem;">delete</span>
                    </button>
                </li>`;

            if (listaEl) listaEl.innerHTML += linhaHTML;
        });

        document.getElementById('saldo-estimado').innerText = saldoPrevisto.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

    } catch (erro) { console.error("Erro estimativa:", erro); }
}

// --- ALERTAS ---
async function carregarAlertas() {
    const container = document.getElementById('container-alertas');
    container.innerHTML = '';
    try {
        const resposta = await fetch(`${API_URL}/contas-recorrentes`);
        const contas = await resposta.json();
        const diaHoje = new Date().getDate();

        contas.forEach(conta => {
            let distancia = conta.dia_vencimento - diaHoje;
            const diasAviso = conta.notificar_antes_dias || 5;

            if (distancia >= 0 && distancia <= diasAviso) {
                criarAlertaVisual(conta, distancia);
            } else if (distancia < 0 && distancia >= -2) {
                criarAlertaVisual(conta, distancia, true);
            }
        });
    } catch (erro) { console.error("Erro alertas:", erro); }
}

function criarAlertaVisual(conta, diasRestantes, vencido=false) {
    const container = document.getElementById('container-alertas');
    const alerta = document.createElement('div');
    alerta.className = 'alerta-card';

    // Define verbos e cores baseados no tipo
    const ehReceita = conta.tipo === 'receita';
    const verboVence = ehReceita ? 'recebe' : 'vence';
    const verboVenceu = ehReceita ? 'recebeu' : 'venceu';

    // Cor Azul para receita, Laranja/Vermelho para despesa
    if (ehReceita) {
        alerta.style.backgroundColor = '#E3F2FD'; // Azul claro
        alerta.style.borderLeftColor = '#2196F3';
        alerta.style.color = '#0D47A1';
    }

    let texto = '';
    let icone = ehReceita ? 'savings' : 'notifications_active';

    if (vencido) {
        const diasAtras = Math.abs(diasRestantes);
        texto = `Atenção: Você ${verboVenceu} ${conta.descricao} há ${diasAtras} dia(s)!`;
        if(!ehReceita) { // Só muda para vermelho se for conta a pagar
            alerta.style.backgroundColor = '#FFEBEE';
            alerta.style.borderLeftColor = '#D32F2F';
            alerta.style.color = '#D32F2F';
            icone = 'warning';
        }
    } else if (diasRestantes === 0) {
        texto = `Hoje! ${conta.descricao} ${verboVence} HOJE!`;
    } else {
        texto = `Lembrete: ${conta.descricao} ${verboVence} em ${diasRestantes} dias.`;
    }

    const valorFmt = conta.valor_estimado.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
    alerta.innerHTML = `<span class="material-icons">${icone}</span><div style="flex-grow:1;"><div>${texto}</div><div style="font-size:0.9rem;opacity:0.9;">Valor: ${valorFmt}</div></div>`;
    container.appendChild(alerta);
}

// --- MODAIS E AÇÕES ---
function abrirModal(tipo) {
    tipoTransacaoAtual = tipo;
    const modal = document.getElementById('modal-transacao');
    const titulo = document.getElementById('modal-titulo');
    const btnSalvar = document.querySelector('#modal-transacao .btn-confirmar');

    if (tipo === 'despesa') {
        titulo.innerText = 'Nova Despesa'; titulo.style.color = '#C62828'; btnSalvar.style.backgroundColor = '#C62828';
    } else {
        titulo.innerText = 'Nova Renda'; titulo.style.color = '#2E7D32'; btnSalvar.style.backgroundColor = '#2E7D32';
    }
    modal.style.display = 'flex';
    document.getElementById('input-descricao').value = '';
    document.getElementById('input-valor').value = '';
    document.getElementById('input-descricao').focus();
}

function fecharModal() { document.getElementById('modal-transacao').style.display = 'none'; }

async function salvarTransacao() {
    const desc = document.getElementById('input-descricao').value;
    const val = document.getElementById('input-valor').value;
    if (!desc || !val) return alert("Preencha tudo!");

    try {
        const resp = await fetch(`${API_URL}/transacao`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({descricao: desc, valor: parseFloat(val), tipo: tipoTransacaoAtual})
        });
        if (resp.ok) { fecharModal(); await carregarDadosFinanceiros(); }
    } catch (e) { alert("Erro ao salvar."); }
}

async function deletarTransacao(id) {
    if(confirm("Apagar lançamento?")) {
        const resp = await fetch(`${API_URL}/transacao/${id}`, { method: 'DELETE' });
        if(resp.ok) carregarDadosFinanceiros();
    }
}

function abrirModalConta() { document.getElementById('modal-conta').style.display = 'flex'; }
function fecharModalConta() { document.getElementById('modal-conta').style.display = 'none'; }

async function salvarConta() {
    const desc = document.getElementById('conta-descricao').value;
    const val = document.getElementById('conta-valor').value;
    const dia = document.getElementById('conta-dia').value;
    const tipo = document.getElementById('conta-tipo').value;
    if (!desc || !val || !dia) return alert("Preencha tudo!");

    try {
        const resp = await fetch(`${API_URL}/conta-recorrente`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                descricao: desc, valor_estimado: parseFloat(val), dia_vencimento: parseInt(dia), tipo: tipo
            })
        });
        if (resp.ok) {
            alert("Agendado!"); fecharModalConta(); carregarAlertas(); carregarDadosFinanceiros(); // Recarrega estimativa
        }
    } catch (e) { alert("Erro ao agendar."); }
}

async function deletarContaRecorrente(id) {
    // Pergunta de segurança antes de apagar
    if(confirm("Tem certeza que deseja remover este agendamento fixo?")) {
        try {
            const resposta = await fetch(`${API_URL}/conta-recorrente/${id}`, {
                method: 'DELETE'
            });

            if (resposta.ok) {
                // Recarrega tudo para atualizar alertas e estimativas
                carregarAlertas();
                carregarDadosFinanceiros();
            } else {
                alert("Erro ao apagar agendamento.");
            }
        } catch (erro) {
            console.error("Erro:", erro);
        }
    }
}
// --- FUNÇÃO DO RELÓGIO (NOVO) ---
function iniciarRelogio() {
    // 1. Cria o elemento HTML do relógio se ele não existir
    if (!document.getElementById('relogio-neide')) {
        const divRelogio = document.createElement('div');
        divRelogio.id = 'relogio-neide';
        divRelogio.className = 'relogio-flutuante';
        document.body.appendChild(divRelogio);
    }

    // 2. Função que atualiza o texto
    const atualizar = () => {
        const agora = new Date();

        // Formata a data: "Segunda-feira, 20 de Janeiro"
        const opcoesData = { weekday: 'long', day: 'numeric', month: 'long' };
        let dataStr = agora.toLocaleDateString('pt-BR', opcoesData);
        dataStr = dataStr.charAt(0).toUpperCase() + dataStr.slice(1); // Primeira letra maiúscula

        // Formata a hora: "15:30"
        const horaStr = agora.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });

        // Escreve no HTML
        const el = document.getElementById('relogio-neide');
        el.innerHTML = `
            <span class="material-icons relogio-icone">schedule</span>
            <span>${dataStr} • ${horaStr}</span>
        `;
    };

    // 3. Roda agora e repete a cada 1 segundo (1000 milissegundos)
    atualizar();
    setInterval(atualizar, 1000);
}
