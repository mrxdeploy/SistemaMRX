from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, FornecedorTabelaPrecos, AuditoriaFornecedorTabelaPrecos, Fornecedor, MaterialBase, Usuario, Notificacao, TabelaPrecoItem, TabelaPreco, FornecedorFuncionarioAtribuicao
from app.auth import admin_required
import pandas as pd
from io import BytesIO
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('fornecedor_tabela_precos', __name__, url_prefix='/api/fornecedor-tabela-precos')

def verificar_acesso_fornecedor(fornecedor_id, usuario_id):
    """Verifica se o usuário tem acesso ao fornecedor"""
    usuario = Usuario.query.get(usuario_id)
    
    if not usuario:
        return False
    
    # Admin tem acesso total
    if usuario.tipo == 'admin':
        return True
    
    # Auditor tem acesso de leitura
    if usuario.perfil and usuario.perfil.nome == 'Auditoria / BI':
        return True
    
    # Verificar se o fornecedor existe
    fornecedor = Fornecedor.query.get(fornecedor_id)
    if not fornecedor:
        return False
    
    # Qualquer comprador (usuário com perfil "Comprador (PJ)") pode enviar tabela para aprovação
    if usuario.perfil and usuario.perfil.nome == 'Comprador (PJ)':
        return True
    
    # Caso não seja comprador, verificar se é o responsável ou criador
    if fornecedor.comprador_responsavel_id == usuario_id or fornecedor.criado_por_id == usuario_id:
        return True
    
    # Verificar se existe atribuição via FornecedorFuncionarioAtribuicao
    atribuicao = FornecedorFuncionarioAtribuicao.query.filter_by(
        fornecedor_id=fornecedor_id,
        funcionario_id=usuario_id
    ).first()
    
    return atribuicao is not None

def notificar_admins_nova_tabela(fornecedor, usuario_criador):
    """Cria notificação para todos os admins sobre nova tabela de preços"""
    admins = Usuario.query.filter_by(tipo='admin', ativo=True).all()
    
    for admin in admins:
        if admin.id == usuario_criador.id:
            continue
            
        notificacao = Notificacao(
            usuario_id=admin.id,
            titulo='Nova Tabela de Preços',
            mensagem=f'Tabela de preços adicionada para o fornecedor {fornecedor.nome} por {usuario_criador.nome}',
            tipo='tabela_precos',
            url='/revisao-tabelas-admin.html'
        )
        db.session.add(notificacao)

@bp.route('/fornecedor/<int:fornecedor_id>', methods=['GET'])
@jwt_required()
def listar_precos_fornecedor(fornecedor_id):
    """Lista todos os preços de um fornecedor"""
    try:
        usuario_id = get_jwt_identity()
        
        if not verificar_acesso_fornecedor(fornecedor_id, usuario_id):
            return jsonify({'erro': 'Acesso negado a este fornecedor'}), 403
        
        fornecedor = Fornecedor.query.get(fornecedor_id)
        if not fornecedor:
            return jsonify({'erro': 'Fornecedor não encontrado'}), 404
        
        status = request.args.get('status', None)
        versao = request.args.get('versao', None)
        
        query = FornecedorTabelaPrecos.query.filter_by(fornecedor_id=fornecedor_id)
        
        if status:
            query = query.filter_by(status=status)
        
        if versao:
            query = query.filter_by(versao=int(versao))
        
        precos = query.order_by(FornecedorTabelaPrecos.material_id, FornecedorTabelaPrecos.versao.desc()).all()
        
        return jsonify({
            'fornecedor': {
                'id': fornecedor.id,
                'nome': fornecedor.nome
            },
            'precos': [p.to_dict() for p in precos]
        }), 200
        
    except Exception as e:
        logger.error(f'Erro ao listar preços do fornecedor: {str(e)}')
        return jsonify({'erro': f'Erro ao listar preços: {str(e)}'}), 500

@bp.route('/fornecedor/<int:fornecedor_id>', methods=['POST'])
@jwt_required()
def adicionar_preco(fornecedor_id):
    """Adiciona um novo preço para um material do fornecedor"""
    try:
        usuario_id = get_jwt_identity()
        usuario = Usuario.query.get(usuario_id)
        
        if not verificar_acesso_fornecedor(fornecedor_id, usuario_id):
            return jsonify({'erro': 'Acesso negado a este fornecedor'}), 403
        
        fornecedor = Fornecedor.query.get(fornecedor_id)
        if not fornecedor:
            return jsonify({'erro': 'Fornecedor não encontrado'}), 404
        
        dados = request.get_json()
        
        if not dados.get('material_id'):
            return jsonify({'erro': 'Material é obrigatório'}), 400
        
        if dados.get('preco_fornecedor') is None:
            return jsonify({'erro': 'Preço é obrigatório'}), 400
        
        material = MaterialBase.query.get(dados['material_id'])
        if not material:
            return jsonify({'erro': 'Material não encontrado'}), 404
        
        preco_existente = FornecedorTabelaPrecos.query.filter_by(
            fornecedor_id=fornecedor_id,
            material_id=dados['material_id'],
            status='ativo'
        ).first()
        
        if preco_existente:
            preco_existente.status = 'inativo'
            preco_existente.updated_by = usuario_id
            nova_versao = preco_existente.versao + 1
        else:
            nova_versao = 1
        
        novo_preco = FornecedorTabelaPrecos(
            fornecedor_id=fornecedor_id,
            material_id=dados['material_id'],
            preco_fornecedor=float(dados['preco_fornecedor']),
            status='pendente_aprovacao',
            versao=nova_versao,
            created_by=usuario_id,
            arquivo_origem_id=dados.get('arquivo_origem_id')
        )
        
        db.session.add(novo_preco)
        
        notificar_admins_nova_tabela(fornecedor, usuario)
        
        db.session.commit()
        
        return jsonify(novo_preco.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'Erro ao adicionar preço: {str(e)}')
        return jsonify({'erro': f'Erro ao adicionar preço: {str(e)}'}), 500

