from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import Solicitacao, ItemSolicitacao, Fornecedor, TipoLote, FornecedorTipoLotePreco, FornecedorTipoLoteClassificacao, db, Usuario, Lote, OrdemCompra, Notificacao, Perfil, MaterialBase, TabelaPreco, TabelaPrecoItem
from app.auth import admin_required
from app.utils.auditoria import registrar_auditoria_oc
from app import socketio
from datetime import datetime
import os

bp = Blueprint('solicitacoes', __name__, url_prefix='/api/solicitacoes')

def _criar_oc_e_lotes(solicitacao, usuario_id, data_request=None):
    """
    Função auxiliar para criar OC e lotes a partir de uma solicitação aprovada.
    Usada tanto na aprovação automática quanto na aprovação manual.
    
    Args:
        solicitacao: Objeto Solicitacao já aprovado
        usuario_id: ID do usuário que aprovou (ou None para aprovação automática)
        data_request: Dados da requisição (opcional)
        
    Returns:
        tuple: (oc, lotes_criados) onde oc é o objeto OrdemCompra e lotes_criados é lista de números de lote
    """
    if data_request is None:
        data_request = {}
    
    print(f"\n{'='*60}")
    print(f" CRIANDO OC E LOTES PARA SOLICITAÇÃO #{solicitacao.id}")
    print(f"{'='*60}")
    
    if not solicitacao.itens or len(solicitacao.itens) == 0:
        raise ValueError('Solicitação não possui itens')
    
    itens_sem_preco = [item for item in solicitacao.itens if item.valor_calculado is None or item.valor_calculado < 0]
    if itens_sem_preco:
        raise ValueError(f'Existem {len(itens_sem_preco)} itens sem preço configurado ou com valor inválido')
    
    oc_existente = OrdemCompra.query.filter_by(solicitacao_id=solicitacao.id).first()
    if oc_existente:
        print(f" ⚠️ OC já existe: #{oc_existente.id} - pulando criação")
        return oc_existente, []
    
    valor_total_oc = sum((item.valor_calculado or 0.0) for item in solicitacao.itens)
    print(f" Valor total calculado: R$ {valor_total_oc:.2f}")
    
    if valor_total_oc < 0:
        raise ValueError('Valor total da OC não pode ser negativo')
    
    print(f"\n ETAPA 1: Criando Ordem de Compra...")
    oc = OrdemCompra(
        solicitacao_id=solicitacao.id,
        fornecedor_id=solicitacao.fornecedor_id,
        valor_total=valor_total_oc,
        status='em_analise',
        criado_por=usuario_id,
        observacao=data_request.get('observacao', f'OC gerada automaticamente pela aprovação da solicitação #{solicitacao.id}')
    )
    db.session.add(oc)
    db.session.flush()
    
    print(f" ✓ OC #{oc.id} criada com sucesso")
    print(f"   Status: {oc.status}")
    print(f"   Valor: R$ {oc.valor_total:.2f}")
    
    print(f"\n ETAPA 2: Criando lotes...")
    
    lotes_agrupados = {}
    
    for item in solicitacao.itens:
        if item.material_id:
            chave = ('material', item.material_id, item.estrelas_final)
        elif item.tipo_lote_id:
            chave = ('tipo_lote', item.tipo_lote_id, item.estrelas_final)
        else:
            print(f"    ⚠️ Item {item.id} sem material_id nem tipo_lote_id - pulando")
            continue
        
        if chave not in lotes_agrupados:
            lotes_agrupados[chave] = []
        lotes_agrupados[chave].append(item)
    
    lotes_criados = []
    
    for chave, itens in lotes_agrupados.items():
        tipo_chave, id_referencia, estrelas = chave
        
        peso_total = sum(item.peso_kg for item in itens)
        valor_total = sum((item.valor_calculado or 0.0) for item in itens)
        estrelas_media = sum((item.estrelas_final or 3) for item in itens) / len(itens)
        
        classificacoes = [item.classificacao for item in itens if item.classificacao]
        classificacao_predominante = max(set(classificacoes), key=classificacoes.count) if classificacoes else None
        
        if tipo_chave == 'material':
            material = MaterialBase.query.get(id_referencia)
            tipo_lote_id = 1
            print(f"    Criando lote para material: {material.nome if material else id_referencia}")
        else:
            tipo_lote_id = id_referencia
            print(f"    Criando lote para tipo_lote_id: {tipo_lote_id}")
        
        lote = Lote(
            fornecedor_id=solicitacao.fornecedor_id,
            tipo_lote_id=tipo_lote_id,
            solicitacao_origem_id=solicitacao.id,
            peso_total_kg=peso_total,
            valor_total=valor_total,
            quantidade_itens=len(itens),
            estrelas_media=estrelas_media,
            classificacao_predominante=classificacao_predominante,
            tipo_retirada=solicitacao.tipo_retirada,
            status='aberto'
        )
        db.session.add(lote)
        db.session.flush()
        
        print(f"    ✓ Lote criado: {lote.numero_lote} (Estrelas: {estrelas}, Itens: {len(itens)})")
        lotes_criados.append(lote.numero_lote)
        
        for item in itens:
            item.lote_id = lote.id
    
    print(f" ✓ {len(lotes_criados)} lote(s) criado(s): {', '.join(lotes_criados)}")
    
    print(f"\n ETAPA 3: Registrando auditoria da OC...")
    if usuario_id:
        ip = request.headers.get('X-Forwarded-For', request.remote_addr) if request else None
        gps = data_request.get('gps')
        dispositivo = request.headers.get('User-Agent', '') if request else 'Sistema'
        
        registrar_auditoria_oc(
            oc_id=oc.id,
            usuario_id=usuario_id,
            acao='criacao',
            status_anterior=None,
            status_novo='em_analise',
            observacao=f'OC criada automaticamente pela aprovação da solicitação #{solicitacao.id}',
            ip=ip,
            gps=gps,
            dispositivo=dispositivo
        )
        print(f" ✓ Auditoria registrada")
    else:
        print(f" ⚠️ Auditoria não registrada (sem usuario_id)")
    
    print(f"{'='*60}\n")
    
    return oc, lotes_criados

