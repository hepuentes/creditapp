from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from models.cliente import Cliente
from models.credito import Credito
from utils.helpers import admin_required, vendedor_required

clientes_bp = Blueprint('clientes', __name__)

@clientes_bp.route('/clientes')
@login_required
def lista():
    clientes = Cliente.query.filter_by(activo=True).all()
    return render_template('clientes/lista.html', clientes=clientes)

@clientes_bp.route('/clientes/gestionar', methods=['GET', 'POST'])
@clientes_bp.route('/clientes/gestionar/<int:id>', methods=['GET', 'POST'])
@login_required
def gestionar(id=None):
    cliente = None
    if id:
        cliente = Cliente.query.get_or_404(id)
    
    if request.method == 'POST':
        if not cliente:
            cliente = Cliente()
        
        cliente.nombre = request.form.get('nombre')
        cliente.documento = request.form.get('documento')
        cliente.telefono = request.form.get('telefono')
        cliente.direccion = request.form.get('direccion')
        cliente.email = request.form.get('email')
        cliente.activo = True
        
        if not id:  # Nuevo cliente
            db.session.add(cliente)
        
        db.session.commit()
        flash('Cliente guardado exitosamente', 'success')
        return redirect(url_for('clientes.lista'))
    
    return render_template('clientes/crear.html', cliente=cliente)

@clientes_bp.route('/clientes/<int:id>')
@login_required
def detalle(id):
    cliente = Cliente.query.get_or_404(id)
    creditos = Credito.query.filter_by(cliente_id=id).order_by(Credito.fecha_creacion.desc()).all()
    return render_template('clientes/detalle.html', cliente=cliente, creditos=creditos)

@clientes_bp.route('/clientes/<int:id>/desactivar', methods=['POST'])
@login_required
@admin_required
def desactivar(id):
    cliente = Cliente.query.get_or_404(id)
    
    # Verificar si tiene créditos pendientes
    creditos_pendientes = Credito.query.filter_by(cliente_id=id, estado='Pendiente').first()
    if creditos_pendientes:
        flash('No se puede desactivar el cliente porque tiene créditos pendientes', 'danger')
        return redirect(url_for('clientes.detalle', id=id))
    
    cliente.activo = not cliente.activo
    db.session.commit()
    
    estado = 'activado' if cliente.activo else 'desactivado'
    flash(f'Cliente {estado} exitosamente', 'success')
    
    return redirect(url_for('clientes.lista'))