@bp.route('/fornecedor/<int:fornecedor_id>/lote', methods=['POST'])
@jwt_required()
def adicionar_precos_lote(fornecedor_id):
    """Adiciona múltiplos preços de uma vez (para upload manual ou importação)"""
    try:
        usuario_id = get_jwt_identity()
        usuario = Usuario.query.get(usuario_id)
        
        logger.info(f'🔍 Tentando adicionar preços em lote - Usuário: {usuario_id}, Fornecedor: {fornecedor_id}')
        
        if not verificar_acesso_fornecedor(fornecedor_id, usuario_id):
            logger.error(f'❌ Acesso negado - Usuário {usuario_id} não tem acesso ao fornecedor {fornecedor_id}')
            return jsonify({'erro': 'Acesso negado a este fornecedor'}), 403
        
        fornecedor = Fornecedor.query.get(fornecedor_id)
        if not fornecedor:
            return jsonify({'erro': 'Fornecedor não encontrado'}), 404
        
        dados = request.get_json()
        logger.info(f'📦 Dados recebidos: {dados}')
        
        itens = dados.get('itens', [])
        
        if not itens:
            logger.error('❌ Nenhum item para adicionar')
            return jsonify({'erro': 'Nenhum item para adicionar'}), 400
        
        logger.info(f'📝 Processando {len(itens)} itens')
        
        precos_criados = []
        erros = []
        
        for idx, item in enumerate(itens):
            try:
                logger.info(f'🔍 Processando item {idx + 1}: {item}')
                
                if not item.get('material_id'):
                    erros.append(f'Item {idx + 1}: Material é obrigatório')
                    logger.warning(f'⚠️ Item {idx + 1}: Material não informado')
                    continue
                
                if item.get('preco_fornecedor') is None:
                    erros.append(f'Item {idx + 1}: Preço é obrigatório')
                    logger.warning(f'⚠️ Item {idx + 1}: Preço não informado')
                    continue
                
                material = MaterialBase.query.get(item['material_id'])
                if not material:
                    erros.append(f'Item {idx + 1}: Material não encontrado')
                    logger.warning(f'⚠️ Item {idx + 1}: Material {item["material_id"]} não encontrado')
                    continue
                
                logger.info(f'✅ Material encontrado: {material.nome}')
                
                preco_existente = FornecedorTabelaPrecos.query.filter_by(
                    fornecedor_id=fornecedor_id,
                    material_id=item['material_id'],
                    status='ativo'
                ).first()
                
                if preco_existente:
                    logger.info(f'📝 Atualizando preço existente (versão {preco_existente.versao})')
                    preco_existente.status = 'inativo'
                    preco_existente.updated_by = usuario_id
                    nova_versao = preco_existente.versao + 1
                else:
                    logger.info(f'✨ Criando novo preço (versão 1)')
                    nova_versao = 1
                
                novo_preco = FornecedorTabelaPrecos(
                    fornecedor_id=fornecedor_id,
                    material_id=item['material_id'],
                    preco_fornecedor=float(item['preco_fornecedor']),
                    status='pendente_aprovacao',
                    versao=nova_versao,
                    created_by=usuario_id,
                    arquivo_origem_id=dados.get('arquivo_origem_id')
                )
                
                db.session.add(novo_preco)
                precos_criados.append(novo_preco)
                logger.info(f'✅ Preço adicionado: {material.nome} - R$ {item["preco_fornecedor"]:.2f}')
                
            except Exception as e:
                erros.append(f'Item {idx + 1}: {str(e)}')
                logger.error(f'❌ Erro no item {idx + 1}: {str(e)}', exc_info=True)
        
        if precos_criados:
            logger.info(f'💾 Salvando {len(precos_criados)} preços no banco de dados')
            try:
                notificar_admins_nova_tabela(fornecedor, usuario)
                db.session.commit()
                logger.info(f'✅ Preços salvos com sucesso!')
            except Exception as commit_error:
                db.session.rollback()
                logger.error(f'❌ Erro ao salvar no banco: {str(commit_error)}', exc_info=True)
                return jsonify({'erro': f'Erro ao salvar no banco de dados: {str(commit_error)}'}), 500
        else:
            logger.warning(f'⚠️ Nenhum preço foi criado. Erros: {erros}')
        
        response_data = {
            'sucesso': len(precos_criados),
            'erros': erros,
            'precos': [p.to_dict() for p in precos_criados]
        }
        logger.info(f'📤 Retornando resposta: {response_data}')
        
        return jsonify(response_data), 201 if precos_criados else 400
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'Erro ao adicionar preços em lote: {str(e)}')
        return jsonify({'erro': f'Erro ao adicionar preços: {str(e)}'}), 500

