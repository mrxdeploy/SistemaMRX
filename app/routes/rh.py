from flask import Blueprint, request, jsonify, send_file, Response
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, Usuario, Solicitacao, Fornecedor, AuditoriaLog, Perfil, Motorista
from app.auth import admin_required, hash_senha
from app.utils.auditoria import registrar_criacao, registrar_atualizacao, registrar_exclusao
from datetime import datetime, timedelta
from sqlalchemy import func, and_
import os
import io
from werkzeug.utils import secure_filename

bp = Blueprint('rh', __name__, url_prefix='/api/rh')


@bp.route('/usuarios/<int:id>/foto', methods=['GET'])
def obter_foto_usuario(id):
    """Retorna a foto do usuário armazenada no banco de dados (público para img tags)"""
    usuario = Usuario.query.get(id)
    if not usuario or not usuario.foto_data:
        return '', 404
    
    return Response(
        usuario.foto_data,
        mimetype=usuario.foto_mimetype or 'image/jpeg',
        headers={
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        }
    )


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads', 'usuarios')
UPLOAD_PATH_PREFIX = 'usuarios'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def ensure_upload_folder():
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@bp.route('/usuarios', methods=['GET'])
@admin_required
def listar_usuarios_rh():
    usuarios = Usuario.query.all()
    usuarios_dict = [u.to_dict() for u in usuarios]
    print(f"📋 Retornando {len(usuarios_dict)} usuários")
    for u in usuarios_dict:
        if u.get('foto_path'):
            print(f"  👤 {u['nome']}: foto_path = {u['foto_path']}")
    return jsonify(usuarios_dict), 200

@bp.route('/usuarios/<int:id>', methods=['GET'])
@admin_required
def obter_usuario_rh(id):
    usuario = Usuario.query.get(id)
    if not usuario:
        return jsonify({'erro': 'Usuário não encontrado'}), 404
    return jsonify(usuario.to_dict()), 200

@bp.route('/usuarios', methods=['POST'])
@admin_required
def criar_usuario_rh():
    admin_id = get_jwt_identity()
    
    if request.content_type and 'multipart/form-data' in request.content_type:
        data = request.form.to_dict()
    else:
        data = request.get_json() or {}
    
    if not data or not data.get('nome') or not data.get('email'):
        return jsonify({'erro': 'Nome e email são obrigatórios'}), 400
    
    if not data.get('perfil_id'):
        return jsonify({'erro': 'Perfil é obrigatório'}), 400
    
    usuario_existente = Usuario.query.filter_by(email=data['email']).first()
    if usuario_existente:
        return jsonify({'erro': 'Email já cadastrado'}), 400
    
    perfil = Perfil.query.get(int(data['perfil_id']))
    if not perfil:
        return jsonify({'erro': 'Perfil não encontrado'}), 404
    
    if perfil.nome == 'Administrador':
        tipo = 'admin'
    elif perfil.nome == 'Motorista':
        tipo = 'motorista'
    else:
        tipo = 'funcionario'
    
    senha = data.get('senha')
    if not senha:
        cpf = data.get('cpf', '')
        cpf_numeros = cpf.replace('.', '').replace('-', '')
        senha = cpf_numeros[-4:] if len(cpf_numeros) >= 4 else '123456'
    
    ativo = data.get('ativo', True)
    if isinstance(ativo, str):
        ativo = ativo.lower() in ('true', '1', 'yes', 'on')
    
    percentual = data.get('percentual_comissao', 0.0)
    if isinstance(percentual, str):
        try:
            percentual = float(percentual) if percentual else 0.0
        except ValueError:
            percentual = 0.0
    
    usuario = Usuario(
        nome=data['nome'],
        email=data['email'],
        senha_hash=hash_senha(senha),
        tipo=tipo,
        perfil_id=int(data['perfil_id']),
        ativo=ativo,
        telefone=data.get('telefone'),
        cpf=data.get('cpf'),
        percentual_comissao=percentual,
        criado_por=admin_id
    )
    
    db.session.add(usuario)
    db.session.flush()
    
    if 'foto' in request.files:
        file = request.files['foto']
        if file and file.filename and allowed_file(file.filename):
            foto_bytes = file.read()
            usuario.foto_data = foto_bytes
            usuario.foto_mimetype = file.content_type or 'image/jpeg'
            filename = secure_filename(f"usuario_{usuario.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{file.filename.rsplit('.', 1)[1].lower()}")
            usuario.foto_path = f"usuarios/{filename}"
    
    if perfil.nome == 'Motorista':
        cpf_limpo = (data.get('cpf') or '').replace('.', '').replace('-', '')
        motorista = Motorista(
            usuario_id=usuario.id,
            nome=usuario.nome,
            cpf=cpf_limpo,
            telefone=data.get('telefone'),
            email=usuario.email,
            ativo=usuario.ativo,
            criado_por=admin_id
        )
        db.session.add(motorista)
    
    db.session.commit()
    
    registrar_criacao(admin_id, 'Usuario', usuario.id, {
        'nome': usuario.nome,
        'email': usuario.email,
        'perfil': perfil.nome,
        'percentual_comissao': usuario.percentual_comissao,
        'ativo': usuario.ativo,
        'foto_path': usuario.foto_path
    })
    
    return jsonify(usuario.to_dict()), 201