@bp.route('/fornecedor/<int:fornecedor_id>/materiais', methods=['GET'])
@jwt_required()
def listar_materiais_fornecedor(fornecedor_id):
    """
    Retorna todos os materiais disponíveis com preços da tabela personalizada do fornecedor.
    Busca os preços na tabela FornecedorTabelaPrecos (preços específicos por fornecedor/material).
    IMPORTANTE: Só retorna materiais se o fornecedor tiver tabela de preços APROVADA.
    """
    try:
        from app.models import FornecedorTabelaPrecos
        
        fornecedor = Fornecedor.query.get(fornecedor_id)
        
        if not fornecedor:
            return jsonify({'erro': 'Fornecedor não encontrado'}), 404
        
        # Verificar se o fornecedor tem tabela de preços APROVADA
        if fornecedor.tabela_preco_status != 'aprovada':
            return jsonify({'erro': 'Este fornecedor não possui tabela de preços aprovada. Solicite ao administrador a aprovação da tabela.'}), 400
        
        # Buscar preços ativos na tabela personalizada do fornecedor
        precos_fornecedor = FornecedorTabelaPrecos.query.filter_by(
            fornecedor_id=fornecedor_id,
            status='ativo'
        ).join(MaterialBase).filter(MaterialBase.ativo == True).all()
        
        if not precos_fornecedor:
            return jsonify({'erro': 'Fornecedor não possui materiais com preços configurados'}), 400
        
        materiais = []
        for preco in precos_fornecedor:
            material_dict = {
                'id': preco.material_id,
                'codigo': preco.material.codigo,
                'nome': preco.material.nome,
                'classificacao': preco.material.classificacao,
                'descricao': preco.material.descricao,
                'preco_unitario': float(preco.preco_fornecedor) if preco.preco_fornecedor else 0.0
            }
            materiais.append(material_dict)
        
        return jsonify({
            'fornecedor_id': fornecedor.id,
            'fornecedor_nome': fornecedor.nome,
            'materiais': materiais,
            'total': len(materiais)
        }), 200
        
    except Exception as e:
        return jsonify({'erro': f'Erro ao buscar materiais: {str(e)}'}), 500

def calcular_valor_item_novo(fornecedor_id, material_id, peso_kg):
    """
    Função de cálculo que busca o preço do material na tabela personalizada do fornecedor.
    Usa FornecedorTabelaPrecos - preços específicos por fornecedor/material, SEM estrelas.
    
    Args:
        fornecedor_id: ID do fornecedor
        material_id: ID do material
        peso_kg: Peso em kg
        
    Returns:
        tuple: (valor_calculado, preco_por_kg, estrelas) - estrelas sempre 3 (padrão válido)
    """
    from app.models import FornecedorTabelaPrecos
    
    fornecedor = Fornecedor.query.get(fornecedor_id)
    
    if not fornecedor:
        print(f"       Fornecedor não encontrado")
        return (0.0, 0.0, 3)
    
    # Buscar preço na tabela personalizada do fornecedor
    preco_fornecedor = FornecedorTabelaPrecos.query.filter_by(
        fornecedor_id=fornecedor_id,
        material_id=material_id,
        status='ativo'
    ).first()
    
    if not preco_fornecedor:
        print(f"       Preço não encontrado para material {material_id} na tabela do fornecedor {fornecedor_id}")
        return (0.0, 0.0, 3)
    
    preco_kg = float(preco_fornecedor.preco_fornecedor) if preco_fornecedor.preco_fornecedor else 0.0
    valor = preco_kg * float(peso_kg)
    
    print(f"       Preço encontrado: R$ {preco_kg}/kg × {peso_kg}kg = R$ {valor:.2f}")
    
    return (valor, preco_kg, 3)

