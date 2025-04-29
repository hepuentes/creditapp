from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from app import db
from models.cliente import Cliente
from models.credito import Credito, ItemCredito, Abono
from models.inventario import ItemInventario, MovimientoInventario
from models.finanzas import Caja, MetodoPago, MovimientoCaja, Vendedor
from utils.helpers import admin_required, vendedor_required, cobrador_required
from utils.formatters import convertir_a_numero

creditos_bp = Blueprint('creditos', __name__)

@creditos_bp.route('/creditos')
@login_required
def lista():
    # Filtros
    estado = request.args.get('estado', 'todos')
    cliente_id = request.args.get('cliente_id')
    
    # Consulta base
    query = Credito.query
    
    # Aplicar filtros
    if estado != 'todos':
        query = query.filter_by(estado=estado)
    
    if cliente_id:
        query = query.filter_by(cliente_id=cliente_id)
    
    # Ordenar por fecha de creación (más recientes primero)
    creditos = query.order_by(Credito.fecha_creacion.desc()).all()
    
    # Obtener clientes para el filtro
    clientes = Cliente.query.filter_by(activo=True).all()
    
    return render_template('creditos/lista.html', 
                          creditos=creditos, 
                          clientes=clientes,
                          estado_filtro=estado,
                          cliente_filtro=cliente_id)

@creditos_bp.route('/creditos/crear', methods=['GET', 'POST'])
@login_required
@vendedor_required
def crear():
    # Inicializar carrito en la sesión si no existe
    if 'carrito' not in session:
        session['carrito'] = []
    
    if request.method == 'POST':
        # Obtener datos del formulario
        cliente_id = request.form.get('cliente_id')
        numero_cuotas = convertir_a_numero(request.form.get('numero_cuotas', '1'))
        monto_cuota = convertir_a_numero(request.form.get('monto_cuota', '0'))
        tasa_interes = float(request.form.get('tasa_interes', '0'))
        metodo_calculo = request.form.get('metodo_calculo', 'Cuota Fija')
        vendedor_id = request.form.get('vendedor_id')
        notas = request.form.get('notas', '')
        
        # Validar que haya productos en el carrito
        carrito = session.get('carrito', [])
        if not carrito:
            flash('Debe agregar al menos un producto al crédito', 'danger')
            return redirect(url_for('creditos.crear'))
        
        # Calcular monto total
        monto_total = sum(item['subtotal'] for item in carrito)
        
        # Crear el crédito
        credito = Credito(
            cliente_id=cliente_id,
            usuario_id=current_user.id,
            vendedor_id=vendedor_id,
            fecha_creacion=datetime.now(),
            fecha_vencimiento=datetime.now() + timedelta(days=30 * numero_cuotas),
            monto_total=monto_total,
            saldo=monto_total,
            numero_cuotas=numero_cuotas,
            monto_cuota=monto_cuota,
            tasa_interes=tasa_interes,
            metodo_calculo=metodo_calculo,
            estado='Pendiente',
            notas=notas
        )
        
        db.session.add(credito)
        db.session.flush()  # Para obtener el ID del crédito
        
        # Crear los items del crédito y actualizar el inventario
        for item in carrito:
            item_credito = ItemCredito(
                credito_id=credito.id,
                item_inventario_id=item['id'],
                cantidad=item['cantidad'],
                precio_unitario=item['precio'],
                subtotal=item['subtotal']
            )
            
            db.session.add(item_credito)
            
            # Actualizar el inventario
            item_inventario = ItemInventario.query.get(item['id'])
            item_inventario.stock_actual -= item['cantidad']
            
            # Registrar el movimiento de inventario
            movimiento = MovimientoInventario(
                item_inventario_id=item['id'],
                usuario_id=current_user.id,
                tipo='Salida',
                cantidad=item['cantidad'],
                referencia=f'Crédito #{credito.id}',
                notas=f'Venta a crédito para {Cliente.query.get(cliente_id).nombre}'
            )
            
            db.session.add(movimiento)
        
        db.session.commit()
        
        # Limpiar el carrito
        session.pop('carrito', None)
        
        flash('Crédito creado exitosamente', 'success')
        return redirect(url_for('creditos.detalle', id=credito.id))
    
    # Obtener clientes y productos para el formulario
    clientes = Cliente.query.filter_by(activo=True).all()
    productos = ItemInventario.query.filter(
        ItemInventario.stock_actual > 0,
        ItemInventario.activo == True
    ).all()
    vendedores = Vendedor.query.join(Usuario).filter(Usuario.activo == True).all()
    
    return render_template('creditos/crear.html', 
                          clientes=clientes, 
                          productos=productos,
                          vendedores=vendedores,
                          carrito=session.get('carrito', []))

