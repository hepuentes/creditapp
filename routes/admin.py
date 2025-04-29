from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from models.usuario import Usuario
from models.cliente import Cliente
from models.credito import Credito, Abono
from models.inventario import ItemInventario
from models.finanzas import Caja, MovimientoCaja
from utils.helpers import admin_required
from utils.formatters import convertir_a_numero

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin')
@login_required
@admin_required
def dashboard():
    # Estadísticas generales
    total_clientes = Cliente.query.filter_by(activo=True).count()
    total_creditos = Credito.query.count()
    creditos_pendientes = Credito.query.filter_by(estado='Pendiente').count()
    creditos_pagados = Credito.query.filter_by(estado='Pagado').count()
    
    # Monto total de créditos
    monto_total_creditos = db.session.query(db.func.sum(Credito.monto_total)).scalar() or 0
    
    # Monto total de abonos
    monto_total_abonos = db.session.query(db.func.sum(Abono.monto)).scalar() or 0
    
    # Saldo pendiente
    saldo_pendiente = monto_total_creditos - monto_total_abonos
    
    # Productos con stock bajo
    productos_stock_bajo = ItemInventario.query.filter(
        ItemInventario.stock_actual <= ItemInventario.stock_minimo,
        ItemInventario.activo == True
    ).all()
    
    return render_template('admin/dashboard.html',
                          total_clientes=total_clientes,
                          total_creditos=total_creditos,
                          creditos_pendientes=creditos_pendientes,
                          creditos_pagados=creditos_pagados,
                          monto_total_creditos=monto_total_creditos,
                          monto_total_abonos=monto_total_abonos,
                          saldo_pendiente=saldo_pendiente,
                          productos_stock_bajo=productos_stock_bajo)

@admin_bp.route('/admin/usuarios')
@login_required
@admin_required
def usuarios():
    usuarios = Usuario.query.all()
    return render_template('admin/usuarios.html', usuarios=usuarios)

@admin_bp.route('/admin/usuarios/gestionar', methods=['GET', 'POST'])
@admin_bp.route('/admin/usuarios/gestionar/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def gestionar_usuario(id=None):
    usuario = None
    if id:
        usuario = Usuario.query.get_or_404(id)
    
    if request.method == 'POST':
        if not usuario:
            usuario = Usuario()
        
        usuario.nombre = request.form.get('nombre')
        usuario.username = request.form.get('username')
        usuario.email = request.form.get('email')
        
        password = request.form.get('password')
        if password:
            usuario.set_password(password)
        
        usuario.es_administrador = 'es_administrador' in request.form
        usuario.es_vendedor = 'es_vendedor' in request.form
        usuario.es_cobrador = 'es_cobrador' in request.form
        usuario.activo = 'activo' in request.form
        
        if not id:  # Nuevo usuario
            db.session.add(usuario)
        
        db.session.commit()
        flash('Usuario guardado exitosamente', 'success')
        return redirect(url_for('admin.usuarios'))
    
    return render_template('admin/gestionar_usuario.html', usuario=usuario)

@admin_bp.route('/admin/usuarios/<int:id>/eliminar', methods=['POST'])
@login_required
@admin_required
def eliminar_usuario(id):
    usuario = Usuario.query.get_or_404(id)
    
    # Verificar si el usuario tiene dependencias
    if usuario.vendedor:
        flash('No se puede eliminar el usuario porque está asociado a un vendedor', 'danger')
        return redirect(url_for('admin.usuarios'))
    
    if usuario.creditos:
        flash('No se puede eliminar el usuario porque tiene créditos asociados', 'danger')
        return redirect(url_for('admin.usuarios'))
    
    if usuario.abonos:
        flash('No se puede eliminar el usuario porque tiene abonos asociados', 'danger')
        return redirect(url_for('admin.usuarios'))
    
    if usuario.movimientos_caja:
        flash('No se puede eliminar el usuario porque tiene movimientos de caja asociados', 'danger')
        return redirect(url_for('admin.usuarios'))
    
    # Si no hay dependencias, eliminar el usuario
    db.session.delete(usuario)
    db.session.commit()
    
    flash('Usuario eliminado exitosamente', 'success')
    return redirect(url_for('admin.usuarios'))

@admin_bp.route('/admin/usuarios/<int:id>/desactivar', methods=['POST'])
@login_required
@admin_required
def desactivar_usuario(id):
    usuario = Usuario.query.get_or_404(id)
    
    # Cambiar el estado del usuario
    usuario.activo = not usuario.activo
    
    db.session.commit()
    
    estado = 'activado' if usuario.activo else 'desactivado'
    flash(f'Usuario {estado} exitosamente', 'success')
    
    return redirect(url_for('admin.usuarios'))

@admin_bp.route('/admin/limpiar-datos', methods=['POST'])
@login_required
@admin_required
def limpiar_datos():
    try:
        # Eliminar en orden para evitar problemas de integridad referencial
        # 1. Primero eliminar abonos
        Abono.query.delete()
        
        # 2. Eliminar items de crédito
        ItemCredito.query.delete()
        
        # 3. Eliminar créditos
        Credito.query.delete()
        
        # 4. Eliminar movimientos de caja
        MovimientoCaja.query.delete()
        
        # 5. Eliminar movimientos de inventario
        MovimientoInventario.query.delete()
        
        # 6. Eliminar items de inventario
        ItemInventario.query.delete()
        
        # 7. Eliminar clientes
        Cliente.query.delete()
        
        # Confirmar los cambios
        db.session.commit()
        
        flash('Datos eliminados exitosamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al limpiar datos: {str(e)}', 'danger')
    
    return redirect(url_for('admin.dashboard'))
