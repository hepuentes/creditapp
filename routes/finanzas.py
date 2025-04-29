from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from app import db
from models.finanzas import Caja, MetodoPago, MovimientoCaja, Vendedor
from models.usuario import Usuario
from models.credito import Credito, Abono
from utils.helpers import admin_required
from utils.formatters import convertir_a_numero

finanzas_bp = Blueprint('finanzas', __name__)

# Rutas para Cajas
@finanzas_bp.route('/finanzas/cajas')
@login_required
@admin_required
def cajas():
    cajas = Caja.query.all()
    return render_template('finanzas/cajas.html', cajas=cajas)

@finanzas_bp.route('/finanzas/cajas/gestionar', methods=['GET', 'POST'])
@finanzas_bp.route('/finanzas/cajas/gestionar/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def gestionar_caja(id=None):
    caja = None
    if id:
        caja = Caja.query.get_or_404(id)
    
    if request.method == 'POST':
        if not caja:
            caja = Caja()
        
        caja.nombre = request.form.get('nombre')
        caja.descripcion = request.form.get('descripcion')
        caja.saldo_inicial = convertir_a_numero(request.form.get('saldo_inicial'))
        caja.activo = True
        
        # Manejar métodos de pago
        metodos_pago_ids = request.form.getlist('metodos_pago')
        metodos_pago = MetodoPago.query.filter(MetodoPago.id.in_(metodos_pago_ids)).all()
        caja.metodos_pago = metodos_pago
        
        if not id:  # Nueva caja
            db.session.add(caja)
        
        db.session.commit()
        flash('Caja guardada exitosamente', 'success')
        return redirect(url_for('finanzas.cajas'))
    
    # Obtener métodos de pago para el formulario
    metodos_pago = MetodoPago.query.filter_by(activo=True).all()
    
    return render_template('finanzas/form_caja.html', 
                          caja=caja, 
                          metodos_pago=metodos_pago)

# Rutas para Métodos de Pago
@finanzas_bp.route('/finanzas/metodos-pago')
@login_required
@admin_required
def metodos_pago():
    metodos = MetodoPago.query.all()
    return render_template('finanzas/metodos_pago.html', metodos=metodos)

@finanzas_bp.route('/finanzas/metodos-pago/gestionar', methods=['GET', 'POST'])
@finanzas_bp.route('/finanzas/metodos-pago/gestionar/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def gestionar_metodo_pago(id=None):
    metodo = None
    if id:
        metodo = MetodoPago.query.get_or_404(id)
    
    if request.method == 'POST':
        if not metodo:
            metodo = MetodoPago()
        
        metodo.nombre = request.form.get('nombre')
        metodo.descripcion = request.form.get('descripcion')
        metodo.activo = True
        
        if not id:  # Nuevo método
            db.session.add(metodo)
        
        db.session.commit()
        flash('Método de pago guardado exitosamente', 'success')
        return redirect(url_for('finanzas.metodos_pago'))
    
    return render_template('finanzas/form_metodo_pago.html', metodo=metodo)

# Rutas para Movimientos de Caja
@finanzas_bp.route('/finanzas/movimientos')
@login_required
@admin_required
def movimientos_caja():
    # Filtros
    tipo = request.args.get('tipo', 'todos')
    caja_id = request.args.get('caja_id')
    
    # Consulta base
    query = MovimientoCaja.query
    
    # Aplicar filtros
    if tipo != 'todos':
        query = query.filter_by(tipo=tipo)
    
    if caja_id:
        query = query.filter_by(caja_id=caja_id)
    
    # Ordenar por fecha (más recientes primero)
    movimientos = query.order_by(MovimientoCaja.fecha.desc()).all()
    
    # Obtener cajas para el filtro
    cajas = Caja.query.filter_by(activo=True).all()
    
    return render_template('finanzas/movimientos_caja.html', 
                          movimientos=movimientos, 
                          cajas=cajas,
                          tipo_filtro=tipo,
                          caja_filtro=caja_id)

@finanzas_bp.route('/finanzas/movimientos/crear', methods=['GET', 'POST'])
@login_required
@admin_required
def crear_movimiento_caja():
    if request.method == 'POST':
        caja_id = request.form.get('caja_id')
        tipo = request.form.get('tipo')
        monto = convertir_a_numero(request.form.get('monto'))
        concepto = request.form.get('concepto')
        metodo_pago_id = request.form.get('metodo_pago_id')
        referencia = request.form.get('referencia')
        
        # Validar monto
        if monto <= 0:
            flash('El monto debe ser mayor que cero', 'danger')
            return redirect(url_for('finanzas.crear_movimiento_caja'))
        
        # Crear el movimiento
        movimiento = MovimientoCaja(
            caja_id=caja_id,
            usuario_id=current_user.id,
            tipo=tipo,
            monto=monto,
            concepto=concepto,
            metodo_pago_id=metodo_pago_id,
            referencia=referencia
        )
        
        db.session.add(movimiento)
        db.session.commit()
        
        flash('Movimiento registrado exitosamente', 'success')
        return redirect(url_for('finanzas.movimientos_caja'))
    
    # Obtener cajas y métodos de pago para el formulario
    cajas = Caja.query.filter_by(activo=True).all()
    metodos_pago = MetodoPago.query.filter_by(activo=True).all()
    
    return render_template('finanzas/crear_movimiento_caja.html', 
                          cajas=cajas, 
                          metodos_pago=metodos_pago)

# Rutas para Vendedores
@finanzas_bp.route('/finanzas/vendedores')
@login_required
@admin_required
def vendedores():
    vendedores = Vendedor.query.join(Usuario).filter(Usuario.activo == True).all()
    return render_template('finanzas/vendedores.html', vendedores=vendedores)

@finanzas_bp.route('/finanzas/vendedores/gestionar', methods=['GET', 'POST'])
@finanzas_bp.route('/finanzas/vendedores/gestionar/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def gestionar_vendedor(id=None):
    vendedor = None
    if id:
        vendedor = Vendedor.query.get_or_404(id)
    
    if request.method == 'POST':
        usuario_id = request.form.get('usuario_id')
        comision = float(request.form.get('comision', '0'))
        notas = request.form.get('notas', '')
        
        # Verificar si ya existe un vendedor para este usuario
        if not id:
            vendedor_existente = Vendedor.query.filter_by(usuario_id=usuario_id).first()
            if vendedor_existente:
                flash('Ya existe un vendedor asociado a este usuario', 'danger')
                return redirect(url_for('finanzas.vendedores'))
        
        if not vendedor:
            vendedor = Vendedor(usuario_id=usuario_id)
        
        vendedor.comision = comision
        vendedor.notas = notas
        
        # Actualizar el rol del usuario
        usuario = Usuario.query.get(usuario_id)
        usuario.es_vendedor = True
        
        if not id:  # Nuevo vendedor
            db.session.add(vendedor)
        
        db.session.commit()
        flash('Vendedor guardado exitosamente', 'success')
        return redirect(url_for('finanzas.vendedores'))
    
    # Obtener usuarios disponibles (que no sean ya vendedores)
    if id:
        usuarios = Usuario.query.filter_by(activo=True).all()
    else:
        subquery = db.session.query(Vendedor.usuario_id)
        usuarios = Usuario.query.filter(
            Usuario.activo == True,
            ~Usuario.id.in_(subquery)
        ).all()
    
    return render_template('finanzas/form_vendedor.html', 
                          vendedor=vendedor, 
                          usuarios=usuarios)

# Rutas para Comisiones
@finanzas_bp.route('/finanzas/comisiones')
@login_required
@admin_required
def comisiones():
    # Filtros
    vendedor_id = request.args.get('vendedor_id')
    periodo = request.args.get('periodo', 'mensual')
    
    # Fechas según el período
    hoy = datetime.now()
    if periodo == 'semanal':
        inicio_periodo = hoy - timedelta(days=hoy.weekday())
    elif periodo == 'quincenal':
        if hoy.day <= 15:
            inicio_periodo = datetime(hoy.year, hoy.month, 1)
        else:
            inicio_periodo = datetime(hoy.year, hoy.month, 16)
    else:  # mensual
        inicio_periodo = datetime(hoy.year, hoy.month, 1)
    
    # Consulta base de vendedores
    vendedores_query = Vendedor.query.join(Usuario).filter(Usuario.activo == True)
    
    if vendedor_id:
        vendedores_query = vendedores_query.filter(Vendedor.id == vendedor_id)
    
    vendedores_lista = vendedores_query.all()
    
    # Calcular comisiones para cada vendedor
    comisiones_data = []
    for vendedor in vendedores_lista:
        # Obtener créditos del vendedor
        creditos = Credito.query.filter_by(vendedor_id=vendedor.id).all()
        
        total_ventas = sum(c.monto_total for c in creditos)
        total_cobrado = 0
        comision_calculada = 0
        
        # Calcular lo cobrado en el período actual
        for credito in creditos:
            abonos_periodo = Abono.query.filter(
                Abono.credito_id == credito.id,
                Abono.fecha_abono >= inicio_periodo
            ).all()
            
            cobrado_periodo = sum(a.monto for a in abonos_periodo)
            total_cobrado += cobrado_periodo
            comision_calculada += cobrado_periodo * (vendedor.comision / 100)
        
        comisiones_data.append({
            'vendedor': vendedor,
            'total_ventas': total_ventas,
            'total_cobrado': total_cobrado,
            'comision_calculada': comision_calculada
        })
    
    return render_template('finanzas/comisiones.html', 
                          comisiones=comisiones_data, 
                          vendedores=vendedores_lista,
                          periodo=periodo,
                          inicio_periodo=inicio_periodo)

# Ruta para liquidar comisiones
@finanzas_bp.route('/finanzas/comisiones/liquidar', methods=['POST'])
@login_required
@admin_required
def liquidar_comision():
    vendedor_id = request.form.get('vendedor_id')
    monto = convertir_a_numero(request.form.get('monto'))
    caja_id = request.form.get('caja_id')
    metodo_pago_id = request.form.get('metodo_pago_id')
    
    # Validar monto
    if monto <= 0:
        flash('El monto debe ser mayor que cero', 'danger')
        return redirect(url_for('finanzas.comisiones'))
    
    # Obtener vendedor
    vendedor = Vendedor.query.get_or_404(vendedor_id)
    
    # Crear movimiento de caja para la liquidación
    movimiento = MovimientoCaja(
        caja_id=caja_id,
        usuario_id=current_user.id,
        tipo='Egreso',
        monto=monto,
        concepto=f'Liquidación de comisiones para {vendedor.usuario.nombre}',
        metodo_pago_id=metodo_pago_id,
        referencia=f'Comisión {datetime.now().strftime("%Y-%m-%d")}'
    )
    
    db.session.add(movimiento)
    db.session.commit()
    
    flash('Comisión liquidada exitosamente', 'success')
    return redirect(url_for('finanzas.comisiones'))