def calcular_valor_item(fornecedor_id, tipo_lote_id, classificacao, estrelas_from_frontend, peso_kg):
    """Calcula o valor de um item baseado no preço configurado

    Args:
        fornecedor_id: ID do fornecedor
        tipo_lote_id: ID do tipo de lote
        classificacao: Classificação do item (leve/medio/pesado)
        estrelas_from_frontend: Estrelas sugeridas pelo frontend (fallback)
        peso_kg: Peso em kg

    Returns:
        tuple: (valor_calculado, preco_por_kg, estrelas_usadas)
    """
    from app.models import TipoLotePreco

    # Primeiro tenta usar a configuração de classificação do fornecedor
    estrelas_final = estrelas_from_frontend

    classificacao_config = FornecedorTipoLoteClassificacao.query.filter_by(
        fornecedor_id=fornecedor_id,
        tipo_lote_id=tipo_lote_id,
        ativo=True
    ).first()

    if classificacao_config and classificacao:
        estrelas_final = classificacao_config.get_estrelas_por_classificacao(classificacao)
        print(f"       Usando estrelas da configuração: {estrelas_final} (classificação: {classificacao})")
    else:
        print(f"       Usando estrelas do frontend: {estrelas_final}")

    # Busca o preço na tabela TipoLotePreco (tabela global de preços)
    preco = TipoLotePreco.query.filter_by(
        tipo_lote_id=tipo_lote_id,
        classificacao=classificacao,
        estrelas=estrelas_final,
        ativo=True
    ).first()

    if not preco:
        print(f"       Preço não encontrado em TipoLotePreco!")
        print(f"       Buscando preços disponíveis para tipo_lote={tipo_lote_id}, classificacao={classificacao}...")

        # Lista todos os preços disponíveis para debug
        precos_disponiveis = TipoLotePreco.query.filter_by(
            tipo_lote_id=tipo_lote_id,
            classificacao=classificacao,
            ativo=True
        ).all()

        if precos_disponiveis:
            print(f"       Preços cadastrados para classificação '{classificacao}':")
            for p in precos_disponiveis:
                print(f"         - {p.estrelas} estrelas: R$ {p.preco_por_kg}/kg")
        else:
            print(f"       Nenhum preço cadastrado para tipo_lote={tipo_lote_id}, classificacao={classificacao}")

        return (0.0, 0.0, estrelas_final)

    valor = preco.preco_por_kg * float(peso_kg)
    print(f"       Preço encontrado: R$ {preco.preco_por_kg}/kg × {peso_kg}kg = R$ {valor:.2f}")

    return (valor, preco.preco_por_kg, estrelas_final)

@bp.route('', methods=['GET'])
@jwt_required()
def listar_solicitacoes():
    try:
        usuario_id = int(get_jwt_identity())
        usuario = Usuario.query.get(usuario_id)

        status = request.args.get('status', '')
        fornecedor_id = request.args.get('fornecedor_id', type=int)

        query = Solicitacao.query

        if usuario and usuario.tipo != 'admin':
            query = query.filter_by(funcionario_id=usuario.id)

        if status:
            query = query.filter_by(status=status)

        if fornecedor_id:
            query = query.filter_by(fornecedor_id=fornecedor_id)

        solicitacoes = query.order_by(Solicitacao.data_envio.desc()).all()

        resultado = []
        for sol in solicitacoes:
            sol_dict = sol.to_dict()
            sol_dict['itens'] = [item.to_dict() for item in sol.itens]
            resultado.append(sol_dict)

        return jsonify(resultado), 200

    except Exception as e:
        return jsonify({'erro': f'Erro ao listar solicitações: {str(e)}'}), 500

@bp.route('/<int:id>', methods=['GET'])
@jwt_required()
def obter_solicitacao(id):
    try:
        solicitacao = Solicitacao.query.get(id)

        if not solicitacao:
            return jsonify({'erro': 'Solicitação não encontrada'}), 404

        sol_dict = solicitacao.to_dict()
        sol_dict['itens'] = [item.to_dict() for item in solicitacao.itens]

        return jsonify(sol_dict), 200

    except Exception as e:
        return jsonify({'erro': f'Erro ao obter solicitação: {str(e)}'}), 500

