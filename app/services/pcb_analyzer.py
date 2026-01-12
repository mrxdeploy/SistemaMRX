import cv2
import numpy as np
import base64

LOW_DENSITY_THRESHOLD = 0.00002
HIGH_DENSITY_THRESHOLD = 0.00008

MIN_BOARD_RATIO = 0.05

MIN_COMPONENT_AREA = 30
MAX_COMPONENT_AREA = 80000

def analyze_pcb_image(image_data) -> dict:
    """
    Analisa uma imagem de placa eletrônica usando OpenCV.
    Retorna um dicionário com:
      - components_count: número aproximado de componentes detectados
      - density_score: densidade normalizada (componentes / área da placa)
      - grade: 'LOW' | 'MEDIUM' | 'HIGH' ou None se placa não detectada
      - board_detected: bool indicando se uma placa foi detectada
      - debug: campos auxiliares para depuração
    """
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
            return {
                'components_count': 0,
                'density_score': 0.0,
                'grade': None,
                'board_detected': False,
                'error': 'Formato de imagem inválido'
            }
        
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return {
                'components_count': 0,
                'density_score': 0.0,
                'grade': None,
                'board_detected': False,
                'error': 'Não foi possível decodificar a imagem'
            }
        
        height, width = img.shape[:2]
        total_pixels = height * width
        
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        lower_green1 = np.array([35, 20, 20])
        upper_green1 = np.array([90, 255, 255])
        
        lower_green2 = np.array([70, 15, 15])
        upper_green2 = np.array([100, 255, 255])
        
        lower_brown = np.array([8, 20, 20])
        upper_brown = np.array([35, 255, 220])
        
        lower_blue = np.array([95, 20, 20])
        upper_blue = np.array([135, 255, 255])
        
        lower_yellow = np.array([15, 40, 40])
        upper_yellow = np.array([40, 255, 255])
        
        lower_red1 = np.array([0, 30, 30])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([160, 30, 30])
        upper_red2 = np.array([180, 255, 255])
        
        mask_green1 = cv2.inRange(hsv, lower_green1, upper_green1)
        mask_green2 = cv2.inRange(hsv, lower_green2, upper_green2)
        mask_brown = cv2.inRange(hsv, lower_brown, upper_brown)
        mask_blue = cv2.inRange(hsv, lower_blue, upper_blue)
        mask_yellow = cv2.inRange(hsv, lower_yellow, upper_yellow)
        mask_red1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask_red2 = cv2.inRange(hsv, lower_red2, upper_red2)
        
        pcb_mask = cv2.bitwise_or(mask_green1, mask_green2)
        pcb_mask = cv2.bitwise_or(pcb_mask, mask_brown)
        pcb_mask = cv2.bitwise_or(pcb_mask, mask_blue)
        pcb_mask = cv2.bitwise_or(pcb_mask, mask_yellow)
        pcb_mask = cv2.bitwise_or(pcb_mask, mask_red1)
        pcb_mask = cv2.bitwise_or(pcb_mask, mask_red2)
        
        kernel = np.ones((5, 5), np.uint8)
        pcb_mask = cv2.morphologyEx(pcb_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        pcb_mask = cv2.morphologyEx(pcb_mask, cv2.MORPH_OPEN, kernel, iterations=1)
        
        board_pixels = float(np.sum(pcb_mask) / 255)
        board_ratio = board_pixels / max(total_pixels, 1)
        
        if board_ratio < MIN_BOARD_RATIO:
            return {
                'grade': None,
                'components_count': 0,
                'density_score': 0.0,
                'board_detected': False,
                'debug': {
                    'board_ratio': round(board_ratio, 4),
                    'board_pixels': int(board_pixels),
                    'total_pixels': total_pixels,
                    'min_board_ratio': MIN_BOARD_RATIO,
                    'image_size': f'{width}x{height}'
                }
            }
        
        components_mask = cv2.bitwise_not(pcb_mask)
        
        kernel_small = np.ones((3, 3), np.uint8)
        components_mask = cv2.morphologyEx(components_mask, cv2.MORPH_OPEN, kernel_small, iterations=2)
        components_mask = cv2.morphologyEx(components_mask, cv2.MORPH_CLOSE, kernel_small, iterations=2)
        
        blurred = cv2.GaussianBlur(components_mask, (5, 5), 0)
        
        contours, _ = cv2.findContours(blurred, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        valid_contours = []
        total_component_area = 0
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if MIN_COMPONENT_AREA <= area <= MAX_COMPONENT_AREA:
                valid_contours.append(contour)
                total_component_area += area
        
        components_count = len(valid_contours)
        
        board_area = max(board_pixels, 1.0)
        density = components_count / board_area
        
        if density < LOW_DENSITY_THRESHOLD:
            grade = 'LOW'
        elif density < HIGH_DENSITY_THRESHOLD:
            grade = 'MEDIUM'
        else:
            grade = 'HIGH'
        
        large_components = sum(1 for c in valid_contours if cv2.contourArea(c) > 1000)
        small_components = sum(1 for c in valid_contours if cv2.contourArea(c) <= 1000)
        
        return {
            'grade': grade,
            'components_count': int(components_count),
            'density_score': float(density),
            'board_detected': True,
            'debug': {
                'board_ratio': round(board_ratio, 4),
                'board_pixels': int(board_pixels),
                'total_pixels': total_pixels,
                'image_size': f'{width}x{height}',
                'total_contours': len(contours),
                'valid_contours': components_count,
                'large_components': large_components,
                'small_components': small_components,
                'component_area_ratio': round(total_component_area / total_pixels, 4) if total_pixels > 0 else 0,
                'thresholds': {
                    'low_density': LOW_DENSITY_THRESHOLD,
                    'high_density': HIGH_DENSITY_THRESHOLD
                }
            }
        }
        
    except Exception as e:
        return {
            'components_count': 0,
            'density_score': 0.0,
            'grade': None,
            'board_detected': False,
            'error': str(e)
        }


def get_type_guess_from_analysis(analysis: dict) -> str:
    """
    Tenta adivinhar o tipo de placa com base na análise.
    """
    if not analysis.get('board_detected', False):
        return 'Placa não detectada'
    
    components = analysis.get('components_count', 0)
    density = analysis.get('density_score', 0)
    debug = analysis.get('debug', {})
    large = debug.get('large_components', 0)
    
    if components > 60 or (large > 25 and density > HIGH_DENSITY_THRESHOLD):
        return 'Placa de alta densidade (possivelmente motherboard, celular ou servidor)'
    elif components > 35 or (large > 15 and density > LOW_DENSITY_THRESHOLD):
        return 'Placa de média densidade (possivelmente roteador, HD ou placa de vídeo)'
    elif components > 20:
        return 'Placa de baixa-média densidade (possivelmente fonte, impressora ou periférico)'
    else:
        return 'Placa simples (possivelmente fonte de alimentação, controle remoto ou eletrônico básico)'


def generate_local_explanation(grade: str, components_count: int, density_score: float, board_detected: bool = True) -> str:
    """
    Gera uma explicação local (fallback) quando a API Perplexity não está disponível.
    """
    if not board_detected or grade is None:
        return 'Placa eletrônica não detectada na imagem. Por favor, envie uma foto clara de uma placa de circuito impresso (PCB).'
    
    grade_labels = {
        'LOW': 'baixo valor',
        'MEDIUM': 'valor intermediário', 
        'HIGH': 'alto valor'
    }
    
    grade_label = grade_labels.get(grade, 'valor não determinado')
    
    density_formatted = f'{density_score:.8f}'
    
    if grade == 'HIGH':
        return (
            f'Esta placa foi classificada como de {grade_label} para reciclagem de metais preciosos. '
            f'Foram detectados aproximadamente {components_count} componentes eletrônicos. '
            f'A alta densidade de componentes indica maior probabilidade de presença de ouro em conectores, chips BGA e processadores.'
        )
    elif grade == 'MEDIUM':
        return (
            f'Esta placa foi classificada como de {grade_label} para reciclagem. '
            f'Foram detectados aproximadamente {components_count} componentes. '
            f'A placa possui quantidade moderada de componentes que podem conter metais preciosos.'
        )
    else:
        return (
            f'Esta placa foi classificada como de {grade_label} para reciclagem. '
            f'Foram detectados aproximadamente {components_count} componentes. '
            f'Placas simples geralmente contêm menos metais preciosos, mas ainda podem ter valor em cobre e estanho.'
        )
