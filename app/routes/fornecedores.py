from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import Fornecedor, FornecedorTipoLotePreco, FornecedorTipoLoteClassificacao, Vendedor, TipoLote, Usuario, FornecedorFuncionarioAtribuicao, db
from app.auth import admin_required
import requests
import re
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('fornecedores', __name__, url_prefix='/api/fornecedores')

def normalizar_cnpj(cnpj):
    if not cnpj:
        return None
    return re.sub(r'[^\d]', '', cnpj)

def normalizar_cpf(cpf):
    if not cpf:
        return None
    return re.sub(r'[^\d]', '', cpf)

def validar_cnpj(cnpj):
    cnpj = normalizar_cnpj(cnpj)
    if not cnpj or len(cnpj) != 14:
        return False
    if cnpj == cnpj[0] * 14:
        return False
    return True

def validar_cpf(cpf):
    cpf = normalizar_cpf(cpf)
    if not cpf or len(cpf) != 11:
        return False
    if cpf == cpf[0] * 11:
        return False
    return True

def verificar_acesso_fornecedor(fornecedor_id, usuario_id):
    """Verifica se o usuário tem acesso ao fornecedor (é comprador responsável ou criador)"""
    usuario = Usuario.query.get(usuario_id)
    
    if not usuario:
        return False
    
    # Admin tem acesso total
    if usuario.tipo == 'admin':
        return True
    
    # Auditor tem acesso total de leitura
    if usuario.perfil and usuario.perfil.nome == 'Auditoria / BI':
        return True
    
    fornecedor = Fornecedor.query.get(fornecedor_id)
    if not fornecedor:
        return False
    
    # Comprador tem acesso se:
    # 1. For o comprador responsável (comprador_responsavel_id)
    # 2. Foi quem criou o fornecedor (criado_por_id)
    # 3. Tem tabela de preços aprovada (para criar solicitações)
    tem_acesso = (
        fornecedor.comprador_responsavel_id == usuario_id or 
        fornecedor.criado_por_id == usuario_id or
        (usuario.perfil and usuario.perfil.nome in ['Comprador (PJ)', 'Producao', 'Produção'])
    )
    
    return tem_acesso

def verificar_conflito_endereco(rua, numero, cidade, estado, cep, fornecedor_id_excluir=None):
    """
    Verifica se já existe um fornecedor com o mesmo endereço.
    Retorna o fornecedor conflitante e o nome do comprador responsável, ou None se não houver conflito.
    
    Args:
        rua: Rua/logradouro
        numero: Número do endereço
        cidade: Cidade
        estado: Estado (UF)
        cep: CEP (será normalizado)
        fornecedor_id_excluir: ID do fornecedor a excluir da busca (para edição)
    
    Returns:
        dict com informações do conflito ou None
    """
    if not rua or not cidade or not estado:
        return None
    
    cep_normalizado = re.sub(r'[^\d]', '', cep) if cep else None
    rua_normalizada = rua.strip().lower() if rua else ''
    numero_normalizado = str(numero).strip() if numero else ''
    cidade_normalizada = cidade.strip().lower() if cidade else ''
    estado_normalizado = estado.strip().upper() if estado else ''
    
    query = Fornecedor.query.filter(
        Fornecedor.ativo == True
    )
    
    if fornecedor_id_excluir:
        query = query.filter(Fornecedor.id != fornecedor_id_excluir)
    
    fornecedores = query.all()
    
    for fornecedor in fornecedores:
        fornecedor_rua = (fornecedor.rua or '').strip().lower()
        fornecedor_numero = str(fornecedor.numero or '').strip()
        fornecedor_cidade = (fornecedor.cidade or '').strip().lower()
        fornecedor_estado = (fornecedor.estado or '').strip().upper()
        fornecedor_cep = re.sub(r'[^\d]', '', fornecedor.cep) if fornecedor.cep else None
        
        endereco_igual = (
            rua_normalizada == fornecedor_rua and
            numero_normalizado == fornecedor_numero and
            cidade_normalizada == fornecedor_cidade and
            estado_normalizado == fornecedor_estado
        )
        
        if cep_normalizado and fornecedor_cep:
            endereco_igual = endereco_igual or (
                cep_normalizado == fornecedor_cep and
                numero_normalizado == fornecedor_numero
            )
        
        if endereco_igual:
            comprador_nome = 'Não atribuído'
            if fornecedor.comprador_responsavel_id:
                comprador = Usuario.query.get(fornecedor.comprador_responsavel_id)
                if comprador:
                    comprador_nome = comprador.nome
            
            mensagem = f'CNPJ já cadastrado\n'
            mensagem += f'Fornecedor: {fornecedor.nome}\n'
            mensagem += f'Comprador Responsável: {comprador_nome}\n'
            mensagem += f'Endereço: {fornecedor.rua}, {fornecedor.numero} - {fornecedor.cidade}/{fornecedor.estado}'
            
            return {
                'conflito': True,
                'fornecedor_id': fornecedor.id,
                'fornecedor_nome': fornecedor.nome,
                'comprador_responsavel': comprador_nome,
                'mensagem': mensagem
            }
    
    return None

