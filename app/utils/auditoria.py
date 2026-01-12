from flask import request
from app.models import AuditoriaLog, AuditoriaOC, db
from typing import Optional, Dict, Any

def registrar_auditoria(
    usuario_id: Optional[int],
    acao: str,
    entidade_tipo: str,
    entidade_id: Optional[int] = None,
    detalhes: Optional[Dict[str, Any]] = None
):
    try:
        ip_address = request.remote_addr if request else None
        user_agent = request.headers.get('User-Agent') if request else None
        
        log = AuditoriaLog(
            usuario_id=usuario_id,
            acao=acao,
            entidade_tipo=entidade_tipo,
            entidade_id=entidade_id,
            detalhes=detalhes,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        db.session.add(log)
        db.session.commit()
        
        return log
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao registrar auditoria: {e}")
        return None

def registrar_login(usuario_id: int, sucesso: bool = True):
    acao = 'login_sucesso' if sucesso else 'login_falha'
    return registrar_auditoria(
        usuario_id=usuario_id,
        acao=acao,
        entidade_tipo='usuario',
        entidade_id=usuario_id
    )

def registrar_criacao(usuario_id: Optional[int], entidade_tipo: str, entidade_id: int, detalhes: Optional[Dict] = None):
    return registrar_auditoria(
        usuario_id=usuario_id,
        acao='criar',
        entidade_tipo=entidade_tipo,
        entidade_id=entidade_id,
        detalhes=detalhes
    )

def registrar_atualizacao(usuario_id: Optional[int], entidade_tipo: str, entidade_id: int, detalhes: Optional[Dict] = None):
    return registrar_auditoria(
        usuario_id=usuario_id,
        acao='atualizar',
        entidade_tipo=entidade_tipo,
        entidade_id=entidade_id,
        detalhes=detalhes
    )

def registrar_exclusao(usuario_id: Optional[int], entidade_tipo: str, entidade_id: int, detalhes: Optional[Dict] = None):
    return registrar_auditoria(
        usuario_id=usuario_id,
        acao='excluir',
        entidade_tipo=entidade_tipo,
        entidade_id=entidade_id,
        detalhes=detalhes
    )

def registrar_auditoria_oc(oc_id, usuario_id, acao, status_anterior=None, status_novo=None, observacao=None, ip=None, gps=None, dispositivo=None):
    """Registra auditoria de ações em Ordem de Compra
    
    Args:
        oc_id: ID da ordem de compra
        usuario_id: ID do usuário que realizou a ação
        acao: Tipo de ação (criacao, aprovacao, rejeicao, etc)
        status_anterior: Status anterior da OC
        status_novo: Novo status da OC
        observacao: Observações sobre a ação
        ip: Endereço IP do usuário
        gps: Coordenadas GPS (latitude, longitude)
        dispositivo: Informações do dispositivo/user agent
    """
    auditoria = AuditoriaOC(
        oc_id=oc_id,
        usuario_id=usuario_id,
        acao=acao,
        status_anterior=status_anterior,
        status_novo=status_novo,
        observacao=observacao,
        ip=ip,
        gps=gps,
        dispositivo=dispositivo
    )
    db.session.add(auditoria)
