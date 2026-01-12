from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, SolicitacaoAutorizacaoPreco, Fornecedor, MaterialBase, TabelaPreco, Usuario, AuditoriaLog
from app.auth import admin_required
from datetime import datetime
from app import socketio

bp = Blueprint('autorizacoes_preco', __name__, url_prefix='/api/autorizacoes-preco')

@bp.route('', methods=['GET'])
@jwt_required()
def listar_autorizacoes():
    try:
        usuario_id = get_jwt_identity()
        usuario = Usuario.query.get(usuario_id)
        
        if not usuario:
            return jsonify({'erro': 'Usuário não encontrado'}), 404
        
        status = request.args.get('status', '')
        fornecedor_id = request.args.get('fornecedor_id', type=int)
        comprador_id = request.args.get('comprador_id', type=int)
        
        query = SolicitacaoAutorizacaoPreco.query
        
        if usuario.tipo != 'admin':
            query = query.filter_by(comprador_id=usuario_id)
        
        if status and status in ['pendente', 'aprovada', 'rejeitada']:
            query = query.filter_by(status=status)
        
        if fornecedor_id:
            query = query.filter_by(fornecedor_id=fornecedor_id)
        
        if comprador_id and usuario.tipo == 'admin':
            query = query.filter_by(comprador_id=comprador_id)
        
        autorizacoes = query.order_by(SolicitacaoAutorizacaoPreco.data_solicitacao.desc()).all()
        
        return jsonify([auth.to_dict() for auth in autorizacoes]), 200
    
    except Exception as e:
        return jsonify({'erro': f'Erro ao listar autorizações: {str(e)}'}), 500

@bp.route('/<int:id>', methods=['GET'])
@jwt_required()
def obter_autorizacao(id):
    try:
        usuario_id = get_jwt_identity()
        usuario = Usuario.query.get(usuario_id)
        
        autorizacao = SolicitacaoAutorizacaoPreco.query.get(id)
        
        if not autorizacao:
            return jsonify({'erro': 'Autorização não encontrada'}), 404
        
        if usuario.tipo != 'admin' and autorizacao.comprador_id != usuario_id:
            return jsonify({'erro': 'Acesso negado'}), 403
        
        return jsonify(autorizacao.to_dict()), 200
    
    except Exception as e:
        return jsonify({'erro': f'Erro ao obter autorização: {str(e)}'}), 500

