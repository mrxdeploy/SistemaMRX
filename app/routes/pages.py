from flask import Blueprint, render_template, send_from_directory
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import Usuario

bp = Blueprint('pages', __name__)

@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/lotes.html')
def lotes():
    return render_template('lotes.html')

@bp.route('/dashboard.html')
def dashboard():
    return render_template('dashboard.html')

@bp.route('/fornecedores.html')
def fornecedores():
    return render_template('fornecedores.html')

@bp.route('/solicitacoes.html')
def solicitacoes():
    return render_template('solicitacoes.html')

@bp.route('/conferencia.html')
def conferencia():
    return render_template('conferencia.html')

@bp.route('/separacao.html')
def separacao():
    return render_template('separacao.html')

@bp.route('/motorista.html')
def motorista():
    return render_template('motorista.html')

@bp.route('/auditoria.html')
def auditoria():
    return render_template('auditoria.html')

@bp.route('/notificacoes.html')
def notificacoes():
    return render_template('notificacoes.html')

@bp.route('/perfil.html')
def perfil():
    return render_template('perfil.html')

@bp.route('/admin.html')
def admin():
    return render_template('admin.html')

@bp.route('/logistica.html')
def logistica():
    return render_template('logistica.html')

@bp.route('/kanban.html')
def kanban():
    return render_template('kanban.html')

@bp.route('/app-motorista.html')
def app_motorista():
    return render_template('app-motorista.html')

@bp.route('/motoristas.html')
def motoristas():
    return render_template('motoristas.html')

@bp.route('/veiculos.html')
def veiculos():
    return render_template('veiculos.html')

@bp.route('/fornecedor-tabela-precos.html')
def fornecedor_tabela_precos():
    return render_template('fornecedor-tabela-precos.html')

@bp.route('/cotacoes-metais.html')
def cotacoes_metais():
    return render_template('cotacoes-metais.html')

@bp.route('/planejamento-conquistas.html')
def planejamento_conquistas():
    return render_template('planejamento-conquistas.html')

@bp.route('/assistente.html')
def assistente():
    return render_template('assistente.html')

@bp.route('/estoque-ativo.html')
def estoque_ativo():
    return render_template('estoque-ativo.html')

@bp.route('/producao.html')
def producao():
    return render_template('producao.html')
