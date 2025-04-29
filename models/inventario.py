from datetime import datetime
from app import db

class ItemInventario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20), unique=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    precio_costo = db.Column(db.Integer, nullable=False)
    precio_venta = db.Column(db.Integer, nullable=False)
    stock_actual = db.Column(db.Integer, default=0)
    stock_minimo = db.Column(db.Integer, default=0)
    categoria = db.Column(db.String(50))
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    ultima_modificacion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    activo = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<ItemInventario {self.nombre}>'

class MovimientoInventario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_inventario_id = db.Column(db.Integer, db.ForeignKey('item_inventario.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # Entrada, Salida, Ajuste
    cantidad = db.Column(db.Integer, nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    referencia = db.Column(db.String(100))
    notas = db.Column(db.Text)
    
    # Relaciones
    item_inventario = db.relationship('ItemInventario', backref='movimientos')
    usuario = db.relationship('Usuario', backref='movimientos_inventario')
    
    def __repr__(self):
        return f'<MovimientoInventario {self.tipo} - {self.item_inventario.nombre} - {self.cantidad}>'