@bp.route('/fornecedor/<int:fornecedor_id>/upload', methods=['POST'])
@jwt_required()
def upload_tabela_precos(fornecedor_id):
    """Upload de arquivo CSV/XLSX com tabela de preços"""
    try:
        usuario_id = get_jwt_identity()
        usuario = Usuario.query.get(usuario_id)
        
        if not verificar_acesso_fornecedor(fornecedor_id, usuario_id):
            return jsonify({'erro': 'Acesso negado a este fornecedor'}), 403
        
        fornecedor = Fornecedor.query.get(fornecedor_id)
        if not fornecedor:
            return jsonify({'erro': 'Fornecedor não encontrado'}), 404
        
        if 'arquivo' not in request.files:
            return jsonify({'erro': 'Arquivo não enviado'}), 400
        
        arquivo = request.files['arquivo']
        
        if arquivo.filename == '':
            return jsonify({'erro': 'Nenhum arquivo selecionado'}), 400
        
        extensao = arquivo.filename.rsplit('.', 1)[-1].lower()
        
        if extensao not in ['csv', 'xlsx', 'xls']:
            return jsonify({'erro': 'Formato de arquivo inválido. Use CSV ou XLSX'}), 400
        
        try:
            if extensao == 'csv':
                df = pd.read_csv(arquivo, encoding='utf-8')
            else:
                df = pd.read_excel(arquivo)
        except Exception as e:
            return jsonify({'erro': f'Erro ao ler arquivo: {str(e)}'}), 400
        
        colunas_obrigatorias = ['material', 'preco']
        colunas_arquivo = [col.lower().strip() for col in df.columns]
        
        coluna_material = None
        coluna_preco = None
        
        for col in df.columns:
            col_lower = col.lower().strip()
            if col_lower in ['material', 'nome_material', 'nome do material', 'material_nome']:
                coluna_material = col
            if col_lower in ['preco', 'preco_kg', 'preco por kg', 'preco_fornecedor', 'valor']:
                coluna_preco = col
        
        if not coluna_material or not coluna_preco:
            return jsonify({
                'erro': 'Colunas obrigatórias não encontradas. O arquivo deve ter colunas: material, preco'
            }), 400
        
        precos_criados = []
        erros = []
        
        for idx, row in df.iterrows():
            try:
                nome_material = str(row[coluna_material]).strip()
                preco_valor = row[coluna_preco]
                
                if pd.isna(nome_material) or nome_material == '':
                    continue
                
                if pd.isna(preco_valor):
                    erros.append(f'Linha {idx + 2}: Preço inválido para material "{nome_material}"')
                    continue
                
                material = MaterialBase.query.filter(
                    db.or_(
                        MaterialBase.nome.ilike(nome_material),
                        MaterialBase.codigo.ilike(nome_material)
                    )
                ).first()
                
                if not material:
                    erros.append(f'Linha {idx + 2}: Material "{nome_material}" não encontrado')
                    continue
                
                try:
                    preco_float = float(str(preco_valor).replace(',', '.').replace('R$', '').strip())
                except:
                    erros.append(f'Linha {idx + 2}: Preço inválido "{preco_valor}"')
                    continue
                
                if preco_float < 0:
                    erros.append(f'Linha {idx + 2}: Preço não pode ser negativo')
                    continue
                
                preco_existente = FornecedorTabelaPrecos.query.filter_by(
                    fornecedor_id=fornecedor_id,
                    material_id=material.id,
                    status='ativo'
                ).first()
                
                if preco_existente:
                    preco_existente.status = 'inativo'
                    preco_existente.updated_by = usuario_id
                    nova_versao = preco_existente.versao + 1
                else:
                    nova_versao = 1
                
                novo_preco = FornecedorTabelaPrecos(
                    fornecedor_id=fornecedor_id,
                    material_id=material.id,
                    preco_fornecedor=preco_float,
                    status='pendente_aprovacao',
                    versao=nova_versao,
                    created_by=usuario_id
                )
                
                db.session.add(novo_preco)
                precos_criados.append(novo_preco)
                
            except Exception as e:
                erros.append(f'Linha {idx + 2}: Erro ao processar - {str(e)}')
        
        if precos_criados:
            notificar_admins_nova_tabela(fornecedor, usuario)
            db.session.commit()
        
        return jsonify({
            'sucesso': len(precos_criados),
            'total_linhas': len(df),
            'erros': erros,
            'precos': [p.to_dict() for p in precos_criados]
        }), 201 if precos_criados else 400
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'Erro ao fazer upload de tabela: {str(e)}')
        return jsonify({'erro': f'Erro ao processar arquivo: {str(e)}'}), 500

