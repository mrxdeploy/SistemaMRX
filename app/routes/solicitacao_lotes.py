from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import (
    db, Solicitacao, ItemSolicitacao, Fornecedor, TipoLote, 
    FornecedorTipoLoteClassificacao, TipoLotePreco, Usuario, Configuracao, Lote, EntradaEstoque
)
from app.auth import admin_required
from datetime import datetime
import os
import base64
from werkzeug.utils import secure_filename
import uuid

bp = Blueprint('solicitacao_lotes', __name__, url_prefix='/api/solicitacao-lotes')

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@bp.route('/geocode', methods=['POST'])
@jwt_required()
def geocode_reverso():
    """Endpoint para geocoding reverso (GPS → endereço)"""
    try:
        from app.utils.geolocation import reverse_geocode
        
        data = request.get_json()
        lat = data.get('latitude')
        lng = data.get('longitude')
        
        if lat is None or lng is None:
            return jsonify({'erro': 'Latitude e longitude são obrigatórias'}), 400
        
        resultado = reverse_geocode(lat, lng)
        
        return jsonify(resultado), 200
    
    except Exception as e:
        return jsonify({'erro': f'Erro ao buscar endereço: {str(e)}'}), 500

@bp.route('/analisar-imagem', methods=['POST'])
@jwt_required()
def analisar_imagem():
    """Endpoint para análise de imagem com Gemini AI"""
    try:
        from app.services.gemini_analyzer import analyze_images
        
        if 'imagem' not in request.files:
            return jsonify({'erro': 'Nenhuma imagem foi enviada'}), 400
        
        file = request.files['imagem']
        
        if file.filename == '':
            return jsonify({'erro': 'Arquivo sem nome'}), 400
        
        # Ler bytes da imagem
        imagem_bytes = file.read()
        
        # Analisar usando Gemini (para solicitações de lote)
        resultados = analyze_images([imagem_bytes], use_case='solicitacao')
        
        if not resultados or len(resultados) == 0:
            return jsonify({'erro': 'Erro ao analisar imagem'}), 500
        
        resultado = resultados[0]
        
        return jsonify(resultado), 200
    
    except Exception as e:
        return jsonify({'erro': f'Erro ao analisar imagem: {str(e)}'}), 500

@bp.route('/upload-imagem', methods=['POST'])
@jwt_required()
def upload_imagem():
    """Endpoint para upload de imagem e retorno do caminho"""
    try:
        if 'imagem' not in request.files:
            return jsonify({'erro': 'Nenhuma imagem foi enviada'}), 400
        
        file = request.files['imagem']
        
        if file.filename == '':
            return jsonify({'erro': 'Arquivo sem nome'}), 400
        
        # Gerar nome único
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
        
        # Salvar arquivo
        file.save(filepath)
        
        # Retornar caminho relativo
        return jsonify({
            'sucesso': True,
            'caminho': filepath,
            'url': f'/uploads/{unique_filename}'
        }), 200
    
    except Exception as e:
        return jsonify({'erro': f'Erro ao fazer upload: {str(e)}'}), 500

