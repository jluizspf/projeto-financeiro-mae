import os
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import extract
from flask_migrate import Migrate
from flask_cors import CORS
from datetime import datetime, timezone

# --- Configuração ---
basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)

# Libera o acesso para qualquer origem (*)
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

    # default='despesa' garante que as contas antigas não quebrem
    tipo = db.Column(db.String(50), nullable=False, default='despesa')

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


# --- TRANSAÇÕES (Ganhos e Gastos) ---

@app.route("/api/transacao", methods=['POST'])
def add_transacao():
    """
    Endpoint para cadastrar uma nova transação (despesa ou receita).
    """
    dados = request.get_json()

    if not dados or 'descricao' not in dados or 'valor' not in dados or 'tipo' not in dados:
        return jsonify({"erro": "Dados incompletos (descricao, valor, tipo)"}), 400

    if dados['tipo'] not in ['despesa', 'receita']:
        return jsonify({"erro": "Tipo inválido, use 'despesa' ou 'receita'"}), 400

    nova_transacao = Transacao(
        descricao=dados['descricao'],
        valor=dados['valor'],
        tipo=dados['tipo'],
        categoria=dados.get('categoria', None)
    )

    try:
        db.session.add(nova_transacao)
        db.session.commit()
        return jsonify({"mensagem": "Transação cadastrada com sucesso!", "id": nova_transacao.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"erro": f"Erro ao salvar no banco: {str(e)}"}), 500


@app.route("/api/transacao/<int:id>", methods=['DELETE'])
def delete_transacao(id):
    try:
        transacao = db.session.get(Transacao, id)
        if not transacao:
            return jsonify({"erro": "Transação não encontrada"}), 404

        db.session.delete(transacao)
        db.session.commit()
        return jsonify({"mensagem": "Transação removida com sucesso!"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"erro": f"Erro ao deletar: {str(e)}"}), 500


@app.route("/api/transacoes", methods=['GET'])
def get_transacoes():
    """
    Endpoint para listar transações.
    Agora aceita filtros opcionais: ?mes=11&ano=2025
    """
    try:
        mes = request.args.get('mes', type=int)
        ano = request.args.get('ano', type=int)

        query = db.session.query(Transacao)

        if mes and ano:
            query = query.filter(
                extract('month', Transacao.data) == mes,
                extract('year', Transacao.data) == ano
            )

        transacoes = query.order_by(Transacao.data.desc()).all()

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

        return jsonify(lista_transacoes), 200

    except Exception as e:
        return jsonify({"erro": f"Erro ao consultar dados: {str(e)}"}), 500


# --- CARTÕES DE CRÉDITO ---

@app.route("/api/cartao", methods=['POST'])
def add_cartao():
    dados = request.get_json()

    if not dados or 'nome' not in dados or 'dia_vencimento' not in dados:
        return jsonify({"erro": "Dados incompletos"}), 400

    novo_cartao = CartaoDeCredito(
        nome=dados['nome'],
        dia_vencimento=dados['dia_vencimento'],
        dia_fechamento=dados['dia_fechamento']
    )

    try:
        db.session.add(novo_cartao)
        db.session.commit()
        return jsonify({"mensagem": "Cartão cadastrado com sucesso!", "id": novo_cartao.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"erro": f"Erro ao salvar no banco: {str(e)}"}), 500


@app.route("/api/gasto-cartao", methods=['POST'])
def add_gasto_cartao():
    dados = request.get_json()

    if not dados or 'descricao' not in dados or 'valor' not in dados or 'cartao_id' not in dados:
        return jsonify({"erro": "Dados incompletos"}), 400

    cartao = db.session.get(CartaoDeCredito, dados['cartao_id'])
    if not cartao:
        return jsonify({"erro": "Cartão de crédito não encontrado"}), 404

    novo_gasto = GastoCartao(
        descricao=dados['descricao'],
        valor=dados['valor'],
        cartao_id=dados['cartao_id']
    )

    try:
        db.session.add(novo_gasto)
        db.session.commit()
        return jsonify({"mensagem": "Gasto cadastrado com sucesso!", "id": novo_gasto.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"erro": f"Erro ao salvar no banco: {str(e)}"}), 500


