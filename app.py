from flask import Flask, render_template, request, jsonify, send_file
from flask_socketio import SocketIO, emit
import os
import mimetypes
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global config dictionary
CONFIG = {}

def load_config():
    """Load configuration from config.json"""
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
            return config
    except FileNotFoundError:
        # Create default config
        default_config = {
            "screens": ["Frame Build 1", "Frame Build 2", "Frame Build 3", "Frame Build 4"],
            "image_base_path": r"C:\Users\100075082\Pictures\AppTEST",
            "supported_extensions": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"],
            "server": {
                "host": "0.0.0.0",
                "port": 5000,
                "debug": True
            },
            "display": {
                "screen_name_size": "24px",
                "image_name_size": "28px",
                "max_image_height": "calc(100vh - 160px)",
                "max_image_width": "95vw"
            }
        }
        save_config(default_config)
        return default_config
    except Exception as e:
        print(f"Error loading config: {e}")
        return {}

def save_config(config):
    """Save configuration to config.json"""
    try:
        with open('config.json', 'w') as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"Error saving config: {e}")

# Load configuration
CONFIG = load_config()
IMAGE_BASE_PATH = CONFIG.get('image_base_path', r"C:\Users\100075082\Pictures\AppTEST")
# Convert relative path to absolute
if not os.path.isabs(IMAGE_BASE_PATH):
    IMAGE_BASE_PATH = os.path.abspath(IMAGE_BASE_PATH)
SUPPORTED_EXTENSIONS = CONFIG.get('supported_extensions', ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'])
SCREENS = CONFIG.get('screens', [])

def find_image(image_name):
    """Find image with any supported extension"""
    # Check if image_name already has an extension
    name_lower = image_name.lower()
    if any(name_lower.endswith(ext) for ext in SUPPORTED_EXTENSIONS):
        image_path = os.path.join(IMAGE_BASE_PATH, image_name)
        if os.path.exists(image_path):
            return image_path, image_name
        return None, image_name
    
    # Try all supported extensions
    for ext in SUPPORTED_EXTENSIONS:
        test_name = image_name + ext
        image_path = os.path.join(IMAGE_BASE_PATH, test_name)
        if os.path.exists(image_path):
            return image_path, test_name
    
    return None, image_name + SUPPORTED_EXTENSIONS[0]

@app.route('/')
def index():
    """Main control panel"""
    return render_template('control.html', screens=SCREENS, supported_types=', '.join(SUPPORTED_EXTENSIONS))

@app.route('/<screen_name>/display')
def display_screen(screen_name):
    """Individual display screen"""
    if screen_name not in SCREENS:
        return f"Screen '{screen_name}' not configured", 404
    return render_template('display_screen.html', screen_name=screen_name, config=CONFIG.get('display', {}), timing=CONFIG.get('timing', {'warning': 20, 'over': 50}))

@app.route('/api/display', methods=['POST'])
def api_display_image():
    """API endpoint for displaying image on a specific screen"""
    try:
        data = request.get_json()
        screen_name = data.get('name', '')
        image_name = data.get('pic', '')
        
        if not screen_name:
            return jsonify({
                'success': False,
                'message': 'Screen name is required'
            }), 400
        
        if screen_name not in SCREENS:
            return jsonify({
                'success': False,
                'message': f'Screen "{screen_name}" not found',
                'available_screens': SCREENS
            }), 404
        
        if not image_name:
            return jsonify({
                'success': False,
                'message': 'Image name (pic) is required'
            }), 400
        
        image_path, final_name = find_image(image_name)
        
        if image_path:
            # Emit to specific screen via WebSocket
            socketio.emit('update_image', {
                'image_name': final_name,
                'image_url': f'/get-image/{final_name}'
            }, room=screen_name)
            
            return jsonify({
                'success': True,
                'message': 'Image displayed',
                'screen': screen_name,
                'image_name': final_name,
                'image_url': f'/get-image/{final_name}'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Image not found',
                'image_name': final_name,
                'supported_types': SUPPORTED_EXTENSIONS
            }), 404
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/get-image/<path:filename>')
def get_image(filename):
    """Serve the actual image file"""
    try:
        image_path = os.path.join(IMAGE_BASE_PATH, filename)
        if os.path.exists(image_path):
            mimetype, _ = mimetypes.guess_type(image_path)
            if not mimetype:
                mimetype = 'image/jpeg'
            return send_file(image_path, mimetype=mimetype)
        return "Image not found", 404
    except Exception as e:
        return f"Error serving image: {str(e)}", 500

@app.route('/api/set-path', methods=['POST'])
def set_base_path():
    """API endpoint to change base image path"""
    global IMAGE_BASE_PATH, CONFIG
    try:
        data = request.get_json()
        new_path = data.get('path', '')
        
        if os.path.exists(new_path):
            IMAGE_BASE_PATH = new_path
            CONFIG['image_base_path'] = new_path
            save_config(CONFIG)
            return jsonify({
                'success': True,
                'message': 'Base path updated',
                'path': IMAGE_BASE_PATH
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Path does not exist'
            }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/config', methods=['GET'])
def get_config():
    """API endpoint to get current configuration"""
    return jsonify(CONFIG)

@socketio.on('join')
def handle_join(data):
    """Handle screen joining its room"""
    screen_name = data.get('screen_name')
    if screen_name in SCREENS:
        from flask_socketio import join_room
        join_room(screen_name)
        emit('joined', {'screen_name': screen_name})

@socketio.on('manual_submit')
def handle_manual_submit(data):
    """Handle manual image submission from control panel"""
    try:
        screen_name = data.get('screen_name')
        image_name = data.get('image_name')
        
        if screen_name not in SCREENS:
            emit('error', {'message': f'Screen "{screen_name}" not found'})
            return
        
        image_path, final_name = find_image(image_name)
        
        if image_path:
            socketio.emit('update_image', {
                'image_name': final_name,
                'image_url': f'/get-image/{final_name}'
            }, room=screen_name)
            
            emit('success', {
                'message': f'Image displayed on {screen_name}',
                'image_name': final_name
            })
        else:
            emit('error', {
                'message': f'Image "{final_name}" not found'
            })
    
    except Exception as e:
        emit('error', {'message': str(e)})

if __name__ == '__main__':
    server_config = CONFIG.get('server', {})
    socketio.run(
        app, 
        debug=server_config.get('debug', True), 
        host=server_config.get('host', '0.0.0.0'), 
        port=server_config.get('port', 5000)
    )
