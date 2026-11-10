from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, ConfiguracaoPrecoEstrela, Configuracao, Usuario
from datetime import datetime
from app.utils.datetime_br import now_brasilia

bp = Blueprint('configuracoes', __name__, url_prefix='/api/configuracoes')

# ---------------------------------------------------------------------------
# Chave usada para controlar o cálculo de Custo Médio do Estoque Geral.
# Valor "v2" (padrão) = filtro por material específico (correção atual).
# Valor "v1" = comportamento legado (média de todos os itens da OC).
# ---------------------------------------------------------------------------
CHAVE_CUSTO_MEDIO_VERSAO = 'CUSTO_MEDIO_ESTOQUE_GERAL_VERSAO'

def get_versao_custo_medio() -> str:
    """Retorna a versão ativa do cálculo de custo médio ('v1' ou 'v2')."""
    cfg = Configuracao.query.filter_by(chave=CHAVE_CUSTO_MEDIO_VERSAO).first()
    return cfg.valor if cfg else 'v2'


@bp.route('/versao-custo-medio', methods=['GET'])
@jwt_required()
def info_versao_custo_medio():
    """
    GET /api/configuracoes/versao-custo-medio
    Retorna a versão ativa do cálculo de Custo Médio no Estoque Geral
    e um resumo do que cada versão faz.
    """
    usuario_id = get_jwt_identity()
    usuario = Usuario.query.get(usuario_id)
    if not usuario or usuario.tipo not in ('admin', 'gestor'):
        return jsonify({'erro': 'Acesso negado'}), 403

    versao_atual = get_versao_custo_medio()

    return jsonify({
        'versao_ativa': versao_atual,
        'commit_v2': '00787d2',
        'commit_v1': 'd996719',
        'descricao': {
            'v2': (
                'VERSÃO ATUAL (corrigida) — '
                'Prioridade 5 do _calcular_preco_kg_sublote filtra itens da OC '
                'pelo material específico do sublote antes de calcular a média. '
                'Evita misturar preços de materiais diferentes do mesmo pedido de compra.'
            ),
            'v1': (
                'VERSÃO LEGADA — '
                'Prioridade 5 usava média ponderada de TODOS os itens da OC '
                '(ex: OC #27 com R$8551,75 ÷ 62,40 kg = R$137/kg para qualquer material).'
            ),
        },
        'como_reverter': (
            'POST /api/configuracoes/versao-custo-medio  '
            'com body {"versao": "v1"} para reverter ao comportamento anterior. '
            'Use {"versao": "v2"} para restaurar a correção.'
        )
    })


@bp.route('/versao-custo-medio', methods=['POST'])
@jwt_required()
def alterar_versao_custo_medio():
    """
    POST /api/configuracoes/versao-custo-medio
    Body: {"versao": "v1"} para reverter ao legado, {"versao": "v2"} para manter a correção.
    Apenas administradores podem alterar.
    """
    usuario_id = get_jwt_identity()
    usuario = Usuario.query.get(usuario_id)
    if not usuario or usuario.tipo != 'admin':
        return jsonify({'erro': 'Apenas administradores podem alterar esta configuração'}), 403

    data = request.get_json() or {}
    versao = data.get('versao', '').strip().lower()

    if versao not in ('v1', 'v2'):
        return jsonify({'erro': 'Versão inválida. Use "v1" (legado) ou "v2" (corrigido)'}), 400

    cfg = Configuracao.query.filter_by(chave=CHAVE_CUSTO_MEDIO_VERSAO).first()
    if cfg:
        cfg.valor = versao
        cfg.data_atualizacao = now_brasilia()
    else:
        cfg = Configuracao(
            chave=CHAVE_CUSTO_MEDIO_VERSAO,
            valor=versao,
            descricao='Versão do cálculo de Custo Médio no Estoque Geral (v1=legado, v2=corrigido)',
            tipo='texto'
        )
        db.session.add(cfg)

    db.session.commit()

    # Invalida o cache em memória do módulo estoque_ativo
    try:
        from app.routes.estoque_ativo import _invalidar_cache_versao
        _invalidar_cache_versao()
    except Exception:
        pass

    mensagens = {
        'v1': '⚠️  Revertido para v1 (legado): Custo Médio calculado com média de TODOS os itens da OC.',
        'v2': '✅ Restaurado para v2 (corrigido): Custo Médio filtrado pelo material específico do sublote.',
    }

    return jsonify({
        'sucesso': True,
        'versao_ativa': versao,
        'mensagem': mensagens[versao]
    })

