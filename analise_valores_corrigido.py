import psycopg2
import sys

# Credenciais do banco fornecidas pelo usuário
DB_URL = 'postgresql://postgres:dWldGAyqtVAsQvMYvTIqBKXTkHedCLAS@shortline.proxy.rlwy.net:26559/railway'

def run_analysis():
    print("Conectando ao banco de dados...")
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
    except Exception as e:
        print(f"Erro ao conectar: {e}")
        return

    print("=" * 80)
    print("ANÁLISE PROFUNDA: Motivo dos valores baixos na Média R$")
    print("=" * 80)

    # 1. Obter Soma dos Preços das Tabelas de Fornecedores (Denominador da fórmula ATUAL/INCORRETA)
    print("\n[1] Analisando Tabelas de Preços de Fornecedores Ativas...")
    cur.execute("""
        SELECT 
            material_id, 
            SUM(preco_fornecedor) as soma_precos
        FROM fornecedor_tabela_precos 
        WHERE status = 'ativo' 
        GROUP BY material_id
    """)
    soma_precos_tabelas = {row[0]: float(row[1]) for row in cur.fetchall()}
    print(f"    -> Encontrados dados de tabelas para {len(soma_precos_tabelas)} materiais.")

    # 2. Obter Dados Reais de Compra (Numerador e Denominador da fórmula CORRETA)
    print("\n[2] Analisando Ordens de Compra (OCs) Aprovadas...")
    # Ajustando para os nomes de tabelas corretos identificados: itens_solicitacao, materiais_base, etc.
    query_compras = """
        SELECT 
            mb.id as material_id,
            mb.nome as material_nome,
            mb.classificacao,
            SUM(its.peso_kg) as peso_total_comprado,
            SUM(its.preco_por_kg_snapshot * its.peso_kg) as valor_total_pago
        FROM itens_solicitacao its
        JOIN materiais_base mb ON mb.id = its.material_id
        JOIN solicitacoes sol ON sol.id = its.solicitacao_id
        JOIN ordens_compra oc ON oc.id = sol.ordem_compra_id
        WHERE oc.status IN ('aprovada', 'em_transporte', 'recebida', 'conferida', 'finalizada')
          AND its.preco_por_kg_snapshot IS NOT NULL
          AND its.peso_kg > 0
        GROUP BY mb.id, mb.nome, mb.classificacao
        ORDER BY mb.classificacao, mb.nome
    """
    
    try:
        cur.execute(query_compras)
        dados_compras = cur.fetchall()
    except Exception as e:
        print(f"Erro ao executar query de compras: {e}")
        conn.close()
        return

    print(f"    -> Encontrados registros de compra para {len(dados_compras)} materiais.")

    # 3. Comparação e Explicação
    print("\n[3] COMPARATIVO DE FÓRMULAS E VALORES CALCULADOS")
    print("-" * 100)
    print(f"{'MATERIAL':<30} | {'VALOR PAGO':<12} | {'SOMA TABELAS':<12} | {'PESO TOTAL':<10} | {'MÉDIA ATUAL':<12} | {'MÉDIA REAL':<12}")
    print("-" * 100)
    print(f"{'':<30} | {'(Numerador)':<12} | {'(Denom. Errado)':<12} | {'(Denom. Certo)':<10} | {'(Vl / Soma)':<12} | {'(Vl / Peso)':<12}")
    print("-" * 100)

    for row in dados_compras:
        mat_id, nome, classif, peso, valor = row
        peso = float(peso)
        valor = float(valor)
        
        # Denominador da fórmula atual (errada)
        soma_tabelas = soma_precos_tabelas.get(mat_id, 0.0)
        
        # Cálculo Atual (Errado)
        media_atual = valor / soma_tabelas if soma_tabelas > 0 else 0.0
        
        # Cálculo Correto (Certo)
        media_real = valor / peso if peso > 0 else 0.0
        
        # Formatando nome para caber na tabela
        nome_fmt = (nome[:27] + '..') if len(nome) > 27 else nome
        
        print(f"{nome_fmt:<30} | R$ {valor:<9.2f} | R$ {soma_tabelas:<9.2f} | {peso:<8.2f}kg | R$ {media_atual:<9.2f} | R$ {media_real:<9.2f}")

    print("-" * 100)
    
    # 4. Explicação detalhada do motivo
    print("\n[4] CONCLUSÃO TÉCNICA DO PROBLEMA")
    print("=" * 80)
    print("Os valores estão baixos porque o sistema está DIVIDINDO o Valor Total Pago pela")
    print("SOMA ARITMÉTICA dos preços de tabela de todos os fornecedores ativos, em vez de")
    print("dividir pelo PESO TOTAL comprado.")
    print("\nExemplo Matemático do Erro:")
    print("Imagine que você comprou 1000kg de um material por R$ 5.000,00.")
    print("A média real é R$ 5,00/kg (5000 / 1000).")
    print("Mas se você tem 10 fornecedores com preço de tabela de R$ 5,00 cada, a soma é R$ 50,00.")
    print("A fórmula atual faz: 5000 / 50 = R$ 100,00 (Neste caso daria alto).")
    print("\nMas veja o caso inverso (seu caso provável):")
    print("Se a soma das tabelas for um valor ALTO (muitos fornecedores ou preços altos) comparado")
    print("ao valor pago relativo, o resultado fica distorcido.")
    print("Mas o erro PRINCIPAL é conceitual: Não faz sentido dividir Valor Financeiro (R$) por Soma de Preços Unitários (R$/kg).")
    print("Isso resulta em uma unidade sem sentido (kg).")
    print("A conta correta deve ser R$ (Valor) / kg (Peso) = R$/kg.")

    conn.close()

if __name__ == "__main__":
    run_analysis()
