import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app, socketio
from app.models import db, MaterialBase, TabelaPreco, TabelaPrecoItem, Fornecedor
from sqlalchemy import text

def seed_tabelas_preco():
    print("\n" + "="*80)
    print(" CRIANDO TABELAS DE PREÇO POR ESTRELAS")
    print("="*80)
    
    tabelas = [
        {"nome": "Tabela 1 Estrela", "nivel_estrelas": 1},
        {"nome": "Tabela 2 Estrelas", "nivel_estrelas": 2},
        {"nome": "Tabela 3 Estrelas", "nivel_estrelas": 3}
    ]
    
    created_count = 0
    for tabela_data in tabelas:
        tabela_existente = TabelaPreco.query.filter_by(nivel_estrelas=tabela_data['nivel_estrelas']).first()
        
        if not tabela_existente:
            tabela = TabelaPreco(
                nome=tabela_data['nome'],
                nivel_estrelas=tabela_data['nivel_estrelas'],
                ativo=True
            )
            db.session.add(tabela)
            created_count += 1
            print(f"✅ Criada: {tabela_data['nome']}")
        else:
            print(f"⏭️  Já existe: {tabela_data['nome']}")
    
    db.session.commit()
    print(f"\n✨ Total de tabelas criadas: {created_count}")
    return created_count

def seed_materiais_base():
    print("\n" + "="*80)
    print(" CADASTRANDO MATERIAIS BASE (45+ TIPOS DE SUCATA ELETRÔNICA)")
    print("="*80)
    
    materiais = [
        {"nome": "SUCATA PROCESSADOR CERÂMICO A", "classificacao": "pesado"},
        {"nome": "SUCATA PROCESSADOR CERÂMICO B", "classificacao": "pesado"},
        {"nome": "SUCATA PROCESSADOR CERÂMICO C", "classificacao": "pesado"},
        {"nome": "SUCATA PROCESSADOR SLOT", "classificacao": "pesado"},
        {"nome": "SUCATA PROCESSADOR PLÁSTICO A", "classificacao": "leve"},
        {"nome": "SUCATA PROCESSADOR PLÁSTICO B", "classificacao": "leve"},
        {"nome": "SUCATA PLACA MÃE SERVIDOR", "classificacao": "pesado"},
        {"nome": "SUCATA PLACA MÃE DESKTOP", "classificacao": "medio"},
        {"nome": "SUCATA PLACA MÃE NOTEBOOK", "classificacao": "medio"},
        {"nome": "SUCATA MEMÓRIA RAM DDR", "classificacao": "pesado"},
        {"nome": "SUCATA HD SATA", "classificacao": "medio"},
        {"nome": "SUCATA SSD", "classificacao": "pesado"},
        {"nome": "SUCATA FONTE ATX", "classificacao": "leve"},
        {"nome": "SUCATA CABO FLAT", "classificacao": "leve"},
        {"nome": "SUCATA PLACA DE REDE", "classificacao": "medio"},
        {"nome": "SUCATA COOLER/DISSIPADOR", "classificacao": "leve"},
        {"nome": "SUCATA CONECTOR GOLD FINGER", "classificacao": "pesado"},
        {"nome": "SUCATA SLOT PCI", "classificacao": "medio"},
        {"nome": "SUCATA CAPACITOR ELETROLÍTICO", "classificacao": "leve"},
        {"nome": "SUCATA RESISTOR/TRANSISTOR", "classificacao": "leve"},
        {"nome": "SUCATA CHIP BIOS", "classificacao": "medio"},
        {"nome": "SUCATA BATERIA CMOS", "classificacao": "leve"},
        {"nome": "SUCATA PLACA CONTROLADORA", "classificacao": "medio"},
        {"nome": "SUCATA MODEM/ROTEADOR", "classificacao": "medio"},
        {"nome": "SUCATA SWITCH/HUB", "classificacao": "medio"},
        {"nome": "SUCATA TECLADO", "classificacao": "leve"},
        {"nome": "SUCATA MOUSE", "classificacao": "leve"},
        {"nome": "SUCATA MONITOR LCD", "classificacao": "pesado"},
        {"nome": "SUCATA MONITOR CRT", "classificacao": "pesado"},
        {"nome": "SUCATA WEBCAM", "classificacao": "leve"},
        {"nome": "SUCATA IMPRESSORA JATO TINTA", "classificacao": "medio"},
        {"nome": "SUCATA IMPRESSORA LASER", "classificacao": "pesado"},
        {"nome": "SUCATA SCANNER", "classificacao": "medio"},
        {"nome": "SUCATA NO-BREAK", "classificacao": "pesado"},
        {"nome": "SUCATA ESTABILIZADOR", "classificacao": "medio"},
        {"nome": "SUCATA DRIVE CD/DVD", "classificacao": "leve"},
        {"nome": "SUCATA DISQUETE/DRIVER", "classificacao": "leve"},
        {"nome": "SUCATA PLACA DE SOM", "classificacao": "medio"},
        {"nome": "SUCATA PLACA DE VÍDEO", "classificacao": "pesado"},
        {"nome": "SUCATA CONECTOR IDE/SATA", "classificacao": "leve"},
        {"nome": "SUCATA JUMPER/PARAFUSO", "classificacao": "leve"},
        {"nome": "SUCATA GABINETE DESKTOP", "classificacao": "medio"},
        {"nome": "SUCATA GABINETE SERVIDOR", "classificacao": "pesado"},
        {"nome": "SUCATA NOTEBOOK COMPLETO", "classificacao": "pesado"},
        {"nome": "SUCATA TABLET", "classificacao": "medio"},
        {"nome": "SUCATA CELULAR/SMARTPHONE", "classificacao": "medio"},
        {"nome": "SUCATA BATERIA NOTEBOOK", "classificacao": "medio"},
        {"nome": "SUCATA CARREGADOR NOTEBOOK", "classificacao": "leve"},
        {"nome": "SUCATA PEN DRIVE", "classificacao": "leve"},
        {"nome": "SUCATA CARTÃO SD/MICROSD", "classificacao": "leve"}
    ]
    
    created_count = 0
    tabelas_preco = TabelaPreco.query.all()
    
    if not tabelas_preco or len(tabelas_preco) < 3:
        print("⚠️  ERRO: É necessário criar as 3 tabelas de preço primeiro!")
        return 0
    
    for idx, material_data in enumerate(materiais, start=1):
        material_existente = MaterialBase.query.filter_by(nome=material_data['nome']).first()
        
        if not material_existente:
            codigo = f"MAT{idx:03d}"
            
            material = MaterialBase(
                codigo=codigo,
                nome=material_data['nome'],
                classificacao=material_data['classificacao'],
                ativo=True
            )
            db.session.add(material)
            db.session.flush()
            
            for tabela in tabelas_preco:
                preco_existente = TabelaPrecoItem.query.filter_by(
                    tabela_preco_id=tabela.id,
                    material_id=material.id
                ).first()
                
                if not preco_existente:
                    preco_item = TabelaPrecoItem(
                        tabela_preco_id=tabela.id,
                        material_id=material.id,
                        preco_por_kg=0.00,
                        ativo=True
                    )
                    db.session.add(preco_item)
            
            created_count += 1
            print(f"✅ {codigo} - {material_data['nome']} ({material_data['classificacao']})")
        else:
            print(f"⏭️  Já existe: {material_data['nome']}")
    
    db.session.commit()
    print(f"\n✨ Total de materiais criados: {created_count}")
    print(f"📊 Total de preços gerados: {created_count * 3} (3 preços por material)")
    return created_count

