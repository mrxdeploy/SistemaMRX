import os
import base64
import json
from datetime import datetime

from google import genai
from google.genai import types

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_MODEL = "gemini-2.5-flash"

client = None
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)

def get_scanner_prompt(prompt_rules=None):
    base_prompt = """Você é um especialista em reciclagem de placas eletrônicas (PCBs) e recuperação de metais preciosos.
Analise a imagem da placa eletrônica fornecida e classifique-a para fins de reciclagem de metais preciosos.

CRITÉRIOS DE CLASSIFICAÇÃO:
- LOW (Baixo valor): Placas simples, poucas camadas, poucos componentes, baixa densidade de conectores dourados (ex: fontes, impressoras, TVs antigas)
- MEDIUM (Médio valor): Placas com densidade moderada de componentes, alguns conectores dourados, chips médios (ex: HDs, roteadores, placas de som)
- HIGH (Alto valor): Placas com alta densidade de componentes, muitos conectores dourados, chips BGA, processadores, memórias (ex: motherboards, celulares, servidores)

TIPOS COMUNS DE PLACAS E SEUS VALORES:
- Motherboard de PC/Servidor (geralmente HIGH) - ricos em ouro nos conectores e slots
- Placa de celular/smartphone (geralmente HIGH) - alta densidade de componentes valiosos
- Placa de fonte de alimentação (geralmente LOW) - poucos metais preciosos
- Placa de telecom/roteador (geralmente MEDIUM a HIGH) - conectores banhados a ouro
- Placa de HD/SSD (geralmente MEDIUM) - alguns componentes valiosos
- Placa de impressora (geralmente LOW) - baixo teor de metais preciosos
- Placa de TV/monitor (geralmente LOW a MEDIUM) - varia conforme a idade

INDICADORES DE VALOR PARA METAIS PRECIOSOS:
- Fingers/conectores dourados: quanto mais, maior o valor
- Chips BGA (Ball Grid Array): alto teor de ouro
- Conectores PCI/PCIe: contêm ouro
- Processadores e CPUs: ouro nos pinos e internamente
- Memórias RAM: fingers dourados

ANÁLISE VISUAL OBRIGATÓRIA:
1. Identifique o tipo provável da placa
2. Conte aproximadamente a quantidade de CIs/chips grandes
3. Avalie se há muitos componentes SMD pequenos ou poucos componentes grandes
4. Procure por conectores ou dedos dourados visíveis (slots, contatos de borda, pinos banhados)

RESPONDA EXCLUSIVAMENTE EM JSON com este formato exato (sem markdown, sem código, apenas o JSON puro):
{
  "grade": "LOW | MEDIUM | HIGH",
  "type_guess": "ex: placa de celular, motherboard de PC, fonte, telecom etc.",
  "visual_analysis": "resumo detalhado do que foi visto na imagem: quantidade de componentes, tipos de chips, conectores, fingers dourados, etc.",
  "explanation": "por que essa placa foi classificada nessa grade, com base no que foi visto na imagem",
  "confidence": 0.0,
  "metal_value_comment": "comentário curto sobre o potencial de metais preciosos baseado na análise visual",
  "notes": "observações adicionais opcionais"
}"""
    
    if prompt_rules:
        base_prompt += f"\n\nREGRAS ADICIONAIS:\n{prompt_rules}"
    
    return base_prompt

