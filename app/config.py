# app/config.py
import os

base_dir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or '151214'  # Render will override this
    
    # DATABASE_URL will be provided by Render for PostgreSQL
    # Fallback to SQLite in /tmp (writeable directory on Render)
    if os.environ.get('RENDER') or os.environ.get('DATABASE_URL'):
        # On Render or with DATABASE_URL, use PostgreSQL
        DATABASE_URL = os.environ.get('DATABASE_URL')
        if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
            # Fix for SQLAlchemy
            DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        SQLALCHEMY_DATABASE_URI = DATABASE_URL or \
            'sqlite:////tmp/users.db'  # Fallback to SQLite in /tmp
    else:
        # Local development with SQLite
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(base_dir, '..', 'users.db')
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Upload settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file upload
    
    # Security settings for production
    SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production'
    REMEMBER_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production'
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True