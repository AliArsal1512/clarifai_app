# app/auth/routes.py
from flask import redirect, url_for, request, jsonify, current_app
from flask_login import login_user, logout_user, current_user, login_required
from sqlalchemy.exc import IntegrityError
from . import auth_bp # from app/auth/__init__.py
from ..models import User # from app/models.py
from .. import db # from app/__init__.py

@auth_bp.route('/login', methods=['POST']) #
def login(): #
    if current_user.is_authenticated: #
        return jsonify({'success': True, 'redirect': '/dashboard'})
    username = request.form.get('username') #
    password = request.form.get('password') #
    user = User.query.filter_by(username=username).first() #
    if user and user.check_password(password): #
        login_user(user) #
        return jsonify({'success': True, 'redirect': '/dashboard'})
    # Return JSON error for React
    return jsonify({'success': False, 'error': 'Invalid username or password'}), 401

@auth_bp.route('/signup', methods=['POST']) #
def signup(): #
    if current_user.is_authenticated: #
        return jsonify({'success': True, 'redirect': '/dashboard'})
    username = request.form.get('username').strip() #
    email = request.form.get('email').strip() #
    password = request.form.get('password') #

    existing_user = User.query.filter((User.username == username) | (User.email == email)).first() #
    if existing_user: #
        error_msg = 'Username already taken.' if existing_user.username == username else 'Email already registered.' #
        return jsonify({'success': False, 'error': error_msg}), 400
    try:
        new_user = User(username=username, email=email) #
        new_user.set_password(password) #
        db.session.add(new_user) #
        db.session.commit() #
        login_user(new_user) #
        return jsonify({'success': True, 'redirect': '/dashboard'})
    except IntegrityError: #
        db.session.rollback() #
        return jsonify({'success': False, 'error': 'Registration failed. Please try again.'}), 400
    except Exception as e: #
        db.session.rollback() #
        current_app.logger.error(f"Signup error: {e}")
        return jsonify({'success': False, 'error': 'An error occurred. Please try again.'}), 500

@auth_bp.route('/logout') #
def logout(): #
    logout_user() #
    return jsonify({'success': True, 'redirect': '/'})