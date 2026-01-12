from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import Fornecedor, Usuario, Vendedor, Placa, db
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from google import genai
from google.genai import types
import io

placas_bp = Blueprint('placas', __name__)

UPLOAD_FOLDER = 'uploads/placas'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def analisar_placa_automatica(imagem_bytes):
    try:
        # Integração com Gemini AI blueprint
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return {'erro': 'Chave da API do Gemini não configurada'}
            
        client = genai.Client(api_key=api_key)
        
        prompt = """Você é um especialista em classificação de placas eletrônicas (PCBs). 
Analise esta imagem de placa eletrônica e classifique como LEVE, MÉDIA ou PESADA.

REGRAS DE CLASSIFICAÇÃO IMPORTANTES:
- LEVE: Alta presença de verde visível (áreas grandes da placa sem muitos componentes soldados). 
  Quanto mais verde aparecer na placa, mais "LEVE" ela é.
- MÉDIA: Quantidade moderada de componentes, com áreas verdes ainda visíveis.
- PESADA: Muitos componentes, conectores, chips, resistores, capacitores e grande densidade visual.
  Pouco verde visível devido à alta quantidade de componentes soldados.

A regra é simples: quanto MAIS VERDE VISÍVEL = mais LEVE a placa.
Quanto MENOS VERDE VISÍVEL (mais componentes) = mais PESADA a placa.

Responda APENAS com:
1. A classificação (LEVE / MÉDIA / PESADA)
2. Uma breve justificativa (1 frase curta)

Formato EXATO da resposta:
Classificação: [LEVE/MÉDIA/PESADA] — [justificativa em 1 frase]

Não adicione informações extras, apenas a classificação e justificativa."""
        
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=[
                types.Part.from_bytes(
                    data=imagem_bytes,
                    mime_type="image/jpeg",
                ),
                prompt
            ],
        )
        
        if not response.text:
            return {'erro': 'Gemini não retornou resposta'}
        
        resultado_texto = response.text.strip()
        print(f"[GEMINI] Resposta completa: {resultado_texto}")
        
        # Detectar classificação
        classificacao = "media"
        resultado_upper = resultado_texto.upper()
        if "LEVE" in resultado_upper:
            classificacao = "leve"
        elif "PESADA" in resultado_upper:
            classificacao = "pesada"
        
        # Extrair justificativa
        import re
        justificativa_match = re.search(r'Classificação:\s*(LEVE|MÉDIA|MEDIA|PESADA)\s*[—\-–]\s*(.+)', resultado_texto, re.IGNORECASE)
        if justificativa_match:
            justificativa = justificativa_match.group(2).strip()
        else:
            # Tentar pegar a primeira linha que não seja vazia
            linhas = [l.strip() for l in resultado_texto.split('\n') if l.strip()]
            justificativa = linhas[0] if linhas else "Placa analisada"
        
        mensagem_final = f" Classificação IA: {classificacao.upper()} — {justificativa}"
        
        return {
            'classificacao': classificacao,
            'mensagem': mensagem_final,
            'justificativa': justificativa,
            'analise_completa': resultado_texto
        }
        
    except Exception as e:
        return {'erro': f'Erro ao processar imagem: {str(e)}'}

@placas_bp.route('/api/placas/analisar', methods=['POST'])
@jwt_required()
def analisar_placa_endpoint():
    if 'imagem' not in request.files:
        return jsonify({'erro': 'Nenhuma imagem enviada'}), 400
    
    file = request.files['imagem']
    
    if file.filename == '':
        return jsonify({'erro': 'Nome de arquivo vazio'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'erro': 'Formato de arquivo não permitido'}), 400
    
    try:
        imagem_bytes = file.read()
        
        resultado = analisar_placa_automatica(imagem_bytes)
        
        if 'erro' in resultado:
            return jsonify(resultado), 400
        
        return jsonify(resultado), 200
        
    except Exception as e:
        return jsonify({'erro': f'Erro ao processar imagem: {str(e)}'}), 500

