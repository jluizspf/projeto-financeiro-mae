// URL do nosso Backend Python (A API)
const API_URL = 'http://127.0.0.1:5000/api';

// Variável para controlar se estamos lançando uma "despesa" ou "receita"
let tipoTransacaoAtual = 'despesa';

// --- 1. INICIALIZAÇÃO (Correção do Aviso) ---
document.addEventListener('DOMContentLoaded', async () => {
    // Verifica se estamos na tela de Dashboard
    if (document.getElementById('saldo-atual')) {
        try {
            // O 'await' aqui diz: "Espere carregar os dados antes de continuar"
            await carregarDadosFinanceiros();
        } catch (error) {
            console.error("Erro ao iniciar dashboard:", error);
        }
    }
});

// --- 2. FUNÇÕES DO DASHBOARD (Saldo e Lista) ---

async function carregarDadosFinanceiros() {
    try {
        const resposta = await fetch(`${API_URL}/transacoes`);
        const transacoes = await resposta.json();

        let saldo = 0;
        const listaElemento = document.getElementById('lista-transacoes');
        listaElemento.innerHTML = '';

        transacoes.forEach(t => {
            if (t.tipo === 'receita') {
                saldo += t.valor;
            } else {
                saldo -= t.valor;
            }

            const item = document.createElement('li');
            item.className = 'transacao-item';

            const valorFormatado = t.valor.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
            const classeCor = t.tipo === 'receita' ? 't-valor-positivo' : 't-valor-negativo';
            const icone = t.tipo === 'receita' ? 'arrow_upward' : 'arrow_downward';

            item.innerHTML = `
                <div style="display: flex; align-items: center;">
                    <span class="material-icons ${classeCor}" style="margin-right: 10px;">${icone}</span>
                    <span class="t-desc">${t.descricao}</span>
                </div>
                <span class="${classeCor}">${valorFormatado}</span>
            `;

            listaElemento.appendChild(item);
        });

        // Atualiza o Saldo Gigante
        const saldoElemento = document.getElementById('saldo-atual');
        saldoElemento.innerText = saldo.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

        if (saldo < 0) {
            saldoElemento.style.color = '#C62828'; // Vermelho
        } else {
            saldoElemento.style.color = '#333333'; // Normal
        }

    } catch (erro) {
        console.error("Erro ao buscar dados:", erro);
        document.getElementById('saldo-atual').innerText = "Erro";
    }
}

// --- 3. FUNÇÕES DO MODAL (Janela de Lançamento) ---

function abrirModal(tipo) {
    tipoTransacaoAtual = tipo;
    const modal = document.getElementById('modal-transacao');
    const titulo = document.getElementById('modal-titulo');
    const btnSalvar = document.querySelector('.btn-confirmar');

    // Configura o visual (Vermelho para Despesa, Verde para Renda)
    if (tipo === 'despesa') {
        titulo.innerText = 'Nova Despesa';
        titulo.style.color = '#C62828';
        btnSalvar.style.backgroundColor = '#C62828';
    } else {
        titulo.innerText = 'Nova Renda';
        titulo.style.color = '#2E7D32';
        btnSalvar.style.backgroundColor = '#2E7D32';
    }

    // Mostra a janela
    modal.style.display = 'flex';

    // Limpa e foca
    document.getElementById('input-descricao').value = '';
    document.getElementById('input-valor').value = '';
    document.getElementById('input-descricao').focus();
}

function fecharModal() {
    document.getElementById('modal-transacao').style.display = 'none';
}

async function salvarTransacao() {
    const descricao = document.getElementById('input-descricao').value;
    const valorTexto = document.getElementById('input-valor').value;

    if (!descricao || !valorTexto) {
        alert("Por favor, preencha a descrição e o valor!");
        return;
    }

    const valor = parseFloat(valorTexto);

    const dados = {
        descricao: descricao,
        valor: valor,
        tipo: tipoTransacaoAtual
    };

    try {
        const resposta = await fetch(`${API_URL}/transacao`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(dados)
        });

        if (resposta.ok) {
            fecharModal();
            await carregarDadosFinanceiros(); // Recarrega tudo para ver o novo saldo!
        } else {
            alert("Erro ao salvar. Tente novamente.");
        }
    } catch (erro) {
        console.error("Erro:", erro);
        alert("Erro de conexão com o servidor.");
    }
}