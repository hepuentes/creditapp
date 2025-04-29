# /config.py

import os
from datetime import timedelta

# Configuración de la base de datos
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, 'credito_app.db')
SQLALCHEMY_DATABASE_URI = f'sqlite:///{DATABASE_PATH}'
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Configuración de la aplicación
SECRET_KEY = os.environ.get('SECRET_KEY', 'clave_secreta_muy_segura_para_desarrollo')
DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'

# Configuración de Flask-Login
REMEMBER_COOKIE_DURATION = timedelta(days=7)

# Configuración de paginación
ITEMS_PER_PAGE = 10

# Configuración de roles
ROLES = {
    'admin': 'Administrador',
    'vendedor': 'Vendedor',
    'cobrador': 'Cobrador'
}

# Configuración de períodos de pago
PERIODOS_PAGO = {
    'semanal': 'Semanal',
    'quincenal': 'Quincenal',
    'mensual': 'Mensual'
}

# Configuración de estados de crédito
ESTADOS_CREDITO = {
    'Pendiente': 'Pendiente',
    'Pagado': 'Pagado',
    'Vencido': 'Vencido',
    'Cancelado': 'Cancelado'
}

# Configuración de tipos de movimiento de inventario
TIPOS_MOVIMIENTO_INVENTARIO = {
    'Entrada': 'Entrada',
    'Salida': 'Salida'
}

# Configuración de tipos de movimiento de caja
TIPOS_MOVIMIENTO_CAJA = {
    'Ingreso': 'Ingreso',
    'Egreso': 'Egreso'
}

# Configuración de conceptos de movimiento de caja
CONCEPTOS_MOVIMIENTO_CAJA = {
    'Apertura': 'Apertura de Caja',
    'Pago de Crédito': 'Pago de Crédito',
    'Pago a Proveedor': 'Pago a Proveedor',
    'Pago de Comisión': 'Pago de Comisión',
    'Gasto Operativo': 'Gasto Operativo',
    'Transferencia': 'Transferencia entre Cajas',
    'Entrega Cobrador': 'Entrega de Cobrador',
    'Otro': 'Otro'
}

# Configuración de unidades de medida para productos
UNIDADES_MEDIDA = [
    'Unidad',
    'Kg',
    'Litro',
    'Metro',
    'Caja',
    'Paquete'
]

# Días de gracia para mora
DIAS_GRACIA_MORA = 3

# Porcentaje de mora (por cada 30 días)
MORA_PORCENTAJE = Decimal('5')