@bp.route('/usuarios/<int:id>', methods=['PUT'])
@admin_required
def atualizar_usuario_rh(id):
    admin_id = get_jwt_identity()
    usuario = Usuario.query.get(id)
    
    if not usuario:
        return jsonify({'erro': 'Usuário não encontrado'}), 404
    
    if request.content_type and 'multipart/form-data' in request.content_type:
        data = request.form.to_dict()
    else:
        data = request.get_json() or {}
    
    alteracoes = {'antes': {}, 'depois': {}}
    
    if data.get('nome'):
        alteracoes['antes']['nome'] = usuario.nome
        usuario.nome = data['nome']
        alteracoes['depois']['nome'] = data['nome']
    
    if data.get('email'):
        if data['email'] != usuario.email:
            existente = Usuario.query.filter_by(email=data['email']).first()
            if existente:
                return jsonify({'erro': 'Email já está em uso'}), 400
        alteracoes['antes']['email'] = usuario.email
        usuario.email = data['email']
        alteracoes['depois']['email'] = data['email']
    
    if data.get('senha'):
        usuario.senha_hash = hash_senha(data['senha'])
        alteracoes['depois']['senha_alterada'] = True
    
    novo_perfil = None
    if data.get('perfil_id'):
        perfil = Perfil.query.get(int(data['perfil_id']))
        if not perfil:
            return jsonify({'erro': 'Perfil não encontrado'}), 404
        
        alteracoes['antes']['perfil'] = usuario.perfil.nome if usuario.perfil else None
        usuario.perfil_id = int(data['perfil_id'])
        
        if perfil.nome == 'Administrador':
            usuario.tipo = 'admin'
        elif perfil.nome == 'Motorista':
            usuario.tipo = 'motorista'
        else:
            usuario.tipo = 'funcionario'
        
        alteracoes['depois']['perfil'] = perfil.nome
        novo_perfil = perfil
    
    if 'ativo' in data:
        ativo = data['ativo']
        if isinstance(ativo, str):
            ativo = ativo.lower() in ('true', '1', 'yes', 'on')
        alteracoes['antes']['ativo'] = usuario.ativo
        usuario.ativo = ativo
        alteracoes['depois']['ativo'] = ativo
    
    if 'telefone' in data:
        alteracoes['antes']['telefone'] = usuario.telefone
        usuario.telefone = data['telefone']
        alteracoes['depois']['telefone'] = data['telefone']
    
    if 'cpf' in data:
        alteracoes['antes']['cpf'] = usuario.cpf
        usuario.cpf = data['cpf']
        alteracoes['depois']['cpf'] = data['cpf']
    
    if 'percentual_comissao' in data:
        percentual = data['percentual_comissao']
        if isinstance(percentual, str):
            try:
                percentual = float(percentual) if percentual else 0.0
            except ValueError:
                percentual = 0.0
        alteracoes['antes']['percentual_comissao'] = usuario.percentual_comissao
        usuario.percentual_comissao = percentual
        alteracoes['depois']['percentual_comissao'] = percentual
    
    if 'foto' in request.files:
        file = request.files['foto']
        if file and file.filename and allowed_file(file.filename):
            # Salvar imagem no banco de dados (Railway-friendly)
            foto_bytes = file.read()
            
            alteracoes['antes']['foto_path'] = usuario.foto_path
            
            usuario.foto_data = foto_bytes
            usuario.foto_mimetype = file.content_type or 'image/jpeg'
            filename = secure_filename(f"usuario_{id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{file.filename.rsplit('.', 1)[1].lower()}")
            usuario.foto_path = f"usuarios/{filename}"
            
            alteracoes['depois']['foto_path'] = usuario.foto_path
    
    if novo_perfil and novo_perfil.nome == 'Motorista':
        motorista_existente = Motorista.query.filter_by(usuario_id=usuario.id).first()
        if not motorista_existente:
            cpf_limpo = (usuario.cpf or '').replace('.', '').replace('-', '')
            motorista = Motorista(
                usuario_id=usuario.id,
                nome=usuario.nome,
                cpf=cpf_limpo,
                telefone=usuario.telefone,
                email=usuario.email,
                ativo=usuario.ativo,
                criado_por=admin_id
            )
            db.session.add(motorista)
        else:
            motorista_existente.nome = usuario.nome
            motorista_existente.email = usuario.email
            motorista_existente.telefone = usuario.telefone
            motorista_existente.ativo = usuario.ativo
            if usuario.cpf:
                motorista_existente.cpf = usuario.cpf.replace('.', '').replace('-', '')
    
    db.session.commit()
    
    registrar_atualizacao(admin_id, 'Usuario', usuario.id, alteracoes)
    
    return jsonify(usuario.to_dict()), 200

