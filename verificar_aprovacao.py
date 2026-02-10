import psycopg2

DB_URL = 'postgresql://postgres:dWldGAyqtVAsQvMYvTIqBKXTkHedCLAS@shortline.proxy.rlwy.net:26559/railway'

conn = psycopg2.connect(DB_URL)
cur = conn.cursor()

# Material ID 15 (SUCATA PLACA CENTRAL B) que tem 13 fornecedores
print("=" * 100)
print("VERIFICAÇÃO: Fornecedores com preço ativo para Material ID 15 (SUCATA PLACA CENTRAL B)")
print("=" * 100)

cur.execute("""
    SELECT 
        f.id as fornecedor_id,
        f.nome as fornecedor_nome,
        f.tabela_preco_status,
        ftp.preco_fornecedor,
        ftp.status as preco_status
    FROM fornecedor_tabela_precos ftp
    JOIN fornecedores f ON f.id = ftp.fornecedor_id
    WHERE ftp.material_id = 15 
      AND ftp.status = 'ativo'
    ORDER BY f.nome
""")

print(f"\n{'ID':<5} {'FORNECEDOR':<40} {'STATUS TABELA':<20} {'PREÇO':<12} {'STATUS PREÇO':<15}")
print("-" * 100)

total = 0
aprovados = 0
nao_aprovados = 0

for forn_id, nome, tab_status, preco, preco_status in cur.fetchall():
    total += 1
    if tab_status == 'aprovada':
        aprovados += 1
        status_display = f"✅ {tab_status}"
    else:
        nao_aprovados += 1
        status_display = f"⚠️  {tab_status}"
    
    print(f"{forn_id:<5} {nome[:38]:<40} {status_display:<20} R$ {float(preco):<9.2f} {preco_status:<15}")

print("-" * 100)
print(f"\nRESUMO:")
print(f"  Total de fornecedores: {total}")
print(f"  ✅ Com tabela APROVADA: {aprovados}")
print(f"  ⚠️  SEM aprovação ou pendente: {nao_aprovados}")

if nao_aprovados > 0:
    print(f"\n⚠️  PROBLEMA: A query está incluindo {nao_aprovados} fornecedor(es) SEM tabela aprovada!")
    print("   Isso pode estar inflacionando a soma dos preços artificialmente.")

conn.close()
