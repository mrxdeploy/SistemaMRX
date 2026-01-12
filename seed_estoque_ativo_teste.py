
#!/usr/bin/env python3
"""
Script para popular dados de teste para Estoque Ativo
Cria lotes, separações e bags para testar a visualização
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from decimal import Decimal
from datetime import datetime, timedelta
import random
from app import create_app, db
from app.models import (
    Usuario, Fornecedor, Lote, ClassificacaoGrade,
    OrdemProducao, ItemSeparadoProducao, BagProducao, TipoLote
)

def criar_lotes_com_separacao():
    """Cria lotes já separados para visualização no estoque ativo"""
    print("\n📦 Criando lotes com separação...")
    
    # Buscar fornecedor e tipo de lote
    fornecedor = Fornecedor.query.first()
    if not fornecedor:
        print("❌ Nenhum fornecedor encontrado. Execute seed_producao_completo.py primeiro")
        return []
    
    tipo_lote = TipoLote.query.first()
    if not tipo_lote:
        tipo_lote = TipoLote(nome='Eletrônicos Diversos', codigo='ELET-DIV', ativo=True)
        db.session.add(tipo_lote)
        db.session.flush()
    
    admin = Usuario.query.filter_by(tipo='admin').first()
    if not admin:
        print("❌ Usuário admin não encontrado")
        return []
    
    # Buscar classificações
    classificacoes = ClassificacaoGrade.query.filter_by(ativo=True).all()
    if not classificacoes:
        print("❌ Nenhuma classificação encontrada. Execute seed_producao_completo.py primeiro")
        return []
    
    lotes_criados = []
    
    # Criar 3 lotes principais que serão separados
    lotes_principais = [
        {
            'material': 'Placas-mãe Desktop Mix',
            'peso': 125.5,
            'separacoes': [
                {'classificacao': 'PLACA-MÃE DESKTOP', 'peso': 45.2, 'qtd': 12},
                {'classificacao': 'PLACA DE VÍDEO', 'peso': 28.5, 'qtd': 8},
                {'classificacao': 'MEMÓRIA DOURADA DDR', 'peso': 12.3, 'qtd': 25},
                {'classificacao': 'PROCESSADOR CERÂMICO OURO B', 'peso': 8.5, 'qtd': 15},
                {'classificacao': 'FONTE ATX', 'peso': 18.0, 'qtd': 10},
                {'classificacao': 'CABOS E FIOS', 'peso': 8.0, 'qtd': 20},
                {'classificacao': 'RESÍDUO MISTO', 'peso': 5.0, 'qtd': 0},
            ]
        },
        {
            'material': 'Celulares e Smartphones',
            'peso': 85.3,
            'separacoes': [
                {'classificacao': 'PROCESSADOR CERÂMICO OURO A', 'peso': 12.5, 'qtd': 35},
                {'classificacao': 'MEMÓRIA DOURADA DDR', 'peso': 8.2, 'qtd': 28},
                {'classificacao': 'PLACA DOURADA TIPO A', 'peso': 25.5, 'qtd': 42},
                {'classificacao': 'CONECTORES BANHADOS OURO', 'peso': 6.8, 'qtd': 50},
                {'classificacao': 'PLÁSTICO ELETRÔNICO', 'peso': 22.3, 'qtd': 85},
                {'classificacao': 'RESÍDUO MISTO', 'peso': 10.0, 'qtd': 0},
            ]
        },
        {
            'material': 'Processadores Intel/AMD Mix',
            'peso': 45.8,
            'separacoes': [
                {'classificacao': 'PROCESSADOR CERÂMICO OURO A', 'peso': 18.5, 'qtd': 55},
                {'classificacao': 'PROCESSADOR CERÂMICO OURO B', 'peso': 12.3, 'qtd': 38},
                {'classificacao': 'CONECTORES BANHADOS OURO', 'peso': 8.0, 'qtd': 45},
                {'classificacao': 'PLACA CENTRAL PREMIUM', 'peso': 5.0, 'qtd': 12},
                {'classificacao': 'RESÍDUO MISTO', 'peso': 2.0, 'qtd': 0},
            ]
        }
    ]
    
    for idx, lote_data in enumerate(lotes_principais, 1):
        # Criar lote principal
        numero = f'LT-{datetime.now().strftime("%Y%m")}-{3000+idx}'
        peso_original = lote_data['peso']
        
        lote_principal = Lote(
            numero_lote=numero,
            fornecedor_id=fornecedor.id,
            tipo_lote_id=tipo_lote.id,
            peso_bruto_recebido=peso_original,
            peso_liquido=peso_original * 0.95,
            peso_total_kg=peso_original,
            status='em_estoque',
            qualidade_recebida='Boa',
            localizacao_atual=f'SETOR-{chr(65+idx)}1',
            lote_pai_id=None,  # Explicitamente definir como lote principal
            data_criacao=datetime.utcnow() - timedelta(days=random.randint(5, 15)),
            observacoes=f'{lote_data["material"]} - Lote recebido e separado'
        )
        db.session.add(lote_principal)
        db.session.flush()
        
        logger.info(f"✅ Lote principal {numero} criado com ID {lote_principal.id}")
        
        print(f"\n✅ Lote principal criado: {numero}")
        print(f"   Material: {lote_data['material']}")
        print(f"   Peso original: {peso_original} kg")
        
        # Criar sublotes (separações)
        for sep_idx, sep in enumerate(lote_data['separacoes'], 1):
            # Buscar classificação
            classificacao = next((c for c in classificacoes if c.nome == sep['classificacao']), None)
            if not classificacao:
                continue
            
            peso_sublote = sep['peso']
            qtd = sep['qtd']
            
            # Criar sublote
            numero_sublote = f'{numero}-SUB{sep_idx}'
            
            # Buscar ou criar tipo de lote específico para o material
            tipo_sublote = TipoLote.query.filter_by(nome=classificacao.nome).first()
            if not tipo_sublote:
                # Gerar código único verificando se já existe
                codigo_base = f'MAT-{sep_idx:03d}'
                contador = 0
                codigo = codigo_base
                while TipoLote.query.filter_by(codigo=codigo).first():
                    contador += 1
                    codigo = f'MAT-{sep_idx:03d}-{contador}'
                
                tipo_sublote = TipoLote(
                    nome=classificacao.nome,
                    codigo=codigo,
                    ativo=True
                )
                db.session.add(tipo_sublote)
                db.session.flush()
            
            sublote = Lote(
                numero_lote=numero_sublote,
                fornecedor_id=fornecedor.id,
                tipo_lote_id=tipo_sublote.id,
                peso_bruto_recebido=peso_sublote,
                peso_total_kg=peso_sublote,
                peso_liquido=peso_sublote,
                quantidade_itens=qtd,
                status='em_estoque',
                qualidade_recebida='Boa',
                localizacao_atual=f'SETOR-{chr(65+idx)}{sep_idx}',
                lote_pai_id=lote_principal.id,
                data_criacao=datetime.utcnow() - timedelta(days=random.randint(1, 5)),
                observacoes=f'Material: {classificacao.nome}'
            )
            db.session.add(sublote)
            
            print(f"   → Sublote: {numero_sublote} - {classificacao.nome} ({peso_sublote} kg)")
        
        lotes_criados.append(lote_principal)
    
    db.session.commit()
    print(f"\n✅ {len(lotes_criados)} lotes principais criados com suas separações!")
    return lotes_criados


def criar_lotes_sem_separacao():
    """Cria alguns lotes que ainda não foram separados"""
    print("\n📦 Criando lotes sem separação (para contraste)...")
    
    fornecedor = Fornecedor.query.first()
    if not fornecedor:
        return []
    
    tipo_lote = TipoLote.query.first()
    if not tipo_lote:
        return []
    
    lotes_simples = []
    
    materiais = [
        'Computadores Completos',
        'Notebooks Diversos',
        'Impressoras e Scanners'
    ]
    
    for idx, material in enumerate(materiais, 1):
        numero = f'LT-{datetime.now().strftime("%Y%m")}-{4000+idx}'
        peso = round(random.uniform(80, 250), 2)
        
        lote = Lote(
            numero_lote=numero,
            fornecedor_id=fornecedor.id,
            tipo_lote_id=tipo_lote.id,
            peso_bruto_recebido=peso,
            peso_liquido=peso * 0.95,
            peso_total_kg=peso,
            status='em_estoque',
            qualidade_recebida='Boa',
            localizacao_atual=f'PATIO-{idx}',
            data_criacao=datetime.utcnow() - timedelta(days=random.randint(1, 3)),
            observacoes=f'{material} - Aguardando separação'
        )
        db.session.add(lote)
        lotes_simples.append(lote)
        
        print(f"   Lote: {numero} - {material} ({peso} kg) - SEM separação")
    
    db.session.commit()
    print(f"✅ {len(lotes_simples)} lotes sem separação criados!")
    return lotes_simples


def criar_bags_estoque():
    """Cria bags no estoque com materiais diversos"""
    print("\n🎒 Criando bags no estoque...")
    
    admin = Usuario.query.filter_by(tipo='admin').first()
    classificacoes = ClassificacaoGrade.query.filter_by(ativo=True).all()
    
    if not classificacoes:
        print("❌ Nenhuma classificação encontrada")
        return []
    
    bags_criados = []
    
    # Criar 5 bags com diferentes níveis de preenchimento
    bags_data = [
        {'classificacao': 'PROCESSADOR CERÂMICO OURO A', 'peso': 45.5, 'qtd': 120, 'status': 'cheio'},
        {'classificacao': 'MEMÓRIA DOURADA DDR', 'peso': 28.3, 'qtd': 85, 'status': 'aberto'},
        {'classificacao': 'PLACA-MÃE DESKTOP', 'peso': 52.0, 'qtd': 42, 'status': 'cheio'},
        {'classificacao': 'CONECTORES BANHADOS OURO', 'peso': 15.8, 'qtd': 95, 'status': 'aberto'},
        {'classificacao': 'HD/SSD COMPONENTES', 'peso': 38.2, 'qtd': 68, 'status': 'devolvido_estoque'},
    ]
    
    for bag_data in bags_data:
        classificacao = next((c for c in classificacoes if c.nome == bag_data['classificacao']), None)
        if not classificacao:
            continue
        
        bag = BagProducao(
            codigo=BagProducao.gerar_codigo_bag(classificacao.nome),
            classificacao_grade_id=classificacao.id,
            peso_acumulado=Decimal(str(bag_data['peso'])),
            quantidade_itens=bag_data['qtd'],
            peso_capacidade_max=Decimal('50.0'),
            status=bag_data['status'],
            criado_por_id=admin.id,
            data_criacao=datetime.utcnow() - timedelta(days=random.randint(1, 10)),
            observacoes=f'Bag de teste - {classificacao.categoria}'
        )
        db.session.add(bag)
        bags_criados.append(bag)
        
        print(f"   Bag: {bag.codigo} - {classificacao.nome} ({bag_data['peso']} kg) - {bag_data['status']}")
    
    db.session.commit()
    print(f"✅ {len(bags_criados)} bags criados!")
    return bags_criados


def main():
    app = create_app()
    with app.app_context():
        print("\n" + "="*60)
        print("🚀 CRIANDO DADOS DE TESTE PARA ESTOQUE ATIVO")
        print("="*60)
        
        # Verificar admin
        admin = Usuario.query.filter_by(tipo='admin').first()
        if not admin:
            print("❌ Usuário admin não encontrado!")
            return
        
        print(f"👤 Admin: {admin.nome}")
        
        # Limpar dados de teste anteriores (lotes com números começando com LT-202512)
        print("\n🗑️  Limpando dados de teste anteriores...")
        lotes_teste = Lote.query.filter(Lote.numero_lote.like('LT-202512%')).all()
        for lote in lotes_teste:
            # Deletar sublotes primeiro
            sublotes = Lote.query.filter_by(lote_pai_id=lote.id).all()
            for sublote in sublotes:
                db.session.delete(sublote)
            # Deletar lote principal
            db.session.delete(lote)
        db.session.commit()
        print(f"✅ {len(lotes_teste)} lotes de teste removidos")
        
        # Criar dados
        lotes_separados = criar_lotes_com_separacao()
        lotes_simples = criar_lotes_sem_separacao()
        bags = criar_bags_estoque()
        
        # Resumo
        print("\n" + "="*60)
        print("✅ DADOS DE TESTE CRIADOS COM SUCESSO!")
        print("="*60)
        print(f"📦 Lotes com separação: {len(lotes_separados)}")
        print(f"📦 Lotes sem separação: {len(lotes_simples)}")
        print(f"🎒 Bags no estoque: {len(bags)}")
        print(f"\n📊 Total de lotes: {Lote.query.count()}")
        print(f"🎒 Total de bags: {BagProducao.query.count()}")
        print("="*60)
        print("\n💡 Acesse /estoque-ativo.html para visualizar os dados!")
        print("="*60 + "\n")

if __name__ == '__main__':
    main()
