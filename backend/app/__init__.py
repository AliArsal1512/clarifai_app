# app/__init__.py
import os
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from .config import Config

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'

from .models import User, CodeSubmission

def create_app(config_class=Config):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    app = Flask(__name__,
                static_folder=os.path.join(base_dir, 'static'),
                instance_relative_config=True)
    
    app.config.from_object(config_class)
    
    # IMPORTANT: Configure CORS for frontend service
    # Allow frontend service to access backend API
    cors_origins = os.environ.get('CORS_ORIGINS', 'http://localhost:3000')
    CORS(app, origins=cors_origins.split(',') if ',' in cors_origins else cors_origins)

    # Register blueprints/routes
    # Register blueprints
    from .auth.routes import auth_bp
    from .main.routes import main_bp  # This should work now
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp)  # Make sure this is main_bp, not main
    
    # Debug database URL
    print(f"Database URI configured: {app.config['SQLALCHEMY_DATABASE_URI']}")
    
    app.config['UPLOAD_FOLDER'] = os.path.join(app.static_folder, 'cfg_images')
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    db.init_app(app)
    login_manager.init_app(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Register blueprints
    from .auth.routes import auth_bp
    from .main.routes import main_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
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
    
    # Health check for Render
    @app.route('/api/health')
    def health_check():
        return jsonify({
            'status': 'healthy',
            'service': 'clarifai-backend',
            'database': 'configured'
        }), 200
    
    # IMPORTANT: Remove React serving routes for two-service approach
    # Frontend will be served separately by the frontend service
    
    # Add a simple root route
    @app.route('/')
    def index():
        return jsonify({
            'message': 'ClarifAI Backend API',
            'status': 'running',
            'endpoints': {
                'auth': '/auth/*',
                'api': '/api/*',
                'health': '/api/health'
            }
        })
    
    with app.app_context():
        db.create_all()
    
    # Initialize ML Pipeline (keep as is)
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