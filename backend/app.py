import os
from flask import Flask, jsonify, request  # <-- MUDANÇA: Importe o 'request'
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from datetime import datetime, timezone

# --- Configuração ---
basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
# <-- NOVO: Adicione esta linha logo depois de criar o 'app'
# Isso libera o acesso para qualquer origem (*)
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'financas.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

migrate = Migrate(app, db)


# --- Modelos de Dados (Nossas Tabelas) ---


class Transacao(db.Model):
    __tablename__ = 'transacao'
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(200), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    tipo = db.Column(db.String(50), nullable=False)  # "receita" ou "despesa"
    data = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    categoria = db.Column(db.String(100), nullable=True)


class ContaRecorrente(db.Model):
    __tablename__ = 'conta_recorrente'
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(200), nullable=False)
    valor_estimado = db.Column(db.Float, nullable=False)
    dia_vencimento = db.Column(db.Integer, nullable=False)
    recorrencia = db.Column(db.String(50), default='mensal')
    notificar_antes_dias = db.Column(db.Integer, default=3)


class CartaoDeCredito(db.Model):
    __tablename__ = 'cartao_de_credito'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, unique=True)
    dia_vencimento = db.Column(db.Integer, nullable=False)
    dia_fechamento = db.Column(db.Integer, nullable=False)
    gastos = db.relationship('GastoCartao', backref='cartao', lazy=True)


class GastoCartao(db.Model):
    __tablename__ = 'gasto_cartao'
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(200), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    data_compra = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    cartao_id = db.Column(db.Integer, db.ForeignKey('cartao_de_credito.id'), nullable=False)


# --- Rotas da API (Nossos Endpoints) ---


@app.route("/")
def ola_mundo():
    return jsonify({"mensagem": "API Financeira está no ar e conectada ao BD!"})


# --- NOSSAS NOVAS ROTAS ---


@app.route("/api/transacao", methods=['POST'])
def add_transacao():
    """
    Endpoint para cadastrar uma nova transação (despesa ou receita).
    Espera um JSON com: descricao, valor, tipo ("despesa" ou "receita")
    Opcional: categoria
    """
    dados = request.get_json()

    # 1. Validar dados
    if not dados or 'descricao' not in dados or 'valor' not in dados or 'tipo' not in dados:
        return jsonify({"erro": "Dados incompletos (descricao, valor, tipo)"}), 400

    # 2. Validar o 'tipo'
    if dados['tipo'] not in ['despesa', 'receita']:
        return jsonify({"erro": "Tipo inválido, use 'despesa' ou 'receita'"}), 400

    # 3. Criar a instância da transação
    nova_transacao = Transacao(
        descricao=dados['descricao'],
        valor=dados['valor'],
        tipo=dados['tipo'],
        # Pega a categoria se ela existir no JSON, senão define como None
        categoria=dados.get('categoria', None)
    )

    # 4. Adicionar ao banco
    try:
        db.session.add(nova_transacao)
        db.session.commit()
        return jsonify({"mensagem": "Transação cadastrada com sucesso!", "id": nova_transacao.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"erro": f"Erro ao salvar no banco: {str(e)}"}), 500


@app.route("/api/transacoes", methods=['GET'])
def get_transacoes():
    """
    Endpoint para listar todas as transações cadastradas.
    """
    try:
        # 1. Consultar o banco de dados
        transacoes = db.session.query(Transacao).all()

        # 2. Converter os objetos Python para dicionários
        lista_transacoes = []
        for transacao in transacoes:
            lista_transacoes.append({
                "id": transacao.id,
                "descricao": transacao.descricao,
                "valor": transacao.valor,
                "tipo": transacao.tipo,
                "data": transacao.data.isoformat(),
                "categoria": transacao.categoria
            })

        # 3. Retornar a lista em formato JSON
        return jsonify(lista_transacoes), 200

    except Exception as e:
        return jsonify({"erro": f"Erro ao consultar dados: {str(e)}"}), 500


@app.route("/api/cartao", methods=['POST'])
def add_cartao():
    """
    Endpoint para cadastrar um novo cartão de crédito.
    Espera um JSON com: nome, dia_vencimento, dia_fechamento
    """
    # 1. Pegar os dados que o frontend enviou (em formato JSON)
    dados = request.get_json()

    # 2. Validar se recebemos os dados esperados
    if not dados or 'nome' not in dados or 'dia_vencimento' not in dados:
        return jsonify({"erro": "Dados incompletos"}), 400  # 400 = Bad Request

    # 3. Criar a nova instância do Modelo (o objeto Python)
    novo_cartao = CartaoDeCredito(
        nome=dados['nome'],
        dia_vencimento=dados['dia_vencimento'],
        dia_fechamento=dados['dia_fechamento']
    )

    # 4. Adicionar ao banco de dados
    try:
        db.session.add(novo_cartao)  # Adiciona à "sessão" (área de preparação)
        db.session.commit()  # "Comita" (salva) as mudanças no banco
        return jsonify({"mensagem": "Cartão cadastrado com sucesso!", "id": novo_cartao.id}), 201  # 201 = Created
    except Exception as e:
        db.session.rollback()  # Desfaz a operação em caso de erro
        return jsonify({"erro": f"Erro ao salvar no banco: {str(e)}"}), 500  # 500 = Internal Server Error


