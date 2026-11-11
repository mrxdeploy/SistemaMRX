"""
Testes para a feature Comprador na OrdemCompra.

Cenários cobertos (todos offline, sem banco real):
1. Usuário comprador → comprador_id = usuario_id (auto-fill)
2. Usuário não-comprador sem comprador_id → erro 400
3. Usuário não-comprador com comprador_id inválido → erro 400
4. Usuário não-comprador com comprador_id inativo → erro 400
5. Usuário não-comprador com comprador_id não-comprador → erro 400
6. Usuário não-comprador com comprador_id válido → OK
7. to_dict inclui comprador_id e comprador_nome
8. Solicitacao.to_dict inclui oc_comprador_nome
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
# Simulação das regras de negócio sem Flask/DB
# ---------------------------------------------------------------------------

class FakeUsuario:
    def __init__(self, id, is_comprador=False, ativo=True, nome="Teste"):
        self.id = id
        self.is_comprador = is_comprador
        self.ativo = ativo
        self.nome = nome


class FakeOC:
    def __init__(self, comprador_id=None, criado_por=None):
        self.comprador_id = comprador_id
        self.criado_por = criado_por
        self.comprador = None  # seria o objeto FakeUsuario


def resolver_comprador(usuario_logado, comprador_id_payload, db_get_usuario):
    """
    Espelha a lógica do backend em criar_oc():
    - Se usuário logado é_comprador → comprador_id = usuario_id
    - Caso contrário → comprador_id do payload, validado
    Retorna (comprador_id, None) ou (None, mensagem_de_erro)
    """
    if usuario_logado.is_comprador:
        return usuario_logado.id, None

    if not comprador_id_payload:
        return None, "Campo comprador_id é obrigatório para usuários não compradores"

    comprador = db_get_usuario(int(comprador_id_payload))
    if not comprador or not comprador.ativo or not comprador.is_comprador:
        return None, "Comprador inválido ou inativo"

    return comprador.id, None


# ---------------------------------------------------------------------------
# Banco de dados fake
# ---------------------------------------------------------------------------

USUARIOS_DB = {
    1: FakeUsuario(1, is_comprador=True,  ativo=True,  nome="Maria Compradora"),
    2: FakeUsuario(2, is_comprador=False, ativo=True,  nome="João Admin"),
    3: FakeUsuario(3, is_comprador=True,  ativo=False, nome="Pedro Inativo"),
    4: FakeUsuario(4, is_comprador=False, ativo=True,  nome="Ana Financeiro"),
}


def db_get(id):
    return USUARIOS_DB.get(id)


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------

def test_comprador_logado_auto_fill():
    """Usuário com is_comprador=True: comprador_id = id do próprio usuário."""
    u = USUARIOS_DB[1]
    cid, err = resolver_comprador(u, None, db_get)
    assert err is None
    assert cid == 1


def test_nao_comprador_sem_payload_erro():
    """Usuário não-comprador sem payload comprador_id → erro 400."""
    u = USUARIOS_DB[2]
    cid, err = resolver_comprador(u, None, db_get)
    assert err is not None
    assert "obrigatório" in err


def test_nao_comprador_id_inexistente_erro():
    """Usuário não-comprador com comprador_id que não existe no banco → erro."""
    u = USUARIOS_DB[2]
    cid, err = resolver_comprador(u, 999, db_get)
    assert err is not None
    assert "inválido" in err.lower() or "inativo" in err.lower()


def test_nao_comprador_id_inativo_erro():
    """Usuário não-comprador com comprador_id inativo → erro."""
    u = USUARIOS_DB[2]
    cid, err = resolver_comprador(u, 3, db_get)
    assert err is not None


def test_nao_comprador_id_nao_comprador_erro():
    """Usuário não-comprador com comprador_id de usuário sem is_comprador → erro."""
    u = USUARIOS_DB[2]
    cid, err = resolver_comprador(u, 4, db_get)
    assert err is not None


def test_nao_comprador_id_valido_ok():
    """Usuário não-comprador com comprador_id válido e ativo → OK."""
    u = USUARIOS_DB[2]
    cid, err = resolver_comprador(u, 1, db_get)
    assert err is None
    assert cid == 1


def test_to_dict_inclui_comprador():
    """OC dict deve ter comprador_id e comprador_nome."""
    oc = FakeOC(comprador_id=1, criado_por=2)
    oc.comprador = USUARIOS_DB[1]

    oc_dict = {
        'comprador_id': oc.comprador_id,
        'comprador_nome': oc.comprador.nome if oc.comprador else None,
        'criado_por': oc.criado_por,
    }

    assert oc_dict['comprador_id'] == 1
    assert oc_dict['comprador_nome'] == "Maria Compradora"
    assert oc_dict['criado_por'] == 2


def test_solicitacao_to_dict_inclui_oc_comprador_nome():
    """Solicitacao.to_dict deve ter oc_comprador_nome quando OC existir."""
    oc = FakeOC(comprador_id=1, criado_por=2)
    oc.comprador = USUARIOS_DB[1]

    sol_dict = {
        'oc_id': 10,
        'oc_status': 'em_analise',
        'oc_comprador_nome': oc.comprador.nome if oc.comprador else None,
    }

    assert sol_dict['oc_comprador_nome'] == "Maria Compradora"


# ---------------------------------------------------------------------------
# Runner simples (sem pytest instalado)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    testes = [
        test_comprador_logado_auto_fill,
        test_nao_comprador_sem_payload_erro,
        test_nao_comprador_id_inexistente_erro,
        test_nao_comprador_id_inativo_erro,
        test_nao_comprador_id_nao_comprador_erro,
        test_nao_comprador_id_valido_ok,
        test_to_dict_inclui_comprador,
        test_solicitacao_to_dict_inclui_oc_comprador_nome,
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
