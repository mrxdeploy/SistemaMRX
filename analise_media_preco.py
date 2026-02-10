import psycopg2
from decimal import Decimal

# Conectar ao banco
conn = psycopg2.connect('postgresql://postgres:dWldGAyqtVAsQvMYvTIqBKXTkHedCLAS@shortline.proxy.rlwy.net:26559/railway')
cur = conn.cursor()

print("=" * 80)
print("ANÁLISE DA FÓRMULA DE MÉDIA R$ - TOTAL COMPRA")
print("=" * 80)

# 1. Verificar soma dos preços nas tabelas de fornecedores
print("\n1. SOMA DOS PREÇOS POR MATERIAL (Tabelas de Fornecedores Ativas)")
print("-" * 80)
cur.execute("""
    SELECT 
        ftp.material_id,
        mb.nome as material_nome,
        COUNT(*) as qtd_fornecedores,
        SUM(ftp.preco_fornecedor) as soma_precos
    FROM fornecedor_tabela_precos ftp
    LEFT JOIN material_base mb ON mb.id = ftp.material_id
    WHERE ftp.status = 'ativo'
    GROUP BY ftp.material_id, mb.nome
    ORDER BY ftp.material_id
""")

soma_precos_dict = {}
for row in cur.fetchall():
    mat_id, mat_nome, qtd, soma = row
    soma_precos_dict[mat_id] = float(soma) if soma else 0.0
    print(f"Material #{mat_id}: {mat_nome}")
    print(f"  → {qtd} fornecedor(es) com preço ativo")
    print(f"  → Soma dos preços: R$ {soma:.2f}")
    print()

# 2. Verificar dados das OC aprovadas
print("\n2. DADOS DAS ORDENS DE COMPRA APROVADAS")
print("-" * 80)
cur.execute("""
    SELECT 
        mb.id as material_id,
        mb.nome as material_nome,
        mb.classificacao,
        SUM(its.peso_kg) as peso_total,
        SUM(its.preco_por_kg_snapshot * its.peso_kg) as valor_total,
        AVG(its.preco_por_kg_snapshot) as media_preco_pago
    FROM item_solicitacao its
    JOIN material_base mb ON mb.id = its.material_id
    JOIN solicitacao sol ON sol.id = its.solicitacao_id
    JOIN ordem_compra oc ON oc.id = sol.ordem_compra_id
    WHERE oc.status IN ('aprovada', 'em_transporte', 'recebida', 'conferida', 'finalizada')
        AND its.preco_por_kg_snapshot IS NOT NULL
        AND its.peso_kg > 0
    GROUP BY mb.id, mb.nome, mb.classificacao
    ORDER BY mb.classificacao, mb.nome
""")

print("Material | Peso Total | Valor Total | Média Real (Valor/Peso)")
print("-" * 80)

materiais_data = {}
for row in cur.fetchall():
    mat_id, mat_nome, classif, peso, valor, media_avg = row
    peso_float = float(peso) if peso else 0.0
    valor_float = float(valor) if valor else 0.0
    
    # Calcular média CORRETA (valor / peso)
    media_correta = valor_float / peso_float if peso_float > 0 else 0.0
    
    # Pegar soma dos preços das tabelas
    soma_tabelas = soma_precos_dict.get(mat_id, 0.0)
    
    # Calcular média ATUAL (fórmula errada no código)
    media_atual = valor_float / soma_tabelas if soma_tabelas > 0 else 0.0
    
    materiais_data[mat_id] = {
        'nome': mat_nome,
        'classif': classif,
        'peso': peso_float,
        'valor': valor_float,
        'media_correta': media_correta,
        'soma_tabelas': soma_tabelas,
        'media_atual': media_atual
    }
    
    print(f"\n{mat_nome} ({classif})")
    print(f"  Peso Total: {peso_float:.2f} kg")
    print(f"  Valor Total Pago: R$ {valor_float:.2f}")
    print(f"  Média CORRETA (Valor/Peso): R$ {media_correta:.2f}/kg")
    print(f"  Soma Tabelas Fornecedores: R$ {soma_tabelas:.2f}")
    print(f"  Média ATUAL no Código (Valor/Soma): R$ {media_atual:.2f}")
    print(f"  ⚠️  DIFERENÇA: R$ {media_correta - media_atual:.2f}/kg")

# 3. Resumo da análise
print("\n" + "=" * 80)
print("RESUMO DA ANÁLISE")
print("=" * 80)
print("\nFÓRMULA ATUAL (INCORRETA):")
print("  Média R$ = Valor Total Pago ÷ Soma dos Preços das Tabelas de Fornecedores")
print("\nFÓRMULA CORRETA:")
print("  Média R$ = Valor Total Pago ÷ Peso Total Comprado")
print("\nPROBLEMA IDENTIFICADO:")
print("  A fórmula atual divide o valor pago pela SOMA dos preços cadastrados")
print("  nas tabelas de fornecedores ativos, o que não tem sentido lógico.")
print("  Isso resulta em valores extremamente baixos e incorretos.")

# 4. Mostrar exemplo prático
if materiais_data:
    primeiro = list(materiais_data.values())[0]
    print("\n" + "=" * 80)
    print("EXEMPLO PRÁTICO")
    print("=" * 80)
    print(f"\nMaterial: {primeiro['nome']}")
    print(f"\nDados:")
    print(f"  - Valor Total Pago (OCs aprovadas): R$ {primeiro['valor']:.2f}")
    print(f"  - Peso Total Comprado: {primeiro['peso']:.2f} kg")
    print(f"  - Soma dos Preços nas Tabelas: R$ {primeiro['soma_tabelas']:.2f}")
    print(f"\nCálculo ERRADO (código atual):")
    print(f"  R$ {primeiro['valor']:.2f} ÷ R$ {primeiro['soma_tabelas']:.2f} = R$ {primeiro['media_atual']:.2f}")
    print(f"\nCálculo CORRETO (deveria ser):")
    print(f"  R$ {primeiro['valor']:.2f} ÷ {primeiro['peso']:.2f} kg = R$ {primeiro['media_correta']:.2f}/kg")

cur.close()
conn.close()

print("\n" + "=" * 80)
print("ANÁLISE CONCLUÍDA")
print("=" * 80)
