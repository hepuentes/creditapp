from datetime import datetime
from app import db

# Tabla de asociación para la relación muchos a muchos entre Caja y MetodoPago
caja_metodo_pago = db.Table('caja_metodo_pago',
    db.Column('caja_id', db.Integer, db.ForeignKey('caja.id'), primary_key=True),
    db.Column('metodo_pago_id', db.Integer, db.ForeignKey('metodo_pago.id'), primary_key=True)
)

class Caja(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    saldo_inicial = db.Column(db.Integer, default=0)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    ultima_modificacion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    activo = db.Column(db.Boolean, default=True)
    
    # Relaciones
    metodos_pago = db.relationship('MetodoPago', secondary=caja_metodo_pago, backref='cajas')
    
    def __repr__(self):
        return f'<Caja {self.nombre}>'
    
    @property
    def saldo_actual(self):
        ingresos = sum(m.monto for m in self.movimientos if m.tipo == 'Ingreso')
        egresos = sum(m.monto for m in self.movimientos if m.tipo == 'Egreso')
        return self.saldo_inicial + ingresos - egresos

class MetodoPago(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    activo = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<MetodoPago {self.nombre}>'

class MovimientoCaja(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    caja_id = db.Column(db.Integer, db.ForeignKey('caja.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    metodo_pago_id = db.Column(db.Integer, db.ForeignKey('metodo_pago.id'), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # Ingreso, Egreso
    monto = db.Column(db.Integer, nullable=False)
    concepto = db.Column(db.String(200), nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    referencia = db.Column(db.String(100))
    
    # Relaciones
    caja = db.relationship('Caja', backref='movimientos')
    usuario = db.relationship('Usuario', backref='movimientos_caja')
    metodo_pago = db.relationship('MetodoPago', backref='movimientos')
    
    def __repr__(self):
        return f'<MovimientoCaja {self.tipo} - {self.caja.nombre} - {self.monto}>'

class Vendedor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    comision = db.Column(db.Float, default=0)
    notas = db.Column(db.Text)
    
    def __repr__(self):
        return f'<Vendedor {self.usuario.nombre}>'
