from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, ModeloTabelaPreco, ModeloTabelaPrecoItem, MaterialBase, Usuario
from app.auth import admin_required
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('modelos_tabela_preco', __name__, url_prefix='/api/modelos-tabela-preco')


def verificar_permissao_modelos(usuario, acao='visualizar'):
    """Verifica se o usuário tem permissão para operar modelos de tabela"""
    if not usuario:
        return False
    # Admin tem acesso total
    if usuario.tipo == 'admin':
        return True
    # Verificar permissão específica no perfil
    if usuario.perfil and usuario.perfil.permissoes:
        permissoes = usuario.perfil.permissoes
        if acao == 'visualizar':
            return permissoes.get('modulo_modelos_tabela', False) or permissoes.get('modelo_tabela_visualizar', False)
        elif acao == 'criar':
            return permissoes.get('modelo_tabela_criar', False)
        elif acao == 'editar':
            return permissoes.get('modelo_tabela_editar', False)
        elif acao == 'excluir':
            return permissoes.get('modelo_tabela_excluir', False)
        elif acao == 'aplicar':
            return permissoes.get('modelo_tabela_aplicar', False) or permissoes.get('modulo_modelos_tabela', False)
    return False


@bp.route('', methods=['GET'])
@jwt_required()
def listar_modelos():
    """Lista todos os modelos de tabela de preço ativos"""
    try:
        usuario_id = get_jwt_identity()
        usuario = Usuario.query.get(usuario_id)

        if not usuario:
            return jsonify({'erro': 'Usuário não encontrado'}), 404

        # Para listagem na tela de fornecedor (aplicar modelo), qualquer usuário autenticado pode ver
        # Para a tela de gerenciamento, a permissão é verificada no frontend
        apenas_ativos = request.args.get('apenas_ativos', 'true').lower() == 'true'

        query = ModeloTabelaPreco.query
        if apenas_ativos:
            query = query.filter_by(ativo=True)

        modelos = query.order_by(ModeloTabelaPreco.nome).all()

        return jsonify([m.to_dict() for m in modelos]), 200

    except Exception as e:
        logger.error(f'Erro ao listar modelos de tabela: {str(e)}')
        return jsonify({'erro': f'Erro ao listar modelos: {str(e)}'}), 500


@bp.route('/<int:modelo_id>', methods=['GET'])
@jwt_required()
def obter_modelo(modelo_id):
    """Obtém um modelo com todos os itens"""
    try:
        usuario_id = get_jwt_identity()
        usuario = Usuario.query.get(usuario_id)

        if not usuario:
            return jsonify({'erro': 'Usuário não encontrado'}), 404

        modelo = ModeloTabelaPreco.query.get(modelo_id)
        if not modelo:
            return jsonify({'erro': 'Modelo não encontrado'}), 404

        return jsonify(modelo.to_dict_com_itens()), 200

    except Exception as e:
        logger.error(f'Erro ao obter modelo: {str(e)}')
        return jsonify({'erro': f'Erro ao obter modelo: {str(e)}'}), 500