@bp.route('/usuarios/<int:id>', methods=['DELETE'])
@admin_required
def deletar_usuario_rh(id):
    admin_id = get_jwt_identity()
    usuario = Usuario.query.get(id)
    
    if not usuario:
        return jsonify({'erro': 'Usuário não encontrado'}), 404
    
    if usuario.tipo == 'admin':
        admins = Usuario.query.filter_by(tipo='admin').count()
        if admins <= 1:
            return jsonify({'erro': 'Não é possível deletar o único administrador do sistema'}), 400
    
    registrar_exclusao(admin_id, 'Usuario', usuario.id, {
        'nome': usuario.nome,
        'email': usuario.email,
        'perfil': usuario.perfil.nome if usuario.perfil else None
    })
    
    db.session.delete(usuario)
    db.session.commit()
    
    return jsonify({'mensagem': 'Usuário deletado com sucesso'}), 200

@bp.route('/usuarios/<int:id>/foto', methods=['POST'])
@admin_required
def upload_foto_usuario(id):
    admin_id = get_jwt_identity()
    usuario = Usuario.query.get(id)
    
    if not usuario:
        return jsonify({'erro': 'Usuário não encontrado'}), 404
    
    if 'foto' not in request.files:
        return jsonify({'erro': 'Nenhuma foto enviada'}), 400
    
    file = request.files['foto']
    
    if file.filename == '':
        return jsonify({'erro': 'Nenhum arquivo selecionado'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'erro': 'Tipo de arquivo não permitido. Use PNG, JPG, JPEG, GIF ou WEBP'}), 400
    
    # Salvar imagem no banco de dados (Railway-friendly)
    foto_bytes = file.read()
    foto_anterior = usuario.foto_path
    
    usuario.foto_data = foto_bytes
    usuario.foto_mimetype = file.content_type or 'image/jpeg'
    filename = secure_filename(f"usuario_{id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{file.filename.rsplit('.', 1)[1].lower()}")
    usuario.foto_path = f"usuarios/{filename}"
    
    db.session.commit()
    
    registrar_atualizacao(admin_id, 'Usuario', usuario.id, {
        'antes': {'foto_path': foto_anterior},
        'depois': {'foto_path': usuario.foto_path}
    })
    
    return jsonify({
        'mensagem': 'Foto atualizada com sucesso',
        'foto_path': usuario.foto_path
    }), 200

