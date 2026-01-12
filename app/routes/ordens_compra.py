from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import OrdemCompra, AuditoriaOC, Solicitacao, Fornecedor, Usuario, ItemSolicitacao, OrdemServico, db
from app.auth import admin_required
from app.utils.auditoria import registrar_auditoria_oc
from datetime import datetime

bp = Blueprint('ordens_compra', __name__, url_prefix='/api/ordens-compra')

def gerar_numero_os():
    """Gera número único para Ordem de Serviço"""
    import uuid
    timestamp = datetime.now().strftime('%Y%m%d')
    random_str = uuid.uuid4().hex[:6].upper()
    return f"OS-{timestamp}-{random_str}"

def criar_snapshot_fornecedor(fornecedor):
    """Cria snapshot dos dados do fornecedor para a OS"""
    return {
        'id': fornecedor.id,
        'nome': fornecedor.nome,
        'cnpj': fornecedor.cnpj if hasattr(fornecedor, 'cnpj') else None,
        'endereco': fornecedor.endereco if hasattr(fornecedor, 'endereco') else None,
        'cidade': fornecedor.cidade if hasattr(fornecedor, 'cidade') else None,
        'estado': fornecedor.estado if hasattr(fornecedor, 'estado') else None,
        'telefone': fornecedor.telefone if hasattr(fornecedor, 'telefone') else None,
    }

def registrar_auditoria_os(os, acao, usuario_id, detalhes=None):
    """Registra ação de auditoria na OS"""
    entrada_auditoria = {
        'acao': acao,
        'usuario_id': usuario_id,
        'timestamp': datetime.utcnow().isoformat(),
        'detalhes': detalhes or {},
        'ip': request.remote_addr,
        'user_agent': request.headers.get('User-Agent')
    }
    
    if os.auditoria is None:
        os.auditoria = []
    os.auditoria.append(entrada_auditoria)

