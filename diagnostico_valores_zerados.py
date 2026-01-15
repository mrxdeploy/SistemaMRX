"""
Script de diagnóstico e correção de valores zerados no Estoque Ativo

Este script:
1. Verifica dados existentes
2. Identifica porque valores estão zerados
3. Adiciona valores fictícios para testes se necessário
"""

import os
import sys

# Adicionar path do projeto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import (
    db, ItemSeparadoProducao, BagProducao, OrdemProducao,
    ItemSolicitacao, Solicitacao, OrdemCompra, MaterialBase, ClassificacaoGrade
)
from decimal import Decimal
import random

app = create_app()

def diagnosticar():
    """Analisa dados existentes para identificar problemas"""
    with app.app_context():
        print("=" * 60)
        print("DIAGNÓSTICO DE VALORES ZERADOS - ESTOQUE ATIVO")
        print("=" * 60)
        
        # 1. Verificar itens separados com custo_proporcional
        print("\n1. ITENS SEPARADOS EM BAGS (Total Bags)")
        print("-" * 40)
        
        bags_ativos = ['devolvido_estoque', 'cheio', 'aberto', 'enviado_refinaria']
        
        itens = db.session.query(ItemSeparadoProducao).join(
            ItemSeparadoProducao.bag
        ).filter(
            BagProducao.status.in_(bags_ativos)
        ).all()
        
        total_itens = len(itens)
        itens_com_custo = sum(1 for i in itens if i.custo_proporcional and float(i.custo_proporcional) > 0)
        itens_sem_custo = total_itens - itens_com_custo
        
        print(f"   Total de itens em bags ativos: {total_itens}")
        print(f"   Itens COM custo_proporcional: {itens_com_custo}")
        print(f"   Itens SEM custo_proporcional: {itens_sem_custo}")
        
        if itens_sem_custo > 0 and total_itens > 0:
            print(f"\n   ⚠️  {itens_sem_custo}/{total_itens} itens sem custo - valores zerados na tela!")
            print("   📋 Motivo: OPs criadas sem custo_total ou itens antigos")
        
        # Mostrar amostra de OPs
        print("\n   Amostra de OPs recentes:")
        ops = OrdemProducao.query.order_by(OrdemProducao.id.desc()).limit(5).all()
        for op in ops:
            custo = float(op.custo_total) if op.custo_total else 0
            print(f"      OP {op.numero_op}: custo_total = R$ {custo:.2f}")
        
        # 2. Verificar OC aprovadas para Total Compra
        print("\n\n2. ORDENS DE COMPRA APROVADAS (Total Compra)")
        print("-" * 40)
        
        oc_status_aprovados = ['aprovada', 'em_transporte', 'recebida', 'conferida', 'finalizada']
        
        ocs = OrdemCompra.query.filter(OrdemCompra.status.in_(oc_status_aprovados)).all()
        print(f"   Total de OCs aprovadas: {len(ocs)}")
        
        # Verificar itens com preco_por_kg_snapshot
        itens_oc = db.session.query(ItemSolicitacao).join(
            ItemSolicitacao.solicitacao
        ).join(
            Solicitacao.ordem_compra
        ).filter(
            OrdemCompra.status.in_(oc_status_aprovados)
        ).all()
        
        itens_com_preco = sum(1 for i in itens_oc if i.preco_por_kg_snapshot and float(i.preco_por_kg_snapshot) > 0)
        
        print(f"   Itens de OC aprovadas: {len(itens_oc)}")
        print(f"   Itens COM preco_por_kg_snapshot: {itens_com_preco}")
        print(f"   Itens SEM preco_por_kg_snapshot: {len(itens_oc) - itens_com_preco}")
        
        if len(itens_oc) - itens_com_preco > 0:
            print(f"\n   ⚠️  Items sem preço - valores zerados na aba Total Compra!")
        
        # 3. Verificar materiais cadastrados
        print("\n\n3. MATERIAIS BASE (tipos-lote)")
        print("-" * 40)
        
        materiais = MaterialBase.query.filter_by(ativo=True).all()
        print(f"   Total de materiais ativos: {len(materiais)}")
        for m in materiais[:10]:
            print(f"      {m.codigo}: {m.nome} ({m.classificacao})")
        
        # 4. Verificar classificações
        print("\n\n4. CLASSIFICAÇÕES DE GRADE")
        print("-" * 40)
        
        classificacoes = ClassificacaoGrade.query.filter_by(ativo=True).all()
        print(f"   Total de classificações ativas: {len(classificacoes)}")
        for c in classificacoes[:10]:
            preco = float(c.preco_estimado_kg) if c.preco_estimado_kg else 0
            print(f"      {c.nome} ({c.categoria}): R$ {preco:.2f}/kg")
        
        return {
            'total_itens': total_itens,
            'itens_sem_custo': itens_sem_custo,
            'ocs_aprovadas': len(ocs),
            'itens_oc': len(itens_oc),
            'itens_com_preco': itens_com_preco
        }