@bp.route('/verificar-endereco', methods=['POST'])
@jwt_required()
def verificar_endereco():
    """Endpoint para verificar conflito de endereço antes de cadastrar"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'erro': 'Dados não fornecidos'}), 400
        
        conflito = verificar_conflito_endereco(
            rua=data.get('rua'),
            numero=data.get('numero'),
            cidade=data.get('cidade'),
            estado=data.get('estado'),
            cep=data.get('cep'),
            fornecedor_id_excluir=data.get('fornecedor_id')
        )
        
        if conflito:
            return jsonify(conflito), 409
        
        return jsonify({'conflito': False}), 200
        
    except Exception as e:
        logger.error(f'Erro ao verificar endereço: {str(e)}')
        return jsonify({'erro': f'Erro ao verificar endereço: {str(e)}'}), 500

@bp.route('/buscar-cep/<cep>', methods=['GET'])
@jwt_required()
def buscar_cep(cep):
    """Busca informações de endereço pelo CEP usando a API ViaCEP"""
    try:
        # Remove formatação do CEP
        cep_limpo = re.sub(r'[^\d]', '', cep)
        
        # Valida formato do CEP
        if not cep_limpo or len(cep_limpo) != 8:
            return jsonify({'erro': 'CEP inválido. O CEP deve conter 8 dígitos.'}), 400
        
        # Consulta API ViaCEP
        logger.info(f'Buscando CEP: {cep_limpo}')
        response = requests.get(f'https://viacep.com.br/ws/{cep_limpo}/json/', timeout=5)
        
        if response.status_code != 200:
            return jsonify({'erro': 'Erro ao consultar CEP. Tente novamente.'}), response.status_code
        
        dados = response.json()
        
        # Verifica se o CEP foi encontrado
        if 'erro' in dados and dados['erro']:
            return jsonify({'erro': 'CEP não encontrado.'}), 404
        
        # Verificar conflito de endereço após buscar CEP
        conflito = verificar_conflito_endereco(
            rua=dados.get('logradouro'),
            numero='',  # Não temos número ainda
            cidade=dados.get('localidade'),
            estado=dados.get('uf'),
            cep=dados.get('cep')
        )
        
        if conflito:
            return jsonify({
                'erro': conflito['mensagem'],
                'conflito_endereco': conflito
            }), 409
        
        # Retorna dados formatados
        return jsonify({
            'cep': dados.get('cep'),
            'rua': dados.get('logradouro'),
            'bairro': dados.get('bairro'),
            'cidade': dados.get('localidade'),
            'estado': dados.get('uf'),
            'complemento': dados.get('complemento', '')
        }), 200
        
    except requests.exceptions.Timeout:
        logger.error('Timeout ao buscar CEP')
        return jsonify({'erro': 'Tempo limite excedido ao buscar CEP. Tente novamente.'}), 408
    except requests.exceptions.RequestException as e:
        logger.error(f'Erro na requisição ViaCEP: {str(e)}')
        return jsonify({'erro': 'Erro ao consultar serviço de CEP. Tente novamente mais tarde.'}), 500
    except Exception as e:
        logger.error(f'Erro ao buscar CEP: {str(e)}')
        return jsonify({'erro': f'Erro interno ao buscar CEP: {str(e)}'}), 500

@bp.route('', methods=['GET'])
@jwt_required()
def listar_fornecedores():
    try:
        usuario_id = get_jwt_identity()
        usuario = Usuario.query.get(usuario_id)
        
        if not usuario:
            return jsonify({'erro': 'Usuário não encontrado'}), 404
        
        busca = request.args.get('busca', '')
        vendedor_id = request.args.get('vendedor_id', type=int)
        cidade = request.args.get('cidade', '')
        forma_pagamento = request.args.get('forma_pagamento', '')
        condicao_pagamento = request.args.get('condicao_pagamento', '')
        
        query = Fornecedor.query
        
        # Auditor tem acesso total aos fornecedores (somente leitura)
        if usuario.tipo == 'funcionario' and usuario.perfil and usuario.perfil.nome != 'Auditoria / BI':
            # Comprador vê apenas fornecedores onde ele é o comprador responsável
            query = query.filter(
                Fornecedor.comprador_responsavel_id == usuario_id
            )
        
        if busca:
            query = query.filter(
                db.or_(
                    Fornecedor.nome.ilike(f'%{busca}%'),
                    Fornecedor.nome_social.ilike(f'%{busca}%'),
                    Fornecedor.cnpj.ilike(f'%{busca}%'),
                    Fornecedor.cpf.ilike(f'%{busca}%'),
                    Fornecedor.email.ilike(f'%{busca}%')
                )
            )
        
        if vendedor_id:
            query = query.filter_by(vendedor_id=vendedor_id)
        
        if cidade:
            query = query.filter(Fornecedor.cidade.ilike(f'%{cidade}%'))
        
        if forma_pagamento:
            query = query.filter_by(forma_pagamento=forma_pagamento)
        
        if condicao_pagamento:
            query = query.filter_by(condicao_pagamento=condicao_pagamento)
        
        fornecedores = query.order_by(Fornecedor.nome).all()
        return jsonify([fornecedor.to_dict() for fornecedor in fornecedores]), 200
    
    except Exception as e:
        return jsonify({'erro': f'Erro ao listar fornecedores: {str(e)}'}), 500

@bp.route('/<int:id>', methods=['GET'])
@jwt_required()
def obter_fornecedor(id):
    try:
        usuario_id = get_jwt_identity()
        usuario = Usuario.query.get(usuario_id)
        
        print(f"\n{'='*60}")
        print(f" ENDPOINT: GET /fornecedores/{id}")
        print(f"{'='*60}")
        print(f"   Usuário ID: {usuario_id}")
        print(f"   Usuário: {usuario.nome if usuario else 'N/A'}")
        print(f"   Tipo: {usuario.tipo if usuario else 'N/A'}")
        
        if not usuario:
            print(f"   ❌ Usuário não encontrado")
            return jsonify({'erro': 'Usuário não encontrado'}), 404
        
        fornecedor = Fornecedor.query.get(id)
        
        if not fornecedor:
            print(f"   ❌ Fornecedor não encontrado")
            return jsonify({'erro': 'Fornecedor não encontrado'}), 404
        
        print(f"   Fornecedor: {fornecedor.nome}")
        print(f"   Criado por ID: {fornecedor.criado_por_id}")
        print(f"   Comprador responsável ID: {fornecedor.comprador_responsavel_id}")
        
        # Verificar acesso
        tem_acesso = verificar_acesso_fornecedor(id, usuario_id)
        print(f"   Tem acesso: {tem_acesso}")
        
        if not tem_acesso:
            print(f"   ❌ Acesso negado - Usuário {usuario_id} não tem permissão")
            return jsonify({'erro': 'Você não tem permissão para acessar este fornecedor'}), 403
        
        print(f"   ✅ Acesso permitido")
        
        fornecedor_dict = fornecedor.to_dict()
        fornecedor_dict['classificacoes'] = [classif.to_dict() for classif in fornecedor.classificacoes_tipo_lote]
        fornecedor_dict['precos'] = [preco.to_dict() for preco in fornecedor.precos]
        fornecedor_dict['total_solicitacoes'] = len(fornecedor.solicitacoes)
        fornecedor_dict['total_lotes'] = len(fornecedor.lotes)
        
        print(f"   ✅ Dados do fornecedor retornados com sucesso")
        print(f"{'='*60}\n")
        
        return jsonify(fornecedor_dict), 200
    
    except Exception as e:
        print(f"   ❌ ERRO: {str(e)}")
        print(f"{'='*60}\n")
        import traceback
        traceback.print_exc()
        return jsonify({'erro': f'Erro ao obter fornecedor: {str(e)}'}), 500

@bp.route('', methods=['POST'])
@jwt_required()
def criar_fornecedor():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'erro': 'Dados não fornecidos'}), 400
        
        if not data.get('nome'):
            return jsonify({'erro': 'Nome é obrigatório'}), 400
        
        if not data.get('cnpj') and not data.get('cpf'):
            return jsonify({'erro': 'CNPJ ou CPF é obrigatório'}), 400
        
        # VERIFICAR CONFLITO DE ENDEREÇO PRIMEIRO (antes de validar CNPJ/CPF)
        conflito = verificar_conflito_endereco(
            rua=data.get('rua'),
            numero=data.get('numero'),
            cidade=data.get('cidade'),
            estado=data.get('estado'),
            cep=data.get('cep')
        )
        
        if conflito:
            return jsonify({
                'erro': conflito['mensagem'],
                'conflito_endereco': conflito
            }), 409
        
        cnpj_normalizado = None
        cpf_normalizado = None
        
        if data.get('cnpj'):
            cnpj_normalizado = normalizar_cnpj(data['cnpj'])
            if not validar_cnpj(cnpj_normalizado):
                return jsonify({'erro': 'CNPJ inválido'}), 400
            
            fornecedor_existente = Fornecedor.query.filter_by(cnpj=cnpj_normalizado).first()
            if fornecedor_existente:
                return jsonify({'erro': 'CNPJ já cadastrado'}), 400
        
        if data.get('cpf'):
            cpf_normalizado = normalizar_cpf(data['cpf'])
            if not validar_cpf(cpf_normalizado):
                return jsonify({'erro': 'CPF inválido'}), 400
            
            fornecedor_existente = Fornecedor.query.filter_by(cpf=cpf_normalizado).first()
            if fornecedor_existente:
                return jsonify({'erro': 'CPF já cadastrado'}), 400
        
        if data.get('email'):
            email_existente = Fornecedor.query.filter_by(email=data['email']).first()
            if email_existente:
                return jsonify({'erro': 'E-mail já cadastrado para outro fornecedor'}), 400
        
        usuario_id = get_jwt_identity()
        usuario = Usuario.query.get(usuario_id)
        
        if not usuario:
            return jsonify({'erro': 'Usuário não encontrado'}), 404
        
        # Definir tabela de preços (padrão: 1 estrela)
        tabela_preco_id = 1  # Padrão para novos fornecedores
        
        # Apenas admin pode definir uma tabela diferente
        if usuario.tipo == 'admin' and 'tabela_preco_id' in data:
            tabela_id_req = data['tabela_preco_id']
            if tabela_id_req in [1, 2, 3]:
                tabela_preco_id = tabela_id_req
        
        # Definir comprador responsável
        comprador_responsavel_id = None
        if usuario.tipo == 'admin':
            # Admin pode escolher qualquer comprador
            if 'comprador_responsavel_id' in data and data['comprador_responsavel_id']:
                comprador_responsavel_id = data['comprador_responsavel_id']
        else:
            # Comprador se auto-atribui automaticamente
            comprador_responsavel_id = usuario_id
        
        # Determinar tipo de documento e validar
        tipo_doc = data.get('tipo_documento', 'cnpj' if cnpj_normalizado else 'cpf')
        
        # Validar se o documento do tipo selecionado está presente
        if tipo_doc == 'cpf':
            if not cpf_normalizado:
                return jsonify({'erro': 'CPF é obrigatório quando tipo de documento for CPF'}), 400
            cnpj_normalizado = None
        else:
            if not cnpj_normalizado:
                return jsonify({'erro': 'CNPJ é obrigatório quando tipo de documento for CNPJ'}), 400
            cpf_normalizado = None
        
        fornecedor = Fornecedor(
            nome=data['nome'],
            nome_social=data.get('nome_social', ''),
            tipo_documento=tipo_doc,
            cnpj=cnpj_normalizado,
            cpf=cpf_normalizado,
            tabela_preco_id=tabela_preco_id,
            comprador_responsavel_id=comprador_responsavel_id,
            rua=data.get('rua', ''),
            numero=data.get('numero', ''),
            cidade=data.get('cidade', ''),
            cep=data.get('cep', ''),
            estado=data.get('estado', ''),
            bairro=data.get('bairro', ''),
            complemento=data.get('complemento', ''),
            tem_outro_endereco=data.get('tem_outro_endereco', False),
            outro_rua=data.get('outro_rua', ''),
            outro_numero=data.get('outro_numero', ''),
            outro_cidade=data.get('outro_cidade', ''),
            outro_cep=data.get('outro_cep', ''),
            outro_estado=data.get('outro_estado', ''),
            outro_bairro=data.get('outro_bairro', ''),
            outro_complemento=data.get('outro_complemento', ''),
            telefone=data.get('telefone', ''),
            email=data.get('email', ''),
            vendedor_id=data.get('vendedor_id'),
            criado_por_id=usuario_id,
            conta_bancaria=data.get('conta_bancaria', ''),
            agencia=data.get('agencia', ''),
            chave_pix=data.get('chave_pix', ''),
            banco=data.get('banco', ''),
            condicao_pagamento=data.get('condicao_pagamento', 'avista'),
            forma_pagamento=data.get('forma_pagamento', 'pix'),
            observacoes=data.get('observacoes', '')
        )
        
        db.session.add(fornecedor)
        db.session.commit()
        
        # Processar tipos de lote selecionados com classificações (leve/médio/pesado)
        # Apenas admin pode definir estrelas
        if 'tipos_lote' in data and isinstance(data['tipos_lote'], list) and usuario.tipo == 'admin':
            for tipo_data in data['tipos_lote']:
                tipo_lote_id = tipo_data.get('tipo_lote_id')
                leve = tipo_data.get('leve_estrelas', 1)
                medio = tipo_data.get('medio_estrelas', 3)
                pesado = tipo_data.get('pesado_estrelas', 5)
                
                if tipo_lote_id:
                    tipo_lote = TipoLote.query.get(tipo_lote_id)
                    if tipo_lote:
                        classif_obj = FornecedorTipoLoteClassificacao(
                            fornecedor_id=fornecedor.id,
                            tipo_lote_id=tipo_lote_id,
                            leve_estrelas=leve,
                            medio_estrelas=medio,
                            pesado_estrelas=pesado
                        )
                        db.session.add(classif_obj)
            
            db.session.commit()
        
        # Processar preços (campo antigo, mantido para compatibilidade)
        # Apenas admin pode definir preços/estrelas
        elif 'precos' in data and isinstance(data['precos'], list) and usuario.tipo == 'admin':
            for preco_data in data['precos']:
                tipo_lote_id = preco_data.get('tipo_lote_id')
                estrelas = preco_data.get('estrelas', 3)
                preco_kg = preco_data.get('preco_por_kg', 0.0)
                
                if tipo_lote_id and 1 <= estrelas <= 5:
                    tipo_lote = TipoLote.query.get(tipo_lote_id)
                    if tipo_lote:
                        preco_obj = FornecedorTipoLotePreco(
                            fornecedor_id=fornecedor.id,
                            tipo_lote_id=tipo_lote_id,
                            estrelas=estrelas,
                            preco_por_kg=preco_kg
                        )
                        db.session.add(preco_obj)
            
            db.session.commit()
        
        return jsonify(fornecedor.to_dict()), 201
    
    except ValueError as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': f'Erro ao criar fornecedor: {str(e)}'}), 500

@bp.route('/<int:id>', methods=['PUT'])
@jwt_required()
def atualizar_fornecedor(id):
    try:
        usuario_id = get_jwt_identity()
        usuario = Usuario.query.get(usuario_id)
        
        if not usuario:
            return jsonify({'erro': 'Usuário não encontrado'}), 404
        
        fornecedor = Fornecedor.query.get(id)
        
        if not fornecedor:
            return jsonify({'erro': 'Fornecedor não encontrado'}), 404
        
        if usuario.tipo == 'funcionario':
            if not verificar_acesso_fornecedor(id, usuario_id):
                return jsonify({'erro': 'Acesso negado. Você não tem permissão para modificar este fornecedor.'}), 403
        
        data = request.get_json()
        
        if not data:
            return jsonify({'erro': 'Dados não fornecidos'}), 400
        
        if data.get('nome'):
            fornecedor.nome = data['nome']
        if 'nome_social' in data:
            fornecedor.nome_social = data['nome_social']
        
        # Atualizar tipo de documento e campos relacionados
        if 'tipo_documento' in data:
            tipo_doc = data['tipo_documento']
            
            # Processar CNPJ se for o tipo selecionado
            if tipo_doc == 'cnpj':
                if not ('cnpj' in data and data['cnpj']):
                    return jsonify({'erro': 'CNPJ é obrigatório quando tipo de documento for CNPJ'}), 400
                
                cnpj_normalizado = normalizar_cnpj(data['cnpj'])
                if not validar_cnpj(cnpj_normalizado):
                    return jsonify({'erro': 'CNPJ inválido'}), 400
                if cnpj_normalizado != fornecedor.cnpj:
                    existente = Fornecedor.query.filter_by(cnpj=cnpj_normalizado).first()
                    if existente:
                        return jsonify({'erro': 'CNPJ já cadastrado para outro fornecedor'}), 400
                    fornecedor.cnpj = cnpj_normalizado
                fornecedor.tipo_documento = 'cnpj'
                fornecedor.cpf = None  # Limpar CPF
            
            # Processar CPF se for o tipo selecionado
            elif tipo_doc == 'cpf':
                if not ('cpf' in data and data['cpf']):
                    return jsonify({'erro': 'CPF é obrigatório quando tipo de documento for CPF'}), 400
                
                cpf_normalizado = normalizar_cpf(data['cpf'])
                if not validar_cpf(cpf_normalizado):
                    return jsonify({'erro': 'CPF inválido'}), 400
                if cpf_normalizado != fornecedor.cpf:
                    existente = Fornecedor.query.filter_by(cpf=cpf_normalizado).first()
                    if existente:
                        return jsonify({'erro': 'CPF já cadastrado para outro fornecedor'}), 400
                    fornecedor.cpf = cpf_normalizado
                fornecedor.tipo_documento = 'cpf'
                fornecedor.cnpj = None  # Limpar CNPJ
        else:
            # Manter compatibilidade com lógica antiga
            if 'cnpj' in data and data['cnpj']:
                cnpj_normalizado = normalizar_cnpj(data['cnpj'])
                if not validar_cnpj(cnpj_normalizado):
                    return jsonify({'erro': 'CNPJ inválido'}), 400
                if cnpj_normalizado != fornecedor.cnpj:
                    existente = Fornecedor.query.filter_by(cnpj=cnpj_normalizado).first()
                    if existente:
                        return jsonify({'erro': 'CNPJ já cadastrado para outro fornecedor'}), 400
                    fornecedor.cnpj = cnpj_normalizado
            
            if 'cpf' in data and data['cpf']:
                cpf_normalizado = normalizar_cpf(data['cpf'])
                if not validar_cpf(cpf_normalizado):
                    return jsonify({'erro': 'CPF inválido'}), 400
                if cpf_normalizado != fornecedor.cpf:
                    existente = Fornecedor.query.filter_by(cpf=cpf_normalizado).first()
                    if existente:
                        return jsonify({'erro': 'CPF já cadastrado para outro fornecedor'}), 400
                    fornecedor.cpf = cpf_normalizado
        
        if 'email' in data and data['email']:
            if data['email'] != fornecedor.email:
                email_existente = Fornecedor.query.filter_by(email=data['email']).first()
                if email_existente:
                    return jsonify({'erro': 'E-mail já cadastrado para outro fornecedor'}), 400
                fornecedor.email = data['email']
        if 'rua' in data:
            fornecedor.rua = data['rua']
        if 'numero' in data:
            fornecedor.numero = data['numero']
        if 'cidade' in data:
            fornecedor.cidade = data['cidade']
        if 'cep' in data:
            fornecedor.cep = data['cep']
        if 'estado' in data:
            fornecedor.estado = data['estado']
        if 'bairro' in data:
            fornecedor.bairro = data['bairro']
        if 'complemento' in data:
            fornecedor.complemento = data['complemento']
        if 'tem_outro_endereco' in data:
            fornecedor.tem_outro_endereco = data['tem_outro_endereco']
        if 'outro_rua' in data:
            fornecedor.outro_rua = data['outro_rua']
        if 'outro_numero' in data:
            fornecedor.outro_numero = data['outro_numero']
        if 'outro_cidade' in data:
            fornecedor.outro_cidade = data['outro_cidade']
        if 'outro_cep' in data:
            fornecedor.outro_cep = data['outro_cep']
        if 'outro_estado' in data:
            fornecedor.outro_estado = data['outro_estado']
        if 'outro_bairro' in data:
            fornecedor.outro_bairro = data['outro_bairro']
        if 'outro_complemento' in data:
            fornecedor.outro_complemento = data['outro_complemento']
        if 'telefone' in data:
            fornecedor.telefone = data['telefone']
        if 'email' in data:
            fornecedor.email = data['email']
        if 'vendedor_id' in data:
            fornecedor.vendedor_id = data['vendedor_id']
        if 'conta_bancaria' in data:
            fornecedor.conta_bancaria = data['conta_bancaria']
        if 'agencia' in data:
            fornecedor.agencia = data['agencia']
        if 'chave_pix' in data:
            fornecedor.chave_pix = data['chave_pix']
        if 'banco' in data:
            fornecedor.banco = data['banco']
        if 'condicao_pagamento' in data:
            fornecedor.condicao_pagamento = data['condicao_pagamento']
        if 'forma_pagamento' in data:
            fornecedor.forma_pagamento = data['forma_pagamento']
        if 'observacoes' in data:
            fornecedor.observacoes = data['observacoes']
        
        # Apenas admin pode alterar a tabela de preços (promover/despromover)
        if usuario.tipo == 'admin' and 'tabela_preco_id' in data:
            tabela_id_req = data['tabela_preco_id']
            if tabela_id_req in [1, 2, 3]:
                fornecedor.tabela_preco_id = tabela_id_req
        
        # Atualizar comprador responsável
        if 'comprador_responsavel_id' in data:
            comprador_id = data['comprador_responsavel_id']
            if comprador_id is None:
                fornecedor.comprador_responsavel_id = None
                print(f"✓ Removendo comprador responsável do fornecedor {fornecedor.nome}")
            else:
                comprador = Usuario.query.get(comprador_id)
                if comprador:
                    fornecedor.comprador_responsavel_id = comprador_id
                    print(f"✓ Atribuindo comprador {comprador.nome} ao fornecedor {fornecedor.nome}")
                else:
                    print(f"✗ Comprador ID {comprador_id} não encontrado")
        
        # Atualizar tipos de lote selecionados com classificações (leve/médio/pesado)
        # Funcionários não podem modificar estrelas
        if 'tipos_lote' in data and isinstance(data['tipos_lote'], list) and usuario.tipo == 'admin':
            # Remover classificações antigas
            FornecedorTipoLoteClassificacao.query.filter_by(fornecedor_id=fornecedor.id).delete()
            FornecedorTipoLotePreco.query.filter_by(fornecedor_id=fornecedor.id).delete()
            
            # Adicionar novas classificações
            for tipo_data in data['tipos_lote']:
                tipo_lote_id = tipo_data.get('tipo_lote_id')
                leve = tipo_data.get('leve_estrelas', 1)
                medio = tipo_data.get('medio_estrelas', 3)
                pesado = tipo_data.get('pesado_estrelas', 5)
                
                if tipo_lote_id:
                    tipo_lote = TipoLote.query.get(tipo_lote_id)
                    if tipo_lote:
                        classif_obj = FornecedorTipoLoteClassificacao(
                            fornecedor_id=fornecedor.id,
                            tipo_lote_id=tipo_lote_id,
                            leve_estrelas=leve,
                            medio_estrelas=medio,
                            pesado_estrelas=pesado
                        )
                        db.session.add(classif_obj)
        
        db.session.commit()
        
        return jsonify(fornecedor.to_dict()), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': f'Erro ao atualizar fornecedor: {str(e)}'}), 500

@bp.route('/<int:id>', methods=['DELETE'])
@admin_required
def deletar_fornecedor(id):
    try:
        fornecedor = Fornecedor.query.get(id)
        
        if not fornecedor:
            return jsonify({'erro': 'Fornecedor não encontrado'}), 404
        
        db.session.delete(fornecedor)
        db.session.commit()
        
        return jsonify({'mensagem': 'Fornecedor deletado com sucesso'}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': f'Erro ao deletar fornecedor: {str(e)}'}), 500

@bp.route('/<int:id>/atribuir', methods=['POST'])
@admin_required
def atribuir_fornecedor(id):
    try:
        admin_id = get_jwt_identity()
        
        fornecedor = Fornecedor.query.get(id)
        
        if not fornecedor:
            return jsonify({'erro': 'Fornecedor não encontrado'}), 404
        
        data = request.get_json()
        
        if not data or 'funcionario_id' not in data:
            return jsonify({'erro': 'funcionario_id é obrigatório'}), 400
        
        funcionario_id = data['funcionario_id']
        
        funcionario = Usuario.query.get(funcionario_id)
        if not funcionario:
            return jsonify({'erro': 'Funcionário não encontrado'}), 404
        
        if funcionario.tipo != 'funcionario':
            return jsonify({'erro': 'O usuário especificado não é um funcionário'}), 400
        
        atribuicao_existente = FornecedorFuncionarioAtribuicao.query.filter_by(
            fornecedor_id=id,
            funcionario_id=funcionario_id
        ).first()
        
        if atribuicao_existente:
            return jsonify({'erro': 'Fornecedor já está atribuído a este funcionário'}), 400
        
        atribuicao = FornecedorFuncionarioAtribuicao(
            fornecedor_id=id,
            funcionario_id=funcionario_id,
            atribuido_por_id=admin_id
        )
        
        db.session.add(atribuicao)
        db.session.commit()
        
        return jsonify({
            'mensagem': 'Fornecedor atribuído com sucesso',
            'atribuicao': atribuicao.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': f'Erro ao atribuir fornecedor: {str(e)}'}), 500

@bp.route('/<int:id>/precos', methods=['GET'])
@jwt_required()
def listar_precos_fornecedor(id):
    try:
        usuario_id = get_jwt_identity()
        
        fornecedor = Fornecedor.query.get(id)
        
        if not fornecedor:
            return jsonify({'erro': 'Fornecedor não encontrado'}), 404
        
        if not verificar_acesso_fornecedor(id, usuario_id):
            return jsonify({'erro': 'Você não tem permissão para acessar este fornecedor'}), 403
        
        precos = FornecedorTipoLotePreco.query.filter_by(fornecedor_id=id).all()
        
        precos_agrupados = {}
        for preco in precos:
            tipo_id = preco.tipo_lote_id
            if tipo_id not in precos_agrupados:
                precos_agrupados[tipo_id] = {
                    'tipo_lote_id': tipo_id,
                    'tipo_lote_nome': preco.tipo_lote.nome if preco.tipo_lote else '',
                    'estrelas': {}
                }
            precos_agrupados[tipo_id]['estrelas'][preco.estrelas] = preco.preco_por_kg
        
        return jsonify(list(precos_agrupados.values())), 200
    
    except Exception as e:
        return jsonify({'erro': f'Erro ao listar preços: {str(e)}'}), 500

@bp.route('/<int:id>/precos', methods=['POST'])
@admin_required
def configurar_precos_fornecedor(id):
    try:
        fornecedor = Fornecedor.query.get(id)
        
        if not fornecedor:
            return jsonify({'erro': 'Fornecedor não encontrado'}), 404
        
        data = request.get_json()
        
        if not data or 'precos' not in data:
            return jsonify({'erro': 'Lista de preços não fornecida'}), 400
        
        precos_inseridos = 0
        precos_atualizados = 0
        
        for preco_data in data['precos']:
            tipo_lote_id = preco_data.get('tipo_lote_id')
            estrelas = preco_data.get('estrelas')
            preco_kg = preco_data.get('preco_por_kg', 0.0)
            
            if not tipo_lote_id or not estrelas:
                continue
            
            if not (1 <= estrelas <= 5):
                continue
            
            tipo_lote = TipoLote.query.get(tipo_lote_id)
            if not tipo_lote:
                continue
            
            preco_existente = FornecedorTipoLotePreco.query.filter_by(
                fornecedor_id=id,
                tipo_lote_id=tipo_lote_id,
                estrelas=estrelas
            ).first()
            
            if preco_existente:
                preco_existente.preco_por_kg = preco_kg
                preco_existente.ativo = preco_data.get('ativo', True)
                precos_atualizados += 1
            else:
                novo_preco = FornecedorTipoLotePreco(
                    fornecedor_id=id,
                    tipo_lote_id=tipo_lote_id,
                    estrelas=estrelas,
                    preco_por_kg=preco_kg,
                    ativo=preco_data.get('ativo', True)
                )
                db.session.add(novo_preco)
                precos_inseridos += 1
        
        db.session.commit()
        
        return jsonify({
            'mensagem': 'Preços configurados com sucesso',
            'inseridos': precos_inseridos,
            'atualizados': precos_atualizados
        }), 200
    
    except ValueError as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': f'Erro ao configurar preços: {str(e)}'}), 500

@bp.route('/<int:fornecedor_id>/preco/<int:tipo_lote_id>/<int:estrelas>', methods=['GET'])
@jwt_required()
def obter_preco_especifico(fornecedor_id, tipo_lote_id, estrelas):
    try:
        usuario_id = get_jwt_identity()
        
        if not verificar_acesso_fornecedor(fornecedor_id, usuario_id):
            return jsonify({'erro': 'Você não tem permissão para acessar este fornecedor'}), 403
        
        if not (1 <= estrelas <= 5):
            return jsonify({'erro': 'Estrelas deve estar entre 1 e 5'}), 400
        
        preco = FornecedorTipoLotePreco.query.filter_by(
            fornecedor_id=fornecedor_id,
            tipo_lote_id=tipo_lote_id,
            estrelas=estrelas
        ).first()
        
        if not preco:
            return jsonify({'erro': 'Preço não encontrado para esta combinação'}), 404
        
        return jsonify(preco.to_dict()), 200
    
    except Exception as e:
        return jsonify({'erro': f'Erro ao obter preço: {str(e)}'}), 500

@bp.route('/<int:fornecedor_id>/tipos-lote', methods=['GET'])
@jwt_required()
def listar_tipos_lote_fornecedor(fornecedor_id):
    """Lista todos os tipos de lote cadastrados para um fornecedor específico com preços por classificação"""
    try:
        usuario_id = get_jwt_identity()
        
        print(f"\n{'='*60}")
        print(f" ENDPOINT: /api/fornecedores/{fornecedor_id}/tipos-lote")
        print(f"{'='*60}")
        print(f"   Usuário ID: {usuario_id}")
        
        fornecedor = Fornecedor.query.get(fornecedor_id)
        
        if not fornecedor:
            print(f"   ❌ Fornecedor não encontrado")
            return jsonify({'erro': 'Fornecedor não encontrado'}), 404
        
        print(f"   Fornecedor: {fornecedor.nome}")
        print(f"   ✅ Acesso autorizado (endpoint de consulta pública para criação de solicitações)")
        
        # Buscar configurações de classificação do fornecedor (novo schema)
        from app.models import FornecedorTipoLoteClassificacao, TipoLotePreco
        
        configs = FornecedorTipoLoteClassificacao.query.filter_by(
            fornecedor_id=fornecedor_id,
            ativo=True
        ).all()
        
        print(f"   Total de configs encontradas: {len(configs)}")
        
        resultado = []
        for config in configs:
            tipo_lote = config.tipo_lote
            if not tipo_lote:
                print(f"   ⚠️ Config sem tipo_lote associado")
                continue
            
            print(f"\n   Processando tipo lote: {tipo_lote.nome} (ID: {tipo_lote.id})")
            
            tipo_dict = tipo_lote.to_dict()
            
            # Incluir mapeamento classificação → estrelas
            tipo_dict['estrelas_config'] = {
                'leve': config.leve_estrelas,
                'medio': config.medio_estrelas,
                'pesado': config.pesado_estrelas
            }
            
            print(f"   Estrelas configuradas: L={config.leve_estrelas}, M={config.medio_estrelas}, P={config.pesado_estrelas}")
            
            # Buscar preços para cada classificação baseado nas estrelas
            tipo_dict['precos_por_classificacao'] = {}
            
            for classificacao in ['leve', 'medio', 'pesado']:
                estrelas = config.get_estrelas_por_classificacao(classificacao)
                
                print(f"   Buscando preço: classificacao={classificacao}, estrelas={estrelas}")
                
                # Buscar preço do tipo de lote para esta classificação+estrelas
                preco = TipoLotePreco.query.filter_by(
                    tipo_lote_id=tipo_lote.id,
                    classificacao=classificacao,
                    estrelas=estrelas,
                    ativo=True
                ).first()
                
                if preco:
                    tipo_dict['precos_por_classificacao'][classificacao] = {
                        'estrelas': estrelas,
                        'preco_por_kg': preco.preco_por_kg
                    }
                    print(f"   ✅ Preço encontrado: R$ {preco.preco_por_kg}/kg")
                else:
                    print(f"   ❌ Preço NÃO encontrado")
            
            resultado.append(tipo_dict)
        
        print(f"\n   Total de tipos de lote retornados: {len(resultado)}")
        print(f"{'='*60}\n")
        
        return jsonify(resultado), 200
    
    except Exception as e:
        print(f"   ❌ ERRO: {str(e)}")
        print(f"{'='*60}\n")
        import traceback
        traceback.print_exc()
        return jsonify({'erro': f'Erro ao listar tipos de lote: {str(e)}'}), 500

@bp.route('/consultar-cnpj/<string:cnpj>', methods=['GET'])
@jwt_required()
def consultar_cnpj(cnpj):
    try:
        cnpj_limpo = normalizar_cnpj(cnpj)
        
        if not validar_cnpj(cnpj_limpo):
            return jsonify({'erro': 'CNPJ inválido. Verifique o número digitado.'}), 400
        
        empresa_data = None
        apis = [
            {
                'name': 'BrasilAPI',
                'url': f'https://brasilapi.com.br/api/cnpj/v1/{cnpj_limpo}',
                'parser': lambda data: {
                    'cnpj': cnpj_limpo,
                    'nome': data.get('nome_fantasia', '') or data.get('razao_social', ''),
                    'nome_social': data.get('razao_social', ''),
                    'telefone': data.get('ddd_telefone_1', ''),
                    'email': data.get('email', ''),
                    'rua': data.get('descricao_tipo_logradouro', '') + ' ' + data.get('logradouro', ''),
                    'numero': data.get('numero', ''),
                    'cidade': data.get('municipio', ''),
                    'estado': data.get('uf', ''),
                    'cep': data.get('cep', '').replace('.', '').replace('-', ''),
                    'bairro': data.get('bairro', ''),
                    'complemento': data.get('complemento', ''),
                }
            },
            {
                'name': 'OpenCNPJ',
                'url': f'https://opencnpj.org/{cnpj_limpo}',
                'parser': lambda data: {
                    'cnpj': cnpj_limpo,
                    'nome': data.get('nome_fantasia', '') or data.get('razao_social', ''),
                    'nome_social': data.get('razao_social', ''),
                    'telefone': data.get('ddd_telefone_1', ''),
                    'email': data.get('email', ''),
                    'rua': data.get('descricao_tipo_logradouro', '') + ' ' + data.get('logradouro', ''),
                    'numero': data.get('numero', ''),
                    'cidade': data.get('municipio', ''),
                    'estado': data.get('uf', ''),
                    'cep': data.get('cep', '').replace('.', '').replace('-', ''),
                    'bairro': data.get('bairro', ''),
                    'complemento': data.get('complemento', ''),
                }
            },
            {
                'name': 'ReceitaWS',
                'url': f'https://receitaws.com.br/v1/cnpj/{cnpj_limpo}',
                'parser': lambda data: {
                    'cnpj': cnpj_limpo,
                    'nome': data.get('fantasia', '') or data.get('nome', ''),
                    'nome_social': data.get('nome', ''),
                    'telefone': data.get('telefone', ''),
                    'email': data.get('email', ''),
                    'rua': data.get('logradouro', ''),
                    'numero': data.get('numero', ''),
                    'cidade': data.get('municipio', ''),
                    'estado': data.get('uf', ''),
                    'cep': data.get('cep', '').replace('.', '').replace('-', ''),
                    'bairro': data.get('bairro', ''),
                    'complemento': data.get('complemento', ''),
                }
            }
        ]
        
        for api in apis:
            try:
                response = requests.get(api['url'], timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if 'error' in data or data.get('status') == 'ERROR':
                        continue
                    
                    empresa_data = api['parser'](data)
                    break
                    
            except (requests.Timeout, requests.ConnectionError, requests.RequestException):
                continue
        
        if not empresa_data:
            return jsonify({'erro': 'CNPJ não encontrado. Preencha os dados manualmente.'}), 404
        
        # Verificar conflito de endereço
        conflito = verificar_conflito_endereco(
            rua=empresa_data.get('rua'),
            numero=empresa_data.get('numero'),
            cidade=empresa_data.get('cidade'),
            estado=empresa_data.get('estado'),
            cep=empresa_data.get('cep')
        )
        
        if conflito:
            # Retornar APENAS a mensagem de conflito se houver
            return jsonify({
                'erro': conflito['mensagem'],
                'conflito_endereco': conflito
            }), 409
        
        # Verificar se CNPJ já existe (apenas depois de verificar endereço)
        fornecedor_existente = Fornecedor.query.filter_by(cnpj=cnpj_limpo).first()
        if fornecedor_existente:
            return jsonify({
                'erro': 'CNPJ já cadastrado',
                'fornecedor': fornecedor_existente.to_dict()
            }), 409
        
        return jsonify(empresa_data), 200
        
    except Exception as e:
        return jsonify({'erro': f'Erro ao processar dados do CNPJ: {str(e)}'}), 500
