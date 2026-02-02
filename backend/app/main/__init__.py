# app/main/__init__.py
from flask import Blueprint

main_bp = Blueprint('main', __name__, template_folder='../templates') # Adjust template_folder

from . import routes # Import routes after blueprint creation