@bp.route('', methods=['GET'])
@jwt_required()
def listar_ocs():
    try:
        print(f"\n{'='*60}")
        print(f" LISTANDO ORDENS DE COMPRA")
        print(f"{'='*60}")
        
        usuario_id = get_jwt_identity()
        usuario = Usuario.query.get(usuario_id)
        
        print(f"   Usuário: {usuario.nome if usuario else 'N/A'} (ID: {usuario_id})")
        
        if not usuario:
            return jsonify({'erro': 'Usuário não encontrado'}), 404
        
        query = OrdemCompra.query
        print(f"   Query inicial criada")
        
        if usuario.tipo != 'admin':
            perfil_nome = usuario.perfil.nome if usuario.perfil else None
            if perfil_nome == 'Comprador (PJ)':
                query = query.join(Solicitacao).filter(Solicitacao.funcionario_id == usuario_id)
            elif perfil_nome not in ['Financeiro', 'Administrador']:
                return jsonify({'erro': 'Acesso negado'}), 403
        
        status = request.args.get('status')
        if status:
            query = query.filter_by(status=status)
            print(f"   Filtrando por status: {status}")
        
        # Contar total de OCs no banco ANTES do filtro de perfil
        total_ocs_db = OrdemCompra.query.count()
        print(f"    Total de OCs no banco: {total_ocs_db}")
        
        ocs = query.order_by(OrdemCompra.criado_em.desc()).all()
        
        print(f"    {len(ocs)} OC(s) encontrada(s) após filtros")
        
        resultado = []
        for oc in ocs:
            oc_dict = oc.to_dict()
            if oc.solicitacao:
                oc_dict['solicitacao'] = {
                    'id': oc.solicitacao.id,
                    'funcionario_nome': oc.solicitacao.funcionario.nome if oc.solicitacao.funcionario else None,
                    'data_envio': oc.solicitacao.data_envio.isoformat() if oc.solicitacao.data_envio else None
                }
            resultado.append(oc_dict)
            print(f"      - OC #{oc.id}: SC #{oc.solicitacao_id}, Fornecedor: {oc.fornecedor.nome if oc.fornecedor else 'N/A'}, Valor: R$ {oc.valor_total:.2f}, Status: {oc.status}")
        
        print(f"\n{'='*60}")
        print(f" Retornando {len(resultado)} OC(s)")
        print(f"{'='*60}\n")
        
        return jsonify(resultado), 200
    
    except Exception as e:
        print(f"\n ERRO ao listar OCs: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'erro': f'Erro ao listar ordens de compra: {str(e)}'}), 500

@bp.route('/solicitacao/<int:sc_id>', methods=['POST'])
@jwt_required()
def criar_oc(sc_id):
    try:
        usuario_id = get_jwt_identity()
        usuario = Usuario.query.get(usuario_id)
        
        if not usuario:
            return jsonify({'erro': 'Usuário não encontrado'}), 404
        
        if usuario.tipo != 'admin' and (not usuario.perfil or usuario.perfil.nome not in ['Administrador', 'Comprador (PJ)']):
            return jsonify({'erro': 'Apenas Administrador ou Comprador PJ podem criar ordens de compra'}), 403
        
        solicitacao = Solicitacao.query.get(sc_id)
        
        if not solicitacao:
            return jsonify({'erro': 'Solicitação não encontrada'}), 404
        
        if solicitacao.status != 'aprovada':
            return jsonify({'erro': 'Apenas solicitações aprovadas podem gerar ordem de compra'}), 400
        
        oc_existente = OrdemCompra.query.filter_by(solicitacao_id=sc_id).first()
        if oc_existente:
            return jsonify({'erro': 'Já existe uma ordem de compra para esta solicitação'}), 400
        
        if not solicitacao.itens or len(solicitacao.itens) == 0:
            return jsonify({'erro': 'Solicitação não possui itens'}), 400
        
        # Validar que todos os itens têm preços válidos (aceita zero, rejeita None e negativos)
        itens_invalidos = [item for item in solicitacao.itens if item.valor_calculado is None or item.valor_calculado < 0]
        if itens_invalidos:
            return jsonify({
                'erro': f'Existem {len(itens_invalidos)} itens sem preço configurado ou com valor inválido',
                'itens_invalidos': len(itens_invalidos)
            }), 400
        
        # Calcular valor total tratando None como 0.0
        valor_total = sum((item.valor_calculado or 0.0) for item in solicitacao.itens)
        
        if valor_total < 0:
            return jsonify({'erro': 'Valor total da OC não pode ser negativo'}), 400
        
        data = request.get_json() or {}
        
        with db.session.begin_nested():
            oc = OrdemCompra(
                solicitacao_id=sc_id,
                fornecedor_id=solicitacao.fornecedor_id,
                valor_total=valor_total,
                status='em_analise',
                criado_por=usuario_id,
                observacao=data.get('observacao', '')
            )
            
            db.session.add(oc)
            db.session.flush()
            
            ip = request.headers.get('X-Forwarded-For', request.remote_addr)
            gps = data.get('gps')
            dispositivo = request.headers.get('User-Agent', '')
            
            registrar_auditoria_oc(
                oc_id=oc.id,
                usuario_id=usuario_id,
                acao='criacao',
                status_anterior=None,
                status_novo='em_analise',
                observacao=data.get('observacao', ''),
                ip=ip,
                gps=gps,
                dispositivo=dispositivo
            )
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Ordem de compra criada com sucesso',
            'oc': oc.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': f'Erro ao criar ordem de compra: {str(e)}'}), 500

@bp.route('/<int:oc_id>', methods=['GET'])
@jwt_required()
def obter_oc(oc_id):
    try:
        usuario_id = get_jwt_identity()
        usuario = Usuario.query.get(usuario_id)
        
        if not usuario:
            return jsonify({'erro': 'Usuário não encontrado'}), 404
        
        oc = OrdemCompra.query.get(oc_id)
        
        if not oc:
            return jsonify({'erro': 'Ordem de compra não encontrada'}), 404
        
        if usuario.tipo != 'admin':
            perfil_nome = usuario.perfil.nome if usuario.perfil else None
            if perfil_nome == 'Comprador (PJ)' and oc.solicitacao.funcionario_id != usuario_id:
                return jsonify({'erro': 'Acesso negado'}), 403
            elif perfil_nome not in ['Financeiro', 'Administrador', 'Comprador (PJ)']:
                return jsonify({'erro': 'Acesso negado'}), 403
        
        oc_dict = oc.to_dict()
        
        if oc.solicitacao:
            solicitacao_dict = oc.solicitacao.to_dict()
            solicitacao_dict['itens'] = [item.to_dict() for item in oc.solicitacao.itens]
            oc_dict['solicitacao'] = solicitacao_dict
        
        oc_dict['auditorias'] = [auditoria.to_dict() for auditoria in oc.auditorias]
        
        return jsonify(oc_dict), 200
    
    except Exception as e:
        return jsonify({'erro': f'Erro ao obter ordem de compra: {str(e)}'}), 500

@bp.route('/<int:oc_id>/aprovar', methods=['PATCH'])
@admin_required
def aprovar_oc(oc_id):
    try:
        usuario_id = get_jwt_identity()
        usuario = Usuario.query.get(usuario_id)
        
        if not usuario:
            return jsonify({'erro': 'Usuário não encontrado'}), 404
        
        if usuario.tipo != 'admin' and (not usuario.perfil or usuario.perfil.nome not in ['Administrador', 'Financeiro']):
            return jsonify({'erro': 'Apenas Administrador ou Financeiro podem aprovar ordens de compra'}), 403
        
        oc = OrdemCompra.query.get(oc_id)
        
        if not oc:
            return jsonify({'erro': 'Ordem de compra não encontrada'}), 404
        
        if oc.status == 'aprovada':
            return jsonify({'erro': 'Ordem de compra já está aprovada'}), 400
        
        if oc.status == 'cancelada':
            return jsonify({'erro': 'Ordem de compra cancelada não pode ser aprovada'}), 400
        
        data = request.get_json() or {}
        
        status_anterior = oc.status
        
        with db.session.begin_nested():
            oc.status = 'aprovada'
            oc.aprovado_por = usuario_id
            oc.aprovado_em = datetime.utcnow()
            oc.observacao = data.get('observacao', oc.observacao)
            oc.ip_aprovacao = request.headers.get('X-Forwarded-For', request.remote_addr)
            oc.gps_aprovacao = data.get('gps')
            oc.device_info = request.headers.get('User-Agent', '')[:100]
            
            registrar_auditoria_oc(
                oc_id=oc.id,
                usuario_id=usuario_id,
                acao='aprovacao',
                status_anterior=status_anterior,
                status_novo='aprovada',
                observacao=data.get('observacao', ''),
                ip=oc.ip_aprovacao,
                gps=oc.gps_aprovacao,
                dispositivo=oc.device_info
            )
            
            # ========================================
            # GERAÇÃO AUTOMÁTICA DE OS
            # ========================================
            print(f"\n{'='*60}")
            print(f" OC #{oc.id} APROVADA - Criando OS automaticamente...")
            print(f"{'='*60}")
            
            try:
                # Buscar fornecedor para criar snapshot
                fornecedor = Fornecedor.query.get(oc.fornecedor_id)
                if not fornecedor:
                    raise Exception(f'Fornecedor {oc.fornecedor_id} não encontrado')
                
                print(f"   Fornecedor: {fornecedor.nome}")
                
                # Verificar se já existe OS para esta OC
                os_existente = OrdemServico.query.filter_by(oc_id=oc.id).first()
                if os_existente:
                    print(f"   ⚠️  OS já existe: {os_existente.numero_os}")
                    os = os_existente
                else:
                    # Gerar número único da OS
                    numero_os = gerar_numero_os()
                    fornecedor_snap = criar_snapshot_fornecedor(fornecedor)
                    
                    print(f"   Número OS: {numero_os}")
                    print(f"   Status inicial: PENDENTE")
                    
                    # Criar a Ordem de Serviço automaticamente
                    os = OrdemServico(
                        oc_id=oc.id,
                        numero_os=numero_os,
                        fornecedor_snapshot=fornecedor_snap,
                        tipo='COLETA',  # Padrão: coleta no fornecedor
                        status='PENDENTE',  # Status inicial
                        created_by=usuario_id
                    )
                    db.session.add(os)
                    
                    # Registrar auditoria da OS
                    registrar_auditoria_os(os, 'CRIACAO', usuario_id, {
                        'oc_id': oc.id,
                        'criado_automaticamente': True,
                        'motivo': 'OC aprovada'
                    })
                    
                    print(f"   ✅ OS criada com sucesso!")
                
            except Exception as e:
                print(f"   ❌ ERRO ao criar OS: {str(e)}")
                db.session.rollback()
                return jsonify({
                    'erro': f'OC aprovada mas falha ao criar OS: {str(e)}',
                    'oc_aprovada': True,
                    'oc_id': oc.id
                }), 500
            
            print(f"{'='*60}\n")
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Ordem de compra aprovada e OS gerada com sucesso',
            'oc': oc.to_dict(),
            'os_criada': {
                'id': os.id,
                'numero_os': os.numero_os,
                'status': os.status
            }
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': f'Erro ao aprovar ordem de compra: {str(e)}'}), 500

@bp.route('/<int:oc_id>/reprovar', methods=['PATCH'])
@admin_required
def reprovar_oc(oc_id):
    try:
        usuario_id = get_jwt_identity()
        usuario = Usuario.query.get(usuario_id)
        
        if not usuario:
            return jsonify({'erro': 'Usuário não encontrado'}), 404
        
        if usuario.tipo != 'admin' and (not usuario.perfil or usuario.perfil.nome not in ['Administrador', 'Financeiro']):
            return jsonify({'erro': 'Apenas Administrador ou Financeiro podem reprovar ordens de compra'}), 403
        
        oc = OrdemCompra.query.get(oc_id)
        
        if not oc:
            return jsonify({'erro': 'Ordem de compra não encontrada'}), 404
        
        if oc.status == 'rejeitada':
            return jsonify({'erro': 'Ordem de compra já está rejeitada'}), 400
        
        if oc.status == 'cancelada':
            return jsonify({'erro': 'Ordem de compra cancelada não pode ser reprovada'}), 400
        
        data = request.get_json() or {}
        
        if not data.get('observacao'):
            return jsonify({'erro': 'Motivo da rejeição é obrigatório'}), 400
        
        status_anterior = oc.status
        
        with db.session.begin_nested():
            oc.status = 'rejeitada'
            oc.aprovado_por = usuario_id
            oc.aprovado_em = datetime.utcnow()
            oc.observacao = data.get('observacao')
            oc.ip_aprovacao = request.headers.get('X-Forwarded-For', request.remote_addr)
            oc.gps_aprovacao = data.get('gps')
            oc.device_info = request.headers.get('User-Agent', '')[:100]
            
            registrar_auditoria_oc(
                oc_id=oc.id,
                usuario_id=usuario_id,
                acao='rejeicao',
                status_anterior=status_anterior,
                status_novo='rejeitada',
                observacao=data.get('observacao', ''),
                ip=oc.ip_aprovacao,
                gps=oc.gps_aprovacao,
                dispositivo=oc.device_info
            )
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Ordem de compra rejeitada com sucesso',
            'oc': oc.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': f'Erro ao reprovar ordem de compra: {str(e)}'}), 500

@bp.route('/<int:oc_id>', methods=['DELETE'])
@admin_required
def cancelar_oc(oc_id):
    try:
        usuario_id = get_jwt_identity()
        
        oc = OrdemCompra.query.get(oc_id)
        
        if not oc:
            return jsonify({'erro': 'Ordem de compra não encontrada'}), 404
        
        if oc.status == 'aprovada':
            return jsonify({'erro': 'Ordem de compra aprovada não pode ser cancelada'}), 400
        
        status_anterior = oc.status
        
        with db.session.begin_nested():
            oc.status = 'cancelada'
            
            registrar_auditoria_oc(
                oc_id=oc.id,
                usuario_id=usuario_id,
                acao='cancelamento',
                status_anterior=status_anterior,
                status_novo='cancelada',
                ip=request.headers.get('X-Forwarded-For', request.remote_addr),
                gps=None,
                dispositivo=request.headers.get('User-Agent', '')[:100]
            )
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Ordem de compra cancelada com sucesso'
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': f'Erro ao cancelar ordem de compra: {str(e)}'}), 500

@bp.route('/estatisticas', methods=['GET'])
@jwt_required()
def obter_estatisticas():
    try:
        usuario_id = get_jwt_identity()
        usuario = Usuario.query.get(usuario_id)
        
        if not usuario:
            return jsonify({'erro': 'Usuário não encontrado'}), 404
        
        query = OrdemCompra.query
        
        if usuario.tipo != 'admin':
            perfil_nome = usuario.perfil.nome if usuario.perfil else None
            if perfil_nome == 'Comprador (PJ)':
                query = query.join(Solicitacao).filter(Solicitacao.funcionario_id == usuario_id)
            elif perfil_nome not in ['Financeiro', 'Administrador']:
                return jsonify({'erro': 'Acesso negado'}), 403
        
        total_ocs = query.count()
        em_analise = query.filter_by(status='em_analise').count()
        aprovadas = query.filter_by(status='aprovada').count()
        rejeitadas = query.filter_by(status='rejeitada').count()
        canceladas = query.filter_by(status='cancelada').count()
        
        valor_total_aprovadas = db.session.query(db.func.sum(OrdemCompra.valor_total)).filter_by(status='aprovada').scalar() or 0
        
        return jsonify({
            'total_ocs': total_ocs,
            'em_analise': em_analise,
            'aprovadas': aprovadas,
            'rejeitadas': rejeitadas,
            'canceladas': canceladas,
            'valor_total_aprovadas': float(valor_total_aprovadas)
        }), 200
    
    except Exception as e:
        return jsonify({'erro': f'Erro ao obter estatísticas: {str(e)}'}), 500
