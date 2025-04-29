from datetime import datetime
from app import db

class Credito(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    vendedor_id = db.Column(db.Integer, db.ForeignKey('vendedor.id'))
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_vencimiento = db.Column(db.DateTime)
    fecha_pago = db.Column(db.DateTime)
    monto_total = db.Column(db.Integer, nullable=False)
    saldo = db.Column(db.Integer, nullable=False)
    numero_cuotas = db.Column(db.Integer, nullable=False)
    monto_cuota = db.Column(db.Integer, nullable=False)
    tasa_interes = db.Column(db.Float, default=0)
    metodo_calculo = db.Column(db.String(20), default='Cuota Fija')
    estado = db.Column(db.String(20), default='Pendiente')
    notas = db.Column(db.Text)
    ultima_modificacion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    usuario = db.relationship('Usuario', backref='creditos')
    vendedor = db.relationship('Vendedor', backref='creditos')
    items = db.relationship('ItemCredito', backref='credito', lazy='dynamic')
    abonos = db.relationship('Abono', backref='credito', lazy='dynamic')
    
    def __repr__(self):
        return f'<Credito #{self.id} - Cliente: {self.cliente.nombre}>'

class ItemCredito(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    credito_id = db.Column(db.Integer, db.ForeignKey('credito.id'), nullable=False)
    item_inventario_id = db.Column(db.Integer, db.ForeignKey('item_inventario.id'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Integer, nullable=False)
    subtotal = db.Column(db.Integer, nullable=False)
    
    # Relaciones
    item_inventario = db.relationship('ItemInventario', backref='items_credito')
    
    def __repr__(self):
        return f'<ItemCredito {self.item_inventario.nombre} - {self.cantidad}>'

class Abono(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    credito_id = db.Column(db.Integer, db.ForeignKey('credito.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    caja_id = db.Column(db.Integer, db.ForeignKey('caja.id'), nullable=False)
    metodo_pago_id = db.Column(db.Integer, db.ForeignKey('metodo_pago.id'), nullable=False)
    fecha_abono = db.Column(db.DateTime, default=datetime.utcnow)
    monto = db.Column(db.Integer, nullable=False)
    notas = db.Column(db.Text)
    
    # Relaciones
    usuario = db.relationship('Usuario', backref='abonos')
    caja = db.relationship('Caja', backref='abonos')
    metodo_pago = db.relationship('MetodoPago', backref='abonos')
    
    def __repr__(self):
        return f'<Abono #{self.id} - Crédito: {self.credito_id} - Monto: {self.monto}>'
