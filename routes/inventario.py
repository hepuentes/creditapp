from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from models.inventario import ItemInventario, MovimientoInventario
from utils.helpers import admin_required
from utils.formatters import convertir_a_numero

inventario_bp = Blueprint('inventario', __name__)

@inventario_bp.route('/inventario')
@login_required
@admin_required
def lista():
    productos = ItemInventario.query.filter_by(activo=True).all()
    return render_template('inventario/lista.html', productos=productos)

@inventario_bp.route('/inventario/gestionar', methods=['GET', 'POST'])
@inventario_bp.route('/inventario/gestionar/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def gestionar(id=None):
    producto = None
    if id:
        producto = ItemInventario.query.get_or_404(id)
    
    if request.method == 'POST':
        if not producto:
            producto = ItemInventario()
        
        producto.codigo = request.form.get('codigo')
        producto.nombre = request.form.get('nombre')
        producto.descripcion = request.form.get('descripcion')
        producto.precio_costo = convertir_a_numero(request.form.get('precio_costo'))
        producto.precio_venta = convertir_a_numero(request.form.get('precio_venta'))
        producto.stock_minimo = convertir_a_numero(request.form.get('stock_minimo'))
        producto.categoria = request.form.get('categoria')
        producto.activo = True
        
        if not id:  # Nuevo producto
            producto.stock_actual = 0
            db.session.add(producto)
        
        db.session.commit()
        flash('Producto guardado exitosamente', 'success')
        return redirect(url_for('inventario.lista'))
    
    return render_template('inventario/crear.html', producto=producto)

@inventario_bp.route('/inventario/movimientos')
@login_required
@admin_required
def movimientos():
    # Filtros
    tipo = request.args.get('tipo', 'todos')
    producto_id = request.args.get('producto_id')
    
    # Consulta base
    query = MovimientoInventario.query
    
    # Aplicar filtros
    if tipo != 'todos':
        query = query.filter_by(tipo=tipo)
    
    if producto_id:
        query = query.filter_by(item_inventario_id=producto_id)
    
    # Ordenar por fecha (más recientes primero)
    movimientos = query.order_by(MovimientoInventario.fecha.desc()).all()
    
    # Obtener productos para el filtro
    productos = ItemInventario.query.filter_by(activo=True).all()
    
    return render_template('inventario/movimientos.html', 
                          movimientos=movimientos, 
                          productos=productos,
                          tipo_filtro=tipo,
                          producto_filtro=producto_id)

@inventario_bp.route('/inventario/movimientos/crear', methods=['GET', 'POST'])
@login_required
@admin_required
def crear_movimiento():
    if request.method == 'POST':
        item_inventario_id = request.form.get('item_inventario_id')
        tipo = request.form.get('tipo')
        cantidad = convertir_a_numero(request.form.get('cantidad'))
        referencia = request.form.get('referencia')
        notas = request.form.get('notas')
        
        # Validar cantidad
        if cantidad <= 0:
            flash('La cantidad debe ser mayor que cero', 'danger')
            return redirect(url_for('inventario.crear_movimiento'))
        
        # Obtener el producto
        producto = ItemInventario.query.get_or_404(item_inventario_id)
        
        # Validar stock para salidas
        if tipo == 'Salida' and cantidad > producto.stock_actual:
            flash(f'No hay suficiente stock. Disponible: {producto.stock_actual}', 'danger')
            return redirect(url_for('inventario.crear_movimiento'))
        
        # Crear el movimiento
        movimiento = MovimientoInventario(
            item_inventario_id=item_inventario_id,
            usuario_id=current_user.id,
            tipo=tipo,
            cantidad=cantidad,
            referencia=referencia,
            notas=notas
        )
        
        # Actualizar el stock del producto
        if tipo == 'Entrada':
            producto.stock_actual += cantidad
        elif tipo == 'Salida':
            producto.stock_actual -= cantidad
        elif tipo == 'Ajuste':
            # Para ajustes, la cantidad es el nuevo valor del stock
            producto.stock_actual = cantidad
        
        db.session.add(movimiento)
        db.session.commit()
        
        flash('Movimiento registrado exitosamente', 'success')
        return redirect(url_for('inventario.movimientos'))
    
    # Obtener productos para el formulario
    productos = ItemInventario.query.filter_by(activo=True).all()
    
    return render_template('inventario/crear_movimiento.html', productos=productos)

@inventario_bp.route('/inventario/<int:id>/desactivar', methods=['POST'])
@login_required
@admin_required
def desactivar(id):
    producto = ItemInventario.query.get_or_404(id)
    producto.activo = not producto.activo
    db.session.commit()
    
    estado = 'activado' if producto.activo else 'desactivado'
    flash(f'Producto {estado} exitosamente', 'success')
    
    return redirect(url_for('inventario.lista'))