def atualizar_fornecedores_tabela_default():
    print("\n" + "="*80)
    print(" ATUALIZANDO FORNECEDORES PARA TABELA 1 ESTRELA (DEFAULT)")
    print("="*80)
    
    tabela_1_estrela = TabelaPreco.query.filter_by(nivel_estrelas=1).first()
    
    if not tabela_1_estrela:
        print("⚠️  ERRO: Tabela 1 estrela não encontrada!")
        return 0
    
    fornecedores_sem_tabela = Fornecedor.query.filter(
        (Fornecedor.tabela_preco_id == None) | (Fornecedor.tabela_preco_id == 0)
    ).all()
    
    updated_count = 0
    for fornecedor in fornecedores_sem_tabela:
        fornecedor.tabela_preco_id = tabela_1_estrela.id
        updated_count += 1
    
    db.session.commit()
    print(f"✅ {updated_count} fornecedores vinculados à Tabela 1 Estrela")
    return updated_count

def main():
    app = create_app()
    
    with app.app_context():
        print("\n" + "🚀" * 40)
        print("SEED: MÓDULO COMPRADOR - SISTEMA DE PREÇOS POR ESTRELAS")
        print("🚀" * 40)
        
        try:
            print("\n📋 Criando tabelas no banco de dados...")
            db.create_all()
            print("✅ Tabelas criadas com sucesso!\n")
            
            tabelas_created = seed_tabelas_preco()
            materiais_created = seed_materiais_base()
            fornecedores_updated = atualizar_fornecedores_tabela_default()
            
            print("\n" + "="*80)
            print("✨ RESUMO DO SEED")
            print("="*80)
            print(f"  📊 Tabelas de preço criadas: {tabelas_created}")
            print(f"  📦 Materiais base cadastrados: {materiais_created}")
            print(f"  💰 Itens de preço gerados: {materiais_created * 3}")
            print(f"  🏭 Fornecedores atualizados: {fornecedores_updated}")
            print("="*80)
            print("🎉 SEED CONCLUÍDO COM SUCESSO!")
            print("="*80 + "\n")
            
        except Exception as e:
            print(f"\n❌ ERRO ao executar seed: {str(e)}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            sys.exit(1)

if __name__ == '__main__':
    main()
