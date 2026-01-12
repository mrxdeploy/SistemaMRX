from flask import Blueprint, jsonify, request
import requests
import os
from datetime import datetime, timedelta
from functools import lru_cache
import time
import json
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

bp = Blueprint('metais', __name__, url_prefix='/api/metais')

METALS_CACHE = {
    'data': None,
    'timestamp': 0,
    'history': {}
}
CACHE_DURATION = 60

METAL_SYMBOLS = {
    'XAU': {
        'name': 'Ouro', 
        'icon': 'gold', 
        'color': '#FFD700',
        'fonte_ewaste': 'Placas de circuito, conectores, processadores, memoria RAM',
        'concentracao': 'Alta em placas-mae e processadores'
    },
    'XAG': {
        'name': 'Prata', 
        'icon': 'silver', 
        'color': '#C0C0C0',
        'fonte_ewaste': 'Contatos eletricos, soldas, teclas de membrana, paineis solares',
        'concentracao': 'Media em teclados e interruptores'
    },
    'XPT': {
        'name': 'Platina', 
        'icon': 'platinum', 
        'color': '#E5E4E2',
        'fonte_ewaste': 'Discos rigidos, termopares, sensores',
        'concentracao': 'Baixa, principalmente em HDDs antigos'
    },
    'XPD': {
        'name': 'Paladio', 
        'icon': 'palladium', 
        'color': '#CED0DD',
        'fonte_ewaste': 'Capacitores ceramicos, conectores, reles',
        'concentracao': 'Media em capacitores MLCC'
    },
    'XCU': {
        'name': 'Cobre', 
        'icon': 'copper', 
        'color': '#B87333',
        'fonte_ewaste': 'Fios, cabos, trilhas de PCB, motores, transformadores',
        'concentracao': 'Muito alta em todos os eletronicos'
    },
    'SN': {
        'name': 'Estanho', 
        'icon': 'tin', 
        'color': '#D3D3D3',
        'fonte_ewaste': 'Soldas, revestimentos de componentes',
        'concentracao': 'Alta em placas soldadas'
    },
    'NI': {
        'name': 'Niquel', 
        'icon': 'nickel', 
        'color': '#848482',
        'fonte_ewaste': 'Baterias NiMH/NiCd, revestimentos, acos inox',
        'concentracao': 'Alta em baterias recarregaveis'
    },
    'CO': {
        'name': 'Cobalto', 
        'icon': 'cobalt', 
        'color': '#0047AB',
        'fonte_ewaste': 'Baterias de litio-ion, imas permanentes',
        'concentracao': 'Alta em baterias de celulares e notebooks'
    },
    'AL': {
        'name': 'Aluminio', 
        'icon': 'aluminum', 
        'color': '#A9A9A9',
        'fonte_ewaste': 'Dissipadores de calor, carcacas, capacitores eletroliticos',
        'concentracao': 'Muito alta em estruturas e refrigeracao'
    },
    'TA': {
        'name': 'Tantalo', 
        'icon': 'tantalum', 
        'color': '#4A4A4A',
        'fonte_ewaste': 'Capacitores de tantalo, celulares, notebooks',
        'concentracao': 'Media em capacitores SMD'
    },
    'IN': {
        'name': 'Indio', 
        'icon': 'indium', 
        'color': '#4B0082',
        'fonte_ewaste': 'Telas LCD/LED, paineis touch, soldas especiais',
        'concentracao': 'Media em displays'
    },
    'GA': {
        'name': 'Galio', 
        'icon': 'gallium', 
        'color': '#6B8E23',
        'fonte_ewaste': 'LEDs, semicondutores GaAs, celulares',
        'concentracao': 'Baixa em chips especializados'
    }
}

def get_metals_live_api():
    try:
        response = requests.get('https://api.metals.live/v1/spot', timeout=10, verify=False)
        if response.status_code == 200:
            data = response.json()
            if not data or not isinstance(data, list):
                return None
            result = {}
            for item in data:
                if not item or not isinstance(item, dict):
                    continue
                symbol = item.get('symbol', '').upper()
                if symbol in METAL_SYMBOLS:
                    result[symbol] = {
                        'price_usd': float(item.get('price', 0)),
                        'name': METAL_SYMBOLS[symbol]['name'],
                        'source': 'metals.live'
                    }
            if result:
                return result
    except Exception as e:
        print(f"Erro ao buscar metals.live: {e}")
    return None