@bp.route('/<int:preco_id>', methods=['PUT'])
@jwt_required()
def atualizar_preco(preco_id):
    """Atualiza um preço existente (enquanto ainda está em rascunho)"""
    try:
        usuario_id = get_jwt_identity()
        
        preco = FornecedorTabelaPrecos.query.get(preco_id)
        if not preco:
            return jsonify({'erro': 'Preço não encontrado'}), 404
        
        if not verificar_acesso_fornecedor(preco.fornecedor_id, usuario_id):
            return jsonify({'erro': 'Acesso negado'}), 403
        
        if preco.status not in ['pendente_aprovacao', 'pendente_reenvio']:
            return jsonify({'erro': 'Apenas preços pendentes podem ser editados'}), 400
        
        dados = request.get_json()
        
        if 'preco_fornecedor' in dados:
            preco.preco_fornecedor = float(dados['preco_fornecedor'])
        
        preco.updated_by = usuario_id
        
        db.session.commit()
        
        return jsonify(preco.to_dict()), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'Erro ao atualizar preço: {str(e)}')
        return jsonify({'erro': f'Erro ao atualizar preço: {str(e)}'}), 500

@bp.route('/<int:preco_id>', methods=['DELETE'])
@jwt_required()
def excluir_preco(preco_id):
    """Exclui um preço (apenas se ainda estiver pendente)"""
    try:
        usuario_id = get_jwt_identity()
        
        preco = FornecedorTabelaPrecos.query.get(preco_id)
        if not preco:
            return jsonify({'erro': 'Preço não encontrado'}), 404
        
        if not verificar_acesso_fornecedor(preco.fornecedor_id, usuario_id):
            return jsonify({'erro': 'Acesso negado'}), 403
        
        if preco.status not in ['pendente_aprovacao', 'pendente_reenvio']:
            return jsonify({'erro': 'Apenas preços pendentes podem ser excluídos'}), 400
        
        preco.updated_by = usuario_id
        db.session.delete(preco)
        db.session.commit()
        
        return jsonify({'mensagem': 'Preço excluído com sucesso'}), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'Erro ao excluir preço: {str(e)}')
        return jsonify({'erro': f'Erro ao excluir preço: {str(e)}'}), 500

@bp.route('/fornecedor/<int:fornecedor_id>/reenviar', methods=['PUT'])
@jwt_required()
def reenviar_tabela(fornecedor_id):
    """Reenvia itens com status pendente_reenvio para aprovação"""
    try:
        usuario_id = get_jwt_identity()
        
        if not verificar_acesso_fornecedor(fornecedor_id, usuario_id):
            return jsonify({'erro': 'Acesso negado'}), 403
        
        fornecedor = Fornecedor.query.get(fornecedor_id)
        if not fornecedor:
            return jsonify({'erro': 'Fornecedor não encontrado'}), 404
        
        precos_reenvio = FornecedorTabelaPrecos.query.filter_by(
            fornecedor_id=fornecedor_id,
            status='pendente_reenvio'
        ).all()
        
        if not precos_reenvio:
            return jsonify({'erro': 'Não há itens para reenviar'}), 400
        
        for preco in precos_reenvio:
            preco.status = 'pendente_aprovacao'
            preco.updated_by = usuario_id
        
        fornecedor.tabela_preco_status = 'pendente_aprovacao'
        
        usuario = Usuario.query.get(usuario_id)
        notificar_admins_nova_tabela(fornecedor, usuario)
        
        db.session.commit()
        
        return jsonify({
            'mensagem': f'{len(precos_reenvio)} item(ns) reenviado(s) para aprovação',
            'total': len(precos_reenvio)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'Erro ao reenviar tabela: {str(e)}')
        return jsonify({'erro': f'Erro ao reenviar tabela: {str(e)}'}), 500

@bp.route('/<int:preco_id>/aprovar', methods=['PUT'])
@jwt_required()
@admin_required
def aprovar_preco(preco_id):
    """Aprova um preço pendente (apenas admin)"""
    try:
        usuario_id = get_jwt_identity()
        
        preco = FornecedorTabelaPrecos.query.get(preco_id)
        if not preco:
            return jsonify({'erro': 'Preço não encontrado'}), 404
        
        if preco.status != 'pendente_aprovacao':
            return jsonify({'erro': 'Preço não está pendente de aprovação'}), 400
        
        preco.status = 'ativo'
        preco.updated_by = usuario_id
        
        db.session.commit()
        
        criador = Usuario.query.get(preco.created_by)
        if criador:
            notificacao = Notificacao(
                usuario_id=criador.id,
                titulo='Tabela de Preços Aprovada',
                mensagem=f'Sua tabela de preços para o fornecedor {preco.fornecedor.nome} foi aprovada',
                tipo='tabela_precos_aprovada',
                url=f'/fornecedor-tabela-precos.html?id={preco.fornecedor_id}'
            )
            db.session.add(notificacao)
            db.session.commit()
        
        return jsonify(preco.to_dict()), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'Erro ao aprovar preço: {str(e)}')
        return jsonify({'erro': f'Erro ao aprovar preço: {str(e)}'}), 500

