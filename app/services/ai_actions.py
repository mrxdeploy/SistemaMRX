from app.models import (
    db, Usuario, Fornecedor, Solicitacao, Lote, TipoLote,
    Notificacao, EntradaEstoque, OrdemCompra, ItemSolicitacao
)
from datetime import datetime
import json
import re

SYSTEM_ACTIONS = {
    'criar_fornecedor': {
        'descricao': 'Criar um novo fornecedor no sistema',
        'parametros': ['nome', 'cnpj_ou_cpf', 'telefone', 'email', 'cidade', 'estado'],
        'exemplo': 'Criar fornecedor João Silva, CPF 123.456.789-00, telefone 11999999999'
    },
    'criar_notificacao': {
        'descricao': 'Enviar notificação para um usuário',
        'parametros': ['usuario_id_ou_tipo', 'titulo', 'mensagem'],
        'exemplo': 'Notificar admin sobre nova solicitação pendente'
    },
    'listar_fornecedores': {
        'descricao': 'Listar fornecedores ativos',
        'parametros': ['limite'],
        'exemplo': 'Listar os 10 últimos fornecedores'
    },
    'listar_solicitacoes': {
        'descricao': 'Listar solicitações pendentes ou por status',
        'parametros': ['status', 'limite'],
        'exemplo': 'Mostrar solicitações pendentes'
    },
    'resumo_sistema': {
        'descricao': 'Gerar resumo completo do sistema',
        'parametros': [],
        'exemplo': 'Me dê um resumo do sistema'
    },
    'dica_operacional': {
        'descricao': 'Fornecer dica baseada nos dados atuais',
        'parametros': ['area'],
        'exemplo': 'Me dê dicas para melhorar as operações'
    }
}

def detectar_intencao_acao(mensagem):
    mensagem_lower = mensagem.lower()
    
    if any(p in mensagem_lower for p in ['criar fornecedor', 'cadastrar fornecedor', 'novo fornecedor', 'adicionar fornecedor']):
        return 'criar_fornecedor'
    
    if any(p in mensagem_lower for p in ['notificar', 'enviar notificacao', 'avisar', 'alertar']):
        return 'criar_notificacao'
    
    if any(p in mensagem_lower for p in ['listar fornecedor', 'mostrar fornecedor', 'quais fornecedor', 'ver fornecedor']):
        return 'listar_fornecedores'
    
    if any(p in mensagem_lower for p in ['listar solicitac', 'mostrar solicitac', 'pedidos pendente', 'solicitacoes pendente']):
        return 'listar_solicitacoes'
    
    if any(p in mensagem_lower for p in ['resumo', 'status geral', 'visao geral', 'como esta o sistema']):
        return 'resumo_sistema'
    
    if any(p in mensagem_lower for p in ['dica', 'sugestao', 'melhorar', 'otimizar', 'recomendacao']):
        return 'dica_operacional'
    
    return None

def executar_acao(acao, mensagem, usuario_id):
    try:
        if acao == 'criar_fornecedor':
            return criar_fornecedor_por_texto(mensagem, usuario_id)
        elif acao == 'criar_notificacao':
            return criar_notificacao_por_texto(mensagem, usuario_id)
        elif acao == 'listar_fornecedores':
            return listar_fornecedores_acao()
        elif acao == 'listar_solicitacoes':
            return listar_solicitacoes_acao(mensagem)
        elif acao == 'resumo_sistema':
            return gerar_resumo_sistema()
        elif acao == 'dica_operacional':
            return gerar_dicas_operacionais()
        else:
            return None, 'Ação não reconhecida'
    except Exception as e:
        return None, f'Erro ao executar ação: {str(e)}'