@creditos_bp.route('/creditos/carrito/agregar', methods=['POST'])
@login_required
def agregar_carrito():
    producto_id = request.form.get('producto_id')
    cantidad = int(request.form.get('cantidad', 1))
    
    producto = ItemInventario.query.get_or_404(producto_id)
    
    # Validar stock
    if cantidad > producto.stock_actual:
        flash(f'No hay suficiente stock. Disponible: {producto.stock_actual}', 'danger')
        return redirect(url_for('creditos.crear'))
    
    # Inicializar carrito si no existe
    if 'carrito' not in session:
        session['carrito'] = []
    
    carrito = session['carrito']
    
    # Verificar si el producto ya está en el carrito
    for item in carrito:
        if item['id'] == int(producto_id):
            item['cantidad'] += cantidad
            item['subtotal'] = item['cantidad'] * item['precio']
            session['carrito'] = carrito
            flash('Producto actualizado en el carrito', 'success')
            return redirect(url_for('creditos.crear'))
    
    # Agregar nuevo producto al carrito
    carrito.append({
        'id': producto.id,
        'nombre': producto.nombre,
        'precio': producto.precio_venta,
        'cantidad': cantidad,
        'subtotal': producto.precio_venta * cantidad
    })
    
    session['carrito'] = carrito
    flash('Producto agregado al carrito', 'success')
    return redirect(url_for('creditos.crear'))

@creditos_bp.route('/creditos/carrito/eliminar/<int:producto_id>', methods=['POST'])
@login_required
def eliminar_carrito(producto_id):
    if 'carrito' in session:
        carrito = session['carrito']
        carrito = [item for item in carrito if item['id'] != producto_id]
        session['carrito'] = carrito
        flash('Producto eliminado del carrito', 'success')
    
    return redirect(url_for('creditos.crear'))

@creditos_bp.route('/creditos/carrito/vaciar', methods=['POST'])
@login_required
def vaciar_carrito():
    session.pop('carrito', None)
    flash('Carrito vaciado exitosamente', 'success')
    return redirect(url_for('creditos.crear'))

@creditos_bp.route('/creditos/<int:id>')
@login_required
def detalle(id):
    credito = Credito.query.get_or_404(id)
    abonos = credito.abonos.order_by(Abono.fecha_abono.desc()).all()
    items = credito.items.all()
    return render_template('creditos/detalle.html', 
                          credito=credito, 
                          abonos=abonos, 
                          items=items)

@creditos_bp.route('/creditos/<int:id>/abonar', methods=['GET', 'POST'])
@login_required
@cobrador_required
def abonar(id):
    credito = Credito.query.get_or_404(id)
    
    # Verificar si el crédito está pagado
    if credito.estado == 'Pagado':
        flash('Este crédito ya está pagado', 'warning')
        return redirect(url_for('creditos.detalle', id=id))
    
    if request.method == 'POST':
        # Convertir el monto correctamente
        monto_str = request.form.get('monto', '0')
        monto = convertir_a_numero(monto_str)
        
        caja_id = request.form.get('caja_id')
        metodo_pago_id = request.form.get('metodo_pago_id')
        notas = request.form.get('notas', '')
        
        # Validar que el monto sea mayor que cero
        if monto <= 0:
            flash('El monto debe ser mayor que cero', 'danger')
            return redirect(url_for('creditos.abonar', id=id))
        
        # Validar que el monto no sea mayor que el saldo
        if monto > credito.saldo:
            flash(f'El monto no puede ser mayor que el saldo pendiente ({credito.saldo})', 'danger')
            return redirect(url_for('creditos.abonar', id=id))
        
        # Crear el abono
        abono = Abono(
            credito_id=credito.id,
            monto=monto,
            fecha_abono=datetime.now(),
            caja_id=caja_id,
            metodo_pago_id=metodo_pago_id,
            notas=notas,
            usuario_id=current_user.id
        )
        
        # Actualizar el saldo del crédito
        credito.saldo -= monto
        
        # Si el saldo es menor o igual a cero, marcar como pagado
        if credito.saldo <= 0:
            credito.estado = 'Pagado'
            credito.fecha_pago = datetime.now()
        
        # Registrar el movimiento de caja
        movimiento = MovimientoCaja(
            caja_id=caja_id,
            tipo='Ingreso',
            monto=monto,
            concepto=f'Abono a crédito #{credito.id} de {credito.cliente.nombre}',
            fecha=datetime.now(),
            metodo_pago_id=metodo_pago_id,
            usuario_id=current_user.id,
            referencia=f'Abono #{abono.id}'
        )
        
        db.session.add(abono)
        db.session.add(movimiento)
        db.session.commit()
        
        flash('Abono registrado exitosamente', 'success')
        return redirect(url_for('creditos.detalle', id=id))
    
    # Cargar las cajas disponibles
    cajas = Caja.query.filter_by(activo=True).all()
    
    # Cargar los métodos de pago disponibles
    metodos_pago = MetodoPago.query.filter_by(activo=True).all()
    
    return render_template('creditos/abonar.html', 
                          credito=credito, 
                          cajas=cajas, 
                          metodos_pago=metodos_pago)