@bp.route('/<int:preco_id>/rejeitar', methods=['PUT'])
@jwt_required()
@admin_required
def rejeitar_preco(preco_id):
    """Rejeita um preço pendente (apenas admin)"""
    try:
        usuario_id = get_jwt_identity()
        
        preco = FornecedorTabelaPrecos.query.get(preco_id)
        if not preco:
            return jsonify({'erro': 'Preço não encontrado'}), 404
        
        if preco.status != 'pendente_aprovacao':
            return jsonify({'erro': 'Preço não está pendente de aprovação'}), 400
        
        dados = request.get_json() or {}
        motivo = dados.get('motivo', 'Não especificado')
        
        preco.status = 'inativo'
        preco.updated_by = usuario_id
        
        db.session.commit()
        
        criador = Usuario.query.get(preco.created_by)
        if criador:
            notificacao = Notificacao(
                usuario_id=criador.id,
                titulo='Tabela de Preços Rejeitada',
                mensagem=f'Sua tabela de preços para o fornecedor {preco.fornecedor.nome} foi rejeitada. Motivo: {motivo}',
                tipo='tabela_precos_rejeitada',
                url=f'/fornecedor-tabela-precos.html?id={preco.fornecedor_id}'
            )
            db.session.add(notificacao)
            db.session.commit()
        
        return jsonify(preco.to_dict()), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'Erro ao rejeitar preço: {str(e)}')
        return jsonify({'erro': f'Erro ao rejeitar preço: {str(e)}'}), 500

@bp.route('/fornecedor/<int:fornecedor_id>/aprovar-todos', methods=['PUT'])
@jwt_required()
@admin_required
def aprovar_todos_precos(fornecedor_id):
    """Aprova todos os preços pendentes de um fornecedor (apenas admin)"""
    try:
        usuario_id = get_jwt_identity()
        
        fornecedor = Fornecedor.query.get(fornecedor_id)
        if not fornecedor:
            return jsonify({'erro': 'Fornecedor não encontrado'}), 404
        
        precos_pendentes = FornecedorTabelaPrecos.query.filter_by(
            fornecedor_id=fornecedor_id,
            status='pendente_aprovacao'
        ).all()
        
        if not precos_pendentes:
            return jsonify({'erro': 'Nenhum preço pendente para aprovar'}), 400
        
        criadores_ids = set()
        for preco in precos_pendentes:
            preco.status = 'ativo'
            preco.updated_by = usuario_id
            if preco.created_by:
                criadores_ids.add(preco.created_by)
        
        db.session.commit()
        
        for criador_id in criadores_ids:
            criador = Usuario.query.get(criador_id)
            if criador:
                notificacao = Notificacao(
                    usuario_id=criador.id,
                    titulo='Tabela de Preços Aprovada',
                    mensagem=f'Sua tabela de preços para o fornecedor {fornecedor.nome} foi aprovada',
                    tipo='tabela_precos_aprovada',
                    url=f'/fornecedor-tabela-precos.html?id={fornecedor_id}'
                )
                db.session.add(notificacao)
        
        db.session.commit()
        
        return jsonify({
            'mensagem': f'{len(precos_pendentes)} preços aprovados com sucesso',
            'aprovados': len(precos_pendentes)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'Erro ao aprovar preços: {str(e)}')
        return jsonify({'erro': f'Erro ao aprovar preços: {str(e)}'}), 500

@bp.route('/fornecedor/<int:fornecedor_id>/template', methods=['GET'])
@jwt_required()
def download_template(fornecedor_id):
    """Gera um template Excel para upload de preços - APENAS com estrutura, SEM materiais pré-carregados"""
    try:
        usuario_id = get_jwt_identity()
        
        if not verificar_acesso_fornecedor(fornecedor_id, usuario_id):
            return jsonify({'erro': 'Acesso negado'}), 403
        
        fornecedor = Fornecedor.query.get(fornecedor_id)
        if not fornecedor:
            return jsonify({'erro': 'Fornecedor não encontrado'}), 404
        
        # Template vazio - apenas com cabeçalhos
        dados = []
        
        df = pd.DataFrame(dados, columns=['Material', 'Código', 'Classificação', 'Preço (R$/kg)'])
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Preços')
        
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'template_precos_{fornecedor.nome.replace(" ", "_")}.xlsx'
        )
        
    except Exception as e:
        logger.error(f'Erro ao gerar template: {str(e)}')
        return jsonify({'erro': f'Erro ao gerar template: {str(e)}'}), 500

@bp.route('/fornecedor/<int:fornecedor_id>/auditoria', methods=['GET'])
@jwt_required()
def listar_auditoria(fornecedor_id):
    """Lista o histórico de auditoria dos preços de um fornecedor"""
    try:
        usuario_id = get_jwt_identity()
        
        if not verificar_acesso_fornecedor(fornecedor_id, usuario_id):
            return jsonify({'erro': 'Acesso negado'}), 403
        
        fornecedor = Fornecedor.query.get(fornecedor_id)
        if not fornecedor:
            return jsonify({'erro': 'Fornecedor não encontrado'}), 404
        
        precos_ids = [p.id for p in FornecedorTabelaPrecos.query.filter_by(fornecedor_id=fornecedor_id).all()]
        
        auditorias = AuditoriaFornecedorTabelaPrecos.query.filter(
            AuditoriaFornecedorTabelaPrecos.preco_id.in_(precos_ids)
        ).order_by(AuditoriaFornecedorTabelaPrecos.data_acao.desc()).limit(100).all()
        
        return jsonify([a.to_dict() for a in auditorias]), 200
        
    except Exception as e:
        logger.error(f'Erro ao listar auditoria: {str(e)}')
        return jsonify({'erro': f'Erro ao listar auditoria: {str(e)}'}), 500

