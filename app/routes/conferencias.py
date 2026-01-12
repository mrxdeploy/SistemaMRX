from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, ConferenciaRecebimento, OrdemServico, OrdemCompra, Usuario, Notificacao, EntradaEstoque, Lote
from app.auth import admin_required
from datetime import datetime
import uuid
import os
from werkzeug.utils import secure_filename

bp = Blueprint('conferencias', __name__, url_prefix='/api/conferencia')

def calcular_percentual_diferenca(peso_fornecedor, peso_real):
    if not peso_fornecedor or peso_fornecedor == 0:
        return 0
    return abs((peso_real - peso_fornecedor) / peso_fornecedor) * 100

def registrar_auditoria_conferencia(conferencia, acao, usuario_id, detalhes=None, gps=None, device_id=None):
    entrada_auditoria = {
        'acao': acao,
        'usuario_id': usuario_id,
        'timestamp': datetime.utcnow().isoformat(),
        'detalhes': detalhes or {},
        'ip': request.remote_addr,
        'user_agent': request.headers.get('User-Agent'),
        'gps': gps,
        'device_id': device_id
    }
    
    if conferencia.auditoria is None:
        conferencia.auditoria = []
    conferencia.auditoria.append(entrada_auditoria)

def criar_lote_apos_conferencia(conferencia, usuario_id, decisao='ACEITAR', percentual_desconto=None, motivo='', gps=None, device_id=None):
    from app.models import MovimentacaoEstoque, LoteSeparacao
    from sqlalchemy.exc import IntegrityError
    
    try:
        # Idempotency guard: lock exclusivo na conferência antes de verificar/criar lote
        # populate_existing() força novo SELECT com lock, mesmo se a conferência já está na session
        ConferenciaRecebimento.query.filter_by(id=conferencia.id).populate_existing().with_for_update().first()
        
        # Verificar se já existe lote para esta conferência (após adquirir o lock)
        lote_existente = Lote.query.filter_by(conferencia_id=conferencia.id).first()
        if lote_existente:
            return lote_existente
        
        os = OrdemServico.query.get(conferencia.os_id)
        oc = OrdemCompra.query.get(conferencia.oc_id)
        
        if not os or not oc:
            raise ValueError('OS ou OC não encontrada')
        
        peso_final = conferencia.peso_real if conferencia.peso_real else conferencia.peso_fornecedor
        peso_liquido = peso_final
        
        if decisao == 'ACEITAR_COM_DESCONTO' and percentual_desconto:
            peso_liquido = peso_final * (1 - percentual_desconto / 100)
        
        # WARNING: Race condition - count()+1 pode gerar números duplicados em alta concorrência
        # TODO: Migrar para sequence do PostgreSQL ou usar UUID para número de lote
        ano = datetime.now().year
        numero_sequencial = Lote.query.filter(
            Lote.numero_lote.like(f"{ano}-%")  # type: ignore
        ).count() + 1
        numero_lote = f"{ano}-{str(numero_sequencial).zfill(5)}"
        
        # Sistema migrado para materiais - usar tipo_lote genérico (ID 1)
        # Tipo de lote genérico criado na migração 017
        tipo_lote_id = 1  # Material Eletrônico (genérico)
        
        # Verificar se o tipo genérico existe
        from app.models import TipoLote
        tipo_generico = TipoLote.query.get(tipo_lote_id)
        if not tipo_generico:
            raise ValueError('Tipo de lote genérico não encontrado. Execute a migração 017: python executar_migracao_017.py')
        
        divergencias_registradas = []
        if conferencia.divergencia:
            divergencias_registradas.append({
                'tipo': conferencia.tipo_divergencia,
                'percentual_diferenca': conferencia.percentual_diferenca,
                'peso_previsto': conferencia.peso_fornecedor,
                'peso_recebido': peso_final,
                'decisao_adm': decisao,
                'motivo': motivo
            })
        
        lote = Lote(
            numero_lote=numero_lote,
            fornecedor_id=oc.fornecedor_id,
            tipo_lote_id=tipo_lote_id,
            solicitacao_origem_id=oc.solicitacao_id if oc.solicitacao else None,
            oc_id=oc.id,
            os_id=os.id,
            conferencia_id=conferencia.id,
            peso_bruto_recebido=peso_final,
            peso_liquido=peso_liquido,
            peso_total_kg=peso_liquido,
            qualidade_recebida=conferencia.qualidade,
            status='AGUARDANDO_SEPARACAO',
            conferente_id=conferencia.conferente_id,
            anexos=conferencia.fotos_pesagem or [],
            divergencias=divergencias_registradas,
            auditoria=[{
                'acao': 'LOTE_CRIADO_APOS_CONFERENCIA',
                'usuario_id': usuario_id,
                'timestamp': datetime.utcnow().isoformat(),
                'ip': request.remote_addr,
                'device_id': conferencia.device_id_conferencia or device_id,
                'gps': conferencia.gps_conferencia or gps,
                'detalhes': {
                    'conferencia_id': conferencia.id,
                    'os_id': os.id,
                    'oc_id': oc.id,
                    'decisao': decisao,
                    'divergencia': conferencia.divergencia,
                    'tipo_divergencia': conferencia.tipo_divergencia
                }
            }],
            data_criacao=datetime.utcnow()
        )
        db.session.add(lote)
        db.session.flush()
        
        if oc.solicitacao and oc.solicitacao.itens:
            for item in oc.solicitacao.itens:
                item.lote_id = lote.id
        
        entrada_estoque = EntradaEstoque(
            lote_id=lote.id,
            status='recebido',
            admin_id=usuario_id,
            observacoes=f'Entrada automática após conferência aprovada. Decisão: {decisao}',
            data_entrada=datetime.utcnow()
        )
        db.session.add(entrada_estoque)
        
        movimentacao = MovimentacaoEstoque(
            lote_id=lote.id,
            tipo='ENTRADA_RECEBIMENTO',
            localizacao_origem='EXTERNO',
            localizacao_destino='PATIO_RECEBIMENTO',
            peso=peso_liquido,
            usuario_id=usuario_id,
            observacoes=f'Entrada inicial após conferência. OS: {os.numero_os}',
            dados_before={},
            dados_after={
                'lote_id': lote.id,
                'numero_lote': numero_lote,
                'localizacao': 'PATIO_RECEBIMENTO',
                'peso': peso_liquido
            },
            auditoria=[{
                'acao': 'MOVIMENTACAO_CRIADA',
                'usuario_id': usuario_id,
                'timestamp': datetime.utcnow().isoformat(),
                'ip': request.remote_addr,
                'user_agent': request.headers.get('User-Agent'),
                'gps': gps,
                'device_id': device_id
            }],
            data_movimentacao=datetime.utcnow()
        )
        db.session.add(movimentacao)
        
        separacao = LoteSeparacao(
            lote_id=lote.id,
            status='AGUARDANDO_SEPARACAO',
            auditoria=[{
                'acao': 'SEPARACAO_CRIADA_AUTOMATICAMENTE',
                'usuario_id': usuario_id,
                'timestamp': datetime.utcnow().isoformat(),
                'ip': request.remote_addr,
                'user_agent': request.headers.get('User-Agent'),
                'gps': gps,
                'device_id': device_id,
                'divergencia_conferencia': conferencia.divergencia,
                'decisao_adm': decisao
            }]
        )
        db.session.add(separacao)
        
        # Flush para detectar IntegrityError antes do commit final
        db.session.flush()
        
        return lote
        
    except IntegrityError:
        # Se ocorrer IntegrityError, outro processo já criou o lote
        # Fazer rollback e retornar o lote existente
        db.session.rollback()
        lote_existente = Lote.query.filter_by(conferencia_id=conferencia.id).first()
        if lote_existente:
            return lote_existente
        # Se não encontrou, algo está muito errado - re-raise o erro
        raise