@bp.route('/usuarios/<int:id>/foto', methods=['DELETE'])
@admin_required
def remover_foto_usuario(id):
    admin_id = get_jwt_identity()
    usuario = Usuario.query.get(id)
    
    if not usuario:
        return jsonify({'erro': 'Usuário não encontrado'}), 404
    
    foto_anterior = usuario.foto_path
    usuario.foto_path = None
    usuario.foto_data = None
    usuario.foto_mimetype = None
    db.session.commit()
    
    registrar_atualizacao(admin_id, 'Usuario', usuario.id, {
        'antes': {'foto_path': foto_anterior},
        'depois': {'foto_path': None}
    })
    
    return jsonify({'mensagem': 'Foto removida com sucesso'}), 200

@bp.route('/comissoes/usuario/<int:usuario_id>', methods=['GET'])
@admin_required
def calcular_comissao_usuario(usuario_id):
    usuario = Usuario.query.get(usuario_id)
    if not usuario:
        return jsonify({'erro': 'Usuário não encontrado'}), 404
    
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    fornecedor_id = request.args.get('fornecedor_id')
    
    query = Solicitacao.query.filter(
        Solicitacao.funcionario_id == usuario_id,
        Solicitacao.status == 'aprovada'
    )
    
    if data_inicio:
        try:
            dt_inicio = datetime.strptime(data_inicio, '%Y-%m-%d')
            query = query.filter(Solicitacao.data_envio >= dt_inicio)
        except ValueError:
            pass
    
    if data_fim:
        try:
            dt_fim = datetime.strptime(data_fim, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(Solicitacao.data_envio < dt_fim)
        except ValueError:
            pass
    
    if fornecedor_id:
        query = query.filter(Solicitacao.fornecedor_id == int(fornecedor_id))
    
    solicitacoes = query.all()
    
    percentual = usuario.percentual_comissao or 0.0
    
    solicitacoes_data = []
    total_valor = 0.0
    total_comissao = 0.0
    
    for sol in solicitacoes:
        valor_solicitacao = 0.0
        if sol.itens:
            for item in sol.itens:
                valor_item = item.valor_calculado if item.valor_calculado else 0.0
                if valor_item == 0 and item.peso_kg and item.preco_por_kg_snapshot:
                    valor_item = float(item.peso_kg) * float(item.preco_por_kg_snapshot)
                valor_solicitacao += valor_item
        
        comissao = valor_solicitacao * (percentual / 100)
        
        total_valor += valor_solicitacao
        total_comissao += comissao
        
        solicitacoes_data.append({
            'id': sol.id,
            'data_envio': sol.data_envio.isoformat() if sol.data_envio else None,
            'data_confirmacao': sol.data_confirmacao.isoformat() if sol.data_confirmacao else None,
            'fornecedor_id': sol.fornecedor_id,
            'fornecedor_nome': sol.fornecedor.nome if sol.fornecedor else None,
            'valor_total': round(valor_solicitacao, 2),
            'comissao': round(comissao, 2),
            'status': sol.status
        })
    
    return jsonify({
        'usuario': usuario.to_dict(),
        'percentual_comissao': percentual,
        'total_solicitacoes': len(solicitacoes),
        'total_valor': round(total_valor, 2),
        'total_comissao': round(total_comissao, 2),
        'solicitacoes': solicitacoes_data
    }), 200

@bp.route('/comissoes/resumo', methods=['GET'])
@admin_required
def resumo_comissoes():
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    
    usuarios = Usuario.query.filter(Usuario.percentual_comissao > 0).all()
    
    resumo = []
    
    for usuario in usuarios:
        query = Solicitacao.query.filter(
            Solicitacao.funcionario_id == usuario.id,
            Solicitacao.status == 'aprovada'
        )
        
        if data_inicio:
            try:
                dt_inicio = datetime.strptime(data_inicio, '%Y-%m-%d')
                query = query.filter(Solicitacao.data_envio >= dt_inicio)
            except ValueError:
                pass
        
        if data_fim:
            try:
                dt_fim = datetime.strptime(data_fim, '%Y-%m-%d') + timedelta(days=1)
                query = query.filter(Solicitacao.data_envio < dt_fim)
            except ValueError:
                pass
        
        solicitacoes = query.all()
        
        total_valor = 0.0
        for sol in solicitacoes:
            valor_solicitacao = 0.0
            if sol.itens:
                for item in sol.itens:
                    valor_item = item.valor_calculado if item.valor_calculado else 0.0
                    if valor_item == 0 and item.peso_kg and item.preco_por_kg_snapshot:
                        valor_item = float(item.peso_kg) * float(item.preco_por_kg_snapshot)
                    valor_solicitacao += valor_item
            total_valor += valor_solicitacao
        
        comissao = total_valor * (usuario.percentual_comissao / 100)
        
        resumo.append({
            'usuario_id': usuario.id,
            'usuario_nome': usuario.nome,
            'perfil': usuario.perfil.nome if usuario.perfil else None,
            'percentual_comissao': usuario.percentual_comissao,
            'total_solicitacoes': len(solicitacoes),
            'total_valor': round(total_valor, 2),
            'total_comissao': round(comissao, 2)
        })
    
    resumo.sort(key=lambda x: x['total_comissao'], reverse=True)
    
    return jsonify({
        'resumo': resumo,
        'total_geral_comissoes': round(sum(r['total_comissao'] for r in resumo), 2)
    }), 200

@bp.route('/comissoes/exportar', methods=['GET'])
@admin_required
def exportar_comissoes():
    try:
        import pandas as pd
        from io import BytesIO
    except ImportError:
        return jsonify({'erro': 'Biblioteca pandas não disponível'}), 500
    
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    usuario_id = request.args.get('usuario_id')
    formato = request.args.get('formato', 'xlsx')
    
    query = Solicitacao.query.filter(Solicitacao.status == 'aprovada')
    
    if usuario_id:
        query = query.filter(Solicitacao.funcionario_id == int(usuario_id))
    
    if data_inicio:
        try:
            dt_inicio = datetime.strptime(data_inicio, '%Y-%m-%d')
            query = query.filter(Solicitacao.data_envio >= dt_inicio)
        except ValueError:
            pass
    
    if data_fim:
        try:
            dt_fim = datetime.strptime(data_fim, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(Solicitacao.data_envio < dt_fim)
        except ValueError:
            pass
    
    solicitacoes = query.all()
    
    dados = []
    for sol in solicitacoes:
        usuario = sol.funcionario
        percentual = usuario.percentual_comissao or 0.0
        valor_total = 0.0
        if sol.itens:
            for item in sol.itens:
                valor_item = item.valor_calculado if item.valor_calculado else 0.0
                if valor_item == 0 and item.peso_kg and item.preco_por_kg_snapshot:
                    valor_item = float(item.peso_kg) * float(item.preco_por_kg_snapshot)
                valor_total += valor_item
        comissao = valor_total * (percentual / 100)
        
        dados.append({
            'ID Solicitação': sol.id,
            'Data': sol.data_envio.strftime('%d/%m/%Y') if sol.data_envio else '',
            'Funcionário': usuario.nome if usuario else '',
            'Email': usuario.email if usuario else '',
            'Perfil': usuario.perfil.nome if usuario and usuario.perfil else '',
            'Fornecedor': sol.fornecedor.nome if sol.fornecedor else '',
            'Valor Total (R$)': round(valor_total, 2),
            '% Comissão': percentual,
            'Comissão (R$)': round(comissao, 2)
        })
    
    df = pd.DataFrame(dados)
    
    output = BytesIO()
    
    if formato == 'csv':
        df.to_csv(output, index=False, encoding='utf-8-sig')
        output.seek(0)
        mimetype = 'text/csv'
        filename = f'relatorio_comissoes_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    else:
        df.to_excel(output, index=False, engine='openpyxl')
        output.seek(0)
        mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        filename = f'relatorio_comissoes_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    
    return send_file(
        output,
        mimetype=mimetype,
        as_attachment=True,
        download_name=filename
    )

@bp.route('/auditoria/usuarios', methods=['GET'])
@admin_required
def auditoria_usuarios():
    usuario_id = request.args.get('usuario_id')
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    limite = request.args.get('limite', 100, type=int)
    
    query = AuditoriaLog.query.filter(AuditoriaLog.entidade_tipo == 'Usuario')
    
    if usuario_id:
        query = query.filter(AuditoriaLog.entidade_id == int(usuario_id))
    
    if data_inicio:
        try:
            dt_inicio = datetime.strptime(data_inicio, '%Y-%m-%d')
            query = query.filter(AuditoriaLog.data_acao >= dt_inicio)
        except ValueError:
            pass
    
    if data_fim:
        try:
            dt_fim = datetime.strptime(data_fim, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(AuditoriaLog.data_acao < dt_fim)
        except ValueError:
            pass
    
    logs = query.order_by(AuditoriaLog.data_acao.desc()).limit(limite).all()
    
    return jsonify([log.to_dict() for log in logs]), 200

@bp.route('/perfis', methods=['GET'])
@admin_required
def listar_perfis():
    perfis = Perfil.query.filter_by(ativo=True).order_by(Perfil.id).all()
    print(f"📋 Listando {len(perfis)} perfis para o RH. IDs: {[p.id for p in perfis]}")
    return jsonify([p.to_dict() for p in perfis]), 200

@bp.route('/fornecedores', methods=['GET'])
@admin_required
def listar_fornecedores_rh():
    fornecedores = Fornecedor.query.filter_by(ativo=True).all()
    return jsonify([{'id': f.id, 'nome': f.nome} for f in fornecedores]), 200

@bp.route('/fornecedores/compradores', methods=['GET'])
@admin_required
def listar_fornecedores_compradores():
    busca = request.args.get('busca', '')
    
    query = Fornecedor.query.filter_by(ativo=True)
    
    if busca:
        query = query.filter(
            db.or_(
                Fornecedor.nome.ilike(f'%{busca}%'),
                Fornecedor.cnpj.ilike(f'%{busca}%'),
                Fornecedor.cpf.ilike(f'%{busca}%')
            )
        )
    
    fornecedores = query.order_by(Fornecedor.nome).all()
    
    resultado = []
    for f in fornecedores:
        resultado.append({
            'id': f.id,
            'nome': f.nome,
            'cnpj': f.cnpj,
            'cpf': f.cpf,
            'tipo_documento': f.tipo_documento,
            'cidade': f.cidade,
            'estado': f.estado,
            'criado_por_id': f.criado_por_id,
            'criado_por_nome': f.criado_por.nome if f.criado_por else None,
            'comprador_responsavel_id': f.comprador_responsavel_id,
            'comprador_responsavel_nome': f.comprador_responsavel.nome if f.comprador_responsavel else None,
            'data_cadastro': f.data_cadastro.isoformat() if f.data_cadastro else None
        })
    
    return jsonify(resultado), 200

@bp.route('/fornecedores/<int:id>/comprador', methods=['PUT'])
@admin_required
def atualizar_comprador_fornecedor(id):
    admin_id = get_jwt_identity()
    
    fornecedor = Fornecedor.query.get(id)
    if not fornecedor:
        return jsonify({'erro': 'Fornecedor não encontrado'}), 404
    
    data = request.get_json() or {}
    comprador_id = data.get('comprador_responsavel_id')
    
    comprador_anterior = fornecedor.comprador_responsavel.nome if fornecedor.comprador_responsavel else None
    comprador_anterior_id = fornecedor.comprador_responsavel_id
    
    if comprador_id is None or comprador_id == '' or comprador_id == 0:
        fornecedor.comprador_responsavel_id = None
        comprador_novo = None
    else:
        comprador = Usuario.query.get(comprador_id)
        if not comprador:
            return jsonify({'erro': 'Comprador não encontrado'}), 404
        fornecedor.comprador_responsavel_id = comprador_id
        comprador_novo = comprador.nome
    
    db.session.commit()
    
    registrar_atualizacao(admin_id, 'Fornecedor', fornecedor.id, {
        'antes': {'comprador_responsavel': comprador_anterior, 'comprador_responsavel_id': comprador_anterior_id},
        'depois': {'comprador_responsavel': comprador_novo, 'comprador_responsavel_id': fornecedor.comprador_responsavel_id}
    })
    
    return jsonify({
        'mensagem': 'Comprador atualizado com sucesso',
        'fornecedor_id': fornecedor.id,
        'comprador_responsavel_id': fornecedor.comprador_responsavel_id,
        'comprador_responsavel_nome': comprador_novo
    }), 200

@bp.route('/compradores', methods=['GET'])
@admin_required
def listar_compradores():
    perfis_comprador = Perfil.query.filter(
        db.or_(
            Perfil.nome.ilike('%comprador%'),
            Perfil.nome.ilike('%gestor%'),
            Perfil.nome.ilike('%producao%'),
            Perfil.nome.ilike('%produção%')
        )
    ).all()
    
    ids_perfis = [p.id for p in perfis_comprador]
    
    if ids_perfis:
        compradores = Usuario.query.filter(
            Usuario.ativo == True,
            db.or_(
                Usuario.perfil_id.in_(ids_perfis),
                Usuario.tipo == 'admin'
            )
        ).order_by(Usuario.nome).all()
    else:
        compradores = Usuario.query.filter(
            Usuario.ativo == True,
            Usuario.tipo.in_(['admin', 'funcionario'])
        ).order_by(Usuario.nome).all()
    
    return jsonify([{
        'id': c.id,
        'nome': c.nome,
        'email': c.email,
        'perfil': c.perfil.nome if c.perfil else None
    } for c in compradores]), 200

@bp.route('/dashboard', methods=['GET'])
@admin_required
def dashboard_rh():
    total_usuarios = Usuario.query.count()
    usuarios_ativos = Usuario.query.filter_by(ativo=True).count()
    usuarios_inativos = Usuario.query.filter_by(ativo=False).count()
    usuarios_com_comissao = Usuario.query.filter(Usuario.percentual_comissao > 0).count()
    
    mes_atual = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    proximo_mes = (mes_atual + timedelta(days=32)).replace(day=1)
    
    solicitacoes_mes = Solicitacao.query.filter(
        Solicitacao.status == 'aprovada',
        Solicitacao.data_envio >= mes_atual,
        Solicitacao.data_envio < proximo_mes
    ).all()
    
    total_valor_mes = 0.0
    total_comissao_mes = 0.0
    
    for sol in solicitacoes_mes:
        valor = 0.0
        if sol.itens:
            for item in sol.itens:
                valor_item = item.valor_calculado if item.valor_calculado else 0.0
                if valor_item == 0 and item.peso_kg and item.preco_por_kg_snapshot:
                    valor_item = float(item.peso_kg) * float(item.preco_por_kg_snapshot)
                valor += valor_item
        total_valor_mes += valor
        if sol.funcionario and sol.funcionario.percentual_comissao:
            total_comissao_mes += valor * (sol.funcionario.percentual_comissao / 100)
    
    por_perfil = db.session.query(
        Perfil.nome,
        func.count(Usuario.id)
    ).join(Usuario, Usuario.perfil_id == Perfil.id).group_by(Perfil.nome).all()
    
    return jsonify({
        'total_usuarios': total_usuarios,
        'usuarios_ativos': usuarios_ativos,
        'usuarios_inativos': usuarios_inativos,
        'usuarios_com_comissao': usuarios_com_comissao,
        'total_valor_mes': round(total_valor_mes, 2),
        'total_comissao_mes': round(total_comissao_mes, 2),
        'solicitacoes_aprovadas_mes': len(solicitacoes_mes),
        'usuarios_por_perfil': [{'perfil': p[0], 'quantidade': p[1]} for p in por_perfil]
    }), 200
