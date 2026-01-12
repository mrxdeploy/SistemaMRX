from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, AuditoriaLog, Usuario
from app.auth import permission_required, perfil_required
from datetime import datetime, timedelta

bp = Blueprint('auditoria', __name__, url_prefix='/api/auditoria')

@bp.route('', methods=['GET'])
@permission_required('visualizar_auditoria')
def listar_logs():
    usuario_id_filter = request.args.get('usuario_id', type=int)
    acao_filter = request.args.get('acao')
    entidade_tipo_filter = request.args.get('entidade_tipo')
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    limit = request.args.get('limit', 100, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    query = AuditoriaLog.query
    
    if usuario_id_filter:
        query = query.filter_by(usuario_id=usuario_id_filter)
    
    if acao_filter:
        query = query.filter_by(acao=acao_filter)
    
    if entidade_tipo_filter:
        query = query.filter_by(entidade_tipo=entidade_tipo_filter)
    
    if data_inicio:
        try:
            data_inicio_dt = datetime.fromisoformat(data_inicio)
            query = query.filter(AuditoriaLog.data_acao >= data_inicio_dt)
        except ValueError:
            return jsonify({'erro': 'Data de início inválida'}), 400
    
    if data_fim:
        try:
            data_fim_dt = datetime.fromisoformat(data_fim)
            query = query.filter(AuditoriaLog.data_acao <= data_fim_dt)
        except ValueError:
            return jsonify({'erro': 'Data de fim inválida'}), 400
    
    total = query.count()
    logs = query.order_by(AuditoriaLog.data_acao.desc()).limit(limit).offset(offset).all()
    
    return jsonify({
        'total': total,
        'limit': limit,
        'offset': offset,
        'logs': [log.to_dict() for log in logs]
    }), 200

@bp.route('/usuario/<int:usuario_id>', methods=['GET'])
@permission_required('visualizar_auditoria')
def listar_logs_usuario(usuario_id):
    usuario = Usuario.query.get(usuario_id)
    if not usuario:
        return jsonify({'erro': 'Usuário não encontrado'}), 404
    
    limit = request.args.get('limit', 50, type=int)
    logs = AuditoriaLog.query.filter_by(usuario_id=usuario_id).order_by(
        AuditoriaLog.data_acao.desc()
    ).limit(limit).all()
    
    return jsonify({
        'usuario': usuario.to_dict(),
        'logs': [log.to_dict() for log in logs]
    }), 200

@bp.route('/entidade/<entidade_tipo>/<int:entidade_id>', methods=['GET'])
@permission_required('visualizar_auditoria')
def listar_logs_entidade(entidade_tipo, entidade_id):
    logs = AuditoriaLog.query.filter_by(
        entidade_tipo=entidade_tipo,
        entidade_id=entidade_id
    ).order_by(AuditoriaLog.data_acao.desc()).all()
    
    return jsonify([log.to_dict() for log in logs]), 200

@bp.route('/estatisticas', methods=['GET'])
@permission_required('visualizar_auditoria')
def estatisticas():
    periodo_dias = request.args.get('dias', 30, type=int)
    data_inicio = datetime.utcnow() - timedelta(days=periodo_dias)
    
    total_logs = AuditoriaLog.query.filter(
        AuditoriaLog.data_acao >= data_inicio
    ).count()
    
    logs_por_acao = db.session.query(
        AuditoriaLog.acao,
        db.func.count(AuditoriaLog.id).label('count')
    ).filter(
        AuditoriaLog.data_acao >= data_inicio
    ).group_by(AuditoriaLog.acao).all()
    
    logs_por_entidade = db.session.query(
        AuditoriaLog.entidade_tipo,
        db.func.count(AuditoriaLog.id).label('count')
    ).filter(
        AuditoriaLog.data_acao >= data_inicio
    ).group_by(AuditoriaLog.entidade_tipo).all()
    
    usuarios_ativos = db.session.query(
        db.func.count(db.func.distinct(AuditoriaLog.usuario_id))
    ).filter(
        AuditoriaLog.data_acao >= data_inicio
    ).scalar()
    
    return jsonify({
        'periodo_dias': periodo_dias,
        'total_logs': total_logs,
        'usuarios_ativos': usuarios_ativos,
        'por_acao': [{'acao': a, 'total': c} for a, c in logs_por_acao],
        'por_entidade': [{'entidade_tipo': e, 'total': c} for e, c in logs_por_entidade]
    }), 200
