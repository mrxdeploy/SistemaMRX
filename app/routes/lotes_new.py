from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import Lote, ItemSolicitacao, Solicitacao, EntradaEstoque, Usuario, db
from app.auth import admin_required
from datetime import datetime
import uuid

bp = Blueprint('lotes', __name__, url_prefix='/api/lotes')

@bp.route('', methods=['GET'])
@jwt_required()
def listar_lotes():
    try:
        status = request.args.get('status', '')
        fornecedor_id = request.args.get('fornecedor_id', type=int)
        tipo_lote_id = request.args.get('tipo_lote_id', type=int)
        
        query = Lote.query
        
        if status:
            query = query.filter_by(status=status)
        
        if fornecedor_id:
            query = query.filter_by(fornecedor_id=fornecedor_id)
        
        if tipo_lote_id:
            query = query.filter_by(tipo_lote_id=tipo_lote_id)
        
        lotes = query.order_by(Lote.data_criacao.desc()).all()
        
        resultado = []
        for lote in lotes:
            lote_dict = lote.to_dict()
            lote_dict['itens_count'] = len(lote.itens)
            resultado.append(lote_dict)
        
        return jsonify(resultado), 200
    
    except Exception as e:
        return jsonify({'erro': f'Erro ao listar lotes: {str(e)}'}), 500

@bp.route('/<int:id>', methods=['GET'])
@jwt_required()
def obter_lote(id):
    try:
        lote = Lote.query.get(id)
        
        if not lote:
            return jsonify({'erro': 'Lote não encontrado'}), 404
        
        lote_dict = lote.to_dict()
        lote_dict['itens'] = [item.to_dict() for item in lote.itens]
        
        if lote.solicitacao_origem:
            lote_dict['solicitacao_origem'] = lote.solicitacao_origem.to_dict()
        
        return jsonify(lote_dict), 200
    
    except Exception as e:
        return jsonify({'erro': f'Erro ao obter lote: {str(e)}'}), 500