def criar_fornecedor_por_texto(mensagem, usuario_id):
    nome_match = re.search(r'(?:fornecedor|nome)[:\s]+([A-Za-zÀ-ú\s]+?)(?:,|cpf|cnpj|telefone|email|$)', mensagem, re.IGNORECASE)
    cpf_match = re.search(r'cpf[:\s]*(\d{3}\.?\d{3}\.?\d{3}-?\d{2})', mensagem, re.IGNORECASE)
    cnpj_match = re.search(r'cnpj[:\s]*(\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2})', mensagem, re.IGNORECASE)
    telefone_match = re.search(r'(?:telefone|tel|fone)[:\s]*(\(?\d{2}\)?\s?\d{4,5}-?\d{4})', mensagem, re.IGNORECASE)
    email_match = re.search(r'email[:\s]*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', mensagem, re.IGNORECASE)
    cidade_match = re.search(r'cidade[:\s]+([A-Za-zÀ-ú\s]+?)(?:,|estado|$)', mensagem, re.IGNORECASE)
    
    if not nome_match:
        return None, 'Não consegui identificar o nome do fornecedor. Por favor, forneça: "Criar fornecedor [NOME], CPF/CNPJ [NUMERO]"'
    
    nome = nome_match.group(1).strip()
    
    fornecedor = Fornecedor(
        nome=nome,
        cnpj=cnpj_match.group(1) if cnpj_match else None,
        cpf=cpf_match.group(1) if cpf_match else None,
        tipo_documento='cnpj' if cnpj_match else 'cpf' if cpf_match else None,
        telefone=telefone_match.group(1) if telefone_match else None,
        email=email_match.group(1) if email_match else None,
        cidade=cidade_match.group(1).strip() if cidade_match else None,
        criado_por_id=usuario_id
    )
    
    db.session.add(fornecedor)
    db.session.commit()
    
    resultado = f"""Fornecedor criado com sucesso!

**Dados cadastrados:**
- ID: {fornecedor.id}
- Nome: {fornecedor.nome}
- Documento: {fornecedor.cnpj or fornecedor.cpf or 'Não informado'}
- Telefone: {fornecedor.telefone or 'Não informado'}
- Email: {fornecedor.email or 'Não informado'}
- Cidade: {fornecedor.cidade or 'Não informada'}

O fornecedor já está disponível no sistema para receber solicitações."""
    
    return {'fornecedor_id': fornecedor.id, 'dados': fornecedor.to_dict()}, resultado

def criar_notificacao_por_texto(mensagem, usuario_id):
    titulo_match = re.search(r'(?:titulo|assunto)[:\s]+([^,\.]+)', mensagem, re.IGNORECASE)
    msg_match = re.search(r'(?:mensagem|texto)[:\s]+(.+?)(?:$|para)', mensagem, re.IGNORECASE)
    
    admin_destinatario = 'admin' in mensagem.lower() or 'administrador' in mensagem.lower()
    todos_destinatario = 'todos' in mensagem.lower()
    
    titulo = titulo_match.group(1).strip() if titulo_match else 'Notificação do Assistente'
    conteudo = msg_match.group(1).strip() if msg_match else mensagem[:200]
    
    destinatarios = []
    
    if admin_destinatario:
        admins = Usuario.query.filter_by(tipo='admin', ativo=True).all()
        destinatarios = [u.id for u in admins]
    elif todos_destinatario:
        usuarios = Usuario.query.filter_by(ativo=True).limit(50).all()
        destinatarios = [u.id for u in usuarios]
    else:
        destinatarios = [usuario_id]
    
    count = 0
    for dest_id in destinatarios:
        notif = Notificacao(
            usuario_id=dest_id,
            titulo=titulo,
            mensagem=conteudo,
            tipo='assistente'
        )
        db.session.add(notif)
        count += 1
    
    db.session.commit()
    
    resultado = f"""Notificação enviada com sucesso!

**Detalhes:**
- Título: {titulo}
- Destinatários: {count} usuário(s)
- Mensagem: {conteudo[:100]}{'...' if len(conteudo) > 100 else ''}"""
    
    return {'notificacoes_enviadas': count}, resultado

def listar_fornecedores_acao(limite=10):
    fornecedores = Fornecedor.query.filter_by(ativo=True).order_by(
        Fornecedor.data_cadastro.desc()
    ).limit(limite).all()
    
    if not fornecedores:
        return {'total': 0}, 'Não há fornecedores cadastrados no sistema.'
    
    lista = []
    for f in fornecedores:
        lista.append(f"- **{f.nome}** (ID: {f.id}) - {f.cidade or 'Cidade não informada'}")
    
    resultado = f"""**Fornecedores Ativos ({len(fornecedores)} mais recentes):**

{chr(10).join(lista)}

Total de fornecedores ativos: {Fornecedor.query.filter_by(ativo=True).count()}"""
    
    return {'fornecedores': [f.to_dict() for f in fornecedores]}, resultado