def adicionar_valores_ficticios():
    """Adiciona valores fictícios para testes"""
    with app.app_context():
        print("\n" + "=" * 60)
        print("ADICIONANDO VALORES FICTÍCIOS PARA TESTES")
        print("=" * 60)
        
        # 1. Atualizar itens separados sem custo
        print("\n1. Atualizando itens sem custo_proporcional...")
        
        bags_ativos = ['devolvido_estoque', 'cheio', 'aberto', 'enviado_refinaria']
        
        itens = db.session.query(ItemSeparadoProducao).join(
            ItemSeparadoProducao.bag
        ).filter(
            BagProducao.status.in_(bags_ativos)
        ).all()
        
        count_updated = 0
        for item in itens:
            if not item.custo_proporcional or float(item.custo_proporcional) == 0:
                # Gerar custo fictício baseado no peso (entre R$15 e R$50/kg)
                preco_kg = random.uniform(15.0, 50.0)
                custo = float(item.peso_kg) * preco_kg
                item.custo_proporcional = Decimal(str(round(custo, 2)))
                count_updated += 1
        
        print(f"   Itens atualizados: {count_updated}")
        
        # 2. Atualizar classificações sem preço estimado
        print("\n2. Atualizando classificações sem preco_estimado_kg...")
        
        classificacoes = ClassificacaoGrade.query.filter_by(ativo=True).all()
        count_class = 0
        for c in classificacoes:
            if not c.preco_estimado_kg or float(c.preco_estimado_kg) == 0:
                # Preços baseados na categoria
                precos_categoria = {
                    'HIGH_GRADE': random.uniform(40.0, 60.0),
                    'high': random.uniform(40.0, 60.0),
                    'MG1': random.uniform(25.0, 40.0),
                    'mg1': random.uniform(25.0, 40.0),
                    'MG2': random.uniform(15.0, 25.0),
                    'mg2': random.uniform(15.0, 25.0),
                    'LOW_GRADE': random.uniform(5.0, 15.0),
                    'low': random.uniform(5.0, 15.0),
                }
                cat = c.categoria if c.categoria else 'LOW_GRADE'
                preco = precos_categoria.get(cat, random.uniform(10.0, 30.0))
                c.preco_estimado_kg = Decimal(str(round(preco, 2)))
                count_class += 1
        
        print(f"   Classificações atualizadas: {count_class}")
        
        # 3. Atualizar itens de solicitação sem preco_por_kg_snapshot  
        print("\n3. Atualizando ItemSolicitacao sem preco_por_kg_snapshot...")
        
        oc_status_aprovados = ['aprovada', 'em_transporte', 'recebida', 'conferida', 'finalizada']
        
        itens_oc = db.session.query(ItemSolicitacao).join(
            ItemSolicitacao.solicitacao
        ).join(
            Solicitacao.ordem_compra
        ).filter(
            OrdemCompra.status.in_(oc_status_aprovados)
        ).all()
        
        count_itens = 0
        for item in itens_oc:
            if not item.preco_por_kg_snapshot or float(item.preco_por_kg_snapshot) == 0:
                # Gerar preço fictício baseado na classificação do material
                classif = item.material.classificacao if item.material else 'low'
                precos = {
                    'high': random.uniform(40.0, 60.0),
                    'mg1': random.uniform(25.0, 40.0),
                    'mg2': random.uniform(15.0, 25.0),
                    'low': random.uniform(5.0, 15.0),
                }
                preco = precos.get(classif, random.uniform(10.0, 30.0))
                item.preco_por_kg_snapshot = round(preco, 2)
                item.valor_calculado = round(float(item.peso_kg) * preco, 2)
                count_itens += 1
        
        print(f"   Itens de solicitação atualizados: {count_itens}")
        
        # Commit
        db.session.commit()
        print("\n✅ Valores fictícios adicionados com sucesso!")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Diagnóstico e correção de valores zerados')
    parser.add_argument('--fix', action='store_true', help='Adicionar valores fictícios')
    args = parser.parse_args()
    
    resultado = diagnosticar()
    
    if args.fix:
        adicionar_valores_ficticios()
        print("\n" + "=" * 60)
        print("DIAGNÓSTICO APÓS CORREÇÃO")
        diagnosticar()
    else:
        print("\n" + "=" * 60)
        print("Para adicionar valores fictícios, execute:")
        print("  python diagnostico_valores_zerados.py --fix")
        print("=" * 60)