@bp.route('/precos-estrelas', methods=['GET'])
@jwt_required()
def listar_configuracoes():
    configuracoes = ConfiguracaoPrecoEstrela.query.all()
    return jsonify([c.to_dict() for c in configuracoes])

@bp.route('/precos-estrelas/<tipo_placa>', methods=['GET'])
@jwt_required()
def obter_configuracao(tipo_placa):
    config = ConfiguracaoPrecoEstrela.query.filter_by(tipo_placa=tipo_placa).first()
    if not config:
        return jsonify({'error': 'Configuração não encontrada'}), 404
    return jsonify(config.to_dict())

@bp.route('/precos-estrelas', methods=['POST'])
@jwt_required()
def criar_ou_atualizar_configuracao():
    usuario_id = get_jwt_identity()
    usuario = Usuario.query.get(usuario_id)
    
    if not usuario:
        return jsonify({'error': 'Usuário não encontrado'}), 401
    
    if usuario.tipo != 'admin':
        return jsonify({'error': 'Acesso negado'}), 403
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Dados inválidos ou ausentes'}), 400
    
    tipo_placa = data.get('tipo_placa')
    
    if not tipo_placa:
        return jsonify({'error': 'Tipo de placa é obrigatório'}), 400
    
    config = ConfiguracaoPrecoEstrela.query.filter_by(tipo_placa=tipo_placa).first()
    
    if config:
        # Atualizar existente
        config.valor_1_estrela = data.get('valor_1_estrela', config.valor_1_estrela)
        config.valor_2_estrelas = data.get('valor_2_estrelas', config.valor_2_estrelas)
        config.valor_3_estrelas = data.get('valor_3_estrelas', config.valor_3_estrelas)
        config.valor_4_estrelas = data.get('valor_4_estrelas', config.valor_4_estrelas)
        config.valor_5_estrelas = data.get('valor_5_estrelas', config.valor_5_estrelas)
    else:
        # Criar novo
        config = ConfiguracaoPrecoEstrela(
            tipo_placa=tipo_placa,
            valor_1_estrela=data.get('valor_1_estrela', 0.0),
            valor_2_estrelas=data.get('valor_2_estrelas', 0.0),
            valor_3_estrelas=data.get('valor_3_estrelas', 0.0),
            valor_4_estrelas=data.get('valor_4_estrelas', 0.0),
            valor_5_estrelas=data.get('valor_5_estrelas', 0.0)
        )
        db.session.add(config)
    
    db.session.commit()
    return jsonify(config.to_dict()), 200

@bp.route('/precos-estrelas/inicializar', methods=['POST'])
@jwt_required()
def inicializar_configuracoes():
    usuario_id = get_jwt_identity()
    usuario = Usuario.query.get(usuario_id)
    
    if not usuario:
        return jsonify({'error': 'Usuário não encontrado'}), 401
    
    if usuario.tipo != 'admin':
        return jsonify({'error': 'Acesso negado'}), 403
    
    tipos_placa = ['leve', 'pesada', 'media']
    
    for tipo in tipos_placa:
        config = ConfiguracaoPrecoEstrela.query.filter_by(tipo_placa=tipo).first()
        if not config:
            config = ConfiguracaoPrecoEstrela(
                tipo_placa=tipo,
                valor_1_estrela=0.50,
                valor_2_estrelas=0.75,
                valor_3_estrelas=1.00,
                valor_4_estrelas=1.25,
                valor_5_estrelas=1.50
            )
            db.session.add(config)
    
    db.session.commit()
    return jsonify({'message': 'Configurações inicializadas com sucesso'}), 200