def listar_solicitacoes_acao(mensagem):
    status = 'pendente'
    if 'aprovad' in mensagem.lower():
        status = 'aprovado'
    elif 'rejeitad' in mensagem.lower() or 'recusad' in mensagem.lower():
        status = 'rejeitado'
    elif 'todas' in mensagem.lower():
        status = None
    
    query = Solicitacao.query
    if status:
        query = query.filter_by(status=status)
    
    solicitacoes = query.order_by(Solicitacao.data_solicitacao.desc()).limit(10).all()
    
    if not solicitacoes:
        return {'total': 0}, f'Não há solicitações {status or "no sistema"}.'
    
    lista = []
    for s in solicitacoes:
        fornecedor_nome = s.fornecedor.nome if s.fornecedor else 'Não informado'
        lista.append(f"- **#{s.id}** - {fornecedor_nome} - Status: {s.status.upper()}")
    
    resultado = f"""**Solicitações {status.upper() if status else 'TODAS'} ({len(solicitacoes)} mais recentes):**

{chr(10).join(lista)}

Total com status '{status or 'todos'}': {query.count()}"""
    
    return {'solicitacoes': [s.to_dict() for s in solicitacoes]}, resultado

def gerar_resumo_sistema():
    total_fornecedores = Fornecedor.query.filter_by(ativo=True).count()
    total_solicitacoes = Solicitacao.query.count()
    solicitacoes_pendentes = Solicitacao.query.filter_by(status='pendente').count()
    solicitacoes_aprovadas = Solicitacao.query.filter_by(status='aprovado').count()
    total_lotes = Lote.query.count()
    total_entradas = EntradaEstoque.query.count()
    total_ocs = OrdemCompra.query.count()
    total_usuarios = Usuario.query.filter_by(ativo=True).count()
    
    try:
        ocs_abertas = OrdemCompra.query.filter(OrdemCompra.status.in_(['pendente', 'em_transito', 'em_analise'])).count()
    except:
        ocs_abertas = 0
    
    resultado = f"""**RESUMO GERAL DO SISTEMA MRX**

**Fornecedores:**
- Ativos: {total_fornecedores}

**Solicitações:**
- Total: {total_solicitacoes}
- Pendentes: {solicitacoes_pendentes}
- Aprovadas: {solicitacoes_aprovadas}

**Operações:**
- Lotes registrados: {total_lotes}
- Entradas no estoque: {total_entradas}
- Ordens de Compra: {total_ocs} ({ocs_abertas} em aberto)

**Usuários:**
- Ativos: {total_usuarios}

O sistema está funcionando normalmente. Use comandos como "listar fornecedores" ou "solicitações pendentes" para mais detalhes."""
    
    return {
        'fornecedores': total_fornecedores,
        'solicitacoes': total_solicitacoes,
        'pendentes': solicitacoes_pendentes,
        'lotes': total_lotes,
        'usuarios': total_usuarios
    }, resultado

def gerar_dicas_operacionais():
    solicitacoes_pendentes = Solicitacao.query.filter_by(status='pendente').count()
    fornecedores_sem_email = Fornecedor.query.filter_by(ativo=True, email=None).count()
    
    try:
        ocs_abertas = OrdemCompra.query.filter(OrdemCompra.status.in_(['pendente', 'em_analise'])).count()
    except:
        ocs_abertas = 0
    
    dicas = []
    
    if solicitacoes_pendentes > 5:
        dicas.append(f"Há **{solicitacoes_pendentes} solicitações pendentes**. Considere revisar e aprovar as mais antigas para manter o fluxo de compras ativo.")
    
    if fornecedores_sem_email > 0:
        dicas.append(f"Existem **{fornecedores_sem_email} fornecedores sem email** cadastrado. Complete os dados para melhorar a comunicação.")
    
    if ocs_abertas > 3:
        dicas.append(f"Há **{ocs_abertas} ordens de compra em aberto**. Verifique se há alguma pendência para finalização.")
    
    if not dicas:
        dicas.append("Parabéns! O sistema está em dia. Continue monitorando as operações regularmente.")
        dicas.append("Dica: Use o scanner de placas para classificar materiais rapidamente.")
        dicas.append("Dica: Acompanhe as cotações de metais para tomar melhores decisões de compra.")
    
    resultado = f"""**DICAS OPERACIONAIS**

{chr(10).join(['- ' + d for d in dicas])}

Posso ajudar com mais alguma análise?"""
    
    return {'dicas': dicas}, resultado

