from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, Notificacao, Usuario
from app.auth import admin_required

bp = Blueprint('notificacoes', __name__, url_prefix='/api/notificacoes')

@bp.route('', methods=['GET'])
@jwt_required()
def listar_notificacoes():
    usuario_id = get_jwt_identity()
    usuario = Usuario.query.get(usuario_id)
    
    from app.services.notificacao_service import gerar_todas_notificacoes_pendentes
    try:
        if usuario.tipo == 'admin':
            gerar_todas_notificacoes_pendentes()
    except Exception as e:
        print(f"Erro ao gerar notificações pendentes: {e}")
    
    if usuario.tipo == 'admin':
        notificacoes = Notificacao.query.filter_by(
            usuario_id=usuario_id
        ).order_by(Notificacao.data_envio.desc()).all()
    else:
        notificacoes = Notificacao.query.filter_by(
            usuario_id=usuario_id
        ).order_by(Notificacao.data_envio.desc()).all()
    
    return jsonify([notificacao.to_dict() for notificacao in notificacoes]), 200

@bp.route('/nao-lidas', methods=['GET'])
@jwt_required()
def contar_nao_lidas():
    usuario_id = get_jwt_identity()
    
    count = Notificacao.query.filter_by(
        usuario_id=usuario_id,
        lida=False
    ).count()
    
    return jsonify({'count': count}), 200

@bp.route('/<int:id>/marcar-lida', methods=['PUT'])
@jwt_required()
def marcar_como_lida(id):
    from app.models import Usuario
    usuario_id = get_jwt_identity()
    usuario = Usuario.query.get(usuario_id)
    
    notificacao = Notificacao.query.get(id)
    
    if not notificacao:
        return jsonify({'erro': 'Notificação não encontrada'}), 404
    
    # Permite admin marcar qualquer notificação, ou o próprio usuário marcar a sua
    if notificacao.usuario_id != usuario_id and usuario.tipo != 'admin':
        return jsonify({'erro': 'Acesso negado'}), 403
    
    notificacao.lida = True
    db.session.commit()
    
    return jsonify(notificacao.to_dict()), 200

@bp.route('/marcar-todas-lidas', methods=['PUT'])
@jwt_required()
def marcar_todas_como_lidas():
    usuario_id = get_jwt_identity()
    
    Notificacao.query.filter_by(
        usuario_id=usuario_id,
        lida=False
    ).update({'lida': True})
    
    db.session.commit()
    
    return jsonify({'mensagem': 'Todas as notificações foram marcadas como lidas'}), 200

@bp.route('/gerar-pendentes', methods=['POST'])
@admin_required
def gerar_notificacoes_pendentes():
    from app.services.notificacao_service import gerar_todas_notificacoes_pendentes
    
    try:
        resultado = gerar_todas_notificacoes_pendentes()
        return jsonify({
            'success': True,
            'message': f'{resultado["total_notificacoes_criadas"]} notificações criadas',
            'resultado': resultado
        }), 200
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@bp.route('/resumo-pendencias', methods=['GET'])
@admin_required
def obter_resumo_pendencias():
    from app.services.notificacao_service import obter_resumo_pendencias
    
    try:
        resumo = obter_resumo_pendencias()
        return jsonify(resumo), 200
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@bp.route('/verificar-fornecedores', methods=['POST'])
@admin_required
def verificar_fornecedores():
    from app.services.notificacao_service import verificar_fornecedores_pendentes
    
    try:
        resultado = verificar_fornecedores_pendentes()
        return jsonify({
            'success': True,
            'message': f'{resultado["notificacoes_criadas"]} notificações criadas para {resultado["total_pendentes"]} fornecedores pendentes',
            'resultado': resultado
        }), 200
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@bp.route('/verificar-ordens-compra', methods=['POST'])
@admin_required
def verificar_ordens_compra():
    from app.services.notificacao_service import verificar_ordens_compra_pendentes
    
    try:
        resultado = verificar_ordens_compra_pendentes()
        return jsonify({
            'success': True,
            'message': f'{resultado["notificacoes_criadas"]} notificações criadas para {resultado["total_pendentes"]} ordens de compra pendentes',
            'resultado': resultado
        }), 200
    except Exception as e:
        return jsonify({'erro': str(e)}), 500
