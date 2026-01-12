from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import Solicitacao, ItemSolicitacao, Lote, Fornecedor, TipoLote, Usuario, db
from datetime import datetime

bp = Blueprint('compras', __name__, url_prefix='/api/compras')

def gerar_codigo_lote():
    """Gera código de lote no formato AAAAMMDD-SEQ (ex: 20251117-001)"""
    hoje = datetime.now()
    data_str = hoje.strftime('%Y%m%d')
    
    ultimo_lote = db.session.query(Lote).filter(
        Lote.numero_lote.like(f'{data_str}-%')
    ).order_by(Lote.numero_lote.desc()).first()
    
    if ultimo_lote:
        try:
            ultima_seq = int(ultimo_lote.numero_lote.split('-')[1])
            proxima_seq = ultima_seq + 1
        except (IndexError, ValueError):
            proxima_seq = 1
    else:
        proxima_seq = 1
    
    return f"{data_str}-{proxima_seq:03d}"

@bp.route('', methods=['POST'])
@jwt_required()
def criar_compra():
    """
    Cria uma nova compra (Solicitação + Lote) conforme especificação do Fluxo_comprador.md
    
    Body esperado:
    {
        "fornecedor_id": int,
        "tipo_operacao": "coleta" | "entrega",
        "endereco_coleta": null | {rua, numero, cidade, uf, cep},
        "observacoes": str,
        "materiais": [
            {
                "codigo": str,
                "descricao": str,
                "classificacao": "Leve" | "Médio" | "Pesado",
                "peso_kg": float,
                "preco_negociado": float (opcional),
                "valor_total": float (opcional)
            }
        ]
    }
    """
    try:
        usuario_id = get_jwt_identity()
        usuario = Usuario.query.get(usuario_id)
        
        if not usuario:
            return jsonify({'erro': 'Usuário não encontrado'}), 404
        
        data = request.get_json()
        
        if not data:
            return jsonify({'erro': 'Dados não fornecidos'}), 400
        
        fornecedor_id = data.get('fornecedor_id')
        if not fornecedor_id:
            return jsonify({'erro': 'Fornecedor é obrigatório'}), 400
        
        fornecedor = Fornecedor.query.get(fornecedor_id)
        if not fornecedor:
            return jsonify({'erro': 'Fornecedor não encontrado'}), 404
        
        materiais = data.get('materiais', [])
        if not materiais or len(materiais) == 0:
            return jsonify({'erro': 'Pelo menos um material deve ser informado'}), 400
        
        tipo_operacao = data.get('tipo_operacao', 'coleta')
        observacoes = data.get('observacoes', '')
        
        novo_endereco = data.get('endereco_coleta')
        
        solicitacao = Solicitacao(
            funcionario_id=usuario_id,
            fornecedor_id=fornecedor_id,
            tipo_retirada='buscar' if tipo_operacao == 'coleta' else 'entregar',
            status='pendente',
            observacoes=observacoes
        )
        
        if novo_endereco:
            solicitacao.rua = novo_endereco.get('rua', '')
            solicitacao.numero = novo_endereco.get('numero', '')
            solicitacao.cep = novo_endereco.get('cep', '')
            solicitacao.endereco_completo = f"{novo_endereco.get('rua', '')}, {novo_endereco.get('numero', '')} - {novo_endereco.get('cidade', '')}/{novo_endereco.get('uf', '')}"
        else:
            solicitacao.rua = fornecedor.rua or ''
            solicitacao.numero = fornecedor.numero or ''
            solicitacao.cep = fornecedor.cep or ''
            solicitacao.endereco_completo = f"{fornecedor.rua or ''}, {fornecedor.numero or ''} - {fornecedor.cidade or ''}/{fornecedor.estado or ''}"
        
        if fornecedor.latitude and fornecedor.longitude:
            solicitacao.localizacao_lat = fornecedor.latitude
            solicitacao.localizacao_lng = fornecedor.longitude
        
        db.session.add(solicitacao)
        db.session.flush()
        
        peso_total = 0
        valor_total = 0
        itens_criados = []
        
        primeiro_tipo_lote = TipoLote.query.first()
        if not primeiro_tipo_lote:
            db.session.rollback()
            return jsonify({
                'erro': 'Sistema não configurado: nenhum tipo de lote cadastrado. Entre em contato com o administrador.'
            }), 400
        
        tipo_lote_id_padrao = primeiro_tipo_lote.id
        
        for material_data in materiais:
            codigo = material_data.get('codigo', '')
            descricao = material_data.get('descricao', '')
            classificacao = material_data.get('classificacao', 'Médio')
            peso_kg = float(material_data.get('peso_kg', 0))
            preco_negociado = float(material_data.get('preco_negociado', 0)) if material_data.get('preco_negociado') else 0
            valor_item = float(material_data.get('valor_total', 0)) if material_data.get('valor_total') else peso_kg * preco_negociado
            
            if peso_kg <= 0:
                db.session.rollback()
                return jsonify({'erro': f'Peso inválido para material {codigo}'}), 400
            
            peso_total += peso_kg
            valor_total += valor_item
            
            item = ItemSolicitacao(
                solicitacao_id=solicitacao.id,
                tipo_lote_id=tipo_lote_id_padrao,
                peso_kg=peso_kg,
                estrelas_final=fornecedor.tabela_preco_nivel_estrelas or 1,
                classificacao=classificacao.lower(),
                valor_calculado=valor_item,
                preco_por_kg_snapshot=preco_negociado,
                estrelas_snapshot=fornecedor.tabela_preco_nivel_estrelas or 1,
                observacoes=f"Material: {codigo} - {descricao}"
            )
            
            db.session.add(item)
            itens_criados.append(item)
        
        codigo_lote = gerar_codigo_lote()
        
        lote = Lote(
            numero_lote=codigo_lote,
            fornecedor_id=fornecedor_id,
            tipo_lote_id=tipo_lote_id_padrao,
            solicitacao_origem_id=solicitacao.id,
            peso_total_kg=peso_total,
            valor_total=valor_total,
            quantidade_itens=len(materiais),
            status='em_transito',
            tipo_retirada='buscar' if tipo_operacao == 'coleta' else 'entregar',
            observacoes=observacoes
        )
        
        db.session.add(lote)
        db.session.flush()
        
        for item in itens_criados:
            item.lote_id = lote.id
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'mensagem': f'Compra criada com sucesso! Lote {codigo_lote} gerado.',
            'lote_codigo': codigo_lote,
            'lote_id': lote.id,
            'solicitacao_id': solicitacao.id,
            'peso_total': peso_total,
            'valor_total': valor_total,
            'status': 'em_transito'
        }), 201
    
    except ValueError as e:
        db.session.rollback()
        return jsonify({'erro': f'Erro de validação: {str(e)}'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': f'Erro ao criar compra: {str(e)}'}), 500

@bp.route('/<int:id>', methods=['GET'])
@jwt_required()
def obter_compra(id):
    """Obtém detalhes de uma compra específica"""
    try:
        usuario_id = get_jwt_identity()
        usuario = Usuario.query.get(usuario_id)
        
        if not usuario:
            return jsonify({'erro': 'Usuário não encontrado'}), 404
        
        solicitacao = Solicitacao.query.get(id)
        
        if not solicitacao:
            return jsonify({'erro': 'Compra não encontrada'}), 404
        
        if usuario.tipo != 'admin' and solicitacao.funcionario_id != usuario_id:
            return jsonify({'erro': 'Sem permissão para acessar esta compra'}), 403
        
        lotes = Lote.query.filter_by(solicitacao_origem_id=id).all()
        
        return jsonify({
            'solicitacao': solicitacao.to_dict(),
            'lotes': [lote.to_dict() for lote in lotes]
        }), 200
    
    except Exception as e:
        return jsonify({'erro': f'Erro ao obter compra: {str(e)}'}), 500

@bp.route('', methods=['GET'])
@jwt_required()
def listar_compras():
    """Lista compras do usuário logado ou todas (se admin)"""
    try:
        usuario_id = get_jwt_identity()
        usuario = Usuario.query.get(usuario_id)
        
        if not usuario:
            return jsonify({'erro': 'Usuário não encontrado'}), 404
        
        query = Solicitacao.query
        
        if usuario.tipo != 'admin':
            query = query.filter_by(funcionario_id=usuario_id)
        
        status_filter = request.args.get('status')
        if status_filter:
            query = query.filter_by(status=status_filter)
        
        fornecedor_id = request.args.get('fornecedor_id', type=int)
        if fornecedor_id:
            query = query.filter_by(fornecedor_id=fornecedor_id)
        
        solicitacoes = query.order_by(Solicitacao.data_envio.desc()).all()
        
        return jsonify([s.to_dict() for s in solicitacoes]), 200
    
    except Exception as e:
        return jsonify({'erro': f'Erro ao listar compras: {str(e)}'}), 500
