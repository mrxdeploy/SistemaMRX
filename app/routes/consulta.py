from flask import Blueprint, request, jsonify, Response
from flask_jwt_extended import jwt_required
from app.models import Fornecedor, Placa, Compra, Solicitacao, db
from datetime import datetime
import csv
import io

bp = Blueprint('consulta', __name__, url_prefix='/api/consulta')

@bp.route('/placas', methods=['GET'])
@jwt_required()
def consultar_placas():
    fornecedor_id = request.args.get('fornecedor_id', type=int)
    tipo_placa = request.args.get('tipo_placa')
    status = request.args.get('status')
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    peso_min = request.args.get('peso_min', type=float)
    peso_max = request.args.get('peso_max', type=float)
    valor_min = request.args.get('valor_min', type=float)
    valor_max = request.args.get('valor_max', type=float)
    ordenar_por = request.args.get('ordenar_por', 'data_registro')
    ordem = request.args.get('ordem', 'desc')
    
    query = Placa.query
    
    if fornecedor_id:
        query = query.filter_by(fornecedor_id=fornecedor_id)
    
    if tipo_placa:
        query = query.filter_by(tipo_placa=tipo_placa)
    
    if status:
        query = query.filter_by(status=status)
    
    if data_inicio:
        data_inicio_dt = datetime.strptime(data_inicio, '%Y-%m-%d')
        query = query.filter(Placa.data_registro >= data_inicio_dt)
    
    if data_fim:
        data_fim_dt = datetime.strptime(data_fim, '%Y-%m-%d')
        query = query.filter(Placa.data_registro <= data_fim_dt)
    
    if peso_min is not None:
        query = query.filter(Placa.peso_kg >= peso_min)
    
    if peso_max is not None:
        query = query.filter(Placa.peso_kg <= peso_max)
    
    if valor_min is not None:
        query = query.filter(Placa.valor >= valor_min)
    
    if valor_max is not None:
        query = query.filter(Placa.valor <= valor_max)
    
    if ordenar_por and hasattr(Placa, ordenar_por):
        coluna = getattr(Placa, ordenar_por)
        if ordem == 'asc':
            query = query.order_by(coluna.asc())
        else:
            query = query.order_by(coluna.desc())
    
    placas = query.all()
    return jsonify([placa.to_dict() for placa in placas]), 200

@bp.route('/fornecedores-detalhado', methods=['GET'])
@jwt_required()
def consultar_fornecedores_detalhado():
    cidade = request.args.get('cidade')
    estado = request.args.get('estado')
    forma_pagamento = request.args.get('forma_pagamento')
    condicao_pagamento = request.args.get('condicao_pagamento')
    busca = request.args.get('busca', '')
    
    query = Fornecedor.query
    
    if cidade:
        query = query.filter(Fornecedor.cidade.ilike(f'%{cidade}%'))
    
    if estado:
        query = query.filter_by(estado=estado)
    
    if forma_pagamento:
        query = query.filter_by(forma_pagamento=forma_pagamento)
    
    if condicao_pagamento:
        query = query.filter_by(condicao_pagamento=condicao_pagamento)
    
    if busca:
        query = query.filter(
            db.or_(
                Fornecedor.nome.ilike(f'%{busca}%'),
                Fornecedor.cnpj.ilike(f'%{busca}%')
            )
        )
    
    fornecedores = query.order_by(Fornecedor.nome).all()
    return jsonify([fornecedor.to_dict() for fornecedor in fornecedores]), 200

@bp.route('/fornecedores', methods=['GET'])
@jwt_required()
def consultar_fornecedores():
    busca = request.args.get('busca', '')
    ativo = request.args.get('ativo', type=bool)
    
    query = Fornecedor.query
    
    if busca:
        query = query.filter(
            db.or_(
                Fornecedor.nome.ilike(f'%{busca}%'),
                Fornecedor.cnpj.ilike(f'%{busca}%')
            )
        )
    
    if ativo is not None:
        query = query.filter_by(ativo=ativo)
    
    fornecedores = query.order_by(Fornecedor.nome).all()
    return jsonify([fornecedor.to_dict() for fornecedor in fornecedores]), 200

@bp.route('/compras', methods=['GET'])
@jwt_required()
def consultar_compras():
    fornecedor_id = request.args.get('fornecedor_id', type=int)
    tipo = request.args.get('tipo')
    status = request.args.get('status')
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    valor_min = request.args.get('valor_min', type=float)
    valor_max = request.args.get('valor_max', type=float)
    
    query = Compra.query
    
    if fornecedor_id:
        query = query.filter_by(fornecedor_id=fornecedor_id)
    
    if tipo:
        query = query.filter_by(tipo=tipo)
    
    if status:
        query = query.filter_by(status=status)
    
    if data_inicio:
        data_inicio_dt = datetime.strptime(data_inicio, '%Y-%m-%d')
        query = query.filter(Compra.data_compra >= data_inicio_dt)
    
    if data_fim:
        data_fim_dt = datetime.strptime(data_fim, '%Y-%m-%d')
        query = query.filter(Compra.data_compra <= data_fim_dt)
    
    if valor_min is not None:
        query = query.filter(Compra.valor >= valor_min)
    
    if valor_max is not None:
        query = query.filter(Compra.valor <= valor_max)
    
    compras = query.order_by(Compra.data_compra.desc()).all()
    return jsonify([compra.to_dict() for compra in compras]), 200

@bp.route('/exportar/placas', methods=['GET'])
@jwt_required()
def exportar_placas_csv():
    params = request.args.to_dict()
    
    placas = Placa.query.all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['ID', 'Tag', 'Fornecedor', 'Tipo Placa', 'Peso (kg)', 'Valor', 'Status', 'Data Registro'])
    
    for placa in placas:
        writer.writerow([
            placa.id,
            placa.tag,
            placa.fornecedor.nome if placa.empresa else '',
            placa.tipo_placa,
            placa.peso_kg,
            placa.valor,
            placa.status,
            placa.data_registro.strftime('%Y-%m-%d %H:%M:%S') if placa.data_registro else ''
        ])
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=placas.csv'}
    )

@bp.route('/exportar/compras', methods=['GET'])
@jwt_required()
def exportar_compras_csv():
    compras = Compra.query.all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['ID', 'Fornecedor', 'Material', 'Tipo', 'Valor', 'Status', 'Data Compra'])
    
    for compra in compras:
        writer.writerow([
            compra.id,
            compra.fornecedor.nome if compra.fornecedor else '',
            compra.material,
            compra.tipo,
            compra.valor,
            compra.status,
            compra.data_compra.strftime('%Y-%m-%d %H:%M:%S') if compra.data_compra else ''
        ])
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=compras.csv'}
    )
