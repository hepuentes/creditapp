from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.urls import url_parse
from app import db
from models.usuario import Usuario
from utils.helpers import admin_required

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = Usuario.query.filter_by(username=username).first()
        
        if user is None or not user.check_password(password):
            flash('Usuario o contraseña incorrectos', 'danger')
            return redirect(url_for('auth.login'))
        
        if not user.activo:
            flash('Esta cuenta está desactivada. Contacta al administrador.', 'warning')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=True)
        
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            if user.es_administrador:
                next_page = url_for('admin.dashboard')
            elif user.es_vendedor:
                next_page = url_for('creditos.crear')
            else:
                next_page = url_for('creditos.lista')
        
        return redirect(next_page)
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth_bp.route('/perfil', methods=['GET', 'POST'])
@login_required
def perfil():
    if request.method == 'POST':
        current_user.nombre = request.form.get('nombre')
        current_user.email = request.form.get('email')
        
        password = request.form.get('password')
        if password:
            current_user.set_password(password)
        
        db.session.commit()
        flash('Perfil actualizado correctamente', 'success')
        return redirect(url_for('auth.perfil'))
    
    return render_template('auth/perfil.html')
