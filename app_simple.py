# app_simple.py

import os
import datetime
from decimal import Decimal
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, SelectField, DecimalField, IntegerField, DateField, HiddenField
from wtforms.validators import DataRequired, Email, Length, Optional, NumberRange
from sqlalchemy import func, desc, or_
import pytz
from datetime import datetime, timedelta, date

# Importar funciones de formateo
from formatters import formatear_numero_python, desformatear_numero_python

# Inicialización de la aplicación
app = Flask(__name__)
app.config['SECRET_KEY'] = 'clave-secreta-muy-segura'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///credito_app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['TIMEZONE'] = 'America/Bogota'  # Ajustar a tu zona horaria
app.config['MORA_PORCENTAJE'] = Decimal('5')  # Porcentaje de mora para créditos vencidos

# Inicialización de la base de datos
db = SQLAlchemy(app)

# Inicialización del login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Configuración de Jinja para usar las funciones de formateo
@app.template_filter('formatear_numero')
def formatear_numero_filter(valor, decimales=0):
    return formatear_numero_python(valor, decimales)

# Función para obtener la fecha y hora actual en la zona horaria configurada
def now():
    utc_now = datetime.utcnow()
    if app.config.get('TIMEZONE'):
        try:
            local_tz = pytz.timezone(app.config.get('TIMEZONE'))
            return utc_now.replace(tzinfo=pytz.utc).astimezone(local_tz)
        except Exception as e:
            print(f"Error al convertir zona horaria: {e}")
    return utc_now

# Modelos de la base de datos
class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    rol = db.Column(db.String(20), default='usuario')  # admin, usuario, cobrador, vendedor
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    documento = db.Column(db.String(20), unique=True, nullable=False)
    telefono = db.Column(db.String(20))
    email = db.Column(db.String(100))
    direccion = db.Column(db.String(200))
    notas = db.Column(db.Text)
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    creditos = db.relationship('Credito', backref='cliente', lazy=True)

class Vendedor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    documento = db.Column(db.String(20), unique=True, nullable=False)
    telefono = db.Column(db.String(20))
    email = db.Column(db.String(100))
    direccion = db.Column(db.String(200))
    porcentaje_comision = db.Column(db.Numeric(5, 2), default=0)
    notas = db.Column(db.Text)
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    creditos = db.relationship('Credito', backref='vendedor', lazy=True)
    comisiones = db.relationship('Comision', backref='vendedor', lazy=True)

class Categoria(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)
    descripcion = db.Column(db.String(200))

    productos = db.relationship('Producto', backref='categoria', lazy=True)

class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20), unique=True, nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    precio = db.Column(db.Numeric(10, 2), nullable=False)
    stock = db.Column(db.Integer, default=0)
    stock_minimo = db.Column(db.Integer, default=5)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categoria.id'))
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    movimientos = db.relationship('MovimientoInventario', backref='producto', lazy=True)
    items_credito = db.relationship('ItemCredito', backref='producto', lazy=True)