@bp.route('', methods=['GET'])
@jwt_required()
def listar_conferencias():
    try:
        usuario_id = get_jwt_identity()
        usuario = Usuario.query.get(usuario_id)
        
        if not usuario:
            return jsonify({'erro': 'Usuário não encontrado'}), 404
        
        query = ConferenciaRecebimento.query
        
        status = request.args.get('status')
        if status:
            query = query.filter_by(conferencia_status=status)
        
        conferencias = query.order_by(ConferenciaRecebimento.criado_em.desc()).all()
        
        resultado = []
        for conf in conferencias:
            conf_dict = conf.to_dict()
            if conf.ordem_servico:
                conf_dict['ordem_servico'] = {
                    'id': conf.ordem_servico.id,
                    'numero_os': conf.ordem_servico.numero_os,
                    'fornecedor_snapshot': conf.ordem_servico.fornecedor_snapshot
                }
            if conf.ordem_compra:
                conf_dict['ordem_compra'] = {
                    'id': conf.ordem_compra.id,
                    'valor_total': conf.ordem_compra.valor_total
                }
            resultado.append(conf_dict)
        
        return jsonify(resultado), 200
    
    except Exception as e:
        return jsonify({'erro': f'Erro ao listar conferências: {str(e)}'}), 500

@bp.route('/<int:id>', methods=['GET'])
@jwt_required()
def obter_conferencia(id):
    try:
        conferencia = ConferenciaRecebimento.query.get(id)
        
        if not conferencia:
            return jsonify({'erro': 'Conferência não encontrada'}), 404
        
        conf_dict = conferencia.to_dict()
        
        if conferencia.ordem_servico:
            conf_dict['ordem_servico'] = conferencia.ordem_servico.to_dict()
        
        if conferencia.ordem_compra:
            conf_dict['ordem_compra'] = conferencia.ordem_compra.to_dict()
            if conferencia.ordem_compra.solicitacao:
                conf_dict['solicitacao'] = conferencia.ordem_compra.solicitacao.to_dict()
        
        return jsonify(conf_dict), 200
    
    except Exception as e:
        return jsonify({'erro': f'Erro ao obter conferência: {str(e)}'}), 500