@bp.route('/pendentes', methods=['GET'])
@jwt_required()
@admin_required
def listar_pendentes():
    """Lista todos os fornecedores com preços pendentes de aprovação (apenas admin)"""
    try:
        precos_pendentes = db.session.query(
            FornecedorTabelaPrecos.fornecedor_id,
            db.func.count(FornecedorTabelaPrecos.id).label('total_pendentes')
        ).filter_by(
            status='pendente_aprovacao'
        ).group_by(
            FornecedorTabelaPrecos.fornecedor_id
        ).all()
        
        resultado = []
        for fornecedor_id, total in precos_pendentes:
            fornecedor = Fornecedor.query.get(fornecedor_id)
            if fornecedor:
                resultado.append({
                    'fornecedor_id': fornecedor_id,
                    'fornecedor_nome': fornecedor.nome,
                    'total_pendentes': total,
                    'tabela_preco_status': fornecedor.tabela_preco_status,
                    'comprador_responsavel_nome': fornecedor.comprador_responsavel.nome if fornecedor.comprador_responsavel else None
                })
        
        return jsonify(resultado), 200
        
    except Exception as e:
        logger.error(f'Erro ao listar pendentes: {str(e)}')
        return jsonify({'erro': f'Erro ao listar pendentes: {str(e)}'}), 500

@bp.route('/admin/revisao/<int:fornecedor_id>', methods=['GET'])
@jwt_required()
@admin_required
def revisar_tabela_fornecedor(fornecedor_id):
    """Retorna tabela de preços do fornecedor com comparação de médias para revisão do admin"""
    try:
        fornecedor = Fornecedor.query.get(fornecedor_id)
        if not fornecedor:
            return jsonify({'erro': 'Fornecedor não encontrado'}), 404
        
        precos_pendentes = FornecedorTabelaPrecos.query.filter_by(
            fornecedor_id=fornecedor_id,
            status='pendente_aprovacao'
        ).all()
        
        if not precos_pendentes:
            precos_pendentes = FornecedorTabelaPrecos.query.filter_by(
                fornecedor_id=fornecedor_id,
                status='ativo'
            ).all()
        
        material_ids = [p.material_id for p in precos_pendentes]
        
        medias_sistema = {}
        for material_id in material_ids:
            precos_tabela = TabelaPrecoItem.query.filter(
                TabelaPrecoItem.material_id == material_id,
                TabelaPrecoItem.ativo == True
            ).all()
            
            if precos_tabela:
                precos_por_estrela = {}
                for item in precos_tabela:
                    if item.tabela_preco:
                        estrelas = item.tabela_preco.nivel_estrelas
                        preco_kg = float(item.preco_por_kg) if item.preco_por_kg else 0
                        if preco_kg > 0:
                            precos_por_estrela[estrelas] = preco_kg
                
                if precos_por_estrela:
                    valores = list(precos_por_estrela.values())
                    media_3_estrelas = round(sum(valores) / len(valores), 2)
                    medias_sistema[material_id] = {
                        'media': media_3_estrelas,
                        'precos_por_estrela': precos_por_estrela,
                        'total_estrelas': len(valores)
                    }
        
        resultado_itens = []
        for preco in precos_pendentes:
            preco_valor = float(preco.preco_fornecedor) if preco.preco_fornecedor else 0
            media_info = medias_sistema.get(preco.material_id, {})
            media_valor = media_info.get('media', 0)
            precos_estrelas = media_info.get('precos_por_estrela', {})
            
            diferenca_percentual = 0
            status_comparacao = 'na_media'
            if media_valor > 0:
                diferenca_percentual = round(((preco_valor - media_valor) / media_valor) * 100, 2)
                if diferenca_percentual > 5:
                    status_comparacao = 'acima'
                elif diferenca_percentual < -5:
                    status_comparacao = 'abaixo'
            
            estrelas_calculadas = 0
            if precos_estrelas:
                estrelas_totais = 0
                for nivel, preco_est in precos_estrelas.items():
                    if preco_est > 0:
                        estrelas_totais += nivel
                if len(precos_estrelas) > 0:
                    estrelas_calculadas = round(estrelas_totais / len(precos_estrelas), 1)
            
            resultado_itens.append({
                'id': preco.id,
                'material_id': preco.material_id,
                'material_nome': preco.material.nome if preco.material else None,
                'material_codigo': preco.material.codigo if preco.material else None,
                'material_classificacao': preco.material.classificacao if preco.material else None,
                'preco_fornecedor': preco_valor,
                'media_sistema': media_valor,
                'precos_por_estrela': precos_estrelas,
                'estrelas_media': estrelas_calculadas,
                'diferenca_percentual': diferenca_percentual,
                'status_comparacao': status_comparacao,
                'status': preco.status,
                'versao': preco.versao,
                'criador_nome': preco.criador.nome if preco.criador else None,
                'created_at': preco.created_at.isoformat() if preco.created_at else None
            })
        
        resultado_itens.sort(key=lambda x: x.get('diferenca_percentual', 0), reverse=True)
        
        return jsonify({
            'fornecedor': {
                'id': fornecedor.id,
                'nome': fornecedor.nome,
                'cnpj': fornecedor.cnpj,
                'cpf': fornecedor.cpf,
                'tabela_preco_status': fornecedor.tabela_preco_status,
                'comprador_responsavel_nome': fornecedor.comprador_responsavel.nome if fornecedor.comprador_responsavel else None
            },
            'itens': resultado_itens,
            'resumo': {
                'total_itens': len(resultado_itens),
                'itens_acima_media': len([i for i in resultado_itens if i['status_comparacao'] == 'acima']),
                'itens_abaixo_media': len([i for i in resultado_itens if i['status_comparacao'] == 'abaixo']),
                'itens_na_media': len([i for i in resultado_itens if i['status_comparacao'] == 'na_media'])
            }
        }), 200
        
    except Exception as e:
        logger.error(f'Erro ao revisar tabela: {str(e)}')
        return jsonify({'erro': f'Erro ao revisar tabela: {str(e)}'}), 500