def analisar_imagem_com_ia(imagem_path):
    """Analisa imagem usando Gemini AI para classificar lote e fornecer justificativa"""
    try:
        import google.genai as genai
        
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            print("AVISO: GEMINI_API_KEY não configurada")
            return None
        
        client = genai.Client(api_key=api_key)
        
        with open(imagem_path, 'rb') as f:
            image_data = f.read()
        
        prompt = """Analise esta imagem de placas eletrônicas e classifique o lote baseado na densidade e quantidade de componentes.

CRITÉRIOS DE CLASSIFICAÇÃO:
- LEVE: Placas com poucos componentes, circuitos simples, baixa densidade, muito cobre/área verde visível
- MEDIO: Placas com quantidade moderada de componentes, complexidade média, densidade balanceada
- PESADO: Placas densamente povoadas com muitos componentes, circuitos complexos, alta densidade

FORMATO DE RESPOSTA (obrigatório):
Classificação: [LEVE ou MEDIO ou PESADO]
Justificativa: [Descreva em 1-2 frases o que você observou na imagem que levou a esta classificação]

Exemplo:
Classificação: LEVE
Justificativa: A placa apresenta poucos componentes SMD e muita área de cobre exposta, indicando baixa densidade de componentes e circuito simples."""

        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=[prompt, {'mime_type': 'image/jpeg', 'data': base64.b64encode(image_data).decode()}]
        )
        
        resposta_texto = response.text.strip()
        
        classificacao = None
        justificativa = ""
        
        linhas = resposta_texto.split('\n')
        for linha in linhas:
            if 'Classificação:' in linha or 'Classificacao:' in linha:
                class_parte = linha.split(':', 1)[1].strip().lower()
                if 'leve' in class_parte:
                    classificacao = 'leve'
                elif 'medio' in class_parte or 'média' in class_parte:
                    classificacao = 'medio'
                elif 'pesado' in class_parte or 'pesada' in class_parte:
                    classificacao = 'pesado'
            elif 'Justificativa:' in linha:
                justificativa = linha.split(':', 1)[1].strip()
        
        if not classificacao or classificacao not in ['leve', 'medio', 'pesado']:
            print(f"AVISO: IA retornou classificação inválida. Resposta: {resposta_texto}")
            return {
                'classificacao': 'medio',
                'justificativa': 'Classificação padrão aplicada (IA retornou resposta inválida)',
                'resposta_bruta': resposta_texto
            }
        
        if not justificativa:
            justificativa = "A IA classificou esta placa mas não forneceu justificativa detalhada."
        
        return {
            'classificacao': classificacao,
            'justificativa': justificativa,
            'resposta_bruta': resposta_texto
        }
        
    except Exception as e:
        print(f"ERRO ao analisar imagem com IA: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def calcular_valor_item(fornecedor_id, tipo_lote_id, classificacao, peso_kg):
    """Calcula o valor do item baseado na classificação e configuração do fornecedor
    
    Novo Fluxo:
    1. Busca do fornecedor: quantas estrelas ele atribui para esta classificação
    2. Busca do tipo de lote: o preço por kg para esta classificação + estrelas
    3. Calcula valor total = preço_por_kg * peso_kg
    
    Raises:
        ValueError: Se não houver configuração de estrelas no fornecedor ou preço no tipo de lote
    """
    config_class = FornecedorTipoLoteClassificacao.query.filter_by(
        fornecedor_id=fornecedor_id,
        tipo_lote_id=tipo_lote_id,
        ativo=True
    ).first()
    
    if not config_class:
        raise ValueError(
            f'Fornecedor {fornecedor_id} não possui configuração de estrelas '
            f'para o tipo de lote {tipo_lote_id}. Configure as estrelas por classificação no fornecedor.'
        )
    
    estrelas = config_class.get_estrelas_por_classificacao(classificacao)
    
    preco_tipo_lote = TipoLotePreco.query.filter_by(
        tipo_lote_id=tipo_lote_id,
        classificacao=classificacao,
        estrelas=estrelas,
        ativo=True
    ).first()
    
    if not preco_tipo_lote:
        raise ValueError(
            f'Tipo de lote {tipo_lote_id} não possui preço configurado para '
            f'classificação "{classificacao}" com {estrelas} estrelas. '
            f'Configure os preços no tipo de lote.'
        )
    
    preco_por_kg = preco_tipo_lote.preco_por_kg
    valor_total = preco_por_kg * peso_kg
    
    return round(valor_total, 2), estrelas, preco_por_kg

@bp.route('/fornecedores-com-tipos', methods=['GET'])
@jwt_required()
def listar_fornecedores_com_tipos():
    """Lista fornecedores que possuem configuração de estrelas para tipos de lote"""
    fornecedores = Fornecedor.query.filter_by(ativo=True).all()
    
    resultado = []
    for fornecedor in fornecedores:
        classificacoes = FornecedorTipoLoteClassificacao.query.filter_by(
            fornecedor_id=fornecedor.id,
            ativo=True
        ).all()
        
        if classificacoes:
            tipos_dict = {}
            for classif in classificacoes:
                tipo_id = classif.tipo_lote_id
                if tipo_id not in tipos_dict:
                    tipos_dict[tipo_id] = {
                        'id': tipo_id,
                        'nome': classif.tipo_lote.nome if classif.tipo_lote else '',
                        'estrelas_config': {
                            'leve': classif.leve_estrelas,
                            'medio': classif.medio_estrelas,
                            'pesado': classif.pesado_estrelas
                        }
                    }
            
            tipos_list = list(tipos_dict.values())
            
            resultado.append({
                'id': fornecedor.id,
                'nome': fornecedor.nome,
                'tipos_lote': tipos_list
            })
    
    return jsonify(resultado), 200

@bp.route('/precos/<int:fornecedor_id>/<int:tipo_lote_id>', methods=['GET'])
@jwt_required()
def buscar_precos(fornecedor_id, tipo_lote_id):
    """Busca preços do tipo de lote e configuração de estrelas do fornecedor"""
    fornecedor = Fornecedor.query.get(fornecedor_id)
    tipo_lote = TipoLote.query.get(tipo_lote_id)
    
    if not fornecedor or not tipo_lote:
        return jsonify({'erro': 'Fornecedor ou tipo de lote não encontrado'}), 404
    
    config_estrelas = FornecedorTipoLoteClassificacao.query.filter_by(
        fornecedor_id=fornecedor_id,
        tipo_lote_id=tipo_lote_id,
        ativo=True
    ).first()
    
    if not config_estrelas:
        return jsonify({
            'erro': 'Configuração não encontrada',
            'mensagem': 'Este fornecedor não possui configuração de estrelas para este tipo de lote.'
        }), 404
    
    precos_tipo = tipo_lote.to_dict().get('precos', {})
    
    return jsonify({
        'fornecedor_id': fornecedor_id,
        'fornecedor_nome': fornecedor.nome,
        'tipo_lote_id': tipo_lote_id,
        'tipo_lote_nome': tipo_lote.nome,
        'estrelas_config': {
            'leve': config_estrelas.leve_estrelas,
            'medio': config_estrelas.medio_estrelas,
            'pesado': config_estrelas.pesado_estrelas
        },
        'precos_tipo_lote': precos_tipo
    }), 200

@bp.route('/criar', methods=['POST'])
@jwt_required()
def criar_solicitacao():
    """Cria uma nova solicitação de compra de lote"""
    usuario_id = get_jwt_identity()
    data = request.get_json()
    
    fornecedor_id = data.get('fornecedor_id')
    tipo_lote_id = data.get('tipo_lote_id')
    classificacao = data.get('classificacao')
    estrelas = data.get('estrelas', 3)
    peso_kg = data.get('peso_kg')
    imagem_url = data.get('imagem_url')
    classificacao_ia = data.get('classificacao_sugerida_ia')
    justificativa_ia = data.get('justificativa_ia')
    estrelas_sugeridas_ia = data.get('estrelas_sugeridas_ia')
    observacoes = data.get('observacoes', '')
    
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    endereco = data.get('endereco', '')
    rua = data.get('rua', '')
    numero = data.get('numero', '')
    cep = data.get('cep', '')
    
    if not all([fornecedor_id, tipo_lote_id, classificacao, peso_kg]):
        return jsonify({'erro': 'Dados incompletos'}), 400
    
    if classificacao not in ['leve', 'medio', 'pesado']:
        return jsonify({'erro': 'Classificação inválida. Use: leve, medio ou pesado'}), 400
    
    if peso_kg is None or peso_kg <= 0:
        return jsonify({'erro': 'Peso deve ser maior que zero'}), 400
    
    if estrelas is None or estrelas < 1 or estrelas > 5:
        return jsonify({'erro': 'Estrelas deve estar entre 1 e 5'}), 400
    
    fornecedor = Fornecedor.query.get(fornecedor_id)
    tipo_lote = TipoLote.query.get(tipo_lote_id)
    
    if not fornecedor or not tipo_lote:
        return jsonify({'erro': 'Fornecedor ou tipo de lote não encontrado'}), 404
    
    from app.models import FornecedorTipoLotePreco
    preco_config = FornecedorTipoLotePreco.query.filter_by(
        fornecedor_id=fornecedor_id,
        tipo_lote_id=tipo_lote_id,
        estrelas=estrelas,
        ativo=True
    ).first()
    
    if not preco_config:
        return jsonify({
            'erro': 'Preço não configurado',
            'mensagem': f'O fornecedor "{fornecedor.nome}" não possui preço configurado '
                       f'para o tipo "{tipo_lote.nome}" com {estrelas} estrelas. '
                       f'Um administrador deve configurar os preços antes de criar solicitações.'
        }), 400
    
    preco_por_kg = preco_config.preco_por_kg
    valor_total = round(preco_por_kg * peso_kg, 2)
    
    if valor_total <= 0:
        return jsonify({
            'erro': 'Valor calculado inválido',
            'mensagem': 'O cálculo resultou em valor zero. Verifique a configuração de preços.'
        }), 400
    
    solicitacao = Solicitacao(
        funcionario_id=usuario_id,
        fornecedor_id=fornecedor_id,
        status='aguardando_aprovacao',
        observacoes=observacoes,
        localizacao_lat=latitude,
        localizacao_lng=longitude,
        endereco_completo=endereco,
        rua=rua,
        numero=numero,
        cep=cep
    )
    
    db.session.add(solicitacao)
    db.session.flush()
    
    item = ItemSolicitacao(
        solicitacao_id=solicitacao.id,
        tipo_lote_id=tipo_lote_id,
        peso_kg=peso_kg,
        classificacao=classificacao,
        classificacao_sugerida_ia=classificacao_ia,
        justificativa_ia=justificativa_ia,
        estrelas_sugeridas_ia=estrelas_sugeridas_ia,
        estrelas_final=estrelas,
        valor_calculado=valor_total,
        preco_por_kg_snapshot=preco_por_kg,
        estrelas_snapshot=estrelas,
        imagem_url=imagem_url,
        observacoes=observacoes
    )
    
    db.session.add(item)
    db.session.commit()
    
    return jsonify({
        'mensagem': 'Solicitação criada com sucesso',
        'solicitacao': solicitacao.to_dict(),
        'item': item.to_dict()
    }), 201

@bp.route('/aguardando-aprovacao', methods=['GET'])
@jwt_required()
def listar_aguardando_aprovacao():
    """Lista todas as solicitações aguardando aprovação"""
    solicitacoes = Solicitacao.query.filter_by(
        status='aguardando_aprovacao'
    ).order_by(Solicitacao.data_envio.desc()).all()
    
    resultado = []
    for sol in solicitacoes:
        sol_dict = sol.to_dict()
        sol_dict['itens'] = [item.to_dict() for item in sol.itens]
        resultado.append(sol_dict)
    
    return jsonify(resultado), 200

@bp.route('/<int:id>/aprovar', methods=['PUT'])
@admin_required
def aprovar_solicitacao(id):
    """Aprova uma solicitação de compra"""
    usuario_id = get_jwt_identity()
    
    solicitacao = Solicitacao.query.get(id)
    
    if not solicitacao:
        return jsonify({'erro': 'Solicitação não encontrada'}), 404
    
    if solicitacao.status != 'aguardando_aprovacao':
        return jsonify({'erro': 'Apenas solicitações aguardando aprovação podem ser aprovadas'}), 400
    
    solicitacao.status = 'aprovado'
    solicitacao.data_confirmacao = datetime.utcnow()
    solicitacao.admin_id = usuario_id
    
    db.session.commit()
    
    return jsonify({
        'mensagem': 'Solicitação aprovada com sucesso',
        'solicitacao': solicitacao.to_dict()
    }), 200

@bp.route('/<int:id>/rejeitar', methods=['PUT'])
@admin_required
def rejeitar_solicitacao(id):
    """Rejeita uma solicitação de compra"""
    data = request.get_json()
    motivo = data.get('motivo', 'Solicitação rejeitada')
    
    solicitacao = Solicitacao.query.get(id)
    
    if not solicitacao:
        return jsonify({'erro': 'Solicitação não encontrada'}), 404
    
    if solicitacao.status != 'aguardando_aprovacao':
        return jsonify({'erro': 'Apenas solicitações aguardando aprovação podem ser rejeitadas'}), 400
    
    solicitacao.status = 'rejeitado'
    solicitacao.data_confirmacao = datetime.utcnow()
    solicitacao.observacoes = f"{solicitacao.observacoes}\n\nMotivo da rejeição: {motivo}"
    
    db.session.commit()
    
    return jsonify({
        'mensagem': 'Solicitação rejeitada',
        'solicitacao': solicitacao.to_dict()
    }), 200

@bp.route('/aprovadas', methods=['GET'])
@jwt_required()
def listar_aprovadas():
    """Lista todas as solicitações aprovadas aguardando entrada"""
    solicitacoes = Solicitacao.query.filter_by(
        status='aprovado'
    ).order_by(Solicitacao.data_confirmacao.desc()).all()
    
    resultado = []
    for sol in solicitacoes:
        sol_dict = sol.to_dict()
        sol_dict['itens'] = [item.to_dict() for item in sol.itens]
        
        entrada_existente = EntradaEstoque.query.join(Lote).filter(
            Lote.solicitacao_origem_id == sol.id
        ).first()
        sol_dict['tem_entrada'] = entrada_existente is not None
        
        resultado.append(sol_dict)
    
    return jsonify(resultado), 200

@bp.route('/<int:id>/registrar-entrada', methods=['POST'])
@admin_required
def registrar_entrada(id):
    """Registra a entrada física do lote aprovado"""
    usuario_id = get_jwt_identity()
    data = request.get_json()
    
    solicitacao = Solicitacao.query.get(id)
    
    if not solicitacao:
        return jsonify({'erro': 'Solicitação não encontrada'}), 404
    
    if solicitacao.status != 'aprovado':
        return jsonify({'erro': 'Apenas solicitações aprovadas podem ter entrada registrada'}), 400
    
    entrada_existente = EntradaEstoque.query.join(Lote).filter(
        Lote.solicitacao_origem_id == solicitacao.id
    ).first()
    
    if entrada_existente:
        return jsonify({'erro': 'Entrada já registrada para esta solicitação'}), 400
    
    peso_total = sum(item.peso_kg for item in solicitacao.itens)
    valor_total = sum(item.valor_calculado for item in solicitacao.itens)
    
    primeiro_item = solicitacao.itens[0] if solicitacao.itens else None
    if not primeiro_item:
        return jsonify({'erro': 'Solicitação sem itens'}), 400
    
    lote = Lote(
        fornecedor_id=solicitacao.fornecedor_id,
        tipo_lote_id=primeiro_item.tipo_lote_id,
        solicitacao_origem_id=solicitacao.id,
        peso_total_kg=peso_total,
        valor_total=valor_total,
        quantidade_itens=len(solicitacao.itens),
        classificacao_predominante=primeiro_item.classificacao,
        status='aprovado',
        data_aprovacao=datetime.utcnow()
    )
    
    db.session.add(lote)
    db.session.flush()
    
    for item in solicitacao.itens:
        item.lote_id = lote.id
    
    entrada = EntradaEstoque(
        lote_id=lote.id,
        admin_id=usuario_id,
        status='processado',
        data_processamento=datetime.utcnow(),
        observacoes=data.get('observacoes', '')
    )
    
    db.session.add(entrada)
    
    solicitacao.status = 'recebido'
    
    db.session.commit()
    
    return jsonify({
        'mensagem': 'Entrada registrada com sucesso',
        'lote': lote.to_dict(),
        'entrada': entrada.to_dict()
    }), 201

@bp.route('/configuracao/fornecedor/<int:fornecedor_id>/tipo/<int:tipo_lote_id>', methods=['GET', 'PUT'])
@admin_required
def gerenciar_configuracao_classificacao(fornecedor_id, tipo_lote_id):
    """Gerencia configuração de estrelas por classificação para fornecedor e tipo de lote"""
    if request.method == 'GET':
        config = FornecedorTipoLoteClassificacao.query.filter_by(
            fornecedor_id=fornecedor_id,
            tipo_lote_id=tipo_lote_id
        ).first()
        
        if not config:
            return jsonify({
                'fornecedor_id': fornecedor_id,
                'tipo_lote_id': tipo_lote_id,
                'leve_estrelas': 1,
                'medio_estrelas': 3,
                'pesado_estrelas': 5
            }), 200
        
        return jsonify(config.to_dict()), 200
    
    elif request.method == 'PUT':
        data = request.get_json()
        
        config = FornecedorTipoLoteClassificacao.query.filter_by(
            fornecedor_id=fornecedor_id,
            tipo_lote_id=tipo_lote_id
        ).first()
        
        if not config:
            config = FornecedorTipoLoteClassificacao(
                fornecedor_id=fornecedor_id,
                tipo_lote_id=tipo_lote_id
            )
            db.session.add(config)
        
        if 'leve_estrelas' in data:
            config.leve_estrelas = data['leve_estrelas']
        if 'medio_estrelas' in data:
            config.medio_estrelas = data['medio_estrelas']
        if 'pesado_estrelas' in data:
            config.pesado_estrelas = data['pesado_estrelas']
        if 'ativo' in data:
            config.ativo = data['ativo']
        
        config.data_atualizacao = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify(config.to_dict()), 200
