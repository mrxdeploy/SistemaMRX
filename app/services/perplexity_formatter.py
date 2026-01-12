import os
import requests
from typing import Optional

PERPLEXITY_API_KEY = os.getenv('PERPLEXITY_API_KEY')
PERPLEXITY_API_URL = 'https://api.perplexity.ai/chat/completions'
PERPLEXITY_MODEL = 'llama-3.1-sonar-small-128k-online'


def build_explanation_with_perplexity(grade: str, components_count: int, density_score: float) -> Optional[str]:
    """
    Usa a API do Perplexity para gerar um parágrafo curto explicando o resultado
    da análise de PCB. Não recebe imagem, apenas dados numéricos.
    
    Retorna None se a API não estiver configurada ou falhar.
    """
    if not PERPLEXITY_API_KEY:
        return None
    
    system_prompt = """Você é um especialista em reciclagem de placas eletrônicas e recuperação de metais preciosos.
Você receberá dados numéricos sobre a densidade de componentes de uma placa eletrônica analisada.
Sua tarefa é explicar para um usuário leigo, em português brasileiro simples e direto, por que essa placa foi classificada como LOW, MEDIUM ou HIGH em termos de valor para reciclagem de metais preciosos (principalmente ouro, prata e paládio).
Seja conciso (máximo 3-4 frases) e foque nos aspectos práticos da classificação."""

    grade_context = {
        'LOW': 'baixo valor - poucas chances de metais preciosos significativos',
        'MEDIUM': 'valor intermediário - quantidade moderada de componentes valiosos',
        'HIGH': 'alto valor - grande probabilidade de ouro em conectores e chips'
    }
    
    user_prompt = f"""Dados da análise da placa:
- Classificação: {grade} ({grade_context.get(grade, '')})
- Componentes detectados: {components_count}
- Score de densidade: {density_score:.2f} (0 a 1)

Explique em poucas frases, em português simples e acessível, por que essa placa foi classificada assim e qual seu potencial para reciclagem de metais preciosos como ouro."""

    try:
        headers = {
            'Authorization': f'Bearer {PERPLEXITY_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': PERPLEXITY_MODEL,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt}
            ],
            'max_tokens': 300,
            'temperature': 0.3,
            'stream': False
        }
        
        response = requests.post(
            PERPLEXITY_API_URL,
            headers=headers,
            json=payload,
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            if 'choices' in data and len(data['choices']) > 0:
                message = data['choices'][0].get('message', {})
                content = message.get('content', '')
                if content:
                    return content.strip()
        
        print(f'Perplexity API error: {response.status_code} - {response.text}')
        return None
        
    except requests.exceptions.Timeout:
        print('Perplexity API timeout')
        return None
    except requests.exceptions.RequestException as e:
        print(f'Perplexity API request error: {e}')
        return None
    except Exception as e:
        print(f'Perplexity formatter error: {e}')
        return None


def is_perplexity_configured() -> bool:
    """Verifica se a API do Perplexity está configurada."""
    return bool(PERPLEXITY_API_KEY)