def analyze_pcb_image(image_data, weight_kg=None, prompt_rules=None, description=None):
    if not GEMINI_API_KEY:
        return None, 'Chave API do Gemini não configurada. Configure GEMINI_API_KEY nas variáveis de ambiente.'
    
    if not client:
        return None, 'Cliente Gemini não inicializado. Verifique a chave API.'
    
    if not image_data:
        return None, 'Imagem não fornecida. Por favor, envie uma imagem da placa para análise.'
    
    try:
        if isinstance(image_data, bytes):
            image_bytes = image_data
        elif isinstance(image_data, str):
            if image_data.startswith('data:image'):
                base64_data = image_data.split(',')[1] if ',' in image_data else image_data
                image_bytes = base64.b64decode(base64_data)
            else:
                image_bytes = base64.b64decode(image_data)
        else:
            return None, 'Formato de imagem inválido.'
        
        system_prompt = get_scanner_prompt(prompt_rules)
        
        user_message = "Analise esta placa eletrônica para reciclagem de metais preciosos."
        if weight_kg:
            user_message += f" O peso estimado da placa é {weight_kg} kg."
        if description:
            user_message += f" Informação adicional do usuário: {description}"
        user_message += "\n\nResponda SOMENTE com o JSON no formato especificado, sem markdown ou texto adicional."
        
        mime_type = "image/jpeg"
        if len(image_bytes) > 4:
            if image_bytes[:4] == b'\x89PNG':
                mime_type = "image/png"
            elif image_bytes[:4] == b'GIF8':
                mime_type = "image/gif"
            elif image_bytes[:2] == b'\xff\xd8':
                mime_type = "image/jpeg"
            elif image_bytes[:4] == b'RIFF':
                mime_type = "image/webp"
        
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[
                types.Part.from_bytes(
                    data=image_bytes,
                    mime_type=mime_type,
                ),
                f"{system_prompt}\n\n{user_message}",
            ],
        )
        
        if response and response.text:
            content = response.text
            
            try:
                if '```json' in content:
                    content = content.split('```json')[1].split('```')[0]
                elif '```' in content:
                    parts = content.split('```')
                    for part in parts:
                        stripped = part.strip()
                        if stripped.startswith('{') and stripped.endswith('}'):
                            content = stripped
                            break
                
                content = content.strip()
                if content.startswith('{'):
                    end_idx = content.rfind('}') + 1
                    content = content[:end_idx]
                
                result = json.loads(content)
                
                if 'grade' not in result:
                    result['grade'] = 'MEDIUM'
                if 'type_guess' not in result:
                    result['type_guess'] = 'Placa eletrônica não identificada'
                if 'visual_analysis' not in result:
                    result['visual_analysis'] = 'Análise visual não disponível'
                if 'explanation' not in result:
                    result['explanation'] = 'Análise baseada em características visuais'
                if 'confidence' not in result:
                    result['confidence'] = 0.5
                if 'metal_value_comment' not in result:
                    result['metal_value_comment'] = 'Avaliação baseada na análise visual'
                if 'notes' not in result:
                    result['notes'] = ''
                
                result['components_detected'] = result.get('components_detected', [])
                result['precious_metals_likelihood'] = result.get('precious_metals_likelihood', {
                    'gold': 'MEDIUM',
                    'silver': 'MEDIUM',
                    'palladium': 'LOW'
                })
                
                result['raw_response'] = response.text
                result['model'] = GEMINI_MODEL
                result['timestamp'] = datetime.now().isoformat()
                
                return result, None
                
            except json.JSONDecodeError as e:
                return {
                    'grade': 'MEDIUM',
                    'type_guess': 'Não foi possível identificar',
                    'visual_analysis': content[:500] if content else 'Erro no processamento',
                    'explanation': 'Erro ao processar resposta da IA',
                    'confidence': 0.3,
                    'metal_value_comment': 'Análise inconclusiva',
                    'notes': f'Erro de parse JSON: {str(e)}',
                    'raw_response': content,
                    'parse_error': True,
                    'timestamp': datetime.now().isoformat()
                }, None
        else:
            return None, 'Resposta vazia do Gemini. Tente novamente.'
            
    except Exception as e:
        error_msg = str(e)
        if 'API key' in error_msg.lower() or 'authentication' in error_msg.lower():
            return None, f'Erro de autenticação com Gemini: {error_msg}'
        if 'quota' in error_msg.lower() or 'limit' in error_msg.lower():
            return None, f'Limite de requisições excedido: {error_msg}'
        return None, f'Erro ao analisar imagem com Gemini: {error_msg}'

def calculate_price_suggestion(grade, weight_kg, config):
    if not config or not weight_kg:
        return None
    
    try:
        weight = float(weight_kg)
        
        if grade == 'LOW':
            min_price = float(config.get('price_low_min', 0))
            max_price = float(config.get('price_low_max', 0))
        elif grade == 'MEDIUM':
            min_price = float(config.get('price_medium_min', 0))
            max_price = float(config.get('price_medium_max', 0))
        elif grade == 'HIGH':
            min_price = float(config.get('price_high_min', 0))
            max_price = float(config.get('price_high_max', 0))
        else:
            return None
        
        if min_price == 0 and max_price == 0:
            return None
        
        avg_price = (min_price + max_price) / 2
        
        return {
            'price_per_kg_min': min_price,
            'price_per_kg_max': max_price,
            'price_per_kg_avg': avg_price,
            'total_min': round(min_price * weight, 2),
            'total_max': round(max_price * weight, 2),
            'total_avg': round(avg_price * weight, 2),
            'weight_kg': weight,
            'grade': grade
        }
    except Exception as e:
        print(f'Erro ao calcular preço: {e}')
        return None
