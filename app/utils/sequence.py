import uuid
import logging
from datetime import datetime
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from app.models import db, Lote

logger = logging.getLogger(__name__)

def obter_max_sequencial_ano(ano):
    """
    Busca o maior número de lote numérico do ano atual, ignorando formatos UUID/Hex.
    Garante que não peguemos lotes de UUID que "ordenam maior" no regex (ex: 2026-FFE81).
    """
    ultimo_lote_numerico = db.session.query(func.max(Lote.numero_lote)).filter(
        Lote.numero_lote.op('~')(f'^{ano}-[0-9]+$')
    ).scalar()
    
    if ultimo_lote_numerico:
        try:
            return int(ultimo_lote_numerico.split('-')[1])
        except (IndexError, ValueError):
            pass
            
    # Fallback conservador
    return Lote.query.filter(Lote.numero_lote.like(f"{ano}-%")).count()

def gerar_numero_lote_ano_com_lock(modelo_instancia, base_seq=None, limite_tentativas=10):
    """
    Insere a instância no banco com lote sequencial ({ano}-{seq}).
    Usa savepoints (begin_nested) para tentar novamente se houver conflito de chave única.
    
    :param modelo_instancia: Instância de Lote pronta
    :param base_seq: Sequência inicial (otimização para múltiplos lotes no mesmo request)
    :param limite_tentativas: Tentativas antes de lançar exceção
    :return: A sequência que deu certo.
    """
    ano = datetime.now().year
    
    if base_seq is None:
        base_seq = obter_max_sequencial_ano(ano)
        
    current_seq = base_seq
    
    for tentativa in range(1, limite_tentativas + 1):
        current_seq += 1
        numero_proposto = f"{ano}-{str(current_seq).zfill(5)}"
        modelo_instancia.numero_lote = numero_proposto
        
        try:
            with db.session.begin_nested():
                db.session.add(modelo_instancia)
                db.session.flush()
            
            logger.info(f"Lote sequencial {numero_proposto} gerado na tentativa {tentativa}")
            return current_seq 
            
        except IntegrityError:
            logger.warning(f"Conflito de lote {numero_proposto} na tentativa {tentativa}. Tentando próximo...")
            continue
            
    raise Exception(f"Não foi possível gerar um número de lote único após {limite_tentativas} tentativas.")

def gerar_codigo_compra_com_lock(modelo_instancia, limite_tentativas=10):
    """
    Insere o lote de compra no formato AAAAMMDD-SEQ.
    """
    hoje = datetime.now()
    data_str = hoje.strftime('%Y%m%d')
    
    ultimo_lote = db.session.query(Lote).filter(
        Lote.numero_lote.like(f'{data_str}-%')
    ).order_by(Lote.numero_lote.desc()).first()
    
    if ultimo_lote:
        try:
            current_seq = int(ultimo_lote.numero_lote.split('-')[1])
        except (IndexError, ValueError):
            current_seq = 0
    else:
        current_seq = 0
        
    for tentativa in range(1, limite_tentativas + 1):
        current_seq += 1
        numero_proposto = f"{data_str}-{current_seq:03d}"
        modelo_instancia.numero_lote = numero_proposto
        
        try:
            with db.session.begin_nested():
                db.session.add(modelo_instancia)
                db.session.flush()
            return numero_proposto
        except IntegrityError:
            continue
            
    raise Exception(f"Não foi possível gerar um código de compra único após {limite_tentativas} tentativas.")

def gerar_numero_lote_uuid_com_lock(modelo_instancia, limite_tentativas=5):
    """
    Insere um lote com sufixo UUID seguro contra colisões raras.
    """
    ano = datetime.now().year
    
    for tentativa in range(limite_tentativas):
        numero_proposto = f"{ano}-{str(uuid.uuid4().hex[:5]).upper()}"
        modelo_instancia.numero_lote = numero_proposto
        
        try:
            with db.session.begin_nested():
                db.session.add(modelo_instancia)
                db.session.flush()
            return numero_proposto
        except IntegrityError:
            continue
            
    raise Exception("Falha ao gerar lote UUID único.")
