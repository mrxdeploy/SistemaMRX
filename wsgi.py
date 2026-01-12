"""
WSGI entry point para Gunicorn
"""
from app import create_app, socketio
from flask import send_from_directory, render_template
from flask_socketio import join_room
from flask_jwt_extended import decode_token
from app.models import Usuario

# Cria a aplicação
application = create_app()
app = application

# Rotas adicionais
@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory('uploads', filename)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/<path:path>')
def serve_page(path):
    if path.endswith('.html'):
        try:
            return render_template(path)
        except:
            return render_template('index.html')
    return render_template('index.html')

@socketio.on('connect')
def handle_connect(auth):
    try:
        token = auth.get('token') if auth else None
        if not token:
            return False
        
        decoded = decode_token(token)
        usuario_id = decoded['sub']
        
        usuario = Usuario.query.get(usuario_id)
        
        if usuario:
            if usuario.tipo == 'admin':
                join_room('admins')
            else:
                join_room(f'user_{usuario_id}')
            print(f'Usuário {usuario.nome} conectado via WebSocket e entrou na sala')
            return True
    except Exception as e:
        print(f'Erro ao conectar WebSocket: {e}')
        return False

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