@app.route("/api/gasto-cartao", methods=['POST'])
def add_gasto_cartao():
    """
    Endpoint para cadastrar um novo gasto em um cartão.
    Espera um JSON com: descricao, valor, cartao_id
    (A data_compra é automática)
    """
    dados = request.get_json()

    # 1. Validar dados
    if not dados or 'descricao' not in dados or 'valor' not in dados or 'cartao_id' not in dados:
        return jsonify({"erro": "Dados incompletos"}), 400

    # 2. (Boa prática) Verificar se o cartão existe antes de adicionar o gasto
    cartao = db.session.get(CartaoDeCredito, dados['cartao_id'])
    if not cartao:
        return jsonify({"erro": "Cartão de crédito não encontrado"}), 404  # 404 = Not Found

    # 3. Criar a instância do gasto
    novo_gasto = GastoCartao(
        descricao=dados['descricao'],
        valor=dados['valor'],
        cartao_id=dados['cartao_id']
        # cartao_id=cartao.id também funcionaria
    )

    # 4. Adicionar ao banco
    try:
        db.session.add(novo_gasto)
        db.session.commit()
        return jsonify({"mensagem": "Gasto cadastrado com sucesso!", "id": novo_gasto.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"erro": f"Erro ao salvar no banco: {str(e)}"}), 500


# --- NOSSAS NOVAS ROTAS GET ---


@app.route("/api/cartoes", methods=['GET'])
def get_cartoes():
    """
    Endpoint para listar todos os cartões cadastrados.
    """
    try:
        # 1. Consultar o banco de dados
        # db.session.query(CartaoDeCredito) -> Pede ao SQLAlchemy
        # .all() -> "me traga todos"
        cartoes = db.session.query(CartaoDeCredito).all()

        # 2. Converter os objetos Python para dicionários
        # Não podemos dar 'jsonify(cartoes)' direto, pois são objetos complexos.
        lista_cartoes = []
        for cartao in cartoes:
            lista_cartoes.append({
                "id": cartao.id,
                "nome": cartao.nome,
                "dia_vencimento": cartao.dia_vencimento,
                "dia_fechamento": cartao.dia_fechamento
            })

        # 3. Retornar a lista em formato JSON
        return jsonify(lista_cartoes), 200  # 200 = OK

    except Exception as e:
        return jsonify({"erro": f"Erro ao consultar dados: {str(e)}"}), 500


@app.route("/api/gastos/<int:cartao_id>", methods=['GET'])
def get_gastos_cartao(cartao_id):
    """
    Endpoint para listar todos os gastos de UM cartão específico.
    O 'cartao_id' vem da própria URL.
    """
    try:
        # 1. (Boa prática) Verificar se o cartão existe
        cartao = db.session.get(CartaoDeCredito, cartao_id)
        if not cartao:
            return jsonify({"erro": "Cartão de crédito não encontrado"}), 404  # 404 = Not Found

        # 2. Consultar os gastos "filtrando" pelo cartao_id
        # GastoCartao.cartao_id == cartao_id -> Esta é a condição do filtro
        gastos = db.session.query(GastoCartao).filter(GastoCartao.cartao_id == cartao_id).all()

        # (Opcional) Poderíamos usar o 'relationship' que definimos!
        # gastos = cartao.gastos # Isso faria a mesma coisa!

        # 3. Converter os objetos para uma lista de dicionários
        lista_gastos = []
        for gasto in gastos:
            lista_gastos.append({
                "id": gasto.id,
                "descricao": gasto.descricao,
                "valor": gasto.valor,
                "data_compra": gasto.data_compra.isoformat()  # Converte data para string
            })

        # 4. Retornar a lista de gastos
        return jsonify(lista_gastos), 200

    except Exception as e:
        return jsonify({"erro": f"Erro ao consultar dados: {str(e)}"}), 500


# --- NOVAS ROTAS PARA CONTAS RECORRENTES ---

@app.route("/api/conta-recorrente", methods=['POST'])
def add_conta_recorrente():
    """
    Endpoint para cadastrar uma nova conta recorrente.
    Espera JSON com: descricao, valor_estimado, dia_vencimento
    Opcional: recorrencia, notificar_antes_dias
    """
    dados = request.get_json()

    # 1. Validar dados essenciais
    if not dados or 'descricao' not in dados or 'valor_estimado' not in dados or 'dia_vencimento' not in dados:
        return jsonify({"erro": "Dados incompletos (descricao, valor_estimado, dia_vencimento)"}), 400

    # 2. Criar a instância da conta
    nova_conta = ContaRecorrente(
        descricao=dados['descricao'],
        valor_estimado=dados['valor_estimado'],
        dia_vencimento=dados['dia_vencimento'],

        # Usamos .get() para os campos opcionais que têm valores 'default' no modelo
        recorrencia=dados.get('recorrencia', 'mensal'),
        notificar_antes_dias=dados.get('notificar_antes_dias', 3)
    )

    # 3. Adicionar ao banco
    try:
        db.session.add(nova_conta)
        db.session.commit()
        return jsonify({"mensagem": "Conta recorrente cadastrada com sucesso!", "id": nova_conta.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"erro": f"Erro ao salvar no banco: {str(e)}"}), 500


@app.route("/api/contas-recorrentes", methods=['GET'])
def get_contas_recorrentes():
    """
    Endpoint para listar todas as contas recorrentes cadastradas.
    """
    try:
        # 1. Consultar o banco de dados
        contas = db.session.query(ContaRecorrente).all()

        # 2. Converter os objetos Python para dicionários
        lista_contas = []
        for conta in contas:
            lista_contas.append({
                "id": conta.id,
                "descricao": conta.descricao,
                "valor_estimado": conta.valor_estimado,
                "dia_vencimento": conta.dia_vencimento,
                "recorrencia": conta.recorrencia,
                "notificar_antes_dias": conta.notificar_antes_dias
            })

        # 3. Retornar a lista em formato JSON
        return jsonify(lista_contas), 200

    except Exception as e:
        return jsonify({"erro": f"Erro ao consultar dados: {str(e)}"}), 500


# --- Execução ---


if __name__ == '__main__':
    app.run(debug=True)