@placas_bp.route('/api/placas/consulta', methods=['GET'])
@jwt_required()
def consultar_placas():
    fornecedor_id = request.args.get('fornecedor_id', type=int)
    vendedor_id = request.args.get('vendedor_id', type=int)
    tipo_placa = request.args.get('tipo_placa')
    status = request.args.get('status')
    tag = request.args.get('tag')
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    peso_min = request.args.get('peso_min', type=float)
    peso_max = request.args.get('peso_max', type=float)
    valor_min = request.args.get('valor_min', type=float)
    valor_max = request.args.get('valor_max', type=float)
    forma_pagamento = request.args.get('forma_pagamento')
    condicao_pagamento = request.args.get('condicao_pagamento')
    
    query = Placa.query
    
    if fornecedor_id:
        query = query.filter_by(fornecedor_id=fornecedor_id)
    
    if vendedor_id:
        query = query.join(Fornecedor).filter(Fornecedor.vendedor_id == vendedor_id)
    
    if tipo_placa:
        query = query.filter_by(tipo_placa=tipo_placa)
    
    if status:
        query = query.filter_by(status=status)
    
    if tag:
        query = query.filter(Placa.tag.ilike(f'%{tag}%'))
    
    if data_inicio:
        query = query.filter(Placa.data_compra >= datetime.fromisoformat(data_inicio))
    
    if data_fim:
        query = query.filter(Placa.data_compra <= datetime.fromisoformat(data_fim))
    
    if peso_min is not None:
        query = query.filter(Placa.peso_kg >= peso_min)
    
    if peso_max is not None:
        query = query.filter(Placa.peso_kg <= peso_max)
    
    if valor_min is not None:
        query = query.filter(Placa.valor >= valor_min)
    
    if valor_max is not None:
        query = query.filter(Placa.valor <= valor_max)
    
    if forma_pagamento:
        query = query.join(Fornecedor).filter(Fornecedor.forma_pagamento == forma_pagamento)
    
    if condicao_pagamento:
        query = query.join(Fornecedor).filter(Fornecedor.condicao_pagamento == condicao_pagamento)
    
    placas = query.order_by(Placa.data_compra.desc()).all()
    
    return jsonify([placa.to_dict() for placa in placas]), 200

@placas_bp.route('/placas', methods=['GET'])
@jwt_required()
def get_placas():
    user_id = get_jwt_identity()
    user = Usuario.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'Usuário não encontrado'}), 404
    
    fornecedor_id = request.args.get('fornecedor_id', type=int)
    solicitacao_id = request.args.get('solicitacao_id', type=int)
    
    query = Placa.query
    
    if fornecedor_id:
        query = query.filter_by(fornecedor_id=fornecedor_id)
    
    if solicitacao_id:
        query = query.filter_by(solicitacao_id=solicitacao_id)
    
    placas = query.order_by(Placa.data_registro.desc()).all()
    return jsonify([placa.to_dict() for placa in placas])

@placas_bp.route('/placas/<int:id>', methods=['GET'])
@jwt_required()
def get_placa(id):
    placa = Placa.query.get(id)
    if not placa:
        return jsonify({'error': 'Placa não encontrada'}), 404
    
    placa_dict = placa.to_dict()
    placa_dict['empresa'] = placa.fornecedor.to_dict() if placa.empresa else None
    placa_dict['funcionario'] = placa.funcionario.to_dict() if placa.funcionario else None
    
    return jsonify(placa_dict)

