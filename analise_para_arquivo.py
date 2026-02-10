import psycopg2
import sys

DB_URL = 'postgresql://postgres:dWldGAyqtVAsQvMYvTIqBKXTkHedCLAS@shortline.proxy.rlwy.net:26559/railway'

# Redirecionar para arquivo
output_file = open('c:\\Users\\User\\SistemaMRX\\analise_resultado.txt', 'w', encoding='utf-8')
sys.stdout = output_file

try:
    print("=" * 100)
    print("ANÁLISE COMPLETA: Por que a Média R$ está retornando valores baixos?")
    print("=" * 100)

    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # Passo 1
    print("\n[PASSO 1] Soma dos Preços nas Tabelas de Fornecedores Ativos")
    print("-" * 100)

    cur.execute("""
        SELECT material_id, COUNT(*), SUM(preco_fornecedor)
        FROM fornecedor_tabela_precos
        WHERE status = 'ativo'
        GROUP BY material_id
    """)
    
    soma_precos_por_material = {}
    for mat_id, qtd, soma in cur.fetchall():
        soma_precos_por_material[mat_id] = float(soma)
        print(f"Material ID {mat_id}: {qtd} fornecedor(es) | Soma = R$ {float(soma):.2f}")

    # Passo 2
    print("\n[PASSO 2] Dados das Ordens de Compra Aprovadas")
    print("-" * 100)
    
    # Tentar com solicitacao_id em ordens_compra
    try:
        cur.execute("""
            SELECT mb.id, mb.nome, mb.classificacao, SUM(its.peso_kg), SUM(its.preco_por_kg_snapshot * its.peso_kg)
            FROM itens_solicitacao its
            JOIN materiais_base mb ON mb.id = its.material_id
            JOIN solicitacoes sol ON sol.id = its.solicitacao_id
            JOIN ordens_compra oc ON oc.solicitacao_id = sol.id
            WHERE oc.status IN ('aprovada', 'em_transporte', 'recebida', 'conferida', 'finalizada')
              AND its.preco_por_kg_snapshot IS NOT NULL AND its.peso_kg > 0
            GROUP BY mb.id, mb.nome, mb.classificacao
        """)
        dados_compras = cur.fetchall()
        print(f"✓ JOIN bem-sucedido: encontrados {len(dados_compras)} materiais em OCs aprovadas")
    except Exception as e:
        print(f"JOIN falhou: {str(e)[:200]}")
        dados_compras = []

    # Passo 3
    print("\n[PASSO 3] ANÁLISE COMPARATIVA")
    print("=" * 100)
    print(f"{'MATERIAL':<40} {'CLASSIF':<10} {'V.PAGO':<12} {'PESO':<12} {'SOMA_TAB':<12} {'MED_ERRADA':<12} {'MED_CERTA':<12}")
    print("-" * 100)
    
    for mat_id, nome, classif, peso, valor in dados_compras:
        peso_f = float(peso)
        valor_f = float(valor)
        soma_tab = soma_precos_por_material.get(mat_id, 0.0)
        
        med_errada = valor_f / soma_tab if soma_tab > 0 else 0
        med_certa = valor_f / peso_f if peso_f > 0 else 0
        
        nome_s = nome[:38] if len(nome) > 40 else nome
        classif_s = (classif or 'N/A')[:8]
        
        print(f"{nome_s:<40} {classif_s:<10} R$ {valor_f:<9.2f} {peso_f:<10.2f}kg R$ {soma_tab:<9.2f} R$ {med_errada:<10.2f} R$ {med_certa:<10.2f}")

    print("\n" + "=" * 100)
    print("CONCLUSÃO")
    print("=" * 100)
    print("\nFÓRMULA ATUAL (ERRADA):")
    print("  Média = Valor Total ÷ Soma dos Preços das Tabelas de Fornecedores")
    print("\nFÓRMULA CORRETA:")
    print("  Média = Valor Total ÷ Peso Total")
    print("\nPROBLEMA: A fórmula atual não faz sentido matematicamente.")
    print("Divide dinheiro por dinheiro, resultando em valor sem unidade lógica.")
    print("=" * 100)

    conn.close()
    
except Exception as e:
    print(f"\nERRO: {e}")
    import traceback
    traceback.print_exc()

finally:
    output_file.close()
    # Restaurar stdout
    sys.stdout = sys.__stdout__
    print("Análise concluída! Resultados salvos em: analise_resultado.txt")