@bp.route('/criar-de-solicitacao/<int:solicitacao_id>', methods=['POST'])
@admin_required
def criar_lotes_de_solicitacao(solicitacao_id):
    try:
        solicitacao = Solicitacao.query.get(solicitacao_id)
        
        if not solicitacao:
            return jsonify({'erro': 'Solicitação não encontrada'}), 404
        
        if solicitacao.status != 'aprovada':
            return jsonify({'erro': 'Apenas solicitações aprovadas podem gerar lotes'}), 400
        
        itens_agrupados = {}
        for item in solicitacao.itens:
            if item.lote_id:
                continue
            
            chave = (item.tipo_lote_id, item.estrelas_final)
            if chave not in itens_agrupados:
                itens_agrupados[chave] = []
            itens_agrupados[chave].append(item)
        
        lotes_criados = []
        
        for (tipo_lote_id, estrelas), itens in itens_agrupados.items():
            peso_total = sum(item.peso_kg for item in itens)
            valor_total = sum(item.valor_calculado for item in itens)
            estrelas_media = sum(item.estrelas_final for item in itens) / len(itens)
            
            lote = Lote(
                numero_lote=str(uuid.uuid4()).upper()[:12],
                fornecedor_id=solicitacao.fornecedor_id,
                tipo_lote_id=tipo_lote_id,
                solicitacao_origem_id=solicitacao.id,
                peso_total_kg=peso_total,
                valor_total=valor_total,
                quantidade_itens=len(itens),
                estrelas_media=estrelas_media,
                status='aberto',
                tipo_retirada=solicitacao.tipo_retirada
            )
            
            db.session.add(lote)
            db.session.flush()
            
            for item in itens:
                item.lote_id = lote.id
            
            lotes_criados.append(lote.to_dict())
        
        db.session.commit()
        
        return jsonify({
            'mensagem': f'{len(lotes_criados)} lote(s) criado(s) com sucesso',
            'lotes': lotes_criados
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': f'Erro ao criar lotes: {str(e)}'}), 500

@bp.route('/<int:id>', methods=['PUT'])
@admin_required
def atualizar_lote(id):
    try:
        lote = Lote.query.get(id)
        
        if not lote:
            return jsonify({'erro': 'Lote não encontrado'}), 404
        
        data = request.get_json()
        
        if not data:
            return jsonify({'erro': 'Dados não fornecidos'}), 400
        
        if 'observacoes' in data:
            lote.observacoes = data['observacoes']
        
        if 'status' in data:
            lote.status = data['status']
            
            if data['status'] == 'fechado' and not lote.data_fechamento:
                lote.data_fechamento = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify(lote.to_dict()), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': f'Erro ao atualizar lote: {str(e)}'}), 500

@bp.route('/<int:id>/aprovar', methods=['POST'])
@admin_required
def aprovar_lote(id):
    try:
        lote = Lote.query.get(id)
        
        if not lote:
            return jsonify({'erro': 'Lote não encontrado'}), 404
        
        if lote.status == 'aprovado':
            return jsonify({'erro': 'Lote já foi aprovado'}), 400
        
        lote.status = 'aprovado'
        lote.data_aprovacao = datetime.utcnow()
        
        entrada_existente = EntradaEstoque.query.filter_by(lote_id=lote.id).first()
        if not entrada_existente:
            entrada = EntradaEstoque(
                lote_id=lote.id,
                status='pendente'
            )
            db.session.add(entrada)
        
        db.session.commit()
        
        return jsonify({
            'mensagem': 'Lote aprovado e movido para entrada de estoque',
            'lote': lote.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': f'Erro ao aprovar lote: {str(e)}'}), 500

@bp.route('/<int:id>/rastreamento', methods=['GET'])
@jwt_required()
def rastrear_lote(id):
    try:
        lote = Lote.query.get(id)
        
        if not lote:
            return jsonify({'erro': 'Lote não encontrado'}), 404
        
        rastreamento = {
            'lote': lote.to_dict(),
            'itens': [item.to_dict() for item in lote.itens],
            'historico': []
        }
        
        if lote.solicitacao_origem:
            rastreamento['solicitacao_origem'] = {
                'id': lote.solicitacao_origem.id,
                'funcionario': lote.solicitacao_origem.funcionario.nome if lote.solicitacao_origem.funcionario else None,
                'data_envio': lote.solicitacao_origem.data_envio.isoformat() if lote.solicitacao_origem.data_envio else None,
                'data_aprovacao': lote.solicitacao_origem.data_confirmacao.isoformat() if lote.solicitacao_origem.data_confirmacao else None
            }
            
            rastreamento['historico'].append({
                'evento': 'Solicitação criada',
                'data': lote.solicitacao_origem.data_envio.isoformat() if lote.solicitacao_origem.data_envio else None,
                'usuario': lote.solicitacao_origem.funcionario.nome if lote.solicitacao_origem.funcionario else None
            })
            
            if lote.solicitacao_origem.data_confirmacao:
                rastreamento['historico'].append({
                    'evento': 'Solicitação aprovada',
                    'data': lote.solicitacao_origem.data_confirmacao.isoformat(),
                    'usuario': lote.solicitacao_origem.admin.nome if lote.solicitacao_origem.admin else None
                })
        
        rastreamento['historico'].append({
            'evento': 'Lote criado',
            'data': lote.data_criacao.isoformat() if lote.data_criacao else None
        })
        
        if lote.data_aprovacao:
            rastreamento['historico'].append({
                'evento': 'Lote aprovado',
                'data': lote.data_aprovacao.isoformat()
            })
        
        if lote.entrada_estoque:
            rastreamento['entrada_estoque'] = lote.entrada_estoque.to_dict()
            rastreamento['historico'].append({
                'evento': 'Entrada no estoque',
                'data': lote.entrada_estoque.data_entrada.isoformat() if lote.entrada_estoque.data_entrada else None,
                'status': lote.entrada_estoque.status
            })
            
            if lote.entrada_estoque.data_processamento:
                rastreamento['historico'].append({
                    'evento': 'Entrada processada',
                    'data': lote.entrada_estoque.data_processamento.isoformat(),
                    'usuario': lote.entrada_estoque.admin.nome if lote.entrada_estoque.admin else None
                })
        
        rastreamento['historico'].sort(key=lambda x: x['data'] if x['data'] else '')
        
        return jsonify(rastreamento), 200
    
    except Exception as e:
        return jsonify({'erro': f'Erro ao rastrear lote: {str(e)}'}), 500

@bp.route('/<int:id>', methods=['DELETE'])
@admin_required
def deletar_lote(id):
    try:
        lote = Lote.query.get(id)
        
        if not lote:
            return jsonify({'erro': 'Lote não encontrado'}), 404
        
        if lote.status in ['aprovado', 'fechado']:
            return jsonify({'erro': 'Não é possível deletar lotes aprovados ou fechados'}), 400
        
        if lote.entrada_estoque:
            return jsonify({'erro': 'Não é possível deletar lote com entrada de estoque associada'}), 400
        
        db.session.delete(lote)
        db.session.commit()
        
        return jsonify({'mensagem': 'Lote deletado com sucesso'}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': f'Erro ao deletar lote: {str(e)}'}), 500