@placas_bp.route('/placas', methods=['POST'])
@jwt_required()
def create_placa():
    user_id = get_jwt_identity()
    user = Usuario.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'Usuário não encontrado'}), 404
    
    imagem_url = None
    
    if 'imagem' in request.files:
        file = request.files['imagem']
        if file and allowed_file(file.filename):
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            filename = f"{timestamp}_{filename}"
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            imagem_url = f'/uploads/placas/{filename}'
    
    data = request.form if request.form else request.get_json()
    
    if not data:
        return jsonify({'error': 'Dados não fornecidos'}), 400
    
    fornecedor_id = data.get('fornecedor_id')
    tipo_placa = data.get('tipo_placa')
    peso_kg = data.get('peso_kg')
    valor = data.get('valor')
    solicitacao_id = data.get('solicitacao_id')
    observacoes = data.get('observacoes')
    localizacao_lat = data.get('localizacao_lat')
    localizacao_lng = data.get('localizacao_lng')
    endereco_completo = data.get('endereco_completo')
    
    if not all([fornecedor_id, tipo_placa, peso_kg, valor]):
        return jsonify({'error': 'Dados incompletos'}), 400
    
    empresa = Fornecedor.query.get(fornecedor_id)
    if not empresa:
        return jsonify({'error': 'Fornecedor não encontrada'}), 404
    
    nova_placa = Placa(
        fornecedor_id=fornecedor_id,
        funcionario_id=user_id,
        solicitacao_id=solicitacao_id if solicitacao_id else None,
        tipo_placa=tipo_placa,
        peso_kg=float(peso_kg),
        valor=float(valor),
        imagem_url=imagem_url,
        localizacao_lat=float(localizacao_lat) if localizacao_lat else None,
        localizacao_lng=float(localizacao_lng) if localizacao_lng else None,
        endereco_completo=endereco_completo,
        observacoes=observacoes,
        status='em_analise'
    )
    
    db.session.add(nova_placa)
    db.session.commit()
    
    return jsonify(nova_placa.to_dict()), 201

@placas_bp.route('/placas/<int:id>', methods=['PUT'])
@jwt_required()
def update_placa(id):
    user_id = get_jwt_identity()
    user = Usuario.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'Usuário não encontrado'}), 404
    
    placa = Placa.query.get(id)
    if not placa:
        return jsonify({'error': 'Placa não encontrada'}), 404
    
    data = request.get_json()
    
    if 'tipo_placa' in data:
        placa.tipo_placa = data['tipo_placa']
    if 'peso_kg' in data:
        placa.peso_kg = float(data['peso_kg'])
    if 'valor' in data:
        placa.valor = float(data['valor'])
    if 'solicitacao_id' in data:
        placa.solicitacao_id = data['solicitacao_id']
    if 'observacoes' in data:
        placa.observacoes = data['observacoes']
    if 'status' in data:
        placa.status = data['status']
    
    db.session.commit()
    
    return jsonify(placa.to_dict())

@placas_bp.route('/placas/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_placa(id):
    user_id = get_jwt_identity()
    user = Usuario.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'Usuário não encontrado'}), 404
    
    placa = Placa.query.get(id)
    if not placa:
        return jsonify({'error': 'Placa não encontrada'}), 404
    
    db.session.delete(placa)
    db.session.commit()
    
    return jsonify({'message': 'Placa removida com sucesso'})

@placas_bp.route('/placas/stats', methods=['GET'])
@jwt_required()
def get_placas_stats():
    fornecedor_id = request.args.get('fornecedor_id', type=int)
    status = request.args.get('status')
    
    query = Placa.query
    
    if fornecedor_id:
        query = query.filter_by(fornecedor_id=fornecedor_id)
    
    if status:
        query = query.filter_by(status=status)
    
    total_placas = query.count()
    total_peso = db.session.query(db.func.sum(Placa.peso_kg)).filter(
        Placa.fornecedor_id == fornecedor_id if fornecedor_id else True
    )
    if status:
        total_peso = total_peso.filter(Placa.status == status)
    total_peso = total_peso.scalar() or 0
    
    total_valor = db.session.query(db.func.sum(Placa.valor)).filter(
        Placa.fornecedor_id == fornecedor_id if fornecedor_id else True
    )
    if status:
        total_valor = total_valor.filter(Placa.status == status)
    total_valor = total_valor.scalar() or 0
    
    placas_por_tipo = {}
    tipos_query = db.session.query(
        Placa.tipo_placa,
        db.func.count(Placa.id),
        db.func.sum(Placa.peso_kg)
    ).group_by(Placa.tipo_placa)
    
    if fornecedor_id:
        tipos_query = tipos_query.filter_by(fornecedor_id=fornecedor_id)
    
    if status:
        tipos_query = tipos_query.filter_by(status=status)
    
    for tipo, count, peso in tipos_query:
        placas_por_tipo[tipo] = {
            'quantidade': count,
            'peso_total': float(peso) if peso else 0
        }
    
    return jsonify({
        'total_placas': total_placas,
        'total_peso_kg': float(total_peso),
        'total_valor': float(total_valor),
        'placas_por_tipo': placas_por_tipo
    })
