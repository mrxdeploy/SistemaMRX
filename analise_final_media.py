import psycopg2
from decimal import Decimal

DB_URL = 'postgresql://postgres:dWldGAyqtVAsQvMYvTIqBKXTkHedCLAS@shortline.proxy.rlwy.net:26559/railway'

print("=" * 100)
print("ANÁLISE COMPLETA: Por que a Média R$ está retornando valores baixos?")
print("=" * 100)

try:
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # Passo 1: Dados das tabelas de fornecedores (denominador da fórmula ERRADA)
    print("\n[PASSO 1] Soma dos Preços nas Tabelas de Fornecedores Ativos")
    print("-" * 100)

    cur.execute("""
        SELECT 
            material_id,
            COUNT(*) as qtd_fornecedores,
            SUM(preco_fornecedor) as soma_precos
        FROM fornecedor_tabela_precos
        WHERE status = 'ativo'
        GROUP BY material_id
        ORDER BY material_id
    """)
    
    soma_precos_por_material = {}
    for mat_id, qtd_forn, soma in cur.fetchall():
        soma_float = float(soma)
        soma_precos_por_material[mat_id] = soma_float
        print(f"Material ID {mat_id}: {qtd_forn} fornecedor(es) | Soma = R$ {soma_float:.2f}")

    # Passo 2: Dados das OCs aprovadas (numerador e denominador correto)
    print("\n\n[PASSO 2] Dados das Ordens de Compra Aprovadas")
    print("-" * 100)
    
    # Como não sei se o FK está em solicitacoes ou ordens_compra, vou tentar ambos
    try:
        cur.execute("""
            SELECT 
                mb.id as material_id,
                mb.nome as material_nome,
                mb.classificacao,
                SUM(its.peso_kg) as peso_total,
                SUM(its.preco_por_kg_snapshot * its.peso_kg) as valor_total
            FROM itens_solicitacao its
            JOIN materiais_base mb ON mb.id = its.material_id
            JOIN solicitacoes sol ON sol.id = its.solicitacao_id
            JOIN ordens_compra oc ON oc.solicitacao_id = sol.id
            WHERE oc.status IN ('aprovada', 'em_transporte', 'recebida', 'conferida', 'finalizada')
              AND its.preco_por_kg_snapshot IS NOT NULL
              AND its.peso_kg > 0
            GROUP BY mb.id, mb.nome, mb.classificacao
            ORDER BY mb.classificacao, mb.nome
        """)
        dados_compras = cur.fetchall()
    except Exception as e:
        print(f"Tentativa 1 falhou (oc.solicitacao_id): {str(e)[:100]}")
        # Tentar inverso
        try:
            cur.execute("""
                SELECT 
                    mb.id as material_id,
                    mb.nome as material_nome,
                    mb.classificacao,
                    SUM(its.peso_kg) as peso_total,
                    SUM(its.preco_por_kg_snapshot * its.peso_kg) as valor_total
                FROM itens_solicitacao its
                JOIN materiais_base mb ON mb.id = its.material_id
                JOIN solicitacoes sol ON sol.id = its.solicitacao_id
                JOIN ordens_compra oc ON sol.ordem_compra_id = oc.id
                WHERE oc.status IN ('aprovada', 'em_transporte', 'recebida', 'conferida', 'finalizada')
                  AND its.preco_por_kg_snapshot IS NOT NULL
                  AND its.peso_kg > 0
                GROUP BY mb.id, mb.nome, mb.classificacao
                ORDER BY mb.classificacao, mb.nome
            """)
            dados_compras = cur.fetchall()
        except Exception as e2:
            print(f"Tentativa 2 falhou (sol.ordem_compra_id): {str(e2)[:100]}")
            dados_compras = []
    
    # Passo 3: Comparação das fórmulas
    print("\n\n[PASSO 3] COMPARAÇÃO: Fórmula Atual vs Fórmula Correta")
    print("=" * 100)
    print(f"{'MATERIAL':<40} | {'CLASSIF':<8} | {'VALOR PAGO':<12} | {'PESO (kg)':<10} | {'SOMA TABS':<12} | {'MÉDIA ERRADA':<12} | {'MÉDIA CERTA':<12}")
    print("-" * 100)
    
    for row in dados_compras:
        mat_id, nome, classif, peso, valor = row
        peso = float(peso)
        valor = float(valor)
        
        soma_tabelas = soma_precos_por_material.get(mat_id, 0.0)
        
        # FÓRMULA ATUAL (ERRADA) - usada no código
        media_errada = valor / soma_tabelas if soma_tabelas > 0 else 0.0
        
        # FÓRMULA CORRETA
        media_certa = valor / peso if peso > 0 else 0.0
        
        nome_curto = (nome[:37] + '...') if len(nome) > 40 else nome
        classif_str = classif if classif else 'N/A'
        
        print(f"{nome_curto:<40} | {classif_str:<8} | R$ {valor:<9.2f} | {peso:<10.2f} | R$ {soma_tabelas:<9.2f} | R$ {media_errada:<10.2f} | R$ {media_certa:<10.2f}")
    
    # Passo 4: Explicação do problema
    print("\n\n[CONCLUSÃO]")
    print("=" * 100)
    print("🔴 PROBLEMA IDENTIFICADO: Fórmula Matematicamente Incorreta")
    print("=" * 100)
    print("\nA fórmula atual no código (linha 470 de estoque_ativo.py) está ERRADA:")
    print("   Média R$ = Valor Total Pago ÷ Soma dos Preços das Tabelas de Fornecedores")
    print("\nEsta fórmula NÃO FAZ SENTIDO porque:")
    print("   1) Divide DINHEIRO (R$) por DINHEIRO (R$), resultando em um número SEM UNIDADE")
    print("   2) A 'Soma dos Preços' não tem relação com o peso comprado")
    print("   3) Quanto mais fornecedores ativos, maior a soma, menor o resultado")
    print("\nA fórmula CORRETA deveria ser:")
    print("   Média R$ = Valor Total Pago ÷ Peso Total Comprado")
    print("   Resultado: R$/kg (preço médio por quilograma)")
    print("\nEXEMPLO PRÁTICO:")
    if dados_compras:
        primeiro = dados_compras[0]
        mat_id_ex, nome_ex, classif_ex, peso_ex, valor_ex = primeiro
        peso_ex = float(peso_ex)
        valor_ex = float(valor_ex)
        soma_ex = soma_precos_por_material.get(mat_id_ex, 0.0)
        media_errada_ex = valor_ex / soma_ex if soma_ex > 0 else 0
        media_certa_ex = valor_ex / peso_ex if peso_ex > 0 else 0
        
        print(f"\n   Material: {nome_ex}")
        print(f"   Valor Pago: R$ {valor_ex:.2f}")
        print(f"   Peso Comprado: {peso_ex:.2f} kg")
        print(f"   Soma Tabelas Fornecedores: R$ {soma_ex:.2f}")
        print(f"\n   Cálculo ERRADO (código atual):")
        print(f"      R$ {valor_ex:.2f} ÷ R$ {soma_ex:.2f} = {media_errada_ex:.2f} (sem unidade lógica)")
        print(f"\n   Cálculo CORRETO (deveria ser):")
        print(f"      R$ {valor_ex:.2f} ÷ {peso_ex:.2f} kg = R$ {media_certa_ex:.2f}/kg")
        print(f"\n   DIFERENÇA: R$ {abs(media_certa_ex - media_errada_ex):.2f}/kg")
    
    print("\n" + "=" * 100)
    print("RECOMENDAÇÃO: Alterar linha 470 de app/routes/estoque_ativo.py")
    print("   DE:   media = round(v / soma_tabelas, 2)")
    print("   PARA: media = round(v / p, 2)  # v = valor, p = peso")
    print("=" * 100)
    
    conn.close()
    
except Exception as e:
    print(f"\n❌ ERRO: {e}")
    import traceback
    traceback.print_exc()