class MovimientoInventario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # entrada, salida, ajuste
    cantidad = db.Column(db.Integer, nullable=False)
    stock_anterior = db.Column(db.Integer, nullable=False)
    stock_nuevo = db.Column(db.Integer, nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    notas = db.Column(db.Text)

    usuario = db.relationship('Usuario', backref='movimientos_inventario')

class MetodoPago(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)
    descripcion = db.Column(db.String(200))
    activo = db.Column(db.Boolean, default=True)

    pagos = db.relationship('Pago', backref='metodo_pago', lazy=True)
    movimientos_caja = db.relationship('MovimientoCaja', backref='metodo_pago', lazy=True)

class Caja(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)
    descripcion = db.Column(db.String(200))
    saldo_inicial = db.Column(db.Numeric(10, 2), default=0)
    saldo_actual = db.Column(db.Numeric(10, 2), default=0)
    activa = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    movimientos = db.relationship('MovimientoCaja', backref='caja', lazy=True)

class MovimientoCaja(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    caja_id = db.Column(db.Integer, db.ForeignKey('caja.id'), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # ingreso, egreso
    concepto = db.Column(db.String(200), nullable=False)
    monto = db.Column(db.Numeric(10, 2), nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    metodo_pago_id = db.Column(db.Integer, db.ForeignKey('metodo_pago.id'))
    referencia = db.Column(db.String(100))  # Para relacionar con pagos, comisiones, etc.
    notas = db.Column(db.Text)
    anulado = db.Column(db.Boolean, default=False)

    usuario = db.relationship('Usuario', backref='movimientos_caja')

class Credito(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    vendedor_id = db.Column(db.Integer, db.ForeignKey('vendedor.id'))
    monto_total = db.Column(db.Numeric(10, 2), nullable=False)
    saldo_pendiente = db.Column(db.Numeric(10, 2), nullable=False)
    tasa_interes = db.Column(db.Numeric(5, 2), default=0)
    numero_cuotas = db.Column(db.Integer, default=1)
    periodo_pago = db.Column(db.String(20), default='mensual')  # diario, semanal, quincenal, mensual
    estado = db.Column(db.String(20), default='pendiente')  # pendiente, pagado, vencido
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_primer_pago = db.Column(db.DateTime)
    notas = db.Column(db.Text)

    items = db.relationship('ItemCredito', backref='credito', lazy=True)
    pagos = db.relationship('Pago', backref='credito', lazy=True)
    plan_pagos = db.relationship('PlanPago', backref='credito', lazy=True)

class ItemCredito(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    credito_id = db.Column(db.Integer, db.ForeignKey('credito.id'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Numeric(10, 2), nullable=False)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)

class Pago(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    credito_id = db.Column(db.Integer, db.ForeignKey('credito.id'), nullable=False)
    monto = db.Column(db.Numeric(10, 2), nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    metodo_pago_id = db.Column(db.Integer, db.ForeignKey('metodo_pago.id'))
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    notas = db.Column(db.Text)

    usuario = db.relationship('Usuario', backref='pagos')

class PlanPago(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    credito_id = db.Column(db.Integer, db.ForeignKey('credito.id'), nullable=False)
    numero_cuota = db.Column(db.Integer, nullable=False)
    fecha_vencimiento = db.Column(db.DateTime, nullable=False)
    monto = db.Column(db.Numeric(10, 2), nullable=False)
    pagada = db.Column(db.Boolean, default=False)
    fecha_pago = db.Column(db.DateTime)

class Comision(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vendedor_id = db.Column(db.Integer, db.ForeignKey('vendedor.id'), nullable=False)
    periodo = db.Column(db.String(20), nullable=False)  # Ej: "2023-01", "2023-Q1", etc.
    monto = db.Column(db.Numeric(10, 2), nullable=False)
    estado = db.Column(db.String(20), default='pendiente')  # pendiente, pagado
    fecha_calculo = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_pago = db.Column(db.DateTime)
    notas = db.Column(db.Text)

# Formularios
class LoginForm(FlaskForm):
    username = StringField('Usuario', validators=[DataRequired()])  # Cambiar de email a username
    password = PasswordField('Contraseña', validators=[DataRequired()])
    remember_me = BooleanField('Recordarme')
    submit = SubmitField('Iniciar Sesión')

class UsuarioForm(FlaskForm):
    nombre = StringField('Nombre', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=100)])
    password = PasswordField('Contraseña', validators=[Length(min=6, max=100)])
    confirm_password = PasswordField('Confirmar Contraseña', validators=[Length(min=6, max=100)])  # Agregar esta línea
    rol = SelectField('Rol', choices=[('admin', 'Administrador'), ('usuario', 'Usuario'), ('cobrador', 'Cobrador'), ('vendedor', 'Vendedor')])
    activo = BooleanField('Activo', default=True)
    submit = SubmitField('Guardar')

class ClienteForm(FlaskForm):
    nombre = StringField('Nombre', validators=[DataRequired(), Length(min=2, max=100)])
    documento = StringField('Documento', validators=[DataRequired(), Length(min=5, max=20)])
    telefono = StringField('Teléfono', validators=[Length(max=20)])
    email = StringField('Email', validators=[Optional(), Email(), Length(max=100)])
    direccion = StringField('Dirección', validators=[Length(max=200)])
    notas = TextAreaField('Notas')
    activo = BooleanField('Activo', default=True)
    submit = SubmitField('Guardar')

class VendedorForm(FlaskForm):
    nombre = StringField('Nombre', validators=[DataRequired(), Length(min=2, max=100)])
    documento = StringField('Documento', validators=[DataRequired(), Length(min=5, max=20)])
    telefono = StringField('Teléfono', validators=[Length(max=20)])
    email = StringField('Email', validators=[Optional(), Email(), Length(max=100)])
    direccion = StringField('Dirección', validators=[Length(max=200)])
    porcentaje_comision = DecimalField('Porcentaje de Comisión (%)', validators=[NumberRange(min=0, max=100)], default=0)
    notas = TextAreaField('Notas')
    activo = BooleanField('Activo', default=True)
    submit = SubmitField('Guardar')

class ProductoForm(FlaskForm):
    codigo = StringField('Código', validators=[DataRequired(), Length(min=2, max=20)])
    nombre = StringField('Nombre', validators=[DataRequired(), Length(min=2, max=100)])
    descripcion = TextAreaField('Descripción')
    precio = StringField('Precio', validators=[DataRequired()])
    stock = IntegerField('Stock', validators=[NumberRange(min=0)], default=0)
    stock_minimo = IntegerField('Stock Mínimo', validators=[NumberRange(min=0)], default=5)
    categoria_id = SelectField('Categoría', coerce=int, validators=[Optional()])
    activo = BooleanField('Activo', default=True)
    submit = SubmitField('Guardar')

class MovimientoInventarioForm(FlaskForm):
    producto_id = SelectField('Producto', coerce=int, validators=[DataRequired()])
    tipo = SelectField('Tipo', choices=[('entrada', 'Entrada'), ('salida', 'Salida'), ('ajuste', 'Ajuste')], validators=[DataRequired()])
    cantidad = IntegerField('Cantidad', validators=[DataRequired(), NumberRange(min=1)])
    fecha = DateField('Fecha', validators=[DataRequired()], default=date.today)
    notas = TextAreaField('Notas')
    submit = SubmitField('Guardar')

class MetodoPagoForm(FlaskForm):
    nombre = StringField('Nombre', validators=[DataRequired(), Length(min=2, max=50)])
    descripcion = TextAreaField('Descripción')
    activo = BooleanField('Activo', default=True)
    submit = SubmitField('Guardar')

class CajaForm(FlaskForm):
    nombre = StringField('Nombre', validators=[DataRequired(), Length(min=2, max=50)])
    descripcion = TextAreaField('Descripción')
    saldo_inicial = StringField('Saldo Inicial', validators=[DataRequired()])
    activa = BooleanField('Activa', default=True)
    submit = SubmitField('Guardar')

class MovimientoCajaForm(FlaskForm):
    caja_id = SelectField('Caja', coerce=int, validators=[DataRequired()])
    tipo = SelectField('Tipo', choices=[('ingreso', 'Ingreso'), ('egreso', 'Egreso')], validators=[DataRequired()])
    concepto = StringField('Concepto', validators=[DataRequired(), Length(min=2, max=200)])
    monto = StringField('Monto', validators=[DataRequired()])
    fecha = DateField('Fecha', validators=[DataRequired()], default=date.today)
    metodo_pago_id = SelectField('Método de Pago', coerce=int, validators=[Optional()])
    referencia = StringField('Referencia', validators=[Length(max=100)])
    notas = TextAreaField('Notas')
    submit = SubmitField('Guardar')

class CreditoForm(FlaskForm):
    cliente_id = HiddenField('Cliente ID', validators=[DataRequired()])
    items_json = HiddenField('Items JSON')  # Agregar esta línea
    monto_total = HiddenField('Monto Total')  # Agregar esta línea
    vendedor_id = SelectField('Vendedor', coerce=int, validators=[DataRequired()])
    monto_inicial = StringField('Abono Inicial', default='0')  # Agregar si no existe
    tasa_interes = DecimalField('Tasa de Interés (%)', validators=[NumberRange(min=0, max=100)], default=0)
    numero_cuotas = IntegerField('Número de Cuotas', validators=[NumberRange(min=1)], default=1)
    periodo_pago = SelectField('Periodo de Pago', choices=[
        ('diario', 'Diario'),
        ('semanal', 'Semanal'),
        ('quincenal', 'Quincenal'),
        ('mensual', 'Mensual')
    ], default='mensual')
    fecha_primer_pago = DateField('Fecha Primer Pago', validators=[DataRequired()], default=lambda: date.today() + timedelta(days=30))
    notas = TextAreaField('Notas')
    submit = SubmitField('Crear Crédito')

class PagoForm(FlaskForm):
    monto = StringField('Monto', validators=[DataRequired()])
    metodo_pago_id = SelectField('Método de Pago', coerce=int, validators=[DataRequired()])
    fecha = DateField('Fecha', validators=[DataRequired()], default=date.today)
    notas = TextAreaField('Notas')
    submit = SubmitField('Registrar Pago')

# Funciones auxiliares
@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

def calcular_estado_credito(credito):
    """Calcula el estado de un crédito basado en sus pagos y fechas."""
    if credito.saldo_pendiente <= 0:
        return 'pagado'

    # Verificar si hay cuotas vencidas
    # Asegúrate de importar datetime si no está ya importado globalmente
    from datetime import datetime
    hoy = datetime.now() # O usa la función now() si la tienes definida
    # Asumiendo que credito.plan_pagos es la relación correcta
    if hasattr(credito, 'plan_pagos'):
        for plan in credito.plan_pagos:
            # Asegúrate que plan.fecha_vencimiento es un objeto datetime
            if not plan.pagada and isinstance(plan.fecha_vencimiento, datetime) and plan.fecha_vencimiento < hoy:
                return 'vencido'
            # Manejo por si no es datetime (opcional, depende de tu modelo)
            elif not plan.pagada and not isinstance(plan.fecha_vencimiento, datetime):
                 print(f"Advertencia: fecha_vencimiento no es datetime para plan {plan.id}") # Log para depurar

    return 'pendiente'

    nuevo_estado = calcular_estado_credito(credito)
    if credito.estado != nuevo_estado:
        credito.estado = nuevo_estado
        db.session.commit()

def generar_plan_pagos(credito):
    # Limpiar plan de pagos existente
    PlanPago.query.filter_by(credito_id=credito.id).delete()

    # Calcular monto de cada cuota
    monto_cuota = credito.monto_total / credito.numero_cuotas

    # Generar fechas de vencimiento según el periodo de pago
    fecha_vencimiento = credito.fecha_primer_pago
    for i in range(1, credito.numero_cuotas + 1):
        plan = PlanPago(
            credito_id=credito.id,
            numero_cuota=i,
            fecha_vencimiento=fecha_vencimiento,
            monto=monto_cuota,
            pagada=False
        )
        db.session.add(plan)

        # Calcular siguiente fecha de vencimiento
        if credito.periodo_pago == 'diario':
            fecha_vencimiento = fecha_vencimiento + timedelta(days=1)
        elif credito.periodo_pago == 'semanal':
            fecha_vencimiento = fecha_vencimiento + timedelta(weeks=1)
        elif credito.periodo_pago == 'quincenal':
            fecha_vencimiento = fecha_vencimiento + timedelta(days=15)
        else:  # mensual
            # Avanzar un mes
            mes = fecha_vencimiento.month + 1
            año = fecha_vencimiento.year
            if mes > 12:
                mes = 1
                año += 1
            # Ajustar día si es necesario (ej. 31 de enero -> 28/29 de febrero)
            dia = min(fecha_vencimiento.day, [31, 29 if año % 4 == 0 and (año % 100 != 0 or año % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][mes-1])
            fecha_vencimiento = fecha_vencimiento.replace(year=año, month=mes, day=dia)

    db.session.commit()

def actualizar_cuotas_pagadas(credito_id):
    credito = Credito.query.get(credito_id)
    if not credito:
        return

    # Obtener total pagado
    total_pagado = sum(pago.monto for pago in credito.pagos if not getattr(pago, 'anulado', False))

    # Marcar cuotas como pagadas
    monto_acumulado = Decimal('0')
    for cuota in sorted(credito.plan_pagos, key=lambda x: x.numero_cuota):
        monto_acumulado += cuota.monto
        cuota.pagada = monto_acumulado <= total_pagado

    db.session.commit()

def calcular_mora(credito):
    # Calcular mora (ej. 5% del saldo si está vencido)
    if calcular_estado_credito(credito) == 'Vencido':
        porcentaje_mora = app.config.get('MORA_PORCENTAJE', Decimal('5'))
        mora = (credito.saldo_pendiente * porcentaje_mora / Decimal('100')).quantize(Decimal('0.01'))
        return mora
    return Decimal('0')

# Rutas de autenticación
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        # Cambiar de email a username
        usuario = Usuario.query.filter_by(username=form.username.data).first()
        if usuario and usuario.check_password(form.password.data) and usuario.activo:
            login_user(usuario, remember=form.remember_me.data)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        flash('Usuario o contraseña incorrectos', 'danger')

    return render_template('auth/login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/perfil')
@login_required
def perfil():
    return render_template('auth/perfil.html')

# Rutas de administración
@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():
    try:
        # --- Calcular datos para el diccionario resumen ---
        creditos_activos = Credito.query.filter(Credito.saldo_pendiente > 0, Credito.estado != 'Pagado').count()
        # Usamos coalesce para asegurarnos de que si no hay créditos, el resultado sea 0
        saldo_total_pendiente = db.session.query(func.coalesce(func.sum(Credito.saldo_pendiente), Decimal(0)))\
                                        .filter(Credito.saldo_pendiente > 0, Credito.estado != 'Pagado').scalar()
        clientes_activos = Cliente.query.filter_by(activo=True).count()
        # Puedes añadir más cálculos aquí si tu plantilla los necesita dentro de 'resumen'
        # total_creditos = Credito.query.count() # Si también lo necesitas

        resumen = {
            'creditos_activos': creditos_activos,
            'saldo_total_pendiente': saldo_total_pendiente,
            'clientes_activos': clientes_activos
            # 'total_creditos': total_creditos # Descomenta si lo necesitas
        }
        # --- Fin del cálculo del resumen ---

        # --- Datos adicionales (fuera del resumen) ---
        # Créditos recientes (estos se mantienen como estaban)
        creditos_recientes = Credito.query.order_by(Credito.fecha_creacion.desc()).limit(5).all()
        # Pagos recientes (estos se mantienen como estaban)
        pagos_recientes = Pago.query.order_by(Pago.fecha.desc()).limit(5).all()
        # --- Fin de datos adicionales ---

    except Exception as e:
        print(f"Error calculando datos del dashboard: {e}")
        flash("Error al cargar los datos del dashboard.", "danger")
        # En caso de error, pasa valores por defecto o vacíos
        resumen = {
            'creditos_activos': 0,
            'saldo_total_pendiente': Decimal(0),
            'clientes_activos': 0
        }
        creditos_recientes = []
        pagos_recientes = []

    # Pasar el diccionario 'resumen' y las listas a la plantilla
    return render_template('admin/dashboard.html',
                           resumen=resumen,
                           creditos_recientes=creditos_recientes,
                           pagos_recientes=pagos_recientes)

@app.route('/usuarios')
@login_required
def usuarios():
    if current_user.rol != 'admin':
        flash('No tienes permiso para acceder a esta página', 'danger')
        return redirect(url_for('dashboard'))

    usuarios = Usuario.query.all()
    return render_template('admin/usuarios.html', usuarios=usuarios)

@app.route('/crear_usuario', methods=['GET', 'POST'])
@login_required
def crear_usuario():
    if current_user.rol != 'admin':
        flash('No tienes permiso para acceder a esta página', 'danger')
        return redirect(url_for('dashboard'))

    form = UsuarioForm()
    if form.validate_on_submit():
        usuario = Usuario(
            nombre=form.nombre.data,
            email=form.email.data,
            rol=form.rol.data,
            activo=form.activo.data
        )
        usuario.set_password(form.password.data)
        db.session.add(usuario)
        db.session.commit()
        flash('Usuario creado correctamente', 'success')
        return redirect(url_for('usuarios'))

    return render_template('admin/form_usuario.html', form=form)

@app.route('/editar_usuario/<int:usuario_id>', methods=['GET', 'POST'])
@login_required
def editar_usuario(usuario_id):
    if current_user.rol != 'admin':
        flash('No tienes permiso para acceder a esta página', 'danger')
        return redirect(url_for('dashboard'))

    usuario = Usuario.query.get_or_404(usuario_id)
    form = UsuarioForm(obj=usuario)

    if form.validate_on_submit():
        usuario.nombre = form.nombre.data
        usuario.email = form.email.data
        usuario.rol = form.rol.data
        usuario.activo = form.activo.data

        if form.password.data:
            usuario.set_password(form.password.data)

        db.session.commit()
        flash('Usuario actualizado correctamente', 'success')
        return redirect(url_for('usuarios'))

    return render_template('admin/form_usuario.html', form=form, usuario=usuario)

@app.route('/activar_usuario/<int:usuario_id>')
@login_required
def activar_usuario(usuario_id):
    if current_user.rol != 'admin':
        flash('No tienes permiso para acceder a esta página', 'danger')
        return redirect(url_for('dashboard'))

    usuario = Usuario.query.get_or_404(usuario_id)
    usuario.activo = True
    db.session.commit()
    flash('Usuario activado correctamente', 'success')
    return redirect(url_for('usuarios'))

@app.route('/desactivar_usuario/<int:usuario_id>')
@login_required
def desactivar_usuario(usuario_id):
    if current_user.rol != 'admin':
        flash('No tienes permiso para acceder a esta página', 'danger')
        return redirect(url_for('dashboard'))

    if usuario_id == current_user.id:
        flash('No puedes desactivar tu propio usuario', 'danger')
        return redirect(url_for('usuarios'))

    usuario = Usuario.query.get_or_404(usuario_id)
    usuario.activo = False
    db.session.commit()
    flash('Usuario desactivado correctamente', 'success')
    return redirect(url_for('usuarios'))

# Rutas de clientes
@app.route('/clientes')
@login_required
def clientes():
    page = request.args.get('page', 1, type=int)
    q = request.args.get('q', '')

    query = Cliente.query

    if q:
        query = query.filter(or_(
            Cliente.nombre.ilike(f'%{q}%'),
            Cliente.documento.ilike(f'%{q}%'),
            Cliente.telefono.ilike(f'%{q}%')
        ))

    pagination = query.order_by(Cliente.nombre).paginate(page=page, per_page=10)

    return render_template('clientes/clientes.html', pagination=pagination, q=q)

@app.route('/crear_cliente', methods=['GET', 'POST'])
@login_required
def crear_cliente():
    form = ClienteForm()
    if form.validate_on_submit():
        # Verificar si ya existe un cliente con ese documento
        cliente_existente = Cliente.query.filter_by(documento=form.documento.data).first()
        if cliente_existente:
            flash(f'Ya existe un cliente con el documento {form.documento.data}', 'danger')
            return render_template('clientes/form_cliente.html', form=form)

        # Si no existe, crear el nuevo cliente
        cliente = Cliente(
            nombre=form.nombre.data,
            documento=form.documento.data,
            telefono=form.telefono.data,
            email=form.email.data,
            direccion=form.direccion.data,
            notas=form.notas.data,
            activo=form.activo.data
        )
        db.session.add(cliente)
        db.session.commit()
        flash('Cliente creado correctamente', 'success')
        return redirect(url_for('clientes'))

    return render_template('clientes/form_cliente.html', form=form)

@app.route('/editar_cliente/<int:cliente_id>', methods=['GET', 'POST'])
@login_required
def editar_cliente(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)
    form = ClienteForm(obj=cliente)

    if form.validate_on_submit():
        cliente.nombre = form.nombre.data
        cliente.documento = form.documento.data
        cliente.telefono = form.telefono.data
        cliente.email = form.email.data
        cliente.direccion = form.direccion.data
        cliente.notas = form.notas.data
        cliente.activo = form.activo.data

        db.session.commit()
        flash('Cliente actualizado correctamente', 'success')
        return redirect(url_for('clientes'))

    return render_template('clientes/form_cliente.html', form=form, cliente=cliente)

@app.route('/activar_cliente/<int:cliente_id>')
@login_required
def activar_cliente(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)
    cliente.activo = True
    db.session.commit()
    flash('Cliente activado correctamente', 'success')
    return redirect(url_for('clientes'))

@app.route('/desactivar_cliente/<int:cliente_id>')
@login_required
def desactivar_cliente(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)
    cliente.activo = False
    db.session.commit()
    flash('Cliente desactivado correctamente', 'success')
    return redirect(url_for('clientes'))

@app.route('/buscar_clientes')
@login_required
def buscar_clientes():
    q = request.args.get('q', '')
    if len(q) < 2:
        return jsonify([])

    clientes = Cliente.query.filter(
        or_(
            Cliente.nombre.ilike(f'%{q}%'),
            Cliente.documento.ilike(f'%{q}%')
        ),
        Cliente.activo == True
    ).limit(10).all()

    resultados = [{
        'id': c.id,
        'nombre': c.nombre,
        'documento': c.documento,
        'telefono': c.telefono
    } for c in clientes]

    return jsonify(resultados)

# Rutas de créditos
@app.route('/creditos')
@login_required
def creditos():
    page = request.args.get('page', 1, type=int)
    estado = request.args.get('estado', '')
    cliente_id = request.args.get('cliente_id', '')

    query = Credito.query

    if estado:
        query = query.filter(Credito.estado == estado)

    if cliente_id:
        query = query.filter(Credito.cliente_id == cliente_id)

    pagination = query.order_by(Credito.fecha_creacion.desc()).paginate(page=page, per_page=10)

    return render_template('creditos/creditos.html', pagination=pagination, estado=estado)

@app.route('/crear_credito', methods=['GET', 'POST'])
@login_required
def crear_credito():
    form = CreditoForm()
    form.vendedor_id.choices = [(v.id, v.nombre) for v in Vendedor.query.filter_by(activo=True).all()]

    if form.validate_on_submit():
        # Obtener datos del carrito desde el formulario
        items_json = request.form.get('items_json', '[]')
        import json
        items_data = json.loads(items_json)

        if not items_data:
            flash('Debe agregar al menos un producto al crédito', 'danger')
            return render_template('creditos/crear_credito.html', form=form)

        # Calcular monto total
        monto_total = sum(float(item['subtotal']) for item in items_data)

        # Crear el crédito
        credito = Credito(
            cliente_id=form.cliente_id.data,
            vendedor_id=form.vendedor_id.data,
            monto_total=monto_total,
            saldo_pendiente=monto_total,
            tasa_interes=form.tasa_interes.data,
            numero_cuotas=form.numero_cuotas.data,
            periodo_pago=form.periodo_pago.data,
            fecha_primer_pago=form.fecha_primer_pago.data,
            notas=form.notas.data,
            estado='Pendiente'
        )
        db.session.add(credito)
        db.session.flush()  # Para obtener el ID del crédito

        # Crear los items del crédito
        for item_data in items_data:
            item = ItemCredito(
                credito_id=credito.id,
                producto_id=item_data['producto_id'],
                cantidad=item_data['cantidad'],
                precio_unitario=item_data['precio'],
                subtotal=item_data['subtotal']
            )
            db.session.add(item)

            # Actualizar stock del producto
            producto = Producto.query.get(item_data['producto_id'])
            if producto:
                stock_anterior = producto.stock
                producto.stock = max(0, producto.stock - item_data['cantidad'])

                # Registrar movimiento de inventario
                movimiento = MovimientoInventario(
                    producto_id=producto.id,
                    tipo='salida',
                    cantidad=item_data['cantidad'],
                    stock_anterior=stock_anterior,
                    stock_nuevo=producto.stock,
                    usuario_id=current_user.id,
                    notas=f'Venta en crédito #{credito.id}'
                )
                db.session.add(movimiento)

        # Generar plan de pagos
        db.session.commit()  # Guardar para obtener el ID del crédito
        generar_plan_pagos(credito)

        flash('Crédito creado correctamente', 'success')
        return redirect(url_for('detalle_credito', credito_id=credito.id))

    return render_template('creditos/crear_credito.html', form=form)

@app.route('/detalle_credito/<int:credito_id>')
@login_required
def detalle_credito(credito_id):
    credito = Credito.query.get_or_404(credito_id)

    # Actualizar estado del crédito
    actualizar_estado_credito(credito_id)

    # Calcular mora si aplica
    mora = calcular_mora(credito)

    return render_template('creditos/detalle_credito.html', credito=credito, mora=mora, now=now())

@app.route('/abonar/<int:credito_id>', methods=['GET', 'POST'])
@login_required
def abonar(credito_id):
    credito = Credito.query.get_or_404(credito_id)

    # Verificar si el crédito ya está pagado
    if credito.estado == 'Pagado':
        flash('Este crédito ya está pagado', 'info')
        return redirect(url_for('detalle_credito', credito_id=credito_id))

    form = PagoForm()
    form.metodo_pago_id.choices = [(m.id, m.nombre) for m in MetodoPago.query.filter_by(activo=True).all()]

    if form.validate_on_submit():
        # Convertir monto a Decimal
        monto = Decimal(desformatear_numero_python(form.monto.data))

        # Verificar que el monto no sea mayor al saldo pendiente
        if monto > credito.saldo_pendiente:
            flash(f'El monto no puede ser mayor al saldo pendiente ({formatear_numero_python(credito.saldo_pendiente, 0)})', 'danger')
            return render_template('creditos/abonar.html', form=form, credito=credito)

        # Crear el pago
        pago = Pago(
            credito_id=credito_id,
            monto=monto,
            fecha=form.fecha.data,
            metodo_pago_id=form.metodo_pago_id.data,
            usuario_id=current_user.id,
            notas=form.notas.data
        )
        db.session.add(pago)

        # Actualizar saldo pendiente
        credito.saldo_pendiente -= monto

        # Registrar movimiento en caja
        metodo_pago = MetodoPago.query.get(form.metodo_pago_id.data)
        # Buscar una caja activa
        caja = Caja.query.filter_by(activa=True).first()
        if caja:
            movimiento = MovimientoCaja(
                caja_id=caja.id,
                tipo='ingreso',
                concepto=f'Abono a crédito #{credito_id}',
                monto=monto,
                fecha=form.fecha.data,
                usuario_id=current_user.id,
                metodo_pago_id=form.metodo_pago_id.data,
                referencia=f'Pago #{pago.id}',
                notas=f'Cliente: {credito.cliente.nombre}'
            )
            db.session.add(movimiento)

            # Actualizar saldo de la caja
            caja.saldo_actual += monto

        db.session.commit()

        # Actualizar cuotas pagadas
        actualizar_cuotas_pagadas(credito_id)

        # Actualizar estado del crédito
        actualizar_estado_credito(credito_id)

        flash('Pago registrado correctamente', 'success')
        return redirect(url_for('detalle_credito', credito_id=credito_id))

    # Calcular mora si aplica
    mora = calcular_mora(credito)

    return render_template('creditos/abonar.html', form=form, credito=credito, mora=mora)

@app.route('/buscar_productos')
@login_required
def buscar_productos():
    q = request.args.get('q', '')
    if len(q) < 2:
        return jsonify([])

    productos = Producto.query.filter(
        or_(
            Producto.nombre.ilike(f'%{q}%'),
            Producto.codigo.ilike(f'%{q}%')
        ),
        Producto.activo == True,
        Producto.stock > 0
    ).limit(10).all()

    resultados = [{
        'id': p.id,
        'nombre': p.nombre,
        'codigo': p.codigo,
        'precio': float(p.precio),
        'stock': p.stock
    } for p in productos]

    return jsonify(resultados)

# Rutas de inventario
@app.route('/inventario')
@login_required
def inventario():
    page = request.args.get('page', 1, type=int)
    q = request.args.get('q', '')
    categoria = request.args.get('categoria', '')
    stock = request.args.get('stock', '')

    query = Producto.query

    if q:
        query = query.filter(or_(
            Producto.nombre.ilike(f'%{q}%'),
            Producto.codigo.ilike(f'%{q}%')
        ))

    if categoria:
        query = query.filter(Producto.categoria_id == categoria)

    if stock == 'disponible':
        query = query.filter(Producto.stock > 0)
    elif stock == 'agotado':
        query = query.filter(Producto.stock == 0)
    elif stock == 'bajo':
        query = query.filter(Producto.stock > 0, Producto.stock <= Producto.stock_minimo)

    pagination = query.order_by(Producto.nombre).paginate(page=page, per_page=10)
    categorias = Categoria.query.all()

    return render_template('inventario/inventario.html', pagination=pagination, categorias=categorias, q=q, categoria=categoria, stock=stock)

@app.route('/crear_producto', methods=['GET', 'POST'])
@login_required
def crear_producto():
    form = ProductoForm()
    form.categoria_id.choices = [(0, 'Sin categoría')] + [(c.id, c.nombre) for c in Categoria.query.all()]

    if form.validate_on_submit():
        # Convertir precio a Decimal
        precio = Decimal(desformatear_numero_python(form.precio.data))

        producto = Producto(
            codigo=form.codigo.data,
            nombre=form.nombre.data,
            descripcion=form.descripcion.data,
            precio=precio,
            stock=form.stock.data,
            stock_minimo=form.stock_minimo.data,
            categoria_id=form.categoria_id.data if form.categoria_id.data != 0 else None,
            activo=form.activo.data
        )
        db.session.add(producto)

        # Si hay stock inicial, registrar movimiento
        if form.stock.data > 0:
            movimiento = MovimientoInventario(
                producto_id=producto.id,
                tipo='entrada',
                cantidad=form.stock.data,
                stock_anterior=0,
                stock_nuevo=form.stock.data,
                usuario_id=current_user.id,
                notas='Stock inicial'
            )
            db.session.add(movimiento)

        db.session.commit()
        flash('Producto creado correctamente', 'success')
        return redirect(url_for('inventario'))

    return render_template('inventario/crear.html', form=form)

@app.route('/editar_producto/<int:producto_id>', methods=['GET', 'POST'])
@login_required
def editar_producto(producto_id):
    producto = Producto.query.get_or_404(producto_id)
    form = ProductoForm(obj=producto)
    form.categoria_id.choices = [(0, 'Sin categoría')] + [(c.id, c.nombre) for c in Categoria.query.all()]

    # Formatear precio para mostrar
    if request.method == 'GET':
        form.precio.data = formatear_numero_python(producto.precio, 0)

    if form.validate_on_submit():
        # Convertir precio a Decimal
        precio = Decimal(desformatear_numero_python(form.precio.data))

        producto.codigo = form.codigo.data
        producto.nombre = form.nombre.data
        producto.descripcion = form.descripcion.data
        producto.precio = precio
        producto.stock_minimo = form.stock_minimo.data
        producto.categoria_id = form.categoria_id.data if form.categoria_id.data != 0 else None
        producto.activo = form.activo.data

        db.session.commit()
        flash('Producto actualizado correctamente', 'success')
        return redirect(url_for('inventario'))

    return render_template('inventario/form_producto.html', form=form, producto=producto)

@app.route('/activar_producto/<int:producto_id>')
@login_required
def activar_producto(producto_id):
    producto = Producto.query.get_or_404(producto_id)
    producto.activo = True
    db.session.commit()
    flash('Producto activado correctamente', 'success')
    return redirect(url_for('inventario'))

@app.route('/desactivar_producto/<int:producto_id>')
@login_required
def desactivar_producto(producto_id):
    producto = Producto.query.get_or_404(producto_id)
    producto.activo = False
    db.session.commit()
    flash('Producto desactivado correctamente', 'success')
    return redirect(url_for('inventario'))

@app.route('/movimientos_inventario')
@login_required
def movimientos_inventario():
    page = request.args.get('page', 1, type=int)
    producto_id = request.args.get('producto_id', '')
    tipo = request.args.get('tipo', '')
    fecha_desde = request.args.get('fecha_desde', '')
    fecha_hasta = request.args.get('fecha_hasta', '')

    query = MovimientoInventario.query

    if producto_id:
        query = query.filter(MovimientoInventario.producto_id == producto_id)

    if tipo:
        query = query.filter(MovimientoInventario.tipo == tipo)

    if fecha_desde:
        query = query.filter(MovimientoInventario.fecha >= datetime.strptime(fecha_desde, '%Y-%m-%d'))

    if fecha_hasta:
        query = query.filter(MovimientoInventario.fecha <= datetime.strptime(fecha_hasta, '%Y-%m-%d') + timedelta(days=1))

    pagination = query.order_by(MovimientoInventario.fecha.desc()).paginate(page=page, per_page=10)
    productos = Producto.query.filter_by(activo=True).all()

    return render_template('inventario/movimientos.html', pagination=pagination, productos=productos)

@app.route('/crear_movimiento_inventario', methods=['GET', 'POST'])
@app.route('/crear_movimiento_inventario/<int:producto_id>', methods=['GET', 'POST'])
@login_required
def crear_movimiento_inventario(producto_id=None):
    form = MovimientoInventarioForm()
    form.producto_id.choices = [(p.id, f"{p.codigo} - {p.nombre} (Stock: {p.stock})") for p in Producto.query.filter_by(activo=True).all()]

    if producto_id:
        form.producto_id.data = producto_id
        producto = Producto.query.get_or_404(producto_id)
    else:
        producto = None

    if form.validate_on_submit():
        producto = Producto.query.get_or_404(form.producto_id.data)
        stock_anterior = producto.stock

        # Actualizar stock según tipo de movimiento
        if form.tipo.data == 'entrada':
            producto.stock += form.cantidad.data
        elif form.tipo.data == 'salida':
            if producto.stock < form.cantidad.data:
                flash('No hay suficiente stock para realizar esta salida', 'danger')
                return render_template('inventario/crear_movimiento.html', form=form, producto=producto)
            producto.stock -= form.cantidad.data
        else:  # ajuste
            producto.stock = form.cantidad.data

        # Registrar movimiento
        movimiento = MovimientoInventario(
            producto_id=producto.id,
            tipo=form.tipo.data,
            cantidad=form.cantidad.data,
            stock_anterior=stock_anterior,
            stock_nuevo=producto.stock,
            fecha=form.fecha.data,
            usuario_id=current_user.id,
            notas=form.notas.data
        )
        db.session.add(movimiento)
        db.session.commit()

        flash('Movimiento registrado correctamente', 'success')
        return redirect(url_for('movimientos_inventario'))

    return render_template('inventario/crear_movimiento.html', form=form, producto=producto)

# Rutas de finanzas
@app.route('/cajas')
@login_required
def cajas():
    cajas = Caja.query.all()
    return render_template('finanzas/cajas.html', cajas=cajas)

@app.route('/crear_caja', methods=['GET', 'POST'])
@login_required
def crear_caja():
    form = CajaForm()

    if form.validate_on_submit():
        # Convertir saldo inicial a Decimal
        saldo_inicial = Decimal(desformatear_numero_python(form.saldo_inicial.data))

        caja = Caja(
            nombre=form.nombre.data,
            descripcion=form.descripcion.data,
            saldo_inicial=saldo_inicial,
            saldo_actual=saldo_inicial,
            activa=form.activa.data
        )
        db.session.add(caja)
        db.session.commit()

        # Registrar movimiento inicial si el saldo es mayor a cero
        if saldo_inicial > 0:
            movimiento = MovimientoCaja(
                caja_id=caja.id,
                tipo='ingreso',
                concepto='Saldo inicial',
                monto=saldo_inicial,
                usuario_id=current_user.id,
                notas='Creación de caja'
            )
            db.session.add(movimiento)
            db.session.commit()

        flash('Caja creada correctamente', 'success')
        return redirect(url_for('cajas'))

    return render_template('finanzas/form_caja.html', form=form)

@app.route('/editar_caja/<int:caja_id>', methods=['GET', 'POST'])
@login_required
def editar_caja(caja_id):
    caja = Caja.query.get_or_404(caja_id)
    form = CajaForm(obj=caja)

    # No permitir editar saldo inicial
    del form.saldo_inicial

    if form.validate_on_submit():
        caja.nombre = form.nombre.data
        caja.descripcion = form.descripcion.data
        caja.activa = form.activa.data

        db.session.commit()
        flash('Caja actualizada correctamente', 'success')
        return redirect(url_for('cajas'))

    return render_template('finanzas/form_caja.html', form=form, caja=caja)

@app.route('/activar_caja/<int:caja_id>')
@login_required
def activar_caja(caja_id):
    caja = Caja.query.get_or_404(caja_id)
    caja.activa = True
    db.session.commit()
    flash('Caja activada correctamente', 'success')
    return redirect(url_for('cajas'))

@app.route('/desactivar_caja/<int:caja_id>')
@login_required
def desactivar_caja(caja_id):
    caja = Caja.query.get_or_404(caja_id)
    caja.activa = False
    db.session.commit()
    flash('Caja desactivada correctamente', 'success')
    return redirect(url_for('cajas'))

@app.route('/movimientos_caja')
@login_required
def movimientos_caja():
    page = request.args.get('page', 1, type=int)
    caja_id = request.args.get('caja_id', '')
    tipo = request.args.get('tipo', '')
    fecha_desde = request.args.get('fecha_desde', '')
    fecha_hasta = request.args.get('fecha_hasta', '')

    query = MovimientoCaja.query.filter_by(anulado=False)

    if caja_id:
        query = query.filter(MovimientoCaja.caja_id == caja_id)

    if tipo:
        query = query.filter(MovimientoCaja.tipo == tipo)

    if fecha_desde:
        query = query.filter(MovimientoCaja.fecha >= datetime.strptime(fecha_desde, '%Y-%m-%d'))

    if fecha_hasta:
        query = query.filter(MovimientoCaja.fecha <= datetime.strptime(fecha_hasta, '%Y-%m-%d') + timedelta(days=1))

    # Calcular totales
    total_ingresos = db.session.query(func.sum(MovimientoCaja.monto)).filter(
        MovimientoCaja.tipo == 'ingreso',
        MovimientoCaja.anulado == False
    ).scalar() or 0

    total_egresos = db.session.query(func.sum(MovimientoCaja.monto)).filter(
        MovimientoCaja.tipo == 'egreso',
        MovimientoCaja.anulado == False
    ).scalar() or 0

    pagination = query.order_by(MovimientoCaja.fecha.desc()).paginate(page=page, per_page=10)
    cajas = Caja.query.all()

    return render_template('finanzas/movimientos_caja.html',
                          pagination=pagination,
                          cajas=cajas,
                          total_ingresos=total_ingresos,
                          total_egresos=total_egresos)

@app.route('/movimientos_caja/<int:caja_id>')
@login_required
def movimientos_caja_id(caja_id):
    return redirect(url_for('movimientos_caja', caja_id=caja_id))

@app.route('/crear_movimiento_caja', methods=['GET', 'POST'])
def crear_movimiento_caja():
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            caja_id = request.form.get('caja')
            tipo = request.form.get('tipo')
            concepto = request.form.get('concepto')
            monto = request.form.get('monto', '0').replace('.', '').replace(',', '.')
            fecha = request.form.get('fecha')
            notas = request.form.get('notas', '')

            # Validación básica
            if not caja_id or not tipo or not concepto or not monto or not fecha:
                flash('Todos los campos marcados con * son obligatorios', 'danger')
                return redirect(url_for('crear_movimiento_caja'))

            monto = float(monto)

            cursor = mysql.connection.cursor()

            # Manejar transferencia entre cajas
            if tipo == 'transferencia':
                caja_destino_id = request.form.get('caja_destino')

                if not caja_destino_id:
                    flash('Debe seleccionar una caja destino para la transferencia', 'danger')
                    return redirect(url_for('crear_movimiento_caja'))

                if caja_id == caja_destino_id:
                    flash('No puede transferir a la misma caja', 'danger')
                    return redirect(url_for('crear_movimiento_caja'))

                # Registrar egreso en caja origen
                cursor.execute(
                    '''INSERT INTO movimientos_caja
                       (caja_id, tipo, concepto, monto, fecha, notas, usuario_id)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)''',
                    (caja_id, 'egreso', f"Transferencia a {request.form.get('caja_destino_nombre', 'otra caja')}: {concepto}",
                     monto, fecha, notas, session['usuario_id'])
                )

                # Registrar ingreso en caja destino
                cursor.execute(
                    '''INSERT INTO movimientos_caja
                       (caja_id, tipo, concepto, monto, fecha, notas, usuario_id)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)''',
                    (caja_destino_id, 'ingreso', f"Transferencia desde {request.form.get('caja_nombre', 'otra caja')}: {concepto}",
                     monto, fecha, notas, session['usuario_id'])
                )

                flash('Transferencia registrada exitosamente', 'success')
            else:
                # Movimiento normal (ingreso o egreso)
                cursor.execute(
                    '''INSERT INTO movimientos_caja
                       (caja_id, tipo, concepto, monto, fecha, notas, usuario_id)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)''',
                    (caja_id, tipo, concepto, monto, fecha, notas, session['usuario_id'])
                )

                flash('Movimiento registrado exitosamente', 'success')

            mysql.connection.commit()
            cursor.close()

            return redirect(url_for('movimientos_caja'))

        except Exception as e:
            print(f"Error al crear movimiento de caja: {str(e)}")
            flash('Error al crear movimiento de caja', 'danger')
            return redirect(url_for('crear_movimiento_caja'))

    # Para solicitudes GET
    cursor = mysql.connection.cursor()
    cursor.execute('SELECT id, nombre FROM cajas WHERE activa = 1 ORDER BY nombre')
    cajas = cursor.fetchall()
    cursor.close()

    return render_template('crear_movimiento_caja.html', cajas=cajas)

@app.route('/anular_movimiento_caja/<int:movimiento_id>')
@login_required
def anular_movimiento_caja(movimiento_id):
    if current_user.rol != 'admin':
        flash('No tienes permiso para anular movimientos', 'danger')
        return redirect(url_for('movimientos_caja'))

    movimiento = MovimientoCaja.query.get_or_404(movimiento_id)

    # Verificar que el movimiento no esté anulado
    if movimiento.anulado:
        flash('Este movimiento ya está anulado', 'warning')
        return redirect(url_for('movimientos_caja'))

    # Verificar que el movimiento sea del día actual
    if movimiento.fecha.date() != now().date():
        flash('Solo se pueden anular movimientos del día actual', 'danger')
        return redirect(url_for('movimientos_caja'))

    # Anular movimiento
    movimiento.anulado = True

    # Actualizar saldo de la caja
    caja = Caja.query.get(movimiento.caja_id)
    if movimiento.tipo == 'ingreso':
        caja.saldo_actual -= movimiento.monto
    else:
        caja.saldo_actual += movimiento.monto

    db.session.commit()
    flash('Movimiento anulado correctamente', 'success')
    return redirect(url_for('movimientos_caja'))

@app.route('/metodos_pago')
@login_required
def metodos_pago():
    metodos = MetodoPago.query.all()
    return render_template('finanzas/metodos_pago.html', metodos_pago=metodos)

@app.route('/crear_metodo_pago', methods=['GET', 'POST'])
@login_required
def crear_metodo_pago():
    form = MetodoPagoForm()

    if form.validate_on_submit():
        metodo = MetodoPago(
            nombre=form.nombre.data,
            descripcion=form.descripcion.data,
            activo=form.activo.data
        )
        db.session.add(metodo)
        db.session.commit()
        flash('Método de pago creado correctamente', 'success')
        return redirect(url_for('metodos_pago'))

    return render_template('finanzas/form_metodo_pago.html', form=form)

@app.route('/editar_metodo_pago/<int:metodo_id>', methods=['GET', 'POST'])
@login_required
def editar_metodo_pago(metodo_id):
    metodo = MetodoPago.query.get_or_404(metodo_id)
    form = MetodoPagoForm(obj=metodo)

    if form.validate_on_submit():
        metodo.nombre = form.nombre.data
        metodo.descripcion = form.descripcion.data
        metodo.activo = form.activo.data

        db.session.commit()
        flash('Método de pago actualizado correctamente', 'success')
        return redirect(url_for('metodos_pago'))

    return render_template('finanzas/form_metodo_pago.html', form=form, metodo=metodo)

@app.route('/activar_metodo_pago/<int:metodo_id>')
@login_required
def activar_metodo_pago(metodo_id):
    metodo = MetodoPago.query.get_or_404(metodo_id)
    metodo.activo = True
    db.session.commit()
    flash('Método de pago activado correctamente', 'success')
    return redirect(url_for('metodos_pago'))

@app.route('/desactivar_metodo_pago/<int:metodo_id>')
@login_required
def desactivar_metodo_pago(metodo_id):
    metodo = MetodoPago.query.get_or_404(metodo_id)
    metodo.activo = False
    db.session.commit()
    flash('Método de pago desactivado correctamente', 'success')
    return redirect(url_for('metodos_pago'))

@app.route('/vendedores')
@login_required
def vendedores():
    vendedores = Vendedor.query.all()
    return render_template('finanzas/vendedores.html', vendedores=vendedores)

@app.route('/crear_vendedor', methods=['GET', 'POST'])
@login_required
def crear_vendedor():
    form = VendedorForm()

    if form.validate_on_submit():
        vendedor = Vendedor(
            nombre=form.nombre.data,
            documento=form.documento.data,
            telefono=form.telefono.data,
            email=form.email.data,
            direccion=form.direccion.data,
            porcentaje_comision=form.porcentaje_comision.data,
            notas=form.notas.data,
            activo=form.activo.data
        )
        db.session.add(vendedor)
        db.session.commit()
        flash('Vendedor creado correctamente', 'success')
        return redirect(url_for('vendedores'))

    return render_template('finanzas/form_vendedor.html', form=form)

@app.route('/editar_vendedor/<int:vendedor_id>', methods=['GET', 'POST'])
@login_required
def editar_vendedor(vendedor_id):
    vendedor = Vendedor.query.get_or_404(vendedor_id)
    form = VendedorForm(obj=vendedor)

    if form.validate_on_submit():
        vendedor.nombre = form.nombre.data
        vendedor.documento = form.documento.data
        vendedor.telefono = form.telefono.data
        vendedor.email = form.email.data
        vendedor.direccion = form.direccion.data
        vendedor.porcentaje_comision = form.porcentaje_comision.data
        vendedor.notas = form.notas.data
        vendedor.activo = form.activo.data

        db.session.commit()
        flash('Vendedor actualizado correctamente', 'success')
        return redirect(url_for('vendedores'))

    return render_template('finanzas/form_vendedor.html', form=form, vendedor=vendedor)

@app.route('/activar_vendedor/<int:vendedor_id>')
@login_required
def activar_vendedor(vendedor_id):
    vendedor = Vendedor.query.get_or_404(vendedor_id)
    vendedor.activo = True
    db.session.commit()
    flash('Vendedor activado correctamente', 'success')
    return redirect(url_for('vendedores'))

@app.route('/desactivar_vendedor/<int:vendedor_id>')
@login_required
def desactivar_vendedor(vendedor_id):
    vendedor = Vendedor.query.get_or_404(vendedor_id)
    vendedor.activo = False
    db.session.commit()
    flash('Vendedor desactivado correctamente', 'success')
    return redirect(url_for('vendedores'))

@app.route('/comisiones')
@login_required
def comisiones():
    page = request.args.get('page', 1, type=int)
    vendedor_id = request.args.get('vendedor_id', '')
    estado = request.args.get('estado', '')
    periodo = request.args.get('periodo', '')

    query = Comision.query

    if vendedor_id:
        query = query.filter(Comision.vendedor_id == vendedor_id)

    if estado:
        query = query.filter(Comision.estado == estado)

    if periodo:
        query = query.filter(Comision.periodo == periodo)

    pagination = query.order_by(Comision.fecha_calculo.desc()).paginate(page=page, per_page=10)
    vendedores = Vendedor.query.filter_by(activo=True).all()

    # Obtener periodos únicos
    periodos = db.session.query(Comision.periodo).distinct().order_by(Comision.periodo.desc()).all()
    periodos = [p[0] for p in periodos]

    return render_template('finanzas/comisiones.html',
                          pagination=pagination,
                          vendedores=vendedores,
                          periodos=periodos)

@app.route('/calcular_comisiones', methods=['GET', 'POST'])
@login_required
def calcular_comisiones():
    if current_user.rol != 'admin':
        flash('No tienes permiso para calcular comisiones', 'danger')
        return redirect(url_for('comisiones'))

    if request.method == 'POST':
        periodo = request.form.get('periodo')
        fecha_inicio = datetime.strptime(request.form.get('fecha_inicio'), '%Y-%m-%d')
        fecha_fin = datetime.strptime(request.form.get('fecha_fin'), '%Y-%m-%d') + timedelta(days=1)

        # Verificar que no existan comisiones para este periodo
        comisiones_existentes = Comision.query.filter_by(periodo=periodo).first()
        if comisiones_existentes:
            flash(f'Ya existen comisiones calculadas para el periodo {periodo}', 'danger')
            return redirect(url_for('comisiones'))

        # Obtener vendedores activos
        vendedores = Vendedor.query.filter_by(activo=True).all()

        for vendedor in vendedores:
            # Obtener pagos del periodo para créditos vendidos por este vendedor
            pagos = db.session.query(Pago).join(Credito).filter(
                Credito.vendedor_id == vendedor.id,
                Pago.fecha >= fecha_inicio,
                Pago.fecha < fecha_fin
            ).all()

            # Calcular monto total de pagos
            monto_total = sum(pago.monto for pago in pagos)

            # Calcular comisión
            monto_comision = (monto_total * vendedor.porcentaje_comision / 100).quantize(Decimal('0.01'))

            # Crear comisión si hay monto
            if monto_comision > 0:
                comision = Comision(
                    vendedor_id=vendedor.id,
                    periodo=periodo,
                    monto=monto_comision,
                    estado='pendiente',
                    notas=f'Comisión calculada para el periodo {periodo}'
                )
                db.session.add(comision)

        db.session.commit()
        flash('Comisiones calculadas correctamente', 'success')
        return redirect(url_for('comisiones'))

    # Generar periodo actual (mes y año)
    hoy = now()
    periodo_actual = hoy.strftime('%Y-%m')

    # Calcular fechas por defecto (mes actual)
    primer_dia = date(hoy.year, hoy.month, 1)
    if hoy.month == 12:
        ultimo_dia = date(hoy.year + 1, 1, 1) - timedelta(days=1)
    else:
        ultimo_dia = date(hoy.year, hoy.month + 1, 1) - timedelta(days=1)

    return render_template('finanzas/comisiones.html',
                           periodos=[], vendedores=[],
                           periodo_actual=periodo_actual,
                           primer_dia=primer_dia,
                           ultimo_dia=ultimo_dia,
                           show_form=True)

@app.route('/detalle_comision/<int:comision_id>')
@login_required
def detalle_comision(comision_id):
    comision = Comision.query.get_or_404(comision_id)

    # Obtener pagos del periodo para créditos vendidos por este vendedor
    fecha_inicio = comision.fecha_calculo - timedelta(days=30)  # Aproximado, mejorar según lógica real
    fecha_fin = comision.fecha_calculo

    pagos = db.session.query(Pago).join(Credito).filter(
        Credito.vendedor_id == comision.vendedor_id,
        Pago.fecha >= fecha_inicio,
        Pago.fecha < fecha_fin
    ).all()

    return render_template('finanzas/detalle_comision.html', comision=comision, pagos=pagos)

@app.route('/pagar_comision/<int:comision_id>')
@login_required
def pagar_comision(comision_id):
    if current_user.rol != 'admin':
        flash('No tienes permiso para pagar comisiones', 'danger')
        return redirect(url_for('comisiones'))

    comision = Comision.query.get_or_404(comision_id)

    # Verificar que la comisión esté pendiente
    if comision.estado != 'pendiente':
        flash('Esta comisión ya ha sido pagada', 'warning')
        return redirect(url_for('comisiones'))

    # Buscar una caja activa
    caja = Caja.query.filter_by(activa=True).first()
    if not caja:
        flash('No hay cajas activas para registrar el pago', 'danger')
        return redirect(url_for('comisiones'))

    # Verificar que haya suficiente saldo en la caja
    if comision.monto > caja.saldo_actual:
        flash('No hay suficiente saldo en la caja para pagar esta comisión', 'danger')
        return redirect(url_for('comisiones'))

    # Registrar movimiento en caja
    movimiento = MovimientoCaja(
        caja_id=caja.id,
        tipo='egreso',
        concepto=f'Pago de comisión periodo {comision.periodo}',
        monto=comision.monto,
        fecha=now(),
        usuario_id=current_user.id,
        referencia=f'Comisión #{comision.id}',
        notas=f'Vendedor: {comision.vendedor.nombre}'
    )
    db.session.add(movimiento)

    # Actualizar saldo de la caja
    caja.saldo_actual -= comision.monto

    # Marcar comisión como pagada
    comision.estado = 'pagado'
    comision.fecha_pago = now()

    db.session.commit()
    flash('Comisión pagada correctamente', 'success')
    return redirect(url_for('comisiones'))

# Inicialización de la base de datos
@app.before_first_request
def create_tables():
    db.create_all()

    # Crear usuario admin si no existe
    admin = Usuario.query.filter_by(email='admin@example.com').first()
    if not admin:
        admin = Usuario(
            nombre='Administrador',
            email='admin@example.com',
            rol='admin',
            activo=True
        )
        admin.set_password('admin123')
        db.session.add(admin)

        # Crear método de pago efectivo
        efectivo = MetodoPago(
            nombre='Efectivo',
            descripcion='Pago en efectivo',
            activo=True
        )
        db.session.add(efectivo)

        # Crear caja principal
        caja = Caja(
            nombre='Caja Principal',
            descripcion='Caja principal del negocio',
            saldo_inicial=0,
            saldo_actual=0,
            activa=True
        )
        db.session.add(caja)

        db.session.commit()

# Ejecutar la aplicación
if __name__ == '__main__':
    app.run(debug=True)

# Añadir esta línea para que PythonAnywhere pueda encontrar la aplicación
application = app
