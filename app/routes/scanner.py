from flask import Blueprint, request, jsonify, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, Usuario, ScannerConfig, ScannerAnalysis
from app.services.pcb_analyzer import (
    analyze_pcb_image as opencv_analyze_pcb,
    get_type_guess_from_analysis,
    generate_local_explanation
)
from app.services.perplexity_formatter import (
    build_explanation_with_perplexity,
    is_perplexity_configured
)
from app.auth import admin_required
from datetime import datetime
import base64
import os

bp = Blueprint('scanner', __name__)

def get_scanner_config():
    config = ScannerConfig.query.first()
    if not config:
        config = ScannerConfig(
            enabled=True,
            price_low_min=5.0,
            price_low_max=15.0,
            price_medium_min=20.0,
            price_medium_max=50.0,
            price_high_min=60.0,
            price_high_max=150.0,
            prompt_rules=''
        )
        db.session.add(config)
        db.session.commit()
    return config

@bp.route('/api/scanner/analyze', methods=['POST'])
@jwt_required()
def analyze_pcb():
    try:
        usuario_id = get_jwt_identity()
        config = get_scanner_config()
        
        if not config.enabled:
            return jsonify({'erro': 'Scanner desativado pelo administrador'}), 403
        
        image_data = None
        image_bytes = None
        image_mimetype = None
        
        if 'image' in request.files:
            image_file = request.files['image']
            image_bytes = image_file.read()
            image_data = image_bytes
            image_mimetype = image_file.mimetype or 'image/jpeg'
        
        if request.is_json:
            data = request.get_json()
            if 'image_base64' in data:
                base64_str = data['image_base64']
                if base64_str.startswith('data:image'):
                    parts = base64_str.split(',')
                    if len(parts) == 2:
                        header = parts[0]
                        image_mimetype = header.split(':')[1].split(';')[0] if ':' in header else 'image/jpeg'
                        image_bytes = base64.b64decode(parts[1])
                else:
                    image_bytes = base64.b64decode(base64_str)
                    image_mimetype = 'image/jpeg'
                image_data = image_bytes
        
        if not image_data:
            return jsonify({'erro': 'Imagem nao fornecida. Por favor, envie uma imagem da placa para analise.'}), 400
        
        analysis_result = opencv_analyze_pcb(image_data)
        
        if 'error' in analysis_result:
            return jsonify({'erro': analysis_result['error']}), 400
        
        board_detected = analysis_result.get('board_detected', False)
        
        if not board_detected:
            return jsonify({
                'grade': None,
                'components_count': 0,
                'density_score': 0.0,
                'board_detected': False,
                'type_guess': 'Placa nao detectada',
                'explanation': 'Placa eletronica nao detectada na imagem. Por favor, envie uma foto clara de uma placa de circuito impresso (PCB).',
                'confidence': 0,
                'timestamp': datetime.now().isoformat(),
                'analysis_method': 'opencv',
                'perplexity_used': False
            }), 200
        
        grade = analysis_result['grade']
        components_count = analysis_result['components_count']
        density_score = analysis_result['density_score']
        
        type_guess = get_type_guess_from_analysis(analysis_result)
        
        explanation = build_explanation_with_perplexity(grade, components_count, density_score)
        
        if not explanation:
            explanation = generate_local_explanation(grade, components_count, density_score, board_detected)
        
        confidence = min(0.95, 0.5 + (min(density_score * 10000, 0.3)) + (min(components_count, 50) / 100))
        
        analysis_id = None
        try:
            analysis = ScannerAnalysis(
                usuario_id=int(usuario_id),
                grade=grade,
                type_guess=type_guess,
                explanation=explanation,
                confidence=confidence,
                components_count=components_count,
                density_score=density_score,
                image_data=image_bytes,
                image_mimetype=image_mimetype,
                raw_response=str(analysis_result)
            )
            db.session.add(analysis)
            db.session.commit()
            analysis_id = analysis.id
        except Exception as e:
            print(f'Erro ao salvar analise: {e}')
            db.session.rollback()
        
        response = {
            'id': analysis_id,
            'grade': grade,
            'components_count': components_count,
            'density_score': density_score,
            'board_detected': True,
            'type_guess': type_guess,
            'explanation': explanation,
            'confidence': round(confidence, 2),
            'timestamp': datetime.now().isoformat(),
            'analysis_method': 'opencv',
            'perplexity_used': is_perplexity_configured()
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        print(f'Erro no scanner: {e}')
        return jsonify({'erro': str(e)}), 500

@bp.route('/api/scanner/config', methods=['GET'])
@jwt_required()
def get_config():
    try:
        usuario_id = get_jwt_identity()
        usuario = Usuario.query.get(usuario_id)
        
        if not usuario or usuario.tipo != 'admin':
            return jsonify({'erro': 'Acesso negado'}), 403
        
        config = get_scanner_config()
        return jsonify(config.to_dict()), 200
        
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@bp.route('/api/admin/scanner-config', methods=['GET'])
@jwt_required()
def get_admin_config():
    try:
        usuario_id = get_jwt_identity()
        usuario = Usuario.query.get(usuario_id)
        
        if not usuario or usuario.tipo != 'admin':
            return jsonify({'erro': 'Acesso negado'}), 403
        
        config = get_scanner_config()
        return jsonify(config.to_dict()), 200
        
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@bp.route('/api/admin/scanner-config', methods=['POST'])
@jwt_required()
def update_admin_config():
    try:
        usuario_id = get_jwt_identity()
        usuario = Usuario.query.get(usuario_id)
        
        if not usuario or usuario.tipo != 'admin':
            return jsonify({'erro': 'Acesso negado'}), 403
        
        data = request.get_json()
        config = get_scanner_config()
        
        if 'enabled' in data:
            config.enabled = bool(data['enabled'])
        if 'prompt_rules' in data:
            config.prompt_rules = str(data['prompt_rules'])
        
        config.updated_at = datetime.utcnow()
        config.updated_by = int(usuario_id)
        db.session.commit()
        
        return jsonify({
            'mensagem': 'Configuracoes atualizadas com sucesso',
            'config': config.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@bp.route('/api/scanner/status', methods=['GET'])
def scanner_status():
    try:
        config = get_scanner_config()
        perplexity_configured = is_perplexity_configured()
        
        return jsonify({
            'enabled': config.enabled,
            'api_configured': True,
            'ready': config.enabled,
            'model': 'opencv+perplexity',
            'perplexity_configured': perplexity_configured
        }), 200
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@bp.route('/api/scanner/history', methods=['GET'])
@jwt_required()
def scanner_history():
    try:
        usuario_id = get_jwt_identity()
        limit = request.args.get('limit', 20, type=int)
        include_images = request.args.get('include_images', 'false').lower() == 'true'
        
        analyses = ScannerAnalysis.query.filter_by(
            usuario_id=int(usuario_id)
        ).order_by(
            ScannerAnalysis.created_at.desc()
        ).limit(limit).all()
        
        return jsonify([a.to_dict(include_image=include_images) for a in analyses]), 200
        
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@bp.route('/api/scanner/analysis/<int:analysis_id>', methods=['GET'])
@jwt_required()
def get_analysis(analysis_id):
    try:
        usuario_id = get_jwt_identity()
        include_image = request.args.get('include_image', 'true').lower() == 'true'
        
        analysis = ScannerAnalysis.query.filter_by(
            id=analysis_id,
            usuario_id=int(usuario_id)
        ).first()
        
        if not analysis:
            return jsonify({'erro': 'Analise nao encontrada'}), 404
        
        return jsonify(analysis.to_dict(include_image=include_image)), 200
        
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@bp.route('/api/scanner/analysis/<int:analysis_id>/image', methods=['GET'])
@jwt_required()
def get_analysis_image(analysis_id):
    try:
        usuario_id = get_jwt_identity()
        
        analysis = ScannerAnalysis.query.filter_by(
            id=analysis_id,
            usuario_id=int(usuario_id)
        ).first()
        
        if not analysis or not analysis.image_data:
            return jsonify({'erro': 'Imagem nao encontrada'}), 404
        
        from flask import Response
        return Response(
            analysis.image_data,
            mimetype=analysis.image_mimetype or 'image/jpeg'
        )
        
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@bp.route('/scanner')
def scanner_page():
    return render_template('scanner.html')

@bp.route('/admin/scanner-config')
def admin_scanner_config_page():
    return render_template('admin-scanner-config.html')