@bp.route('', methods=['POST'])
@jwt_required()
def criar_solicitacao():
    try:
        usuario_id = int(get_jwt_identity())
        usuario = Usuario.query.get(usuario_id)

        if not usuario:
            return jsonify({'erro': 'Usuário não encontrado'}), 404

        data = request.get_json()

        if not data:
            return jsonify({'erro': 'Dados não fornecidos'}), 400

        if not data.get('fornecedor_id'):
            return jsonify({'erro': 'Fornecedor é obrigatório'}), 400

        if not data.get('itens') or not isinstance(data['itens'], list) or len(data['itens']) == 0:
            return jsonify({'erro': 'Pelo menos um item é obrigatório'}), 400

        fornecedor = Fornecedor.query.get(data['fornecedor_id'])
        if not fornecedor:
            return jsonify({'erro': 'Fornecedor não encontrado'}), 404

        # Determinar se a solicitação será aprovada automaticamente ou ficará pendente
        # Inicialmente assumir que NÃO requer aprovação manual (será auto-aprovada)
        # IMPORTANTE: Uma vez setado como True, nunca volta para False (flag latched)
        requer_aprovacao_manual = False

        solicitacao = Solicitacao(
            funcionario_id=usuario.id,
            fornecedor_id=data['fornecedor_id'],
            tipo_retirada=data.get('tipo_retirada', 'buscar'),
            observacoes=data.get('observacoes', ''),
            status='pendente'  # Será atualizado para 'aprovada' ou 'pendente' após processar todos os itens
        )

        db.session.add(solicitacao)
        db.session.flush()

        print(f"\n{'='*60}")
        print(f" CRIANDO SOLICITAÇÃO #{solicitacao.id}")
        print(f"   Fornecedor: {fornecedor.nome}")
        print(f"   Total de itens recebidos: {len(data['itens'])}")
        print(f"{'='*60}")

        for item_data in data['itens']:
            print(f"\n Item recebido do frontend:")
            print(f"   {item_data}")

            # VALIDAÇÃO CRÍTICA: Peso deve ser positivo
            if not item_data.get('peso_kg') or float(item_data.get('peso_kg', 0)) <= 0:
                db.session.rollback()
                return jsonify({'erro': f'Peso inválido ({item_data.get("peso_kg", 0)} kg). Todos os itens devem ter peso maior que zero.'}), 400

            # NOVO FORMATO: usando material_id (alinhado com Fluxo_comprador.md)
            if item_data.get('material_id'):
                print(f"    Usando NOVO formato (material_id)")
                
                material_id = item_data['material_id']
                material = MaterialBase.query.get(material_id)
                
                if not material:
                    print(f"    Material não encontrado - pulando")
                    continue
                
                print(f"    Material: {material.nome} (Classificação: {material.classificacao})")
                
                # Verificar se usa preço customizado
                preco_customizado = item_data.get('preco_customizado', False)
                preco_oferecido = item_data.get('preco_oferecido')
                
                if preco_customizado and preco_oferecido is not None:
                    print(f"    Usando PREÇO CUSTOMIZADO: R$ {preco_oferecido}/kg")
                    
                    # VALIDAÇÃO CRÍTICA: Preço oferecido deve ser > 0
                    if float(preco_oferecido) <= 0:
                        db.session.rollback()
                        return jsonify({'erro': f'Preço oferecido inválido (R$ {preco_oferecido}/kg). O preço deve ser maior que zero.'}), 400
                    
                    # Buscar o preço da tabela para comparação
                    _, preco_tabela, tabela_estrelas = calcular_valor_item_novo(
                        data['fornecedor_id'],
                        material_id,
                        item_data['peso_kg']
                    )
                    
                    # Validar que o material tem preço configurado na tabela
                    if preco_tabela <= 0:
                        print(f"    ⚠️ Material sem preço configurado na tabela - REQUER APROVAÇÃO MANUAL")
                        requer_aprovacao_manual = True  # Flag latched - uma vez True, sempre True
                        preco_tabela = 0
                        tabela_estrelas = 3  # Valor padrão válido (entre 1 e 5)
                    
                    print(f"    Preço da tabela ({tabela_estrelas}★): R$ {preco_tabela}/kg")
                    print(f"    Preço oferecido: R$ {preco_oferecido}/kg")
                    
                    # Calcular valor com preço oferecido
                    valor = float(preco_oferecido) * float(item_data['peso_kg'])
                    
                    # Verificar se precisa aprovação manual (apenas se preço da tabela é válido)
                    if preco_tabela > 0 and float(preco_oferecido) > float(preco_tabela):
                        print(f"    ⚠️ Preço oferecido MAIOR que tabela - REQUER APROVAÇÃO MANUAL")
                        requer_aprovacao_manual = True  # Flag latched - uma vez True, sempre True
                    elif preco_tabela > 0:
                        print(f"    ✓ Preço oferecido menor ou igual à tabela - aprovação automática")
                    
                    item = ItemSolicitacao(
                        solicitacao_id=solicitacao.id,
                        material_id=material_id,
                        peso_kg=float(item_data['peso_kg']),
                        classificacao=material.classificacao,
                        estrelas_sugeridas_ia=item_data.get('estrelas_sugeridas_ia'),
                        estrelas_final=tabela_estrelas,
                        valor_calculado=valor,
                        preco_por_kg_snapshot=float(preco_oferecido),
                        estrelas_snapshot=tabela_estrelas,
                        preco_customizado=True,
                        preco_oferecido=float(preco_oferecido),
                        imagem_url=item_data.get('imagem_url', ''),
                        observacoes=item_data.get('observacoes', '')
                    )
                    
                    print(f"    Item salvo: Material={material.nome}, Valor=R$ {item.valor_calculado:.2f}, Preço custom=R$ {preco_oferecido}/kg")
                else:
                    # Usar preço da tabela (comportamento padrão)
                    print(f"    Calculando valor usando tabela do fornecedor...")
                    
                    valor, preco_por_kg, tabela_estrelas = calcular_valor_item_novo(
                        data['fornecedor_id'],
                        material_id,
                        item_data['peso_kg']
                    )
                    
                    # VALIDAÇÃO: Material deve ter preço configurado na tabela
                    if preco_por_kg <= 0:
                        print(f"    ⚠️ Material sem preço configurado na tabela - REQUER APROVAÇÃO MANUAL")
                        requer_aprovacao_manual = True  # Flag latched - uma vez True, sempre True
                        preco_por_kg = 0
                        tabela_estrelas = 3  # Valor padrão válido (entre 1 e 5)
                        valor = 0
                    
                    print(f"    Valor final: R$ {valor:.2f} (Tabela: {tabela_estrelas}★)")
                    if preco_por_kg > 0:
                        print(f"    ✓ Usando preço da tabela - aprovação automática")
                    else:
                        print(f"    ⚠️ Preço inválido - solicitação requer aprovação manual")
                    
                    item = ItemSolicitacao(
                        solicitacao_id=solicitacao.id,
                        material_id=material_id,
                        peso_kg=float(item_data['peso_kg']),
                        classificacao=material.classificacao,
                        estrelas_sugeridas_ia=item_data.get('estrelas_sugeridas_ia'),
                        estrelas_final=tabela_estrelas,
                        valor_calculado=valor,
                        preco_por_kg_snapshot=preco_por_kg,
                        estrelas_snapshot=tabela_estrelas,
                        preco_customizado=False,
                        preco_oferecido=None,
                        imagem_url=item_data.get('imagem_url', ''),
                        observacoes=item_data.get('observacoes', '')
                    )
                    
                    print(f"    Item salvo: Material={material.nome}, Valor=R$ {item.valor_calculado:.2f}, Tabela={tabela_estrelas}★")
                
                db.session.add(item)
            
            # FORMATO ANTIGO: usando tipo_lote_id + classificacao (retrocompatibilidade)
            elif item_data.get('tipo_lote_id'):
                print(f"    Usando formato ANTIGO (tipo_lote_id + classificacao)")
                
                tipo_lote = TipoLote.query.get(item_data['tipo_lote_id'])
                if not tipo_lote:
                    print(f"    Tipo de lote não encontrado - pulando")
                    continue

                print(f"    Tipo de lote: {tipo_lote.nome}")

                classificacao = item_data.get('classificacao', 'medio')
                estrelas_final = item_data.get('estrelas_final', 3)
                if estrelas_final is None or not (1 <= estrelas_final <= 5):
                    estrelas_final = 3

                print(f"    Classificação: {classificacao}")
                print(f"    Estrelas (frontend): {estrelas_final}")
                print(f"    Calculando valor...")

                valor, preco_por_kg, estrelas_usadas = calcular_valor_item(
                    data['fornecedor_id'],
                    item_data['tipo_lote_id'],
                    classificacao,
                    estrelas_final,
                    item_data['peso_kg']
                )

                print(f"    Valor final: R$ {valor:.2f}")
                print(f"    Estrelas usadas: {estrelas_usadas}")

                item = ItemSolicitacao(
                    solicitacao_id=solicitacao.id,
                    tipo_lote_id=item_data['tipo_lote_id'],
                    peso_kg=float(item_data['peso_kg']),
                    classificacao=classificacao,
                    estrelas_sugeridas_ia=item_data.get('estrelas_sugeridas_ia'),
                    estrelas_final=estrelas_usadas,
                    valor_calculado=valor,
                    preco_por_kg_snapshot=preco_por_kg,
                    estrelas_snapshot=estrelas_usadas,
                    imagem_url=item_data.get('imagem_url', ''),
                    observacoes=item_data.get('observacoes', '')
                )

                print(f"    Item salvo: Valor=R$ {item.valor_calculado:.2f}, Classificação={item.classificacao}, Estrelas={item.estrelas_final}")
                db.session.add(item)
            
            else:
                print(f"    Item inválido - sem material_id nem tipo_lote_id - pulando")
                continue

        # Definir status final da solicitação
        if requer_aprovacao_manual:
            solicitacao.status = 'pendente'
            print(f"\n{'='*60}")
            print(f" STATUS FINAL: PENDENTE (requer aprovação manual)")
            print(f" Motivo: Um ou mais itens têm preço oferecido acima da tabela")
            print(f"{'='*60}")
            
            db.session.commit()
            
            sol_dict = solicitacao.to_dict()
            sol_dict['itens'] = [item.to_dict() for item in solicitacao.itens]
            
            return jsonify(sol_dict), 201
        else:
            solicitacao.status = 'aprovada'
            solicitacao.data_confirmacao = datetime.utcnow()
            print(f"\n{'='*60}")
            print(f" STATUS FINAL: APROVADA AUTOMATICAMENTE")
            print(f" Motivo: Todos os itens usam preço da tabela ou preço oferecido ≤ tabela")
            print(f"{'='*60}")
            
            db.session.flush()
            
            try:
                oc, lotes_criados = _criar_oc_e_lotes(solicitacao, usuario_id, data)
                
                db.session.commit()
                
                sol_dict = solicitacao.to_dict()
                sol_dict['itens'] = [item.to_dict() for item in solicitacao.itens]
                sol_dict['oc_id'] = oc.id
                sol_dict['lotes_criados'] = lotes_criados
                
                print(f"\n{'='*60}")
                print(f" ✅ SOLICITAÇÃO APROVADA AUTOMATICAMENTE E OC #{oc.id} CRIADA")
                print(f" Lotes criados: {', '.join(lotes_criados)}")
                print(f"{'='*60}\n")
                
                return jsonify(sol_dict), 201
                
            except Exception as e:
                print(f"\n❌ ERRO ao criar OC/lotes: {str(e)}")
                db.session.rollback()
                raise

    except ValueError as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': f'Erro ao criar solicitação: {str(e)}'}), 500

