import psycopg2

conn = psycopg2.connect('postgresql://postgres:dWldGAyqtVAsQvMYvTIqBKXTkHedCLAS@shortline.proxy.rlwy.net:26559/railway')
cur = conn.cursor()

print("=" * 80)
print("ANÁLISE: Por que a Média R$ está baixa?")
print("=" * 80)

# Passo 1: Ver soma dos preços nas tabelas de fornecedores
print("\n1. SOMA DOS PREÇOS DAS TABELAS DE FORNECEDORES (por material)")
print("-" * 80)
cur.execute("""
    SELECT material_id, SUM(preco_fornecedor) 
    FROM fornecedor_tabela_precos 
    WHERE status = 'ativo' 
    GROUP BY material_id
""")
soma_precos = {}
for row in cur.fetchall():
    soma_precos[row[0]] = float(row[1])
    print(f"Material ID {row[0]}: Soma = R$ {row[1]:.2f}")

# Passo 2: Ver dados das OCs aprovadas
print("\n2. DADOS DAS ORDENS DE COMPRA APROVADAS")
print("-" * 80)
cur.execute("""
    SELECT 
        its.material_id,
        SUM(its.peso_kg) as peso_total,
        SUM(its.preco_por_kg_snapshot * its.peso_kg) as valor_total
    FROM item_solicitacao its
    JOIN solicitacao sol ON sol.id = its.solicitacao_id
    JOIN ordem_compra oc ON oc.id = sol.ordem_compra_id
    WHERE oc.status IN ('aprovada', 'em_transporte', 'recebida', 'conferida', 'finalizada')
        AND its.preco_por_kg_snapshot IS NOT NULL
        AND its.peso_kg > 0
    GROUP BY its.material_id
""")

print("\nMaterial | Peso | Valor Pago | Média CORRETA | Soma Tabelas | Média ERRADA")
print("-" * 80)
for row in cur.fetchall():
    mat_id = row[0]
    peso = float(row[1])
    valor = float(row[2])
    soma_tab = soma_precos.get(mat_id, 0.0)
    
    media_correta = valor / peso if peso > 0 else 0
    media_errada = valor / soma_tab if soma_tab > 0 else 0
    
    print(f"\nMaterial #{mat_id}")
    print(f"  Peso: {peso:.2f} kg")
    print(f"  Valor Pago: R$ {valor:.2f}")
    print(f"  Média CORRETA (Valor/Peso): R$ {media_correta:.2f}/kg")
    print(f"  Soma Tabelas: R$ {soma_tab:.2f}")
    print(f"  Média ERRADA (Valor/Soma): R$ {media_errada:.2f}")
    print(f"  DIFERENÇA: R$ {media_correta - media_errada:.2f}/kg")

print("\n" + "=" * 80)
print("CONCLUSÃO")
print("=" * 80)
print("A fórmula no código está ERRADA:")
print("  Média = Valor Total / Soma dos Preços das Tabelas de Fornecedores")
print("\nDeveria ser:")
print("  Média = Valor Total / Peso Total")
print("=" * 80)

cur.close()
conn.close()
