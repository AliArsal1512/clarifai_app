# backend/app/config.py
import os

base_dir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or '151214'
    DATABASE_URL = os.environ.get('DATABASE_URL')
    
    if DATABASE_URL:
        # Fix for SQLAlchemy - change postgres:// to postgresql://
        if DATABASE_URL.startswith("postgres://"):
            DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
    else:
        # Fallback to SQLite (local development)
        base_dir = os.path.abspath(os.path.dirname(__file__))
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(base_dir, '..', 'users.db')
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    
    # Security settings
    FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
    IS_PRODUCTION = FLASK_ENV == 'production'
    
    SESSION_COOKIE_SECURE = IS_PRODUCTION  # True in production, False in development
    REMEMBER_COOKIE_SECURE = IS_PRODUCTION
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True

    # IMPORTANT FIX: Remove or comment out SESSION_COOKIE_DOMAIN
    # SESSION_COOKIE_DOMAIN = '.onrender.com'  # REMOVE THIS LINE
    
    # For SameSite cookies in cross-origin scenarios
    if IS_PRODUCTION:
        SESSION_COOKIE_SAMESITE = 'None'  # Required for cross-origin in production
        REMEMBER_COOKIE_SAMESITE = 'None'
    else:
        SESSION_COOKIE_SAMESITE = 'Lax'  # Safer for development
        REMEMBER_COOKIE_SAMESITE = 'Lax'
    
    SESSION_COOKIE_PATH = '/'
    
    # CORS settings
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:3000').split(',')