@bp.route('/<int:id>/aprovar', methods=['POST'])
@admin_required
def aprovar_solicitacao(id):
    oc = None
    lotes_criados = []
    solicitacao = None
    
    try:
        print(f"\n{'='*60}")
        print(f" INICIANDO APROVAÇÃO DA SOLICITAÇÃO #{id}")
        print(f"{'='*60}")
        
        usuario_id = get_jwt_identity()
        data = request.get_json(silent=True) or {}
        
        print(f"\n FASE 1: Validações preliminares (SEM modificar dados)...")
        
        solicitacao = Solicitacao.query.get(id)
        
        if not solicitacao:
            print(f" Solicitação #{id} não encontrada")
            return jsonify({'erro': 'Solicitação não encontrada'}), 404
        
        print(f" Solicitação encontrada: #{solicitacao.id}")
        print(f"   Status atual: {solicitacao.status}")
        print(f"   Fornecedor: {solicitacao.fornecedor.nome if solicitacao.fornecedor else 'N/A'}")
        
        if solicitacao.status != 'pendente':
            print(f" Status inválido: {solicitacao.status}")
            return jsonify({'erro': f'Solicitação já foi processada (status: {solicitacao.status})'}), 400
        
        if not solicitacao.itens or len(solicitacao.itens) == 0:
            print(f" Solicitação sem itens")
            return jsonify({'erro': 'Solicitação não possui itens'}), 400
        
        print(f" Solicitação possui {len(solicitacao.itens)} itens")
        
        itens_sem_preco = [item for item in solicitacao.itens if item.valor_calculado is None or item.valor_calculado < 0]
        if itens_sem_preco:
            print(f" Existem {len(itens_sem_preco)} itens sem preço configurado ou com valor inválido")
            return jsonify({'erro': f'Existem {len(itens_sem_preco)} itens sem preço configurado ou com valor inválido. Configure os preços antes de aprovar.'}), 400
        
        oc_existente = OrdemCompra.query.filter_by(solicitacao_id=id).first()
        if oc_existente:
            print(f" Já existe OC #{oc_existente.id} para esta solicitação")
            return jsonify({'erro': f'Já existe uma ordem de compra (#{oc_existente.id}) para esta solicitação'}), 400
        
        valor_total_oc = sum((item.valor_calculado or 0.0) for item in solicitacao.itens)
        print(f" Valor total calculado: R$ {valor_total_oc:.2f}")
        
        if valor_total_oc < 0:
            print(f" Valor total negativo")
            return jsonify({'erro': 'Valor total da OC não pode ser negativo'}), 400
        
        print(f" Todas as validações passaram!")
        
        print(f"\n FASE 2: Salvando alterações no banco...")
        
        print(f"\n ETAPA 1: Atualizando status da solicitação...")
        solicitacao.status = 'aprovada'
        solicitacao.data_confirmacao = datetime.utcnow()
        solicitacao.admin_id = usuario_id
        print(f" Status atualizado para: aprovada")
        
        db.session.flush()
        
        oc, lotes_criados = _criar_oc_e_lotes(solicitacao, usuario_id, data)
        
        print(f"\n ETAPA 2: Criando notificações...")
        notificacao_funcionario = Notificacao(
            usuario_id=solicitacao.funcionario_id,
            titulo='Solicitação Aprovada',
            mensagem=f'Sua solicitação #{solicitacao.id} foi aprovada! OC #{oc.id} criada (R$ {oc.valor_total:.2f}) e {len(lotes_criados)} lote(s) gerado(s).',
            url=f'/solicitacoes.html?id={solicitacao.id}'
        )
        db.session.add(notificacao_funcionario)
        print(f"    Notificação para funcionário criada")
        
        usuarios_financeiro = Usuario.query.filter(
            db.and_(
                Usuario.ativo == True,
                db.or_(
                    Usuario.tipo == 'admin',
                    Usuario.perfil.has(Perfil.nome.in_(['Administrador', 'Financeiro']))
                )
            )
        ).all()
        
        usuarios_ids_notificados = set()
        for usuario_fin in usuarios_financeiro:
            if usuario_fin.id not in usuarios_ids_notificados and usuario_fin.id != solicitacao.funcionario_id:
                notificacao_financeiro = Notificacao(
                    usuario_id=usuario_fin.id,
                    titulo='Nova Ordem de Compra - Aprovação Pendente',
                    mensagem=f'OC #{oc.id} gerada (R$ {oc.valor_total:.2f}) da Solicitação #{solicitacao.id} - Fornecedor: {solicitacao.fornecedor.nome}. Aguardando sua aprovação!',
                    url='/compras.html'
                )
                db.session.add(notificacao_financeiro)
                usuarios_ids_notificados.add(usuario_fin.id)
        
        print(f"    {len(usuarios_ids_notificados)} notificações para financeiro/admin criadas")
        
        db.session.commit()
        print(f"\n Transação commitada com sucesso!")
        
        print(f"\n FASE 3: Enviando notificações WebSocket...")
        try:
            socketio.emit('nova_notificacao', {
                'tipo': 'solicitacao_aprovada',
                'solicitacao_id': id,
                'oc_id': oc.id,
                'valor_total': float(oc.valor_total)
            }, room='funcionarios')
            
            socketio.emit('nova_notificacao', {
                'tipo': 'nova_oc',
                'oc_id': oc.id,
                'solicitacao_id': id,
                'valor_total': float(oc.valor_total),
                'fornecedor': solicitacao.fornecedor.nome
            }, room='admins')
            
            print(f" Notificações WebSocket enviadas")
        except Exception as ws_error:
            print(f" Erro ao enviar WebSocket (não crítico): {str(ws_error)}")
        
        print(f"\n{'='*60}")
        print(f" APROVAÇÃO CONCLUÍDA COM SUCESSO!")
        print(f"{'='*60}")
        print(f"   Solicitação: #{solicitacao.id} (aprovada)")
        print(f"   Lotes criados: {len(lotes_criados)}")
        print(f"   OC criada: #{oc.id} (em_analise)")
        print(f"   Valor total: R$ {oc.valor_total:.2f}")
        print(f"{'='*60}\n")
        
        return jsonify({
            'mensagem': 'Solicitação aprovada, lotes criados e Ordem de Compra gerada com sucesso',
            'solicitacao': solicitacao.to_dict(),
            'oc_id': oc.id,
            'oc_status': oc.status,
            'lotes_criados': lotes_criados,
            'valor_total': oc.valor_total
        }), 200
    
    except Exception as e:
        db.session.rollback()
        print(f"\n{'='*60}")
        print(f" ERRO AO APROVAR SOLICITAÇÃO #{id}")
        print(f"{'='*60}")
        print(f"Erro: {str(e)}")
        import traceback
        traceback.print_exc()
        print(f"{'='*60}\n")
        return jsonify({'erro': f'Erro ao aprovar solicitação: {str(e)}'}), 500

