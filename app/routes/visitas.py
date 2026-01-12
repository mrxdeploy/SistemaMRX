from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import VisitaFornecedor, Fornecedor, Usuario, db
from app.auth import admin_required
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('visitas', __name__, url_prefix='/api/fornecedores/visitas')


@bp.route('', methods=['GET'])
@jwt_required()
def listar_visitas():
    """Lista todas as visitas do usuário ou todas (admin)"""
    try:
        usuario_id = int(get_jwt_identity())
        usuario = Usuario.query.get(usuario_id)
        
        if not usuario:
            return jsonify({'erro': 'Usuário não encontrado'}), 404
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status = request.args.get('status', None)
        
        query = VisitaFornecedor.query
        
        if usuario.tipo != 'admin':
            query = query.filter(VisitaFornecedor.usuario_id == usuario_id)
        
        if status:
            query = query.filter(VisitaFornecedor.status == status)
        
        query = query.order_by(VisitaFornecedor.data_visita.desc())
        
        visitas_pag = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'visitas': [v.to_dict() for v in visitas_pag.items],
            'total': visitas_pag.total,
            'pages': visitas_pag.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        logger.error(f'Erro ao listar visitas: {str(e)}')
        return jsonify({'erro': 'Erro ao listar visitas'}), 500


@bp.route('', methods=['POST'])
@jwt_required()
def criar_visita():
    """Cria uma nova visita"""
    try:
        usuario_id = int(get_jwt_identity())
        data = request.get_json()
        
        if not data:
            return jsonify({'erro': 'Dados não fornecidos'}), 400
        
        nome_fornecedor = data.get('nome_fornecedor', '').strip()
        contato_nome = data.get('contato_nome', '').strip()
        
        if not nome_fornecedor:
            return jsonify({'erro': 'Nome do fornecedor é obrigatório'}), 400
        
        if not contato_nome:
            return jsonify({'erro': 'Nome do contato é obrigatório'}), 400
        
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        if latitude is not None and longitude is not None:
            try:
                latitude = float(latitude)
                longitude = float(longitude)
            except (ValueError, TypeError):
                return jsonify({'erro': 'Coordenadas inválidas'}), 400
        
        visita = VisitaFornecedor(
            nome_fornecedor=nome_fornecedor,
            contato_nome=contato_nome,
            contato_email=data.get('contato_email', '').strip() or None,
            contato_telefone=data.get('contato_telefone', '').strip() or None,
            latitude=latitude,
            longitude=longitude,
            observacoes=data.get('observacoes', '').strip() or None,
            status='pendente',
            data_visita=datetime.utcnow(),
            usuario_id=usuario_id
        )
        
        db.session.add(visita)
        db.session.commit()
        
        logger.info(f'Visita {visita.id} criada por usuário {usuario_id}')
        
        return jsonify(visita.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'Erro ao criar visita: {str(e)}')
        return jsonify({'erro': 'Erro ao criar visita'}), 500


@bp.route('/<int:id>', methods=['GET'])
@jwt_required()
def obter_visita(id):
    """Obtém detalhes de uma visita"""
    try:
        usuario_id = int(get_jwt_identity())
        usuario = Usuario.query.get(usuario_id)
        
        if not usuario:
            return jsonify({'erro': 'Usuário não encontrado'}), 404
        
        visita = VisitaFornecedor.query.get(id)
        
        if not visita:
            return jsonify({'erro': 'Visita não encontrada'}), 404
        
        if usuario.tipo != 'admin' and visita.usuario_id != usuario_id:
            return jsonify({'erro': 'Acesso negado'}), 403
        
        return jsonify(visita.to_dict()), 200
        
    except Exception as e:
        logger.error(f'Erro ao obter visita: {str(e)}')
        return jsonify({'erro': 'Erro ao obter visita'}), 500


