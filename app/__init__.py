# app/__init__.py
import os
from flask import Flask, jsonify, logging, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from .config import Config # We'll create this file next

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login' # Refers to the 'login' route in the 'auth' blueprint

# Import models here to avoid circular imports when db.create_all() is called
# This needs to be after db is defined and before create_app returns if using create_all in create_app
from .models import User, CodeSubmission

def create_app(config_class=Config):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    app = Flask(__name__,
                template_folder=os.path.join(base_dir, 'templates'),
                static_folder=os.path.join(base_dir, 'static'),
                instance_relative_config=True) # For instance folder config

    app.config.from_object(config_class)
     # Add CORS support
    CORS(app)
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Debug database URL (remove in production if needed)
    print(f"Database URI configured: {app.config['SQLALCHEMY_DATABASE_URI']}")
    app.config['UPLOAD_FOLDER'] = os.path.join(app.static_folder, 'cfg_images')
    # Create the folder if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Optionally load instance config
    # app.config.from_pyfile('config.py', silent=True) # if you have instance/config.py

    db.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    from .auth.routes import auth_bp
    from .main.routes import main_bp

    app.register_blueprint(auth_bp, url_prefix='/auth') # All auth routes will be /auth/login, /auth/signup etc.
    app.register_blueprint(main_bp)
    
    # Add API route for checking authentication
    @app.route('/api/check-auth')
    def check_auth():
        if current_user.is_authenticated:
            return jsonify({
                'authenticated': True,
                'user': {'username': current_user.username, 'id': current_user.id}
            })
        return jsonify({'authenticated': False, 'user': None})
    
    # Serve React app for all non-API routes (catch-all route - must be registered last)
    # This route only handles GET requests - POST requests go to API routes

        # Health check for Render
    @app.route('/api/health')
    def health_check():
        return jsonify({
            'status': 'healthy',
            'service': 'clarifai-fyp',
            'database': 'configured'
        }), 200
    
    @app.route('/', defaults={'path': ''}, methods=['GET'])
    @app.route('/<path:path>', methods=['GET'])
    def serve_react_app(path):
        # Don't serve React for API routes, auth POST routes, or static files
        # These are handled by Flask routes above
        excluded_prefixes = ['api', 'static']
        
        # Check if this is an excluded route (should have been handled already)
        path_parts = path.split('/') if path else []
        if path_parts and path_parts[0] in excluded_prefixes:
            from flask import abort
            abort(404)  # Should have been handled by Flask routes
        
        # Serve React build files
        react_build_dir = os.path.join(base_dir, 'static', 'react-build')
        if os.path.exists(react_build_dir):
            # Check if requesting a specific file (like .js, .css, .png, etc.)
            if path:
                file_path = os.path.join(react_build_dir, path)
                if os.path.exists(file_path) and os.path.isfile(file_path):
                    return send_from_directory(react_build_dir, path)
            
            # Serve index.html for React Router (SPA routing)
            index_path = os.path.join(react_build_dir, 'index.html')
            if os.path.exists(index_path):
                return send_from_directory(react_build_dir, 'index.html')
            else:
                # React build doesn't exist
                from flask import abort
                abort(404, description="React build not found. Please run 'npm run build' first.")

            # Fallback to any HTML file (Vite might have different structure)
            for file in os.listdir(react_build_dir):
                if file.endswith('.html'):
                    return send_from_directory(react_build_dir, file)

    with app.app_context():
        db.create_all() # Create database tables

    # Initialize ML Pipeline (consider moving to a dedicated module if complex)
    try:
        from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline as hf_pipeline
        import torch

        MODEL_ID = "aliarsal1512/clarifai_java_code_commenter"
        DEVICE = -1

        tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
        model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_ID)

        app.hf_pipeline = hf_pipeline(
            "text2text-generation",
            model=model,
            tokenizer=tokenizer,
            device=DEVICE,
            max_length=64,
            num_beams=1,
            do_sample=False
        )

        print("✅ Hugging Face pipeline initialized")

    except Exception as e:
        print("❌ Model initialization error:", e)
        app.hf_pipeline = None

    return app