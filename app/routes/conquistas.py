from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from app.models import db, Conquista, AporteConquista, Usuario
from app.auth import admin_required

bp = Blueprint('conquistas', __name__, url_prefix='/api/conquistas')

@bp.route('', methods=['GET'])
@jwt_required()
def listar_conquistas():
    try:
        usuario_id = get_jwt_identity()
        usuario = Usuario.query.get(usuario_id)
        
        if not usuario:
            return jsonify({'erro': 'Usuario nao encontrado'}), 404
        
        if usuario.tipo != 'admin':
            return jsonify({'erro': 'Acesso negado'}), 403
        
        status_filter = request.args.get('status')
        categoria_filter = request.args.get('categoria')
        
        query = Conquista.query.filter_by(usuario_id=usuario_id)
        
        if status_filter:
            query = query.filter_by(status=status_filter)
        if categoria_filter:
            query = query.filter_by(categoria=categoria_filter)
        
        conquistas = query.order_by(Conquista.prioridade.asc(), Conquista.data_meta.asc()).all()
        
        return jsonify([c.to_dict() for c in conquistas])
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@bp.route('', methods=['POST'])
@jwt_required()
def criar_conquista():
    try:
        usuario_id = get_jwt_identity()
        usuario = Usuario.query.get(usuario_id)
        
        if not usuario or usuario.tipo != 'admin':
            return jsonify({'erro': 'Acesso negado'}), 403
        
        data = request.get_json()
        
        if not data:
            return jsonify({'erro': 'Dados nao fornecidos'}), 400
        
        required_fields = ['titulo', 'valor_total', 'prazo_meses']
        for field in required_fields:
            if field not in data:
                return jsonify({'erro': f'Campo obrigatorio: {field}'}), 400
        
        prazo_meses = int(data['prazo_meses'])
        data_inicio = date.today()
        data_meta = data_inicio + relativedelta(months=prazo_meses)
        
        conquista = Conquista(
            usuario_id=usuario_id,
            titulo=data['titulo'],
            descricao=data.get('descricao', ''),
            categoria=data.get('categoria', 'outros'),
            valor_total=float(data['valor_total']),
            valor_investido=float(data.get('valor_investido', 0)),
            aporte_mensal=float(data.get('aporte_mensal', 0)),
            prazo_meses=prazo_meses,
            data_inicio=data_inicio,
            data_meta=data_meta,
            status='em_andamento',
            prioridade=int(data.get('prioridade', 1)),
            cor=data.get('cor', '#8b5cf6'),
            icone=data.get('icone', 'fa-trophy')
        )
        
        db.session.add(conquista)
        db.session.commit()
        
        return jsonify(conquista.to_dict()), 201
    except ValueError as e:
        return jsonify({'erro': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 500


@bp.route('/<int:id>', methods=['GET'])
@jwt_required()
def obter_conquista(id):
    try:
        usuario_id = get_jwt_identity()
        usuario = Usuario.query.get(usuario_id)
        
        if not usuario or usuario.tipo != 'admin':
            return jsonify({'erro': 'Acesso negado'}), 403
        
        conquista = Conquista.query.filter_by(id=id, usuario_id=usuario_id).first()
        
        if not conquista:
            return jsonify({'erro': 'Conquista nao encontrada'}), 404
        
        result = conquista.to_dict()
        result['aportes'] = [a.to_dict() for a in conquista.aportes]
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@bp.route('/<int:id>', methods=['PUT'])
@jwt_required()
def atualizar_conquista(id):
    try:
        usuario_id = get_jwt_identity()
        usuario = Usuario.query.get(usuario_id)
        
        if not usuario or usuario.tipo != 'admin':
            return jsonify({'erro': 'Acesso negado'}), 403
        
        conquista = Conquista.query.filter_by(id=id, usuario_id=usuario_id).first()
        
        if not conquista:
            return jsonify({'erro': 'Conquista nao encontrada'}), 404
        
        data = request.get_json()
        
        if 'titulo' in data:
            conquista.titulo = data['titulo']
        if 'descricao' in data:
            conquista.descricao = data['descricao']
        if 'categoria' in data:
            conquista.categoria = data['categoria']
        if 'valor_total' in data:
            conquista.valor_total = float(data['valor_total'])
        if 'valor_investido' in data:
            conquista.valor_investido = float(data['valor_investido'])
        if 'aporte_mensal' in data:
            conquista.aporte_mensal = float(data['aporte_mensal'])
        if 'prazo_meses' in data:
            conquista.prazo_meses = int(data['prazo_meses'])
            conquista.data_meta = conquista.data_inicio + relativedelta(months=conquista.prazo_meses)
        if 'status' in data:
            conquista.status = data['status']
        if 'prioridade' in data:
            conquista.prioridade = int(data['prioridade'])
        if 'cor' in data:
            conquista.cor = data['cor']
        if 'icone' in data:
            conquista.icone = data['icone']
        
        db.session.commit()
        
        return jsonify(conquista.to_dict())
    except ValueError as e:
        return jsonify({'erro': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 500


@bp.route('/<int:id>', methods=['DELETE'])
@jwt_required()
def excluir_conquista(id):
    try:
        usuario_id = get_jwt_identity()
        usuario = Usuario.query.get(usuario_id)
        
        if not usuario or usuario.tipo != 'admin':
            return jsonify({'erro': 'Acesso negado'}), 403
        
        conquista = Conquista.query.filter_by(id=id, usuario_id=usuario_id).first()
        
        if not conquista:
            return jsonify({'erro': 'Conquista nao encontrada'}), 404
        
        db.session.delete(conquista)
        db.session.commit()
        
        return jsonify({'mensagem': 'Conquista excluida com sucesso'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 500


@bp.route('/<int:id>/aportes', methods=['GET'])
@jwt_required()
def listar_aportes(id):
    try:
        usuario_id = get_jwt_identity()
        usuario = Usuario.query.get(usuario_id)
        
        if not usuario or usuario.tipo != 'admin':
            return jsonify({'erro': 'Acesso negado'}), 403
        
        conquista = Conquista.query.filter_by(id=id, usuario_id=usuario_id).first()
        
        if not conquista:
            return jsonify({'erro': 'Conquista nao encontrada'}), 404
        
        aportes = AporteConquista.query.filter_by(conquista_id=id).order_by(AporteConquista.data_aporte.desc()).all()
        
        return jsonify([a.to_dict() for a in aportes])
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@bp.route('/<int:id>/aportes', methods=['POST'])
@jwt_required()
def registrar_aporte(id):
    try:
        usuario_id = get_jwt_identity()
        usuario = Usuario.query.get(usuario_id)
        
        if not usuario or usuario.tipo != 'admin':
            return jsonify({'erro': 'Acesso negado'}), 403
        
        conquista = Conquista.query.filter_by(id=id, usuario_id=usuario_id).first()
        
        if not conquista:
            return jsonify({'erro': 'Conquista nao encontrada'}), 404
        
        data = request.get_json()
        
        if not data or 'valor' not in data:
            return jsonify({'erro': 'Valor do aporte e obrigatorio'}), 400
        
        valor = float(data['valor'])
        
        if valor <= 0:
            return jsonify({'erro': 'Valor deve ser maior que zero'}), 400
        
        data_aporte = date.today()
        if 'data_aporte' in data:
            data_aporte = datetime.strptime(data['data_aporte'], '%Y-%m-%d').date()
        
        aporte = AporteConquista(
            conquista_id=id,
            valor=valor,
            data_aporte=data_aporte,
            observacao=data.get('observacao', '')
        )
        
        conquista.valor_investido = float(conquista.valor_investido or 0) + valor
        
        if conquista.valor_investido >= float(conquista.valor_total):
            conquista.status = 'concluida'
        
        db.session.add(aporte)
        db.session.commit()
        
        return jsonify({
            'aporte': aporte.to_dict(),
            'conquista': conquista.to_dict()
        }), 201
    except ValueError as e:
        return jsonify({'erro': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 500


@bp.route('/resumo', methods=['GET'])
@jwt_required()
def obter_resumo():
    try:
        usuario_id = get_jwt_identity()
        usuario = Usuario.query.get(usuario_id)
        
        if not usuario or usuario.tipo != 'admin':
            return jsonify({'erro': 'Acesso negado'}), 403
        
        conquistas = Conquista.query.filter_by(usuario_id=usuario_id).all()
        
        total_metas = len(conquistas)
        metas_concluidas = len([c for c in conquistas if c.status == 'concluida'])
        metas_em_andamento = len([c for c in conquistas if c.status == 'em_andamento'])
        
        total_objetivo = sum(float(c.valor_total or 0) for c in conquistas)
        total_investido = sum(float(c.valor_investido or 0) for c in conquistas)
        total_aporte_mensal = sum(float(c.aporte_mensal or 0) for c in conquistas if c.status == 'em_andamento')
        
        progresso_geral = (total_investido / total_objetivo * 100) if total_objetivo > 0 else 0
        
        por_categoria = {}
        for c in conquistas:
            if c.categoria not in por_categoria:
                por_categoria[c.categoria] = {
                    'quantidade': 0,
                    'valor_total': 0,
                    'valor_investido': 0
                }
            por_categoria[c.categoria]['quantidade'] += 1
            por_categoria[c.categoria]['valor_total'] += float(c.valor_total or 0)
            por_categoria[c.categoria]['valor_investido'] += float(c.valor_investido or 0)
        
        return jsonify({
            'total_metas': total_metas,
            'metas_concluidas': metas_concluidas,
            'metas_em_andamento': metas_em_andamento,
            'total_objetivo': round(total_objetivo, 2),
            'total_investido': round(total_investido, 2),
            'total_aporte_mensal': round(total_aporte_mensal, 2),
            'progresso_geral': round(progresso_geral, 2),
            'por_categoria': por_categoria
        })
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@bp.route('/recomendacoes', methods=['GET'])
@jwt_required()
def obter_recomendacoes():
    try:
        usuario_id = get_jwt_identity()
        usuario = Usuario.query.get(usuario_id)
        
        if not usuario or usuario.tipo != 'admin':
            return jsonify({'erro': 'Acesso negado'}), 403
        
        conquistas = Conquista.query.filter_by(usuario_id=usuario_id, status='em_andamento').all()
        
        recomendacoes = []
        
        for c in conquistas:
            if c.aporte_necessario > float(c.aporte_mensal or 0) * 1.2:
                diferenca = c.aporte_necessario - float(c.aporte_mensal or 0)
                recomendacoes.append({
                    'tipo': 'aumento_aporte',
                    'conquista_id': c.id,
                    'titulo': c.titulo,
                    'mensagem': f'Para atingir sua meta no prazo, considere aumentar o aporte mensal em R$ {diferenca:.2f}',
                    'prioridade': 'alta' if diferenca > float(c.aporte_mensal or 1) else 'media'
                })
            
            if c.meses_restantes <= 3 and c.progresso < 80:
                recomendacoes.append({
                    'tipo': 'prazo_curto',
                    'conquista_id': c.id,
                    'titulo': c.titulo,
                    'mensagem': f'Faltam apenas {c.meses_restantes} meses e o progresso esta em {c.progresso:.1f}%. Considere estender o prazo ou aumentar os aportes.',
                    'prioridade': 'alta'
                })
            
            if c.progresso >= 90 and c.status == 'em_andamento':
                recomendacoes.append({
                    'tipo': 'quase_concluida',
                    'conquista_id': c.id,
                    'titulo': c.titulo,
                    'mensagem': f'Voce esta a {100 - c.progresso:.1f}% de concluir esta meta! Continue assim!',
                    'prioridade': 'baixa'
                })
        
        return jsonify(recomendacoes)
    except Exception as e:
        return jsonify({'erro': str(e)}), 500
