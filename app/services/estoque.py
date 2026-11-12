"""
Serviço centralizado de cálculo de resumo do estoque.

Regras de negócio:
- Material conta em UM lugar: lote (matéria-prima) OU bag (em produção/pronto).
- Bags com status 'expedido' saíram fisicamente — NÃO entram em nenhum indicador.
- Peso Total = Σ peso_liquido lotes ativos (principais) + Σ peso_acumulado bags (aberto|cheio|devolvido_estoque)
"""

from app.models import db, Lote, BagProducao
from sqlalchemy import func

LOTES_ATIVOS_STATUS = [
    'em_estoque', 'disponivel', 'aprovado', 'em_producao',
    'CRIADO_SEPARACAO', 'PROCESSADO', 'criado_separacao', 'processado',
    'AGUARDANDO_SEPARACAO', 'EM_SEPARACAO'
]

# Statuses de bag que ainda contam no estoque (expedido fica de fora)
BAG_ESTOQUE_STATUS = ['aberto', 'cheio', 'devolvido_estoque']


def calcular_resumo_estoque():
    """
    Retorna dict com indicadores do estoque ativo.
    Usado pelo dashboard e por qualquer tela que precise dos totais.
    """
    lotes_ativos = Lote.query.filter(
        Lote.status.in_(LOTES_ATIVOS_STATUS),
        Lote.bloqueado == False,
        Lote.lote_pai_id.is_(None)
    ).count()

    em_producao = Lote.query.filter(
        Lote.status == 'em_producao',
        Lote.bloqueado == False,
        Lote.lote_pai_id.is_(None)
    ).count()

    bags_estoque = BagProducao.query.filter(
        BagProducao.status.in_(BAG_ESTOQUE_STATUS)
    ).count()

    # Peso de lotes principais (não sublotes — para evitar duplicação)
    peso_lotes = db.session.query(
        func.sum(func.coalesce(Lote.peso_liquido, Lote.peso_total_kg))
    ).filter(
        Lote.status.in_(LOTES_ATIVOS_STATUS),
        Lote.bloqueado == False,
        Lote.lote_pai_id.is_(None)
    ).scalar() or 0.0

    # Peso de bags em estoque (aberto + cheio + devolvido) — EXCLUINDO expedido
    peso_bags = db.session.query(
        func.sum(BagProducao.peso_acumulado)
    ).filter(
        BagProducao.status.in_(BAG_ESTOQUE_STATUS)
    ).scalar() or 0.0

    peso_lotes = float(peso_lotes)
    peso_bags = float(peso_bags)

    return {
        'lotes_ativos': lotes_ativos,
        'em_producao': em_producao,
        'bags_estoque': bags_estoque,
        'peso_total': round(peso_lotes + peso_bags, 3),
        'peso_materia_prima': round(peso_lotes, 3),
        'peso_em_bags': round(peso_bags, 3),
    }