def obter_contexto_completo_ia():
    dados = gerar_resumo_sistema()[0]
    
    fornecedores_recentes = Fornecedor.query.filter_by(ativo=True).order_by(
        Fornecedor.data_cadastro.desc()
    ).limit(5).all()
    fornecedores_nomes = [f.nome for f in fornecedores_recentes]
    
    try:
        tipos_lote = TipoLote.query.filter_by(ativo=True).all()
        tipos_nomes = [t.nome for t in tipos_lote]
    except:
        tipos_nomes = ['Leve', 'Medio', 'Pesado']
    
    try:
        ocs_abertas = OrdemCompra.query.filter(OrdemCompra.status.in_(['pendente', 'em_analise', 'em_transito'])).count()
    except:
        ocs_abertas = 0
    
    contexto = f"""Voce e o assistente virtual do MRX Systems, um sistema ERP especializado em gestao de compra e reciclagem de materiais eletronicos para extracao de metais preciosos como ouro, prata, cobre e paladio.

PERSONALIDADE E COMUNICACAO:
- Responda de forma natural, amigavel e conversacional em portugues brasileiro
- Use linguagem simples e acessivel, evitando jargoes tecnicos desnecessarios
- Seja proativo em oferecer ajuda e sugestoes relevantes
- Demonstre conhecimento profundo sobre o mercado de reciclagem de eletronicos

DADOS EM TEMPO REAL DO SISTEMA (atualizados agora):
- Fornecedores ativos: {dados.get('fornecedores', 0)}
- Fornecedores recentes: {', '.join(fornecedores_nomes) if fornecedores_nomes else 'Nenhum cadastrado'}
- Total de solicitacoes: {dados.get('solicitacoes', 0)}
- Solicitacoes pendentes de analise: {dados.get('pendentes', 0)}
- Lotes classificados: {dados.get('lotes', 0)}
- Ordens de compra abertas: {ocs_abertas}
- Usuarios ativos: {dados.get('usuarios', 0)}
- Tipos de lote: {', '.join(tipos_nomes)}

MODULOS DO SISTEMA QUE VOCE CONHECE E PODE AJUDAR:
1. FORNECEDORES - Cadastro completo de fornecedores de sucata eletronica, com dados de contato, localizacao e historico
2. SOLICITACOES - Pedidos de compra de materiais enviados por fornecedores, que passam por aprovacao
3. LOTES - Classificacao de placas eletronicas em LEVE, MEDIO ou PESADO baseado na densidade de componentes
4. ESTOQUE - Controle de entradas e saidas de materiais
5. ORDENS DE COMPRA - Documentos formais de compra enviados aos fornecedores aprovados
6. CONFERENCIAS - Verificacao fisica dos materiais recebidos na unidade
7. LOGISTICA - Gestao de veiculos, motoristas e rotas de coleta
8. SCANNER DE PLACAS - Ferramenta com IA que analisa fotos de PCBs e classifica automaticamente
9. COTACOES DE METAIS - Precos atualizados de ouro, prata, cobre e outros metais
10. DASHBOARD - Metricas e indicadores do negocio

ACOES QUE VOCE PODE EXECUTAR AUTOMATICAMENTE:
- Criar novos fornecedores: "Criar fornecedor Joao Silva, telefone 11999999999"
- Enviar notificacoes: "Avisar o admin sobre solicitacao urgente"
- Listar dados: "Mostrar fornecedores" ou "Quais solicitacoes estao pendentes?"
- Gerar resumos: "Como esta o sistema?" ou "Me de um resumo"
- Dar dicas: "O que posso melhorar?" ou "Alguma sugestao?"

CONHECIMENTO ESPECIALIZADO:
- Placas de computador, servidor e video possuem maior concentracao de ouro
- Componentes como chips BGA, conectores dourados e processadores sao mais valiosos
- O preco do material depende da classificacao (LEVE, MEDIO, PESADO)
- Fornecedores recorrentes podem ter tabela de precos diferenciada

REGRAS DE RESPOSTA:
- Sempre responda em portugues brasileiro
- Seja conciso mas completo nas informacoes
- Ofereca ajuda adicional quando apropriado
- Se nao souber algo especifico do sistema, admita e sugira alternativas
- Use os dados reais do sistema para fundamentar suas respostas"""
    
    return contexto
