from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import EntradaEstoque, Lote, Usuario, db
from app.auth import admin_required
from datetime import datetime

bp = Blueprint('entradas', __name__, url_prefix='/api/entradas')

@bp.route('', methods=['GET'])
@jwt_required()
def listar_entradas():
    try:
        status = request.args.get('status', '')
        fornecedor_id = request.args.get('fornecedor_id', type=int)
        
        query = EntradaEstoque.query
        
        if status:
            query = query.filter_by(status=status)
        
        if fornecedor_id:
            query = query.join(Lote).filter(Lote.fornecedor_id == fornecedor_id)
        
        entradas = query.order_by(EntradaEstoque.data_entrada.desc()).all()
        
        return jsonify([entrada.to_dict() for entrada in entradas]), 200
    
    except Exception as e:
        return jsonify({'erro': f'Erro ao listar entradas: {str(e)}'}), 500

@bp.route('/<int:id>', methods=['GET'])
@jwt_required()
def obter_entrada(id):
    try:
        entrada = EntradaEstoque.query.get(id)
        
        if not entrada:
            return jsonify({'erro': 'Entrada não encontrada'}), 404
        
        entrada_dict = entrada.to_dict()
        
        if entrada.lote:
            entrada_dict['lote']['itens'] = [item.to_dict() for item in entrada.lote.itens]
        
        return jsonify(entrada_dict), 200
    
    except Exception as e:
        return jsonify({'erro': f'Erro ao obter entrada: {str(e)}'}), 500

@bp.route('', methods=['POST'])
@admin_required
def criar_entrada():
    try:
        data = request.get_json()
        
        if not data or not data.get('lote_id'):
            return jsonify({'erro': 'ID do lote é obrigatório'}), 400
        
        lote = Lote.query.get(data['lote_id'])
        
        if not lote:
            return jsonify({'erro': 'Lote não encontrado'}), 404
        
        if lote.status != 'aprovado':
            return jsonify({'erro': 'Apenas lotes aprovados podem ter entrada no estoque'}), 400
        
        entrada_existente = EntradaEstoque.query.filter_by(lote_id=lote.id).first()
        if entrada_existente:
            return jsonify({'erro': 'Este lote já possui entrada de estoque'}), 400
        
        entrada = EntradaEstoque(
            lote_id=lote.id,
            status='pendente',
            observacoes=data.get('observacoes', '')
        )
        
        db.session.add(entrada)
        db.session.commit()
        
        return jsonify(entrada.to_dict()), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': f'Erro ao criar entrada: {str(e)}'}), 500

@bp.route('/<int:id>/processar', methods=['POST'])
@admin_required
def processar_entrada(id):
    try:
        admin_id = int(get_jwt_identity())
        admin = Usuario.query.get(admin_id)
        
        entrada = EntradaEstoque.query.get(id)
        
        if not entrada:
            return jsonify({'erro': 'Entrada não encontrada'}), 404
        
        if entrada.status == 'processada':
            return jsonify({'erro': 'Entrada já foi processada'}), 400
        
        data = request.get_json()
        
        entrada.status = 'processada'
        entrada.data_processamento = datetime.utcnow()
        entrada.admin_id = admin.id if admin else None
        
        if data and 'observacoes' in data:
            entrada.observacoes = (entrada.observacoes or '') + '\n' + data['observacoes']
        
        if entrada.lote:
            entrada.lote.status = 'estoque'
            entrada.lote.data_fechamento = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'mensagem': 'Entrada processada com sucesso',
            'entrada': entrada.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': f'Erro ao processar entrada: {str(e)}'}), 500

@bp.route('/<int:id>', methods=['PUT'])
@admin_required
def atualizar_entrada(id):
    try:
        entrada = EntradaEstoque.query.get(id)
        
        if not entrada:
            return jsonify({'erro': 'Entrada não encontrada'}), 404
        
        data = request.get_json()
        
        if not data:
            return jsonify({'erro': 'Dados não fornecidos'}), 400
        
        if 'observacoes' in data:
            entrada.observacoes = data['observacoes']
        
        if 'status' in data and entrada.status != 'processada':
            entrada.status = data['status']
        
        db.session.commit()
        
        return jsonify(entrada.to_dict()), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': f'Erro ao atualizar entrada: {str(e)}'}), 500

@bp.route('/<int:id>', methods=['DELETE'])
@admin_required
def deletar_entrada(id):
    try:
        entrada = EntradaEstoque.query.get(id)
        
        if not entrada:
            return jsonify({'erro': 'Entrada não encontrada'}), 404
        
        if entrada.status == 'processada':
            return jsonify({'erro': 'Não é possível deletar entradas já processadas'}), 400
        
        db.session.delete(entrada)
        db.session.commit()
        
        return jsonify({'mensagem': 'Entrada deletada com sucesso'}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': f'Erro ao deletar entrada: {str(e)}'}), 500
