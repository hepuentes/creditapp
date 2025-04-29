from datetime import datetime
from app import db

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    documento = db.Column(db.String(20), unique=True, nullable=False)
    telefono = db.Column(db.String(20))
    direccion = db.Column(db.String(200))
    email = db.Column(db.String(120))
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    ultima_modificacion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    activo = db.Column(db.Boolean, default=True)
    
    # Relaciones
    creditos = db.relationship('Credito', backref='cliente', lazy='dynamic')
    
    def __repr__(self):
        return f'<Cliente {self.nombre}>'
    
    @property
    def estado(self):
        creditos_activos = [c for c in self.creditos if c.estado != 'Pagado']
        if not creditos_activos:
            if self.creditos.count() > 0:
                return 'Sin créditos activos'
            return 'Sin créditos'
        return 'Con créditos activos'