@app.route("/api/cartoes", methods=['GET'])
def get_cartoes():
    try:
        cartoes = db.session.query(CartaoDeCredito).all()
        lista_cartoes = []
        for cartao in cartoes:
            lista_cartoes.append({
                "id": cartao.id,
                "nome": cartao.nome,
                "dia_vencimento": cartao.dia_vencimento,
                "dia_fechamento": cartao.dia_fechamento
            })
        return jsonify(lista_cartoes), 200
    except Exception as e:
        return jsonify({"erro": f"Erro ao consultar dados: {str(e)}"}), 500


@app.route("/api/gastos/<int:cartao_id>", methods=['GET'])
def get_gastos_cartao(cartao_id):
    try:
        cartao = db.session.get(CartaoDeCredito, cartao_id)
        if not cartao:
            return jsonify({"erro": "Cartão de crédito não encontrado"}), 404

        gastos = db.session.query(GastoCartao).filter(GastoCartao.cartao_id == cartao_id).all()

        lista_gastos = []
        for gasto in gastos:
            lista_gastos.append({
                "id": gasto.id,
                "descricao": gasto.descricao,
                "valor": gasto.valor,
                "data_compra": gasto.data_compra.isoformat()
            })
        return jsonify(lista_gastos), 200
    except Exception as e:
        return jsonify({"erro": f"Erro ao consultar dados: {str(e)}"}), 500


# --- CONTAS RECORRENTES (Agendamentos) ---

@app.route("/api/conta-recorrente", methods=['POST'])
def add_conta_recorrente():
    dados = request.get_json()

    if not dados or 'descricao' not in dados or 'valor_estimado' not in dados or 'dia_vencimento' not in dados:
        return jsonify({"erro": "Dados incompletos"}), 400

    nova_conta = ContaRecorrente(
        descricao=dados['descricao'],
        valor_estimado=dados['valor_estimado'],
        dia_vencimento=dados['dia_vencimento'],
        recorrencia=dados.get('recorrencia', 'mensal'),
        notificar_antes_dias=dados.get('notificar_antes_dias', 3),
        tipo=dados.get('tipo', 'despesa')
    )

    try:
        db.session.add(nova_conta)
        db.session.commit()
        return jsonify({"mensagem": "Conta recorrente cadastrada com sucesso!", "id": nova_conta.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"erro": f"Erro ao salvar no banco: {str(e)}"}), 500


@app.route("/api/contas-recorrentes", methods=['GET'])
def get_contas_recorrentes():
    try:
        contas = db.session.query(ContaRecorrente).all()
        lista_contas = []
        for conta in contas:
            lista_contas.append({
                "id": conta.id,
                "descricao": conta.descricao,
                "valor_estimado": conta.valor_estimado,
                "dia_vencimento": conta.dia_vencimento,
                "recorrencia": conta.recorrencia,
                "notificar_antes_dias": conta.notificar_antes_dias,
                "tipo": conta.tipo  # Garante que o tipo vai para o front
            })
        return jsonify(lista_contas), 200
    except Exception as e:
        return jsonify({"erro": f"Erro ao consultar dados: {str(e)}"}), 500


@app.route("/api/conta-recorrente/<int:id>", methods=['DELETE'])
def delete_conta_recorrente(id):
    try:
        conta = db.session.get(ContaRecorrente, id)
        if not conta:
            return jsonify({"erro": "Conta não encontrada"}), 404

        db.session.delete(conta)
        db.session.commit()
        return jsonify({"mensagem": "Conta removida!"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"erro": f"Erro ao deletar: {str(e)}"}), 500


# --- Execução ---

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # <--- Isso cria as tabelas se elas não existirem!
    app.run(debug=True)
    