@bp.route('', methods=['POST'])
@jwt_required()
def criar_autorizacao():
    try:
        usuario_id = get_jwt_identity()
        data = request.get_json()
        
        required_fields = ['fornecedor_id', 'material_id', 'peso_kg', 'preco_negociado', 'justificativa']
        for field in required_fields:
            if field not in data:
                return jsonify({'erro': f'Campo {field} é obrigatório'}), 400
        
        fornecedor = Fornecedor.query.get(data['fornecedor_id'])
        if not fornecedor:
            return jsonify({'erro': 'Fornecedor não encontrado'}), 404
        
        if not fornecedor.tabela_preco_id:
            return jsonify({'erro': 'Fornecedor não possui tabela de preço vinculada'}), 400
        
        material = MaterialBase.query.get(data['material_id'])
        if not material:
            return jsonify({'erro': 'Material não encontrado'}), 404
        
        tabela_preco = TabelaPreco.query.get(fornecedor.tabela_preco_id)
        if not tabela_preco:
            return jsonify({'erro': 'Tabela de preço não encontrada'}), 404
        
        from app.models import TabelaPrecoItem
        preco_item = TabelaPrecoItem.query.filter_by(
            tabela_preco_id=tabela_preco.id,
            material_id=material.id
        ).first()
        
        if not preco_item:
            return jsonify({'erro': 'Preço não definido para este material na tabela do fornecedor'}), 400
        
        try:
            preco_tabela = float(preco_item.preco_por_kg)
            preco_negociado = float(data['preco_negociado'])
            peso_kg = float(data['peso_kg'])
        except (ValueError, TypeError):
            return jsonify({'erro': 'Valores numéricos inválidos para preço ou peso'}), 400
        
        if preco_negociado <= 0 or peso_kg <= 0:
            return jsonify({'erro': 'Preço e peso devem ser maiores que zero'}), 400
        
        if preco_negociado <= preco_tabela:
            return jsonify({'erro': 'Preço negociado deve ser maior que o preço da tabela para requerer autorização'}), 400
        
        autorizacao_existente = SolicitacaoAutorizacaoPreco.query.filter_by(
            fornecedor_id=data['fornecedor_id'],
            material_id=data['material_id'],
            status='pendente'
        ).first()
        
        if autorizacao_existente:
            return jsonify({
                'erro': 'Já existe uma autorização pendente para este fornecedor e material',
                'autorizacao_id': autorizacao_existente.id
            }), 400
        
        diferenca_percentual = ((preco_negociado - preco_tabela) / preco_tabela) * 100
        
        autorizacao = SolicitacaoAutorizacaoPreco(
            ordem_compra_id=data.get('ordem_compra_id'),
            fornecedor_id=data['fornecedor_id'],
            comprador_id=usuario_id,
            material_id=data['material_id'],
            peso_kg=peso_kg,
            tabela_atual_id=tabela_preco.id,
            preco_tabela=preco_tabela,
            preco_negociado=preco_negociado,
            diferenca_percentual=diferenca_percentual,
            justificativa=data['justificativa'],
            status='pendente'
        )
        
        db.session.add(autorizacao)
        db.session.commit()
        
        try:
            socketio.emit('nova_autorizacao_preco', {
                'autorizacao_id': autorizacao.id,
                'fornecedor': fornecedor.nome,
                'material': material.nome,
                'comprador': autorizacao.comprador.nome if autorizacao.comprador else 'N/A',
                'diferenca_percentual': float(diferenca_percentual)
            }, room='admins')
        except:
            pass
        
        return jsonify({
            'mensagem': 'Solicitação de autorização criada com sucesso',
            'autorizacao': autorizacao.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': f'Erro ao criar autorização: {str(e)}'}), 500

@bp.route('/<int:id>/aprovar', methods=['POST'])
@admin_required
def aprovar_autorizacao(id):
    try:
        usuario_id = get_jwt_identity()
        autorizacao = SolicitacaoAutorizacaoPreco.query.get(id)
        
        if not autorizacao:
            return jsonify({'erro': 'Autorização não encontrada'}), 404
        
        if autorizacao.status != 'pendente':
            return jsonify({'erro': 'Apenas autorizações pendentes podem ser aprovadas'}), 400
        
        data = request.get_json()
        promover_fornecedor = data.get('promover_fornecedor', False)
        nova_tabela_id = data.get('nova_tabela_id')
        motivo_decisao = data.get('motivo_decisao', '')
        
        autorizacao.status = 'aprovada'
        autorizacao.decisao_adm_id = usuario_id
        autorizacao.data_decisao = datetime.utcnow()
        autorizacao.motivo_decisao = motivo_decisao
        
        if promover_fornecedor and nova_tabela_id:
            nova_tabela = TabelaPreco.query.get(nova_tabela_id)
            
            if not nova_tabela:
                return jsonify({'erro': 'Nova tabela não encontrada'}), 404
            
            if nova_tabela.nivel_estrelas <= autorizacao.tabela_atual.nivel_estrelas:
                return jsonify({'erro': 'Nova tabela deve ter nível superior à atual'}), 400
            
            fornecedor = autorizacao.fornecedor
            tabela_antiga = fornecedor.tabela_preco
            
            fornecedor.tabela_preco_id = nova_tabela.id
            autorizacao.nova_tabela_atribuida_id = nova_tabela.id
            
            auditoria = AuditoriaLog(
                usuario_id=usuario_id,
                acao='promocao_tabela_fornecedor',
                entidade='fornecedor',
                entidade_id=fornecedor.id,
                descricao=f'Fornecedor {fornecedor.nome} promovido de {tabela_antiga.nome if tabela_antiga else "sem tabela"} para {nova_tabela.nome}',
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent', '')
            )
            db.session.add(auditoria)
        
        db.session.commit()
        
        try:
            socketio.emit('autorizacao_aprovada', {
                'autorizacao_id': autorizacao.id,
                'comprador_id': autorizacao.comprador_id,
                'fornecedor': autorizacao.fornecedor.nome if autorizacao.fornecedor else 'N/A',
                'promovido': promover_fornecedor
            })
        except:
            pass
        
        return jsonify({
            'mensagem': 'Autorização aprovada com sucesso',
            'autorizacao': autorizacao.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': f'Erro ao aprovar autorização: {str(e)}'}), 500

@bp.route('/<int:id>/rejeitar', methods=['POST'])
@admin_required
def rejeitar_autorizacao(id):
    try:
        usuario_id = get_jwt_identity()
        autorizacao = SolicitacaoAutorizacaoPreco.query.get(id)
        
        if not autorizacao:
            return jsonify({'erro': 'Autorização não encontrada'}), 404
        
        if autorizacao.status != 'pendente':
            return jsonify({'erro': 'Apenas autorizações pendentes podem ser rejeitadas'}), 400
        
        data = request.get_json()
        motivo_decisao = data.get('motivo_decisao', '')
        
        if not motivo_decisao:
            return jsonify({'erro': 'Motivo da decisão é obrigatório para rejeitar'}), 400
        
        autorizacao.status = 'rejeitada'
        autorizacao.decisao_adm_id = usuario_id
        autorizacao.data_decisao = datetime.utcnow()
        autorizacao.motivo_decisao = motivo_decisao
        
        db.session.commit()
        
        try:
            socketio.emit('autorizacao_rejeitada', {
                'autorizacao_id': autorizacao.id,
                'comprador_id': autorizacao.comprador_id,
                'fornecedor': autorizacao.fornecedor.nome if autorizacao.fornecedor else 'N/A',
                'motivo': motivo_decisao
            })
        except:
            pass
        
        return jsonify({
            'mensagem': 'Autorização rejeitada',
            'autorizacao': autorizacao.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': f'Erro ao rejeitar autorização: {str(e)}'}), 500

@bp.route('/estatisticas', methods=['GET'])
@admin_required
def estatisticas():
    try:
        total = SolicitacaoAutorizacaoPreco.query.count()
        pendentes = SolicitacaoAutorizacaoPreco.query.filter_by(status='pendente').count()
        aprovadas = SolicitacaoAutorizacaoPreco.query.filter_by(status='aprovada').count()
        rejeitadas = SolicitacaoAutorizacaoPreco.query.filter_by(status='rejeitada').count()
        
        from sqlalchemy import func
        valor_medio_diferenca = db.session.query(
            func.avg(SolicitacaoAutorizacaoPreco.diferenca_percentual)
        ).filter(
            SolicitacaoAutorizacaoPreco.status == 'aprovada'
        ).scalar()
        
        top_materiais = db.session.query(
            MaterialBase.nome,
            func.count(SolicitacaoAutorizacaoPreco.id).label('total')
        ).join(
            SolicitacaoAutorizacaoPreco
        ).group_by(
            MaterialBase.nome
        ).order_by(
            func.count(SolicitacaoAutorizacaoPreco.id).desc()
        ).limit(10).all()
        
        return jsonify({
            'total': total,
            'pendentes': pendentes,
            'aprovadas': aprovadas,
            'rejeitadas': rejeitadas,
            'taxa_aprovacao': round((aprovadas / total * 100) if total > 0 else 0, 2),
            'valor_medio_diferenca': round(float(valor_medio_diferenca) if valor_medio_diferenca else 0, 2),
            'top_materiais': [{'material': mat[0], 'total': mat[1]} for mat in top_materiais]
        }), 200
    
    except Exception as e:
        return jsonify({'erro': f'Erro ao obter estatísticas: {str(e)}'}), 500