@bp.route('/os/<int:os_id>/iniciar', methods=['POST'])
@jwt_required()
def iniciar_conferencia(os_id):
    try:
        usuario_id = get_jwt_identity()
        usuario = Usuario.query.get(usuario_id)
        
        if not usuario:
            return jsonify({'erro': 'Usuário não encontrado'}), 404
        
        perfil_nome = usuario.perfil.nome if usuario.perfil else None
        if perfil_nome not in ['Conferente / Estoque', 'Administrador'] and usuario.tipo != 'admin':
            return jsonify({'erro': 'Acesso negado. Apenas conferentes podem iniciar conferências'}), 403
        
        os = OrdemServico.query.get(os_id)
        if not os:
            return jsonify({'erro': 'Ordem de Serviço não encontrada'}), 404
        
        if os.status not in ['ENTREGUE', 'FINALIZADA']:
            return jsonify({'erro': f'Conferência só pode ser iniciada quando OS estiver ENTREGUE ou FINALIZADA. Status atual: {os.status}'}), 400
        
        conferencia_existente = ConferenciaRecebimento.query.filter_by(os_id=os_id).first()
        if conferencia_existente:
            return jsonify({'erro': 'Já existe uma conferência para esta OS', 'conferencia': conferencia_existente.to_dict()}), 400
        
        oc = OrdemCompra.query.get(os.oc_id)
        if not oc:
            return jsonify({'erro': 'Ordem de Compra não encontrada'}), 404
        
        data = request.get_json() or {}
        
        peso_total_previsto = 0
        quantidade_total_prevista = 0
        if oc.solicitacao and oc.solicitacao.itens:
            for item in oc.solicitacao.itens:
                peso_kg = item.peso_kg or 0
                peso_total_previsto += peso_kg
                quantidade_total_prevista += 1
        
        peso_fornecedor = data.get('peso_fornecedor') or peso_total_previsto
        
        conferencia = ConferenciaRecebimento(
            os_id=os_id,
            oc_id=os.oc_id,
            peso_fornecedor=peso_fornecedor,
            quantidade_prevista=quantidade_total_prevista,
            conferencia_status='PENDENTE',
            conferente_id=usuario_id
        )
        
        db.session.add(conferencia)
        registrar_auditoria_conferencia(
            conferencia, 
            'INICIO_CONFERENCIA', 
            usuario_id, 
            detalhes={'os_id': os_id, 'oc_id': os.oc_id},
            gps=data.get('gps'),
            device_id=data.get('device_id')
        )
        
        db.session.commit()
        
        return jsonify({
            'mensagem': 'Conferência iniciada com sucesso',
            'conferencia': conferencia.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': f'Erro ao iniciar conferência: {str(e)}'}), 500

@bp.route('/<int:id>/registrar-pesagem', methods=['PUT'])
@jwt_required()
def registrar_pesagem(id):
    try:
        usuario_id = get_jwt_identity()
        usuario = Usuario.query.get(usuario_id)
        data = request.get_json()
        
        if not data or not data.get('peso_real'):
            return jsonify({'erro': 'peso_real é obrigatório'}), 400
        
        if not usuario:
            return jsonify({'erro': 'Usuário não encontrado'}), 404
        
        perfil_nome = usuario.perfil.nome if usuario.perfil else None
        if perfil_nome not in ['Conferente / Estoque', 'Administrador'] and usuario.tipo != 'admin':
            return jsonify({'erro': 'Acesso negado'}), 403
        
        conferencia = ConferenciaRecebimento.query.get(id)
        if not conferencia:
            return jsonify({'erro': 'Conferência não encontrada'}), 404
        
        conferencia.peso_real = data['peso_real']
        conferencia.quantidade_real = data.get('quantidade_real')
        conferencia.qualidade = data.get('qualidade', 'A')
        conferencia.observacoes = data.get('observacoes', '')
        conferencia.fotos_pesagem = data.get('fotos', [])
        
        if data.get('gps'):
            conferencia.gps_conferencia = data['gps']
        
        conferencia.device_id_conferencia = data.get('device_id')
        
        if conferencia.peso_fornecedor:
            percentual_dif = calcular_percentual_diferenca(conferencia.peso_fornecedor, data['peso_real'])
            conferencia.percentual_diferenca = percentual_dif
            
            limite_divergencia = 10.0
            
            if percentual_dif > limite_divergencia:
                conferencia.divergencia = True
                conferencia.tipo_divergencia = 'PESO_EXCEDENTE' if data['peso_real'] > conferencia.peso_fornecedor else 'PESO_INSUFICIENTE'
                conferencia.conferencia_status = 'DIVERGENTE'
            else:
                conferencia.divergencia = False
                conferencia.conferencia_status = 'APROVADA'
        else:
            conferencia.conferencia_status = 'APROVADA'
        
        if data.get('qualidade') in ['C', 'Descartável']:
            conferencia.divergencia = True
            conferencia.tipo_divergencia = 'QUALIDADE_RUIM'
            conferencia.conferencia_status = 'DIVERGENTE'
        
        registrar_auditoria_conferencia(
            conferencia, 
            'PESAGEM_REGISTRADA', 
            usuario_id, 
            detalhes={
                'peso_real': data['peso_real'],
                'quantidade_real': data.get('quantidade_real'),
                'qualidade': conferencia.qualidade,
                'observacoes': conferencia.observacoes,
                'divergencia': conferencia.divergencia,
                'percentual_diferenca': conferencia.percentual_diferenca
            },
            gps=data.get('gps'),
            device_id=data.get('device_id')
        )
        
        lote_criado = None
        if conferencia.conferencia_status == 'APROVADA':
            try:
                lote_criado = criar_lote_apos_conferencia(
                    conferencia=conferencia,
                    usuario_id=usuario_id,
                    decisao='ACEITAR',
                    motivo='Aprovação automática - sem divergência',
                    gps=data.get('gps'),
                    device_id=data.get('device_id')
                )
            except Exception as e:
                db.session.rollback()
                return jsonify({'erro': f'Erro ao criar lote após conferência: {str(e)}'}), 500
        
        db.session.commit()
        
        response_data = {
            'mensagem': 'Pesagem registrada com sucesso',
            'conferencia': conferencia.to_dict()
        }
        
        if lote_criado:
            response_data['lote_criado'] = lote_criado.to_dict()
            response_data['mensagem'] = 'Pesagem registrada e lote criado com sucesso'
        
        return jsonify(response_data), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': f'Erro ao registrar pesagem: {str(e)}'}), 500

@bp.route('/<int:id>/enviar-para-adm', methods=['PUT'])
@jwt_required()
def enviar_para_adm(id):
    try:
        usuario_id = get_jwt_identity()
        
        conferencia = ConferenciaRecebimento.query.get(id)
        if not conferencia:
            return jsonify({'erro': 'Conferência não encontrada'}), 404
        
        if not conferencia.divergencia:
            return jsonify({'erro': 'Apenas conferências com divergência podem ser enviadas para ADM'}), 400
        
        conferencia.conferencia_status = 'AGUARDANDO_ADM'
        
        # Get JSON data if present, but don't fail if not
        data = {}
        if request.is_json:
            data = request.get_json() or {}
        
        registrar_auditoria_conferencia(
            conferencia, 
            'ENVIADO_PARA_ADM', 
            usuario_id, 
            detalhes={
                'tipo_divergencia': conferencia.tipo_divergencia,
                'percentual_diferenca': conferencia.percentual_diferenca
            },
            gps=data.get('gps'),
            device_id=data.get('device_id')
        )
        
        admins = Usuario.query.filter_by(tipo='admin').all()
        for admin in admins:
            notificacao = Notificacao(
                usuario_id=admin.id,
                titulo='Divergência em Conferência',
                mensagem=f'Conferência #{conferencia.id} com divergência de {conferencia.percentual_diferenca:.2f}% precisa de análise',
                tipo='divergencia_conferencia',
                url=f'/conferencia.html?id={conferencia.id}',
                lida=False
            )
            db.session.add(notificacao)
        
        db.session.commit()
        
        return jsonify({
            'mensagem': 'Conferência enviada para análise administrativa',
            'conferencia': conferencia.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': f'Erro ao enviar para ADM: {str(e)}'}), 500

@bp.route('/<int:id>/decisao-adm', methods=['PUT'])
@admin_required
def decisao_adm(id):
    try:
        usuario_id = get_jwt_identity()
        data = request.get_json()
        
        if not data or not data.get('decisao'):
            return jsonify({'erro': 'decisao é obrigatória (ACEITAR, ACEITAR_COM_DESCONTO, REJEITAR)'}), 400
        
        conferencia = ConferenciaRecebimento.query.get(id)
        if not conferencia:
            return jsonify({'erro': 'Conferência não encontrada'}), 404
        
        if conferencia.conferencia_status != 'AGUARDANDO_ADM':
            return jsonify({'erro': 'Conferência não está aguardando decisão administrativa'}), 400
        
        decisao = data['decisao'].upper()
        if decisao not in ['ACEITAR', 'ACEITAR_COM_DESCONTO', 'REJEITAR']:
            return jsonify({'erro': 'Decisão inválida'}), 400
        
        conferencia.decisao_adm = decisao
        conferencia.decisao_adm_por = usuario_id
        conferencia.decisao_adm_em = datetime.utcnow()
        conferencia.decisao_adm_motivo = data.get('motivo', '')
        
        lote_criado = None
        if decisao in ['ACEITAR', 'ACEITAR_COM_DESCONTO']:
            conferencia.conferencia_status = 'APROVADA'
            
            try:
                lote_criado = criar_lote_apos_conferencia(
                    conferencia=conferencia,
                    usuario_id=usuario_id,
                    decisao=decisao,
                    percentual_desconto=data.get('percentual_desconto'),
                    motivo=data.get('motivo', ''),
                    gps=data.get('gps'),
                    device_id=data.get('device_id')
                )
            except Exception as e:
                db.session.rollback()
                return jsonify({'erro': f'Erro ao criar lote: {str(e)}'}), 500
        else:
            conferencia.conferencia_status = 'REJEITADA'
        
        registrar_auditoria_conferencia(
            conferencia, 
            'DECISAO_ADM', 
            usuario_id, 
            detalhes={
                'decisao': decisao,
                'motivo': data.get('motivo'),
                'percentual_desconto': data.get('percentual_desconto')
            },
            gps=data.get('gps'),
            device_id=data.get('device_id')
        )
        
        if conferencia.conferente_id:
            notificacao = Notificacao(
                usuario_id=conferencia.conferente_id,
                titulo=f'Conferência {decisao.title()}',
                mensagem=f'A conferência #{conferencia.id} foi {decisao.lower()} pelo administrador',
                tipo='decisao_conferencia',
                url=f'/conferencia.html?id={conferencia.id}',
                lida=False
            )
            db.session.add(notificacao)
        
        db.session.commit()
        
        response_data = {
            'mensagem': f'Decisão {decisao} registrada com sucesso',
            'conferencia': conferencia.to_dict()
        }
        
        if lote_criado:
            response_data['lote_criado'] = lote_criado.to_dict()
            response_data['mensagem'] = f'Decisão {decisao} registrada e lote criado com sucesso'
        
        return jsonify(response_data), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': f'Erro ao registrar decisão: {str(e)}'}), 500

@bp.route('/estatisticas', methods=['GET'])
@jwt_required()
def obter_estatisticas():
    try:
        total_conferencias = ConferenciaRecebimento.query.count()
        pendentes = ConferenciaRecebimento.query.filter_by(conferencia_status='PENDENTE').count()
        divergentes = ConferenciaRecebimento.query.filter_by(conferencia_status='DIVERGENTE').count()
        aguardando_adm = ConferenciaRecebimento.query.filter_by(conferencia_status='AGUARDANDO_ADM').count()
        aprovadas = ConferenciaRecebimento.query.filter_by(conferencia_status='APROVADA').count()
        rejeitadas = ConferenciaRecebimento.query.filter_by(conferencia_status='REJEITADA').count()
        
        return jsonify({
            'total_conferencias': total_conferencias,
            'pendentes': pendentes,
            'divergentes': divergentes,
            'aguardando_adm': aguardando_adm,
            'aprovadas': aprovadas,
            'rejeitadas': rejeitadas
        }), 200
    
    except Exception as e:
        return jsonify({'erro': f'Erro ao obter estatísticas: {str(e)}'}), 500

@bp.route('/<int:id>/upload-foto', methods=['POST'])
@jwt_required()
def upload_foto(id):
    try:
        usuario_id = get_jwt_identity()
        conferencia = ConferenciaRecebimento.query.get(id)
        
        if not conferencia:
            return jsonify({'erro': 'Conferência não encontrada'}), 404
        
        if 'foto' not in request.files:
            return jsonify({'erro': 'Nenhuma foto enviada'}), 400
        
        foto = request.files['foto']
        if not foto.filename or foto.filename == '':
            return jsonify({'erro': 'Nome de arquivo inválido'}), 400
        
        if foto:
            pasta_evidencias = f'uploads/evidencias/conferencia/{id}'
            os.makedirs(pasta_evidencias, exist_ok=True)
            
            filename = secure_filename(foto.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            nome_arquivo = f'{timestamp}_{filename}'
            caminho_arquivo = os.path.join(pasta_evidencias, nome_arquivo)
            
            foto.save(caminho_arquivo)
            
            if conferencia.fotos_pesagem is None:
                conferencia.fotos_pesagem = []
            
            conferencia.fotos_pesagem.append(caminho_arquivo)
            
            registrar_auditoria_conferencia(
                conferencia, 
                'FOTO_ADICIONADA', 
                usuario_id, 
                detalhes={
                    'caminho_arquivo': caminho_arquivo,
                    'nome_original': foto.filename
                },
                gps=None,
                device_id=None
            )
            
            db.session.commit()
            
            return jsonify({
                'mensagem': 'Foto enviada com sucesso',
                'caminho': caminho_arquivo,
                'conferencia': conferencia.to_dict()
            }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': f'Erro ao fazer upload da foto: {str(e)}'}), 500
