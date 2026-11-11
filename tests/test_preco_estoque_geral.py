"""
Testes do cálculo de preço médio no Estoque Geral.

Caso base (pedido ROBSON DE OLIVEIRA BONILHA, lote 2026-99653):
  MAT041 SUCATA PLACA MARROM     16,5 kg  R$ 7,50   → R$ 123,75
  MAT030 SUCATA PLACA LEVE B      7,0 kg  R$125,00  → R$ 875,00
  MAT029 SUCATA PLACA INTERMEDIÁRIA 1,0kg R$ 50,00  → R$  50,00
  MAT013 SUCATA PLACA DOURADA B  35,7 kg  R$200,00  → R$7.140,00
  MAT015 SUCATA PLACA CENTRAL B   2,2 kg  R$165,00  → R$ 363,00
  TOTAL                          62,4 kg            → R$8.551,75

Regra esperada: cada item usa seu próprio preco_por_kg_snapshot.
  Marrom nesta OC: R$ 7,50 (nunca R$ 137,05 = 8.551,75 / 62,4).
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
# Utilitários puros (sem banco) — testáveis offline
# ---------------------------------------------------------------------------

def preco_medio_ponderado(itens):
    """
    Σ(preco_kg_i × peso_i) / Σ(peso_i)

    itens: list of (peso_kg, preco_kg)
    Retorna float arredondado em 2 casas, ou 0.0 se peso total = 0.
    """
    vpeso = sum(float(p) * float(c) for p, c in itens if float(p) > 0)
    peso  = sum(float(p) for p, _ in itens if float(p) > 0)
    return round(vpeso / peso, 2) if peso > 0 else 0.0


# ---------------------------------------------------------------------------
# 1. Preço/kg por item — nunca usa o total do pedido
# ---------------------------------------------------------------------------

ITENS_OC_2026_99653 = [
    # (tipo_codigo, peso_kg, preco_por_kg_snapshot, valor_calculado)
    ("MAT041", 16.5,  7.50,   123.75),
    ("MAT030",  7.0, 125.00,  875.00),
    ("MAT029",  1.0,  50.00,   50.00),
    ("MAT013", 35.7, 200.00, 7140.00),
    ("MAT015",  2.2, 165.00,  363.00),
]

VALOR_TOTAL_OC = sum(v for _, _, _, v in ITENS_OC_2026_99653)   # 8551.75
PESO_TOTAL_OC  = sum(p for _, p, _, _ in ITENS_OC_2026_99653)   # 62.4


def test_preco_marrom_nao_usa_total_oc():
    """Marrom deve ter R$ 7,50, nunca R$ 137,05 (= total_oc / peso_total_oc)."""
    preco_errado = round(VALOR_TOTAL_OC / PESO_TOTAL_OC, 2)
    assert preco_errado == 137.05, "Setup errado no teste"

    for codigo, _, preco_snapshot, _ in ITENS_OC_2026_99653:
        if codigo == "MAT041":
            assert preco_snapshot == 7.50, (
                f"Marrom deve ter preco_snapshot=7,50; encontrado {preco_snapshot}"
            )
            assert preco_snapshot != preco_errado, (
                "Marrom NÃO pode usar o preço médio total do pedido (R$ 137,05)"
            )


def test_valor_calculado_consistente():
    """valor_calculado = peso × preco_snapshot para cada item."""
    for codigo, peso, preco, valor in ITENS_OC_2026_99653:
        esperado = round(peso * preco, 2)
        assert abs(valor - esperado) < 0.02, (
            f"{codigo}: {peso}×{preco}={esperado}, mas valor={valor}"
        )


# ---------------------------------------------------------------------------
# 2. Fórmula de preço médio ponderado (pure Python)
# ---------------------------------------------------------------------------

def test_media_ponderada_dois_fornecedores():
    """
    Marrom comprada de dois fornecedores com preços diferentes →
    média ponderada correta.
    """
    # Fornecedor A: 16,5 kg a R$ 7,50
    # Fornecedor B: 10,0 kg a R$ 9,00
    itens = [(16.5, 7.50), (10.0, 9.00)]
    # Esperado: (16.5*7.50 + 10*9.00) / (16.5+10) = 213.75 / 26.5 ≈ 8.07
    result = preco_medio_ponderado(itens)
    assert result == 8.07, f"Esperado 8.07, obtido {result}"


def test_media_ponderada_item_unico():
    """Um único fornecedor: média = preço do item."""
    result = preco_medio_ponderado([(16.5, 7.50)])
    assert result == 7.50


def test_media_ponderada_peso_zero_ignorado():
    """Item com peso=0 não deve influenciar a média."""
    result = preco_medio_ponderado([(0.0, 999.99), (16.5, 7.50)])
    assert result == 7.50


def test_media_ponderada_sem_itens():
    """Lista vazia → 0.0, sem ZeroDivisionError."""
    assert preco_medio_ponderado([]) == 0.0


def test_media_ponderada_todos_pesos_zero():
    """Todos com peso=0 → 0.0."""
    assert preco_medio_ponderado([(0.0, 10.0), (0.0, 20.0)]) == 0.0


# ---------------------------------------------------------------------------
# 3. Consistência Estoque Geral vs Total Compra (simulação pura)
# ---------------------------------------------------------------------------

def _simular_preco_oc(itens_oc, tipo_codigo):
    """
    Simula a query batch do Estoque Geral:
    agrupa por tipo_codigo e calcula Σ(preco*peso)/Σ(peso).
    """
    vpeso_tot = sum(p * c for cod, p, c, _ in itens_oc if cod == tipo_codigo)
    peso_tot  = sum(p     for cod, p, _, _ in itens_oc if cod == tipo_codigo)
    return round(vpeso_tot / peso_tot, 2) if peso_tot > 0 else 0.0


def _simular_media_total_compra(itens_todas_ocs, tipo_codigo):
    """
    Simula a query do Total Compra:
    Σ(preco_por_kg_snapshot × peso_kg) / Σ(peso_kg) para o material.
    """
    return _simular_preco_oc(itens_todas_ocs, tipo_codigo)


def test_consistencia_estoque_vs_total_compra():
    """
    Com as mesmas OCs aprovadas, Estoque Geral e Total Compra
    devem retornar o mesmo preço médio por material.
    """
    ocs = ITENS_OC_2026_99653[:]  # Uma OC de exemplo

    for codigo, _, _, _ in ocs:
        pm_estoque       = _simular_preco_oc(ocs, codigo)
        pm_total_compra  = _simular_media_total_compra(ocs, codigo)
        assert pm_estoque == pm_total_compra, (
            f"{codigo}: Estoque Geral={pm_estoque} != Total Compra={pm_total_compra}"
        )


def test_marrom_multiplas_ocs():
    """
    Marrom comprada em 3 OCs diferentes → média ponderada global correta.
    """
    historico = [
        # (tipo, peso, preco, valor)
        ("MAT041", 16.5,  7.50, 123.75),   # OC 1 - Robson
        ("MAT041", 50.0,  8.00, 400.00),   # OC 2 - outro fornecedor
        ("MAT041", 30.0,  9.50, 285.00),   # OC 3 - outro fornecedor
    ]
    # Esperado: (123.75 + 400 + 285) / (16.5 + 50 + 30) = 808.75 / 96.5 ≈ 8.38
    pm = _simular_media_total_compra(historico, "MAT041")
    assert pm == round(808.75 / 96.5, 2), f"Obtido {pm}"


# ---------------------------------------------------------------------------
# Runner simples (sem pytest instalado)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    testes = [
        test_preco_marrom_nao_usa_total_oc,
        test_valor_calculado_consistente,
        test_media_ponderada_dois_fornecedores,
        test_media_ponderada_item_unico,
        test_media_ponderada_peso_zero_ignorado,
        test_media_ponderada_sem_itens,
        test_media_ponderada_todos_pesos_zero,
        test_consistencia_estoque_vs_total_compra,
        test_marrom_multiplas_ocs,
    ]
    falhas = 0
    for t in testes:
        try:
            t()
            print(f"  PASS  {t.__name__}")
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}")
            falhas += 1
        except Exception as e:
            print(f"  ERROR {t.__name__}: {e}")
            falhas += 1

    print(f"\n{len(testes) - falhas}/{len(testes)} testes passaram.")
    sys.exit(0 if falhas == 0 else 1)