@bp.route('', methods=['POST'])
@jwt_required()
def criar_modelo():
    """Cria um novo modelo de tabela de preço com itens"""
    try:
        usuario_id = get_jwt_identity()
        usuario = Usuario.query.get(usuario_id)

        if not verificar_permissao_modelos(usuario, 'criar'):
            return jsonify({'erro': 'Sem permissão para criar modelos'}), 403

        dados = request.get_json()

        if not dados.get('nome'):
            return jsonify({'erro': 'Nome do modelo é obrigatório'}), 400

        # Verificar nome duplicado
        existente = ModeloTabelaPreco.query.filter_by(nome=dados['nome']).first()
        if existente:
            return jsonify({'erro': 'Já existe um modelo com este nome'}), 400

        itens = dados.get('itens', [])
        if not itens:
            return jsonify({'erro': 'O modelo deve ter pelo menos um material com preço'}), 400

        # Criar modelo
        modelo = ModeloTabelaPreco(
            nome=dados['nome'],
            descricao=dados.get('descricao', ''),
            ativo=True,
            created_by=usuario_id
        )
        db.session.add(modelo)
        db.session.flush()  # Obter o ID

        # Criar itens
        erros = []
        itens_criados = 0
        for idx, item in enumerate(itens):
            try:
                material_id = item.get('material_id')
                preco = item.get('preco_por_kg', 0)

                if not material_id:
                    erros.append(f'Item {idx + 1}: Material é obrigatório')
                    continue

                material = MaterialBase.query.get(material_id)
                if not material:
                    erros.append(f'Item {idx + 1}: Material não encontrado')
                    continue

                preco_float = float(preco) if preco else 0.0
                if preco_float < 0:
                    erros.append(f'Item {idx + 1}: Preço não pode ser negativo')
                    continue

                novo_item = ModeloTabelaPrecoItem(
                    modelo_id=modelo.id,
                    material_id=material_id,
                    preco_por_kg=preco_float
                )
                db.session.add(novo_item)
                itens_criados += 1

            except Exception as e:
                erros.append(f'Item {idx + 1}: {str(e)}')

        if itens_criados == 0:
            db.session.rollback()
            return jsonify({'erro': 'Nenhum item válido para criar o modelo', 'erros': erros}), 400

        db.session.commit()

        logger.info(f'Modelo de tabela "{modelo.nome}" criado por {usuario.nome} com {itens_criados} itens')

        return jsonify({
            'mensagem': f'Modelo criado com sucesso com {itens_criados} materiais',
            'modelo': modelo.to_dict_com_itens(),
            'erros': erros
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f'Erro ao criar modelo: {str(e)}')
        return jsonify({'erro': f'Erro ao criar modelo: {str(e)}'}), 500


@bp.route('/<int:modelo_id>', methods=['PUT'])
@jwt_required()
def atualizar_modelo(modelo_id):
    """Atualiza um modelo e seus itens"""
    try:
        usuario_id = get_jwt_identity()
        usuario = Usuario.query.get(usuario_id)

        if not verificar_permissao_modelos(usuario, 'editar'):
            return jsonify({'erro': 'Sem permissão para editar modelos'}), 403

        modelo = ModeloTabelaPreco.query.get(modelo_id)
        if not modelo:
            return jsonify({'erro': 'Modelo não encontrado'}), 404

        dados = request.get_json()

        # Atualizar dados básicos
        if 'nome' in dados and dados['nome'] != modelo.nome:
            existente = ModeloTabelaPreco.query.filter(
                ModeloTabelaPreco.nome == dados['nome'],
                ModeloTabelaPreco.id != modelo_id
            ).first()
            if existente:
                return jsonify({'erro': 'Já existe outro modelo com este nome'}), 400
            modelo.nome = dados['nome']

        if 'descricao' in dados:
            modelo.descricao = dados['descricao']

        if 'ativo' in dados:
            modelo.ativo = dados['ativo']

        # Atualizar itens se enviados
        if 'itens' in dados:
            itens = dados['itens']

            # Remover itens antigos
            ModeloTabelaPrecoItem.query.filter_by(modelo_id=modelo_id).delete()

            # Criar novos
            erros = []
            itens_criados = 0
            for idx, item in enumerate(itens):
                try:
                    material_id = item.get('material_id')
                    preco = item.get('preco_por_kg', 0)

                    if not material_id:
                        erros.append(f'Item {idx + 1}: Material é obrigatório')
                        continue

                    material = MaterialBase.query.get(material_id)
                    if not material:
                        erros.append(f'Item {idx + 1}: Material não encontrado')
                        continue

                    preco_float = float(preco) if preco else 0.0
                    if preco_float < 0:
                        erros.append(f'Item {idx + 1}: Preço não pode ser negativo')
                        continue

                    novo_item = ModeloTabelaPrecoItem(
                        modelo_id=modelo.id,
                        material_id=material_id,
                        preco_por_kg=preco_float
                    )
                    db.session.add(novo_item)
                    itens_criados += 1

                except Exception as e:
                    erros.append(f'Item {idx + 1}: {str(e)}')

        modelo.updated_by = usuario_id
        modelo.updated_at = datetime.utcnow()
        db.session.commit()

        logger.info(f'Modelo de tabela "{modelo.nome}" atualizado por {usuario.nome}')

        return jsonify({
            'mensagem': 'Modelo atualizado com sucesso',
            'modelo': modelo.to_dict_com_itens()
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f'Erro ao atualizar modelo: {str(e)}')
        return jsonify({'erro': f'Erro ao atualizar modelo: {str(e)}'}), 500


@bp.route('/<int:modelo_id>', methods=['DELETE'])
@jwt_required()
def excluir_modelo(modelo_id):
    """Desativa um modelo (soft delete)"""
    try:
        usuario_id = get_jwt_identity()
        usuario = Usuario.query.get(usuario_id)

        if not verificar_permissao_modelos(usuario, 'excluir'):
            return jsonify({'erro': 'Sem permissão para excluir modelos'}), 403

        modelo = ModeloTabelaPreco.query.get(modelo_id)
        if not modelo:
            return jsonify({'erro': 'Modelo não encontrado'}), 404

        modelo.ativo = False
        modelo.updated_by = usuario_id
        modelo.updated_at = datetime.utcnow()
        db.session.commit()

        logger.info(f'Modelo de tabela "{modelo.nome}" desativado por {usuario.nome}')

        return jsonify({'mensagem': f'Modelo "{modelo.nome}" desativado com sucesso'}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f'Erro ao excluir modelo: {str(e)}')
        return jsonify({'erro': f'Erro ao excluir modelo: {str(e)}'}), 500


@bp.route('/<int:modelo_id>/ativar', methods=['PUT'])
@jwt_required()
def ativar_modelo(modelo_id):
    """Reativa um modelo desativado"""
    try:
        usuario_id = get_jwt_identity()
        usuario = Usuario.query.get(usuario_id)

        if not verificar_permissao_modelos(usuario, 'editar'):
            return jsonify({'erro': 'Sem permissão para ativar modelos'}), 403

        modelo = ModeloTabelaPreco.query.get(modelo_id)
        if not modelo:
            return jsonify({'erro': 'Modelo não encontrado'}), 404

        modelo.ativo = True
        modelo.updated_by = usuario_id
        modelo.updated_at = datetime.utcnow()
        db.session.commit()

        logger.info(f'Modelo de tabela "{modelo.nome}" reativado por {usuario.nome}')

        return jsonify({'mensagem': f'Modelo "{modelo.nome}" ativado com sucesso'}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f'Erro ao ativar modelo: {str(e)}')
        return jsonify({'erro': f'Erro ao ativar modelo: {str(e)}'}), 500


@bp.route('/<int:modelo_id>/duplicar', methods=['POST'])
@jwt_required()
def duplicar_modelo(modelo_id):
    """Duplica um modelo existente com novo nome"""
    try:
        usuario_id = get_jwt_identity()
        usuario = Usuario.query.get(usuario_id)

        if not verificar_permissao_modelos(usuario, 'criar'):
            return jsonify({'erro': 'Sem permissão para duplicar modelos'}), 403

        modelo_original = ModeloTabelaPreco.query.get(modelo_id)
        if not modelo_original:
            return jsonify({'erro': 'Modelo original não encontrado'}), 404

        dados = request.get_json() or {}
        novo_nome = dados.get('nome', f'{modelo_original.nome} (Cópia)')

        # Verificar nome duplicado
        existente = ModeloTabelaPreco.query.filter_by(nome=novo_nome).first()
        if existente:
            # Gerar nome único
            contador = 2
            while True:
                nome_tentativa = f'{modelo_original.nome} (Cópia {contador})'
                if not ModeloTabelaPreco.query.filter_by(nome=nome_tentativa).first():
                    novo_nome = nome_tentativa
                    break
                contador += 1

        # Criar cópia
        novo_modelo = ModeloTabelaPreco(
            nome=novo_nome,
            descricao=modelo_original.descricao,
            ativo=True,
            created_by=usuario_id
        )
        db.session.add(novo_modelo)
        db.session.flush()

        # Copiar itens
        for item in modelo_original.itens:
            novo_item = ModeloTabelaPrecoItem(
                modelo_id=novo_modelo.id,
                material_id=item.material_id,
                preco_por_kg=item.preco_por_kg
            )
            db.session.add(novo_item)

        db.session.commit()

        logger.info(f'Modelo "{modelo_original.nome}" duplicado como "{novo_nome}" por {usuario.nome}')

        return jsonify({
            'mensagem': f'Modelo duplicado com sucesso como "{novo_nome}"',
            'modelo': novo_modelo.to_dict_com_itens()
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f'Erro ao duplicar modelo: {str(e)}')
        return jsonify({'erro': f'Erro ao duplicar modelo: {str(e)}'}), 500