@bp.route('/admin/<int:preco_id>/editar', methods=['PUT'])
@jwt_required()
@admin_required
def admin_editar_preco(preco_id):
    """Admin edita um preço e notifica o comprador sobre a alteração"""
    try:
        usuario_id = get_jwt_identity()
        admin = Usuario.query.get(usuario_id)
        
        preco = FornecedorTabelaPrecos.query.get(preco_id)
        if not preco:
            return jsonify({'erro': 'Preço não encontrado'}), 404
        
        dados = request.get_json()
        novo_preco = dados.get('preco_fornecedor')
        
        if novo_preco is None:
            return jsonify({'erro': 'Novo preço é obrigatório'}), 400
        
        preco_anterior = float(preco.preco_fornecedor) if preco.preco_fornecedor else 0
        preco.preco_fornecedor = float(novo_preco)
        preco.updated_by = usuario_id
        preco.updated_at = datetime.utcnow()
        
        auditoria = AuditoriaFornecedorTabelaPrecos(
            preco_id=preco.id,
            usuario_id=usuario_id,
            acao='atualizacao',
            dados_anteriores={'preco_fornecedor': preco_anterior},
            dados_novos={'preco_fornecedor': float(novo_preco)}
        )
        db.session.add(auditoria)
        
        comprador = preco.fornecedor.comprador_responsavel
        if comprador:
            notificacao = Notificacao(
                usuario_id=comprador.id,
                titulo='Preço Alterado pelo Admin',
                mensagem=f'O preço do material "{preco.material.nome}" foi alterado de R$ {preco_anterior:.2f} para R$ {float(novo_preco):.2f} pelo administrador {admin.nome}',
                tipo='preco_alterado',
                url=f'/fornecedor-tabela-precos.html?id={preco.fornecedor_id}'
            )
            db.session.add(notificacao)
        
        db.session.commit()
        
        return jsonify({
            'mensagem': 'Preço atualizado com sucesso',
            'preco': preco.to_dict(),
            'alteracao': {
                'material': preco.material.nome if preco.material else None,
                'anterior': preco_anterior,
                'novo': float(novo_preco)
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'Erro ao editar preço: {str(e)}')
        return jsonify({'erro': f'Erro ao editar preço: {str(e)}'}), 500

@bp.route('/admin/fornecedor/<int:fornecedor_id>/aprovar-tabela', methods=['PUT'])
@jwt_required()
@admin_required
def aprovar_tabela_completa(fornecedor_id):
    """Aprova toda a tabela de preços de um fornecedor"""
    try:
        usuario_id = get_jwt_identity()
        
        fornecedor = Fornecedor.query.get(fornecedor_id)
        if not fornecedor:
            return jsonify({'erro': 'Fornecedor não encontrado'}), 404
        
        precos_pendentes = FornecedorTabelaPrecos.query.filter_by(
            fornecedor_id=fornecedor_id,
            status='pendente_aprovacao'
        ).all()
        
        if not precos_pendentes:
            return jsonify({'erro': 'Nenhum preço pendente para aprovar'}), 400
        
        criadores_ids = set()
        for preco in precos_pendentes:
            preco.status = 'ativo'
            preco.updated_by = usuario_id
            preco.updated_at = datetime.utcnow()
            if preco.created_by:
                criadores_ids.add(preco.created_by)
        
        fornecedor.tabela_preco_status = 'aprovada'
        fornecedor.tabela_preco_aprovada_em = datetime.utcnow()
        fornecedor.tabela_preco_aprovada_por_id = usuario_id
        
        db.session.commit()
        
        for criador_id in criadores_ids:
            criador = Usuario.query.get(criador_id)
            if criador:
                notificacao = Notificacao(
                    usuario_id=criador.id,
                    titulo='Tabela de Preços Aprovada',
                    mensagem=f'Sua tabela de preços para o fornecedor {fornecedor.nome} foi aprovada. O fornecedor já pode ser utilizado em solicitações.',
                    tipo='tabela_precos_aprovada',
                    url=f'/fornecedor-tabela-precos.html?id={fornecedor_id}'
                )
                db.session.add(notificacao)
        
        db.session.commit()
        
        return jsonify({
            'mensagem': f'Tabela de preços aprovada com sucesso. {len(precos_pendentes)} itens aprovados.',
            'fornecedor': fornecedor.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'Erro ao aprovar tabela: {str(e)}')
        return jsonify({'erro': f'Erro ao aprovar tabela: {str(e)}'}), 500

@bp.route('/admin/fornecedor/<int:fornecedor_id>/rejeitar-tabela', methods=['PUT'])
@jwt_required()
@admin_required
def rejeitar_tabela_completa(fornecedor_id):
    """Rejeita a tabela de preços e solicita reenvio"""
    try:
        usuario_id = get_jwt_identity()
        admin = Usuario.query.get(usuario_id)
        
        fornecedor = Fornecedor.query.get(fornecedor_id)
        if not fornecedor:
            return jsonify({'erro': 'Fornecedor não encontrado'}), 404
        
        dados = request.get_json() or {}
        motivo = dados.get('motivo', 'Tabela de preços precisa ser revisada')
        
        precos_pendentes = FornecedorTabelaPrecos.query.filter_by(
            fornecedor_id=fornecedor_id,
            status='pendente_aprovacao'
        ).all()
        
        criadores_ids = set()
        for preco in precos_pendentes:
            preco.status = 'pendente_reenvio'
            preco.updated_by = usuario_id
            preco.updated_at = datetime.utcnow()
            if preco.created_by:
                criadores_ids.add(preco.created_by)
        
        fornecedor.tabela_preco_status = 'pendente_reenvio'
        
        db.session.commit()
        
        for criador_id in criadores_ids:
            criador = Usuario.query.get(criador_id)
            if criador:
                notificacao = Notificacao(
                    usuario_id=criador.id,
                    titulo='Tabela de Preços Rejeitada - Reenvio Necessário',
                    mensagem=f'A tabela de preços do fornecedor {fornecedor.nome} foi rejeitada pelo administrador {admin.nome}. Motivo: {motivo}. Por favor, revise e reenvie.',
                    tipo='tabela_precos_rejeitada',
                    url=f'/fornecedor-tabela-precos.html?id={fornecedor_id}'
                )
                db.session.add(notificacao)
        
        comprador = fornecedor.comprador_responsavel
        if comprador and comprador.id not in criadores_ids:
            notificacao = Notificacao(
                usuario_id=comprador.id,
                titulo='Tabela de Preços Rejeitada - Reenvio Necessário',
                mensagem=f'A tabela de preços do fornecedor {fornecedor.nome} foi rejeitada. Motivo: {motivo}. Por favor, revise e reenvie.',
                tipo='tabela_precos_rejeitada',
                url=f'/fornecedor-tabela-precos.html?id={fornecedor_id}'
            )
            db.session.add(notificacao)
        
        db.session.commit()
        
        return jsonify({
            'mensagem': 'Tabela rejeitada. Notificação enviada ao comprador para reenvio.',
            'fornecedor': fornecedor.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'Erro ao rejeitar tabela: {str(e)}')
        return jsonify({'erro': f'Erro ao rejeitar tabela: {str(e)}'}), 500

@bp.route('/fornecedores-aprovados', methods=['GET'])
@jwt_required()
def listar_fornecedores_aprovados():
    """Lista apenas fornecedores com tabela de preços aprovada"""
    try:
        usuario_id = get_jwt_identity()
        usuario = Usuario.query.get(usuario_id)
        
        if not usuario:
            return jsonify({'erro': 'Usuário não encontrado'}), 404
        
        query = Fornecedor.query.filter_by(
            ativo=True,
            tabela_preco_status='aprovada'
        )
        
        if usuario.tipo != 'admin':
            query = query.filter(Fornecedor.comprador_responsavel_id == usuario_id)
        
        fornecedores = query.all()
        
        return jsonify([f.to_dict() for f in fornecedores]), 200
        
    except Exception as e:
        logger.error(f'Erro ao listar fornecedores aprovados: {str(e)}')
        return jsonify({'erro': f'Erro ao listar fornecedores aprovados: {str(e)}'}), 500

@bp.route('/fornecedor/<int:fornecedor_id>/itens-aprovados', methods=['GET'])
@jwt_required()
def listar_itens_aprovados_fornecedor(fornecedor_id):
    """Lista os itens da tabela de preços aprovada de um fornecedor para uso em solicitações"""
    try:
        fornecedor = Fornecedor.query.get(fornecedor_id)
        if not fornecedor:
            return jsonify({'erro': 'Fornecedor não encontrado'}), 404
        
        if fornecedor.tabela_preco_status != 'aprovada':
            return jsonify({'erro': 'Este fornecedor não possui tabela de preços aprovada'}), 400
        
        precos_ativos = FornecedorTabelaPrecos.query.filter_by(
            fornecedor_id=fornecedor_id,
            status='ativo'
        ).all()
        
        itens = []
        for preco in precos_ativos:
            itens.append({
                'material_id': preco.material_id,
                'material_nome': preco.material.nome if preco.material else None,
                'material_codigo': preco.material.codigo if preco.material else None,
                'material_classificacao': preco.material.classificacao if preco.material else None,
                'preco_fornecedor': float(preco.preco_fornecedor) if preco.preco_fornecedor else 0
            })
        
        return jsonify({
            'fornecedor': {
                'id': fornecedor.id,
                'nome': fornecedor.nome
            },
            'itens': itens
        }), 200
        
    except Exception as e:
        logger.error(f'Erro ao listar itens aprovados: {str(e)}')
        return jsonify({'erro': f'Erro ao listar itens: {str(e)}'}), 500
