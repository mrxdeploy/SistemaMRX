"""
Classificação de faixa de preço P1/P2/P3 para itens de Pedido de Compra.

Regras:
  P1 (1★, verde)   — preco <= preco_p1
  P2 (2★, laranja) — preco_p1 < preco <= preco_p2
  P3 (3★, vermelho)— preco_p2 < preco <= preco_p3
  P3+ (roxo)       — preco > preco_p3  (custom acima da tabela)
  SEM_TABELA (cinza)— material não possui preços cadastrados
"""

from app.models import TabelaPrecoItem, TabelaPreco


_COR_P1  = '#10b981'  # verde
_COR_P2  = '#f59e0b'  # laranja
_COR_P3  = '#dc2626'  # vermelho
_COR_P3P = '#7c3aed'  # roxo (acima da tabela)
_COR_SEM = '#6b7280'  # cinza


def buscar_precos_tabela_material(material_id):
    """Retorna {p1, p2, p3} em float para o material, ou None em cada campo ausente."""
    if not material_id:
        return {'p1': None, 'p2': None, 'p3': None}

    itens = (
        TabelaPrecoItem.query
        .join(TabelaPreco, TabelaPrecoItem.tabela_preco_id == TabelaPreco.id)
        .filter(
            TabelaPrecoItem.material_id == material_id,
            TabelaPrecoItem.ativo == True,
            TabelaPreco.ativo == True,
        )
        .all()
    )

    mapa = {}
    for item in itens:
        nivel = item.tabela_preco.nivel_estrelas  # 1, 2 ou 3
        mapa[nivel] = float(item.preco_por_kg) if item.preco_por_kg else 0.0

    return {
        'p1': mapa.get(1),
        'p2': mapa.get(2),
        'p3': mapa.get(3),
    }


def classificar_faixa_preco(p1, p2, p3, preco_unitario):
    """
    Classifica preco_unitario nas faixas P1/P2/P3/P3+/SEM_TABELA.
    p1, p2, p3 podem ser None se não cadastrado.
    """
    sem_tabela = (p1 is None and p2 is None and p3 is None)
    if sem_tabela or preco_unitario is None:
        return {
            'faixa': 'SEM_TABELA',
            'estrelas': None,
            'cor': _COR_SEM,
            'label': '—',
            'p1': p1, 'p2': p2, 'p3': p3,
            'sem_tabela': True,
        }

    p = float(preco_unitario)

    if p1 is not None and p <= p1:
        return {'faixa': 'P1', 'estrelas': 1, 'cor': _COR_P1, 'label': 'P1',
                'p1': p1, 'p2': p2, 'p3': p3, 'sem_tabela': False}

    if p2 is not None and p <= p2:
        return {'faixa': 'P2', 'estrelas': 2, 'cor': _COR_P2, 'label': 'P2',
                'p1': p1, 'p2': p2, 'p3': p3, 'sem_tabela': False}

    if p3 is not None and p <= p3:
        return {'faixa': 'P3', 'estrelas': 3, 'cor': _COR_P3, 'label': 'P3',
                'p1': p1, 'p2': p2, 'p3': p3, 'sem_tabela': False}

    # Acima de P3
    return {'faixa': 'P3+', 'estrelas': 3, 'cor': _COR_P3P, 'label': 'P3+',
            'p1': p1, 'p2': p2, 'p3': p3, 'sem_tabela': False}


def enriquecer_item_com_faixa(item_dict):
    """
    Recebe o dict de um ItemSolicitacao e devolve o mesmo dict
    com 'faixa_preco' e 'precos_tabela' adicionados.
    Não modifica o DB — apenas acrescenta campos calculados.
    """
    material_id = item_dict.get('material_id')
    preco_customizado = item_dict.get('preco_customizado', False)
    estrelas_snapshot = item_dict.get('estrelas_snapshot')
    preco_por_kg_snapshot = item_dict.get('preco_por_kg_snapshot')
    preco_oferecido = item_dict.get('preco_oferecido')

    tabela = buscar_precos_tabela_material(material_id)
    item_dict['precos_tabela'] = tabela

    if preco_customizado:
        # Preço negociado: compara contra tabela atual
        preco_ref = preco_oferecido if preco_oferecido is not None else preco_por_kg_snapshot
        faixa = classificar_faixa_preco(tabela['p1'], tabela['p2'], tabela['p3'], preco_ref)
    elif estrelas_snapshot is not None:
        # Preço da tabela: usa estrelas_snapshot como fonte confiável
        _mapa_faixa = {1: 'P1', 2: 'P2', 3: 'P3'}
        _mapa_cor   = {1: _COR_P1, 2: _COR_P2, 3: _COR_P3}
        faixa_nome = _mapa_faixa.get(estrelas_snapshot, 'P3')
        faixa = {
            'faixa': faixa_nome,
            'estrelas': estrelas_snapshot,
            'cor': _mapa_cor.get(estrelas_snapshot, _COR_P3),
            'label': faixa_nome,
            'p1': tabela['p1'],
            'p2': tabela['p2'],
            'p3': tabela['p3'],
            'sem_tabela': False,
        }
    else:
        # Fallback: calcula pelo preço snapshot
        preco_ref = preco_por_kg_snapshot
        faixa = classificar_faixa_preco(tabela['p1'], tabela['p2'], tabela['p3'], preco_ref)

    item_dict['faixa_preco'] = faixa
    return item_dict
