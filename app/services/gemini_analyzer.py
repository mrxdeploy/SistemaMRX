"""
Serviço centralizado de análise de imagens usando Gemini AI
Reutilizável para placas eletrônicas e itens de solicitação
"""

import os
from typing import List, Dict, Literal
from google import genai
from google.genai import types
import re


def analyze_images(
    images: List[bytes],
    use_case: Literal['placa', 'solicitacao'] = 'placa',
    model: str = "gemini-2.0-flash-exp"
) -> List[Dict[str, str]]:
    """
    Analisa múltiplas imagens usando Gemini AI
    
    Args:
        images: Lista de imagens em bytes
        use_case: Tipo de análise ('placa' ou 'solicitacao')
        model: Modelo do Gemini a usar
    
    Returns:
        Lista de dicionários com classificacao, justificativa e raw_text
    """
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return [{
            'classificacao': 'medio',
            'justificativa': 'Chave da API do Gemini não configurada. Configure GEMINI_API_KEY.',
            'raw_text': '',
            'erro': 'API key não configurada'
        }] * len(images)
    
    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        return [{
            'classificacao': 'medio',
            'justificativa': f'Erro ao conectar com Gemini: {str(e)}',
            'raw_text': '',
            'erro': str(e)
        }] * len(images)
    
    prompt = _get_prompt(use_case)
    resultados = []
    
    for imagem_bytes in images:
        try:
            response = client.models.generate_content(
                model=model,
                contents=[
                    types.Part.from_bytes(
                        data=imagem_bytes,
                        mime_type="image/jpeg",
                    ),
                    prompt
                ],
            )
            
            if not response.text:
                resultados.append({
                    'classificacao': 'mg1',
                    'justificativa': 'Gemini não retornou resposta para esta imagem',
                    'raw_text': '',
                    'erro': 'Resposta vazia'
                })
                continue
            
            resultado_texto = response.text.strip()
            print(f"[GEMINI] Resposta completa: {resultado_texto}")
            
            # Parsear a resposta
            parsed = _parse_gemini_response(resultado_texto)
            resultados.append(parsed)
        
        except Exception as e:
            resultados.append({
                'classificacao': 'mg1',
                'justificativa': f'Erro ao analisar imagem: {str(e)}',
                'raw_text': '',
                'erro': str(e)
            })
    
    return resultados


def _get_prompt(use_case: str) -> str:
    """Retorna o prompt apropriado para o tipo de análise"""
    
    if use_case == 'solicitacao':
        return """Você é um especialista em classificação de lotes de placas eletrônicas (PCBs). 
Analise esta imagem de lote de placas eletrônicas e classifique como HIGH, MG1, MG2 ou LOW.

REGRAS DE CLASSIFICAÇÃO IMPORTANTES:
- HIGH (Antigo Leve): Poucas placas eletrônicas visíveis (1-3 unidades), ou placas com muita área verde visível 
  (poucas peças/componentes soldados). Baixa densidade de componentes.
- MG1 (Antigo Médio): Quantidade moderada de placas (4-8 unidades), ou placas com densidade média de componentes.
  Áreas verdes ainda parcialmente visíveis.
- MG2 (Antigo Pesado): Muitas placas eletrônicas (9+ unidades), ou placas completamente densas com muitos 
  componentes, chips, conectores. Pouco ou nenhum verde visível devido à alta quantidade de peças soldadas.
- LOW: Sucata de muito baixo valor, placas quebradas, periféricos baratos ou resíduos.

A regra é simples: 
- MENOS PLACAS ou MAIS VERDE VISÍVEL = HIGH
- QUANTIDADE MÉDIA de placas ou componentes = MG1
- MUITAS PLACAS ou COMPONENTES DENSOS (pouco verde) = MG2
- RESÍDUOS ou BAIXO VALOR = LOW

Responda APENAS com:
1. A classificação (HIGH / MG1 / MG2 / LOW)
2. Uma breve justificativa (1 frase curta)

Formato EXATO da resposta:
Classificação: [HIGH/MG1/MG2/LOW] — [justificativa em 1 frase]

Não adicione informações extras, apenas a classificação e justificativa."""
    
    else:  # 'placa' (análise individual)
        return """Você é um especialista em classificação de placas eletrônicas (PCBs). 
Analise esta imagem de placa eletrônica e classifique como HIGH, MG1, MG2 ou LOW.

REGRAS DE CLASSIFICAÇÃO IMPORTANTES:
- HIGH (Verde): Alta presença de verde visível (áreas grandes da placa sem muitos componentes soldados). 
  Quanto mais verde aparecer na placa, mais "HIGH" ela é. Alto valor.
- MG1 (Amarelo): Quantidade moderada de componentes, com áreas verdes ainda visíveis.
- MG2 (Laranja): Muitos componentes, conectores, chips, resistores, capacitores e grande densidade visual.
  Pouco verde visível devido à alta quantidade de componentes soldados.
- LOW (Vermelho): Placas pobres, quebradas, periféricos ou sucata de baixo valor.

A regra é simples: quanto MAIS VERDE VISÍVEL = mais HIGH a placa.
Quanto MENOS VERDE VISÍVEL (mais componentes) = mais MG2 a placa.

Responda APENAS com:
1. A classificação (HIGH / MG1 / MG2 / LOW)
2. Uma breve justificativa (1 frase curta)

Formato EXATO da resposta:
Classificação: [HIGH/MG1/MG2/LOW] — [justificativa em 1 frase]

Não adicione informações extras, apenas a classificação e justificativa."""


