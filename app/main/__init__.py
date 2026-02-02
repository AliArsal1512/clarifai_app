# app/main/__init__.py
from flask import Blueprint

main_bp = Blueprint('main', __name__, template_folder='../templates') # Adjust template_folder

from . import routes # Import routes after blueprint creation

from flask_cors import CORS  # ADD THIS LINE
import logging  # ADD THIS LINE