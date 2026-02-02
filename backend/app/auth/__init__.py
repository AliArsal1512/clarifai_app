# app/auth/__init__.py
from flask import Blueprint

auth_bp = Blueprint('auth', __name__, template_folder='../templates') # Adjust template_folder if needed

from . import routes # Import routes after blueprint creation