def _parse_gemini_response(texto: str) -> Dict[str, str]:
    """
    Parseia a resposta do Gemini para extrair classificação e justificativa
    """
    
    # Detectar classificação
    classificacao = "mg1"
    texto_upper = texto.upper()
    
    if "HIGH" in texto_upper or "LEVE" in texto_upper:
        classificacao = "high"
    elif "MG2" in texto_upper or "PESAD" in texto_upper:
        classificacao = "mg2"
    elif "MG1" in texto_upper or "MEDIO" in texto_upper or "MÉDI" in texto_upper:
        classificacao = "mg1"
    elif "LOW" in texto_upper:
        classificacao = "low"
    
    # Extrair justificativa
    justificativa = ""
    
    # Tentar padrão: "Classificação: X — justificativa"
    match = re.search(
        r'Classificação:\s*(HIGH|LEVE|MG1|MÉDIA|MEDIA|MEDIO|MÉDIO|MG2|PESADA|PESADO|LOW)\s*[—\-–]\s*(.+)',
        texto,
        re.IGNORECASE
    )
    
    if match:
        justificativa = match.group(2).strip()
    else:
        # Fallback: pegar primeira linha não vazia após "Classificação:"
        linhas = texto.split('\n')
        for i, linha in enumerate(linhas):
            if 'classificação' in linha.lower() or 'classificacao' in linha.lower():
                # Pegar próxima linha ou resto da linha atual
                partes = linha.split('—')
                if len(partes) > 1:
                    justificativa = partes[1].strip()
                elif i + 1 < len(linhas):
                    justificativa = linhas[i + 1].strip()
                break
        
        # Se ainda não achou, pegar a segunda linha (geralmente é a justificativa)
        if not justificativa and len(linhas) >= 2:
            justificativa = linhas[1].strip()
    
    # Limpar justificativa
    justificativa = justificativa.replace('**', '').strip()
    
    # Se justificativa está vazia, usar texto completo (limitado)
    if not justificativa:
        # Remover primeira linha (classificação) e pegar o resto
        linhas_limpas = [l.strip() for l in texto.split('\n') if l.strip()]
        if len(linhas_limpas) > 1:
            justificativa = ' '.join(linhas_limpas[1:])[:150]
        else:
            justificativa = texto[:150]
    
    return {
        'classificacao': classificacao,
        'justificativa': justificativa,
        'raw_text': texto,
        'sucesso': True
    }