@bp.route('/<int:id>/aprovar-e-promover', methods=['POST'])
@admin_required
def aprovar_e_promover_solicitacao(id):
    """
    Aprova a solicitação E promove o fornecedor (aumenta a tabela de preço).
    Promoção: 1★ → 2★ ou 2★ → 3★ (máximo 3★)
    """
    try:
        print(f"\n{'='*60}")
        print(f" INICIANDO APROVAÇÃO COM PROMOÇÃO - SOLICITAÇÃO #{id}")
        print(f"{'='*60}")
        
        solicitacao = Solicitacao.query.get(id)
        
        if not solicitacao:
            return jsonify({'erro': 'Solicitação não encontrada'}), 404
        
        if solicitacao.status != 'pendente':
            return jsonify({'erro': f'Solicitação já foi processada (status: {solicitacao.status})'}), 400
        
        fornecedor = solicitacao.fornecedor
        if not fornecedor:
            return jsonify({'erro': 'Fornecedor não encontrado'}), 404
        
        # Salvar tabela de preço anterior
        tabela_anterior_id = fornecedor.tabela_preco_id
        tabela_anterior = TabelaPreco.query.get(tabela_anterior_id) if tabela_anterior_id else None
        estrelas_anterior = tabela_anterior.nivel_estrelas if tabela_anterior else 0
        
        print(f" Fornecedor: {fornecedor.nome}")
        print(f" Tabela de preço atual: {tabela_anterior.nome if tabela_anterior else 'Nenhuma'} ({estrelas_anterior}★)")
        
        # Promover fornecedor (aumentar estrelas)
        if estrelas_anterior >= 3:
            # Já está no nível máximo, não pode promover mais
            print(f" Fornecedor já está no nível máximo ({estrelas_anterior}★)")
            return jsonify({
                'erro': f'Fornecedor já está no nível máximo ({estrelas_anterior}★) e não pode ser promovido. Use a opção "Aceitar" ao invés de "Aceitar e Promover".'
            }), 400
        elif not tabela_anterior_id or estrelas_anterior < 1:
            # Fornecedor sem tabela, atribuir 1★
            nova_tabela = TabelaPreco.query.filter_by(nivel_estrelas=1).first()
            print(f" Promovendo de: Sem tabela → 1★")
        elif estrelas_anterior == 1:
            # 1★ → 2★
            nova_tabela = TabelaPreco.query.filter_by(nivel_estrelas=2).first()
            print(f" Promovendo de: 1★ → 2★")
        elif estrelas_anterior == 2:
            # 2★ → 3★
            nova_tabela = TabelaPreco.query.filter_by(nivel_estrelas=3).first()
            print(f" Promovendo de: 2★ → 3★")
        else:
            # Caso inesperado
            nova_tabela = tabela_anterior
            print(f" Situação inesperada - mantendo tabela atual")
        
        if not nova_tabela:
            return jsonify({'erro': 'Tabela de preço para promoção não encontrada no sistema'}), 500
        
        # Atualizar tabela do fornecedor
        fornecedor.tabela_preco_id = nova_tabela.id
        
        print(f" Nova tabela de preço: {nova_tabela.nome} ({nova_tabela.nivel_estrelas}★)")
        
        # Aprovar a solicitação usando a lógica existente
        # Criar OC e lotes (reutilizar lógica da função aprovar_solicitacao)
        usuario_id = get_jwt_identity()
        data = request.get_json(silent=True) or {}
        
        solicitacao.status = 'aprovada'
        solicitacao.data_confirmacao = datetime.utcnow()
        solicitacao.admin_id = usuario_id
        
        # Criar Ordem de Compra
        valor_total_oc = sum((item.valor_calculado or 0.0) for item in solicitacao.itens)
        
        oc = OrdemCompra(
            solicitacao_id=id,
            fornecedor_id=solicitacao.fornecedor_id,
            valor_total=valor_total_oc,
            status='em_analise',
            criado_por=usuario_id,
            observacao=data.get('observacao', f'OC gerada pela aprovação da solicitação #{id} COM PROMOÇÃO do fornecedor de {estrelas_anterior}★ para {nova_tabela.nivel_estrelas}★')
        )
        db.session.add(oc)
        db.session.flush()
        
        print(f" OC #{oc.id} criada com sucesso")
        
        # Criar lotes (simplificado)
        lotes_criados = []
        lotes_agrupados = {}
        
        for item in solicitacao.itens:
            if item.material_id:
                chave = ('material', item.material_id, item.estrelas_final)
            elif item.tipo_lote_id:
                chave = ('tipo_lote', item.tipo_lote_id, item.estrelas_final)
            else:
                continue
            
            if chave not in lotes_agrupados:
                lotes_agrupados[chave] = []
            lotes_agrupados[chave].append(item)
        
        for chave, itens in lotes_agrupados.items():
            tipo_chave, id_referencia, estrelas = chave
            
            peso_total = sum(item.peso_kg for item in itens)
            valor_total = sum(item.valor_calculado for item in itens)
            
            lote = Lote(
                fornecedor_id=solicitacao.fornecedor_id,
                tipo_lote_id=itens[0].tipo_lote_id if itens[0].tipo_lote_id else 1,
                solicitacao_origem_id=id,
                oc_id=oc.id,
                peso_total_kg=peso_total,
                valor_total=valor_total,
                quantidade_itens=len(itens),
                estrelas_media=estrelas,
                status='em_transito',
                tipo_retirada=solicitacao.tipo_retirada
            )
            db.session.add(lote)
            db.session.flush()
            
            for item in itens:
                item.lote_id = lote.id
            
            lotes_criados.append({
                'id': lote.id,
                'numero_lote': lote.numero_lote,
                'peso_total_kg': lote.peso_total_kg,
                'valor_total': lote.valor_total
            })
            
            print(f" Lote criado: #{lote.numero_lote} ({len(itens)} itens)")
        
        db.session.commit()
        
        print(f"\n{'='*60}")
        print(f" APROVAÇÃO COM PROMOÇÃO CONCLUÍDA!")
        print(f"{'='*60}")
        print(f" Fornecedor promovido: {estrelas_anterior}★ → {nova_tabela.nivel_estrelas}★")
        print(f" Solicitação: #{solicitacao.id} (aprovada)")
        print(f" OC criada: #{oc.id}")
        print(f" Lotes criados: {len(lotes_criados)}")
        print(f"{'='*60}\n")
        
        return jsonify({
            'mensagem': f'Solicitação aprovada e fornecedor promovido de {estrelas_anterior}★ para {nova_tabela.nivel_estrelas}★',
            'solicitacao': solicitacao.to_dict(),
            'oc_id': oc.id,
            'lotes_criados': lotes_criados,
            'promocao': {
                'estrelas_anterior': estrelas_anterior,
                'estrelas_nova': nova_tabela.nivel_estrelas,
                'tabela_anterior': tabela_anterior.nome if tabela_anterior else None,
                'tabela_nova': nova_tabela.nome
            }
        }), 200
    
    except Exception as e:
        db.session.rollback()
        print(f"\nERRO ao aprovar com promoção: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'erro': f'Erro ao aprovar e promover: {str(e)}'}), 500

@bp.route('/<int:id>/rejeitar', methods=['POST'])
@admin_required
def rejeitar_solicitacao(id):
    try:
        solicitacao = Solicitacao.query.get(id)

        if not solicitacao:
            return jsonify({'erro': 'Solicitação não encontrada'}), 404

        if solicitacao.status != 'pendente':
            return jsonify({'erro': 'Apenas solicitações pendentes podem ser rejeitadas'}), 400

        data = request.get_json()
        motivo = data.get('motivo', '') if data else ''

        solicitacao.status = 'rejeitada'
        solicitacao.data_confirmacao = datetime.utcnow()
        if motivo:
            solicitacao.observacoes = (solicitacao.observacoes or '') + f'\nMotivo da rejeição: {motivo}'

        db.session.commit()

        return jsonify({
            'mensagem': 'Solicitação rejeitada',
            'solicitacao': solicitacao.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': f'Erro ao rejeitar solicitação: {str(e)}'}), 500

@bp.route('/<int:id>', methods=['DELETE'])
@jwt_required()
def deletar_solicitacao(id):
    try:
        usuario_id = int(get_jwt_identity())
        usuario = Usuario.query.get(usuario_id)

        solicitacao = Solicitacao.query.get(id)

        if not solicitacao:
            return jsonify({'erro': 'Solicitação não encontrada'}), 404

        if usuario.tipo != 'admin' and solicitacao.funcionario_id != usuario.id:
            return jsonify({'erro': 'Sem permissão para deletar esta solicitação'}), 403

        if solicitacao.status != 'pendente':
            return jsonify({'erro': 'Apenas solicitações pendentes podem ser deletadas'}), 400

        db.session.delete(solicitacao)
        db.session.commit()

        return jsonify({'mensagem': 'Solicitação deletada com sucesso'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': f'Erro ao deletar solicitação: {str(e)}'}), 500