def get_gold_api_free():
    try:
        response = requests.get('https://api.goldpricez.com/v1/rates/currency/usd/metal/xau', timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'price_gram_24k' in data:
                price_per_gram = float(data['price_gram_24k'])
                price_per_oz = price_per_gram * 31.1035
                return {
                    'XAU': {
                        'price_usd': price_per_oz,
                        'name': 'Ouro',
                        'source': 'goldpricez'
                    }
                }
    except Exception as e:
        print(f"Erro ao buscar goldpricez: {e}")
    return None

def get_awesome_api_currencies():
    try:
        response = requests.get('https://economia.awesomeapi.com.br/json/last/USD-BRL', timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'USDBRL' in data:
                return float(data['USDBRL']['bid'])
    except Exception as e:
        print(f"Erro ao buscar taxa USD/BRL: {e}")
    return 5.0

def get_simulated_metals_data():
    import random
    base_prices = {
        'XAU': 2650.0,
        'XAG': 31.5,
        'XPT': 1020.0,
        'XPD': 1050.0,
        'XCU': 4.2,
        'SN': 28.5,
        'NI': 8.2,
        'CO': 14.5,
        'AL': 1.15,
        'TA': 180.0,
        'IN': 250.0,
        'GA': 280.0
    }
    
    result = {}
    for symbol, base_price in base_prices.items():
        if symbol not in METAL_SYMBOLS:
            continue
        variation = random.uniform(-0.02, 0.02)
        price = base_price * (1 + variation)
        metal_info = METAL_SYMBOLS[symbol]
        result[symbol] = {
            'price_usd': round(price, 2),
            'name': metal_info['name'],
            'color': metal_info.get('color', '#888888'),
            'fonte_ewaste': metal_info.get('fonte_ewaste', ''),
            'concentracao': metal_info.get('concentracao', ''),
            'source': 'simulated'
        }
    return result

def fetch_metals_data():
    current_time = time.time()
    
    if METALS_CACHE['data'] and (current_time - METALS_CACHE['timestamp']) < CACHE_DURATION:
        return METALS_CACHE['data']
    
    metals_data = get_metals_live_api()
    
    if not metals_data:
        metals_data = get_gold_api_free()
    
    if not metals_data:
        metals_data = get_simulated_metals_data()
    
    if not metals_data:
        return {'metals': {}, 'usd_brl': 5.0, 'timestamp': datetime.now().isoformat(), 'source': 'none'}
    
    usd_brl = get_awesome_api_currencies()
    
    previous_cache = METALS_CACHE.get('previous') or {}
    
    for symbol, data in metals_data.items():
        metal_info = METAL_SYMBOLS.get(symbol, {})
        data['price_brl'] = round(data['price_usd'] * usd_brl, 2)
        data['price_oz'] = data['price_usd']
        data['price_gram_usd'] = round(data['price_usd'] / 31.1035, 4)
        data['price_gram_brl'] = round(data['price_brl'] / 31.1035, 4)
        data['price_kg_brl'] = round(data['price_gram_brl'] * 1000, 2)
        data['symbol'] = symbol
        data['color'] = metal_info.get('color', '#666')
        data['fonte_ewaste'] = metal_info.get('fonte_ewaste', '')
        data['concentracao'] = metal_info.get('concentracao', '')
        
        prev_metal = previous_cache.get(symbol) if isinstance(previous_cache, dict) else None
        prev_price = prev_metal.get('price_usd', data['price_usd']) if isinstance(prev_metal, dict) else data['price_usd']
        data['variation'] = round(((data['price_usd'] - prev_price) / prev_price) * 100, 2) if prev_price else 0
        data['variation_absolute'] = round(data['price_usd'] - prev_price, 2)
    
    result = {
        'metals': metals_data,
        'usd_brl': usd_brl,
        'timestamp': datetime.now().isoformat(),
        'source': list(metals_data.values())[0]['source'] if metals_data else 'none'
    }
    
    cached_data = METALS_CACHE.get('data') or {}
    METALS_CACHE['previous'] = cached_data.get('metals', {}) if isinstance(cached_data, dict) else {}
    METALS_CACHE['data'] = result
    METALS_CACHE['timestamp'] = current_time
    
    today = datetime.now().strftime('%Y-%m-%d')
    if today not in METALS_CACHE['history']:
        METALS_CACHE['history'][today] = []
    METALS_CACHE['history'][today].append({
        'time': datetime.now().strftime('%H:%M:%S'),
        'metals': {k: v['price_usd'] for k, v in metals_data.items()}
    })
    
    if len(METALS_CACHE['history'][today]) > 1440:
        METALS_CACHE['history'][today] = METALS_CACHE['history'][today][-1440:]
    
    return result

def generate_historical_data(days=30):
    import random
    history = {}
    base_prices = {
        'XAU': 2650.0,
        'XAG': 31.5,
        'XPT': 1020.0,
        'XPD': 1050.0,
        'XCU': 4.2,
        'SN': 28.5,
        'NI': 8.2,
        'CO': 14.5,
        'AL': 1.15,
        'TA': 180.0,
        'IN': 250.0,
        'GA': 280.0
    }
    
    for i in range(days, -1, -1):
        date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        daily_data = []
        
        for hour in range(0, 24, 1):
            time_str = f"{hour:02d}:00:00"
            metals = {}
            for symbol, base_price in base_prices.items():
                trend = (days - i) * random.uniform(-0.001, 0.002)
                daily_variation = random.uniform(-0.015, 0.015)
                hourly_variation = random.uniform(-0.005, 0.005)
                price = base_price * (1 + trend + daily_variation + hourly_variation)
                metals[symbol] = round(price, 2)
            
            daily_data.append({
                'time': time_str,
                'metals': metals
            })
        
        history[date] = daily_data
    
    return history

@bp.route('/cotacoes', methods=['GET'])
def get_cotacoes():
    try:
        data = fetch_metals_data()
        return jsonify(data)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500

@bp.route('/historico', methods=['GET'])
def get_historico():
    try:
        days = request.args.get('days', 7, type=int)
        days = min(days, 30)
        
        history = generate_historical_data(days)
        
        real_history = METALS_CACHE.get('history') or {}
        for date, entries in real_history.items():
            if date in history and entries:
                history[date] = entries
        
        return jsonify({
            'history': history,
            'days': days
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@bp.route('/calcular', methods=['POST'])
def calcular_combo():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Dados nao fornecidos'}), 400
            
        items = data.get('items', [])
        if not items:
            return jsonify({'error': 'Nenhum item fornecido para calculo'}), 400
        
        metals_data = fetch_metals_data()
        metals = metals_data.get('metals', {})
        usd_brl = metals_data.get('usd_brl', 5.0)
        
        if not metals:
            return jsonify({'error': 'Nao foi possivel obter cotacoes dos metais'}), 500
        
        result = {
            'items': [],
            'total_usd': 0,
            'total_brl': 0,
            'total_oz': 0
        }
        
        valid_symbols = list(METAL_SYMBOLS.keys())
        
        for item in items:
            symbol = item.get('metal', '').upper()
            
            if symbol not in valid_symbols:
                continue
                
            if symbol not in metals:
                continue
            
            try:
                quantity = float(item.get('quantity', 0))
            except (ValueError, TypeError):
                continue
                
            if quantity <= 0:
                continue
                
            unit = item.get('unit', 'grams')
            metal = metals[symbol]
            
            if unit == 'oz':
                oz_quantity = quantity
            elif unit == 'kg':
                oz_quantity = quantity * 32.1507
            else:
                oz_quantity = quantity / 31.1035
            
            price_usd = oz_quantity * metal['price_usd']
            price_brl = oz_quantity * metal['price_brl']
            
            result['items'].append({
                'metal': symbol,
                'name': metal['name'],
                'quantity': quantity,
                'unit': unit,
                'oz_equivalent': round(oz_quantity, 4),
                'price_usd': round(price_usd, 2),
                'price_brl': round(price_brl, 2),
                'unit_price_usd': metal['price_usd']
            })
            
            result['total_usd'] += price_usd
            result['total_brl'] += price_brl
            result['total_oz'] += oz_quantity
        
        if not result['items']:
            return jsonify({'error': 'Nenhum item valido para calculo'}), 400
        
        result['total_usd'] = round(result['total_usd'], 2)
        result['total_brl'] = round(result['total_brl'], 2)
        result['total_oz'] = round(result['total_oz'], 4)
        result['usd_brl'] = usd_brl
        result['timestamp'] = datetime.now().isoformat()
        
        return jsonify(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@bp.route('/exportar', methods=['POST'])
def exportar_csv():
    from flask import Response
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Dados nao fornecidos'}), 400
            
        export_type = data.get('type', 'cotacoes')
        
        metals_data = fetch_metals_data()
        metals_dict = metals_data.get('metals', {})
        
        if export_type == 'cotacoes':
            csv_content = "Metal,Simbolo,Preco USD,Preco BRL,Preco/g USD,Preco/g BRL,Variacao %\n"
            for symbol, metal in metals_dict.items():
                csv_content += f"{metal['name']},{symbol},{metal['price_usd']},{metal['price_brl']},{metal['price_gram_usd']},{metal['price_gram_brl']},{metal['variation']}\n"
        elif export_type == 'combo':
            items = data.get('items', [])
            if not items:
                return jsonify({'error': 'Nenhum item para exportar'}), 400
            csv_content = "Metal,Quantidade,Unidade,Preco USD,Preco BRL\n"
            total_usd = 0
            total_brl = 0
            for item in items:
                name = item.get('name', item.get('metal', 'N/A'))
                qty = item.get('quantity', 0)
                unit = item.get('unit', 'grams')
                p_usd = item.get('price_usd', 0)
                p_brl = item.get('price_brl', 0)
                csv_content += f"{name},{qty},{unit},{p_usd},{p_brl}\n"
                total_usd += p_usd
                total_brl += p_brl
            csv_content += f"TOTAL,,,{round(total_usd, 2)},{round(total_brl, 2)}\n"
        elif export_type == 'historico':
            days = data.get('days', 7)
            history = generate_historical_data(days)
            real_history = METALS_CACHE.get('history') or {}
            for date, entries in real_history.items():
                if date in history and entries:
                    history[date] = entries
            metals_list = list(METAL_SYMBOLS.keys())
            csv_content = "Data,Hora," + ",".join(metals_list) + "\n"
            for date, entries in sorted(history.items()):
                for entry in entries:
                    entry_metals = entry.get('metals', {})
                    values = [str(entry_metals.get(m, '')) for m in metals_list]
                    csv_content += f"{date},{entry['time']}," + ",".join(values) + "\n"
        else:
            return jsonify({'error': 'Tipo de exportacao invalido'}), 400
        
        filename = f'metais_{export_type}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        return Response(
            csv_content,
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@bp.route('/alertas', methods=['GET', 'POST', 'DELETE'])
def manage_alertas():
    if not hasattr(bp, 'alertas'):
        bp.alertas = []
    
    if request.method == 'GET':
        return jsonify(bp.alertas)
    
    elif request.method == 'POST':
        data = request.get_json()
        alerta = {
            'id': len(bp.alertas) + 1,
            'metal': data.get('metal'),
            'condition': data.get('condition'),
            'price': float(data.get('price', 0)),
            'currency': data.get('currency', 'USD'),
            'created_at': datetime.now().isoformat(),
            'active': True
        }
        bp.alertas.append(alerta)
        return jsonify(alerta), 201
    
    elif request.method == 'DELETE':
        alerta_id = request.args.get('id', type=int)
        bp.alertas = [a for a in bp.alertas if a['id'] != alerta_id]
        return jsonify({'success': True})

@bp.route('/estatisticas', methods=['GET'])
def get_estatisticas():
    try:
        days = request.args.get('days', 7, type=int)
        history = generate_historical_data(days)
        
        stats = {}
        for symbol in METAL_SYMBOLS.keys():
            prices = []
            for date, entries in history.items():
                for entry in entries:
                    if symbol in entry['metals']:
                        prices.append(entry['metals'][symbol])
            
            if prices:
                stats[symbol] = {
                    'name': METAL_SYMBOLS[symbol]['name'],
                    'min': round(min(prices), 2),
                    'max': round(max(prices), 2),
                    'avg': round(sum(prices) / len(prices), 2),
                    'current': prices[-1] if prices else 0,
                    'variation': round(((prices[-1] - prices[0]) / prices[0]) * 100, 2) if len(prices) > 1 and prices[0] else 0
                }
        
        return jsonify({
            'stats': stats,
            'period_days': days
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
