"""
Utilitário de geocoding reverso (GPS → endereço)
Usa Nominatim (OpenStreetMap) como fonte principal com fallback para ViaCEP
"""

import requests
from typing import Dict, Optional
import time

def reverse_geocode(lat: float, lng: float, max_retries: int = 3) -> Dict[str, Optional[str]]:
    """
    Converte coordenadas GPS em endereço completo
    
    Args:
        lat: Latitude
        lng: Longitude
        max_retries: Número máximo de tentativas em caso de erro
    
    Returns:
        Dict com chaves: rua, numero, cep, bairro, cidade, estado, pais, endereco_completo, raw
    """
    
    # Tentar Nominatim (OpenStreetMap) primeiro
    for tentativa in range(max_retries):
        try:
            # Nominatim exige User-Agent customizado
            headers = {
                'User-Agent': 'MRX-System/1.0 (Sistema de Gestão de Compras)'
            }
            
            url = f'https://nominatim.openstreetmap.org/reverse'
            params = {
                'lat': lat,
                'lon': lng,
                'format': 'json',
                'addressdetails': 1,
                'zoom': 18
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 429:  # Rate limit
                if tentativa < max_retries - 1:
                    time.sleep(2 ** tentativa)  # Backoff exponencial
                    continue
                else:
                    return _erro_rate_limit()
            
            if response.status_code == 200:
                data = response.json()
                
                if 'error' in data:
                    return _erro_nao_encontrado()
                
                address = data.get('address', {})
                
                # Extrair componentes do endereço
                rua = (address.get('road') or 
                       address.get('pedestrian') or 
                       address.get('path') or 
                       address.get('street') or '')
                
                numero = (address.get('house_number') or '')
                
                bairro = (address.get('suburb') or 
                          address.get('neighbourhood') or 
                          address.get('quarter') or '')
                
                cidade = (address.get('city') or 
                          address.get('town') or 
                          address.get('village') or 
                          address.get('municipality') or '')
                
                estado = address.get('state', '')
                pais = address.get('country', '')
                cep = address.get('postcode', '')
                
                # Se não encontrou CEP, tentar buscar via ViaCEP (Brasil apenas)
                if not cep and pais.lower() in ['brasil', 'brazil'] and rua and cidade:
                    cep_viacep = _buscar_cep_viacep(rua, cidade, estado)
                    if cep_viacep:
                        cep = cep_viacep
                
                # Montar endereço completo
                partes_endereco = []
                if rua:
                    partes_endereco.append(rua)
                if numero:
                    partes_endereco.append(numero)
                if bairro:
                    partes_endereco.append(bairro)
                if cidade:
                    partes_endereco.append(cidade)
                if estado:
                    partes_endereco.append(estado)
                if cep:
                    partes_endereco.append(f'CEP: {cep}')
                
                endereco_completo = ', '.join(partes_endereco)
                
                return {
                    'rua': rua,
                    'numero': numero,
                    'cep': cep,
                    'bairro': bairro,
                    'cidade': cidade,
                    'estado': estado,
                    'pais': pais,
                    'endereco_completo': endereco_completo,
                    'raw': data,
                    'sucesso': True
                }
        
        except requests.Timeout:
            if tentativa < max_retries - 1:
                time.sleep(1)
                continue
            else:
                return _erro_timeout()
        
        except requests.RequestException as e:
            if tentativa < max_retries - 1:
                time.sleep(1)
                continue
            else:
                return _erro_conexao(str(e))
        
        except Exception as e:
            return _erro_generico(str(e))
    
    return _erro_generico('Tentativas de geocoding esgotadas')


def _buscar_cep_viacep(rua: str, cidade: str, estado: str) -> Optional[str]:
    """
    Busca CEP usando ViaCEP (fallback para endereços brasileiros)
    """
    try:
        # ViaCEP formato: GET https://viacep.com.br/ws/{UF}/{Cidade}/{Logradouro}/json/
        if not estado or len(estado) != 2:
            return None
        
        # Limpar e formatar
        rua_limpa = rua.replace(' ', '%20')
        cidade_limpa = cidade.replace(' ', '%20')
        
        url = f'https://viacep.com.br/ws/{estado}/{cidade_limpa}/{rua_limpa}/json/'
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            
            # ViaCEP retorna lista de endereços
            if isinstance(data, list) and len(data) > 0:
                # Pegar o primeiro resultado
                primeiro = data[0]
                return primeiro.get('cep', '').replace('-', '')
        
        return None
    
    except Exception:
        return None


def _erro_rate_limit() -> Dict:
    return {
        'rua': '',
        'numero': '',
        'cep': '',
        'bairro': '',
        'cidade': '',
        'estado': '',
        'pais': '',
        'endereco_completo': '',
        'raw': {},
        'sucesso': False,
        'erro': 'Rate limit atingido. Tente novamente em alguns segundos.'
    }


def _erro_nao_encontrado() -> Dict:
    return {
        'rua': '',
        'numero': '',
        'cep': '',
        'bairro': '',
        'cidade': '',
        'estado': '',
        'pais': '',
        'endereco_completo': '',
        'raw': {},
        'sucesso': False,
        'erro': 'Endereço não encontrado para estas coordenadas'
    }


def _erro_timeout() -> Dict:
    return {
        'rua': '',
        'numero': '',
        'cep': '',
        'bairro': '',
        'cidade': '',
        'estado': '',
        'pais': '',
        'endereco_completo': '',
        'raw': {},
        'sucesso': False,
        'erro': 'Timeout ao buscar endereço. Tente novamente.'
    }


def _erro_conexao(mensagem: str) -> Dict:
    return {
        'rua': '',
        'numero': '',
        'cep': '',
        'bairro': '',
        'cidade': '',
        'estado': '',
        'pais': '',
        'endereco_completo': '',
        'raw': {},
        'sucesso': False,
        'erro': f'Erro de conexão: {mensagem}'
    }


def _erro_generico(mensagem: str) -> Dict:
    return {
        'rua': '',
        'numero': '',
        'cep': '',
        'bairro': '',
        'cidade': '',
        'estado': '',
        'pais': '',
        'endereco_completo': '',
        'raw': {},
        'sucesso': False,
        'erro': f'Erro ao buscar endereço: {mensagem}'
    }