@bp.route('/<int:id>/status', methods=['PUT'])
@jwt_required()
def atualizar_status_visita(id):
    """Atualiza o status de uma visita"""
    try:
        usuario_id = int(get_jwt_identity())
        usuario = Usuario.query.get(usuario_id)
        
        if not usuario:
            return jsonify({'erro': 'Usuário não encontrado'}), 404
        
        visita = VisitaFornecedor.query.get(id)
        
        if not visita:
            return jsonify({'erro': 'Visita não encontrada'}), 404
        
        if usuario.tipo != 'admin' and visita.usuario_id != usuario_id:
            return jsonify({'erro': 'Acesso negado'}), 403
        
        data = request.get_json()
        novo_status = data.get('status')
        
        if novo_status not in ['pendente', 'nao_fechado', 'negociacao_fechada']:
            return jsonify({'erro': 'Status inválido'}), 400
        
        visita.status = novo_status
        db.session.commit()
        
        logger.info(f'Status da visita {id} atualizado para {novo_status}')
        
        return jsonify(visita.to_dict()), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'Erro ao atualizar status da visita: {str(e)}')
        return jsonify({'erro': 'Erro ao atualizar status'}), 500


@bp.route('/<int:id>/fornecedor', methods=['PUT'])
@jwt_required()
def associar_fornecedor(id):
    """Associa um fornecedor criado a uma visita"""
    try:
        usuario_id = int(get_jwt_identity())
        usuario = Usuario.query.get(usuario_id)
        
        if not usuario:
            return jsonify({'erro': 'Usuário não encontrado'}), 404
        
        visita = VisitaFornecedor.query.get(id)
        
        if not visita:
            return jsonify({'erro': 'Visita não encontrada'}), 404
        
        if usuario.tipo != 'admin' and visita.usuario_id != usuario_id:
            return jsonify({'erro': 'Acesso negado'}), 403
        
        data = request.get_json()
        fornecedor_id = data.get('fornecedor_id')
        
        if not fornecedor_id:
            return jsonify({'erro': 'ID do fornecedor é obrigatório'}), 400
        
        fornecedor = Fornecedor.query.get(fornecedor_id)
        
        if not fornecedor:
            return jsonify({'erro': 'Fornecedor não encontrado'}), 404
        
        visita.fornecedor_id = fornecedor_id
        visita.status = 'negociacao_fechada'
        db.session.commit()
        
        logger.info(f'Visita {id} associada ao fornecedor {fornecedor_id}')
        
        return jsonify(visita.to_dict()), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'Erro ao associar fornecedor: {str(e)}')
        return jsonify({'erro': 'Erro ao associar fornecedor'}), 500


@bp.route('/<int:id>', methods=['DELETE'])
@admin_required
def excluir_visita(id):
    """Exclui uma visita (somente admin)"""
    try:
        visita = VisitaFornecedor.query.get(id)
        
        if not visita:
            return jsonify({'erro': 'Visita não encontrada'}), 404
        
        db.session.delete(visita)
        db.session.commit()
        
        logger.info(f'Visita {id} excluída')
        
        return jsonify({'mensagem': 'Visita excluída com sucesso'}), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'Erro ao excluir visita: {str(e)}')
        return jsonify({'erro': 'Erro ao excluir visita'}), 500


@bp.route('/estatisticas', methods=['GET'])
@jwt_required()
def estatisticas_visitas():
    """Retorna estatísticas das visitas"""
    try:
        usuario_id = int(get_jwt_identity())
        usuario = Usuario.query.get(usuario_id)
        
        if not usuario:
            return jsonify({'erro': 'Usuário não encontrado'}), 404
        
        query = VisitaFornecedor.query
        
        if usuario.tipo != 'admin':
            query = query.filter(VisitaFornecedor.usuario_id == usuario_id)
        
        total = query.count()
        pendentes = query.filter(VisitaFornecedor.status == 'pendente').count()
        nao_fechados = query.filter(VisitaFornecedor.status == 'nao_fechado').count()
        fechados = query.filter(VisitaFornecedor.status == 'negociacao_fechada').count()
        
        return jsonify({
            'total': total,
            'pendentes': pendentes,
            'nao_fechados': nao_fechados,
            'negociacao_fechada': fechados
        }), 200
        
    except Exception as e:
        logger.error(f'Erro ao obter estatísticas: {str(e)}')
        return jsonify({'erro': 'Erro ao obter estatísticas'}), 500
