# /helpers.py

from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP, ROUND_UP
from flask import current_app
import pytz

# --- Funciones de Cálculo Financiero ---

def calcular_cuota(monto_total, tasa_interes, numero_cuotas):
    """
    Calcula el monto de la cuota para un crédito.
    
    Args:
        monto_total (Decimal): Monto total del crédito.
        tasa_interes (Decimal): Tasa de interés por período (porcentaje).
        numero_cuotas (int): Número de cuotas.
        
    Returns:
        Decimal: Monto de la cuota.
    """
    if numero_cuotas <= 0 or tasa_interes <= 0:
        return monto_total
    
    # Convertir tasa de porcentaje a decimal
    tasa_decimal = tasa_interes / Decimal('100')
    
    # Fórmula de cuota: P * r * (1+r)^n / ((1+r)^n - 1)
    numerador = monto_total * tasa_decimal * (1 + tasa_decimal) ** numero_cuotas
    denominador = (1 + tasa_decimal) ** numero_cuotas - 1
    
    if denominador == 0:  # Evitar división por cero
        return monto_total
    
    cuota = numerador / denominador
    
    # Redondear a 2 decimales
    return cuota.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

def generar_plan_pagos(monto_total, tasa_interes, numero_cuotas, fecha_primer_pago, periodo_pago):
    """
    Genera un plan de pagos para un crédito.
    
    Args:
        monto_total (Decimal): Monto total del crédito.
        tasa_interes (Decimal): Tasa de interés por período (porcentaje).
        numero_cuotas (int): Número de cuotas.
        fecha_primer_pago (date): Fecha del primer pago.
        periodo_pago (str): Período de pago ('mensual', 'quincenal', 'semanal').
        
    Returns:
        list: Lista de diccionarios con información de cada cuota.
    """
    cuota = calcular_cuota(monto_total, tasa_interes, numero_cuotas)
    tasa_decimal = tasa_interes / Decimal('100')
    saldo_capital = monto_total
    plan_pagos = []
    
    for i in range(1, numero_cuotas + 1):
        # Calcular fecha de vencimiento según período
        if i == 1:
            fecha_vencimiento = fecha_primer_pago
        else:
            if periodo_pago == 'mensual':
                # Mismo día del mes siguiente
                mes = fecha_primer_pago.month + (i - 1)
                año = fecha_primer_pago.year + (mes - 1) // 12
                mes = ((mes - 1) % 12) + 1
                try:
                    fecha_vencimiento = fecha_primer_pago.replace(year=año, month=mes)
                except ValueError:  # Para manejar 29/02 en años no bisiestos, etc.
                    # Si el día no existe en el mes (ej. 31 de abril), usar el último día del mes
                    if mes == 2:  # Febrero
                        if año % 4 == 0 and (año % 100 != 0 or año % 400 == 0):  # Año bisiesto
                            ultimo_dia = 29
                        else:
                            ultimo_dia = 28
                    elif mes in [4, 6, 9, 11]:  # Abril, Junio, Septiembre, Noviembre
                        ultimo_dia = 30
                    else:
                        ultimo_dia = 31
                    fecha_vencimiento = fecha_primer_pago.replace(year=año, month=mes, day=min(fecha_primer_pago.day, ultimo_dia))
            elif periodo_pago == 'quincenal':
                fecha_vencimiento = fecha_primer_pago + timedelta(days=15 * (i - 1))
            else:  # semanal
                fecha_vencimiento = fecha_primer_pago + timedelta(days=7 * (i - 1))
        
        # Calcular interés y capital de la cuota
        interes = (saldo_capital * tasa_decimal).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        capital = (cuota - interes).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        # Ajustar la última cuota para que el saldo quede exactamente en cero
        if i == numero_cuotas:
            capital = saldo_capital
            cuota = capital + interes
        
        # Actualizar saldo
        saldo_capital -= capital
        
        # Agregar cuota al plan
        plan_pagos.append({
            'numero_cuota': i,
            'fecha_vencimiento': fecha_vencimiento,
            'monto_cuota': cuota,
            'capital': capital,
            'interes': interes,
            'saldo_capital': saldo_capital,
            'estado': 'Pendiente'
        })
    
    return plan_pagos

def calcular_comision(monto_cobrado, porcentaje_comision):
    """
    Calcula la comisión de un vendedor por un cobro.
    
    Args:
        monto_cobrado (Decimal): Monto cobrado.
        porcentaje_comision (Decimal): Porcentaje de comisión del vendedor (Decimal, ej. 10 para 10%).
        
    Returns:
        Decimal: Monto de la comisión.
    """
    if porcentaje_comision is None or porcentaje_comision <= 0:
        return Decimal('0')
    comision = (monto_cobrado * porcentaje_comision / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return comision

def calcular_estado_credito(credito):
    """
    Determina el estado actual de un crédito (Pendiente, Pagado, Vencido).
    
    Args:
        credito: Objeto Crédito.
        
    Returns:
        str: Estado del crédito ('Pendiente', 'Pagado', 'Vencido').
    """
    if credito.saldo_pendiente <= 0:
        return 'Pagado'
    
    hoy = datetime.now().date()
    proxima_cuota = credito.proxima_fecha_vencimiento()
    
    if proxima_cuota and hoy > (proxima_cuota + timedelta(days=current_app.config.get('DIAS_GRACIA_MORA', 3))):
        return 'Vencido'
        
    return 'Pendiente' # Si no está pagado ni vencido, está pendiente

def calcular_proximos_vencimientos(creditos, dias=7):
    """
    Encuentra créditos con vencimientos próximos.
    
    Args:
        creditos: Lista de objetos Crédito activos.
        dias: Número de días en el futuro para considerar.
        
    Returns:
        list: Lista de créditos con vencimientos próximos.
    """
    hoy = datetime.now().date()
    fecha_limite = hoy + timedelta(days=dias)
    proximos = []
    for credito in creditos:
        if credito.estado == 'Pendiente':
            proxima_fecha = credito.proxima_fecha_vencimiento()
            if proxima_fecha and hoy <= proxima_fecha <= fecha_limite:
                proximos.append(credito)
    return proximos

def calcular_mora(credito):
    """
    Calcula el monto de mora si el crédito está vencido.
    (Implementación simple: porcentaje fijo sobre saldo si está vencido)
    
    Args:
        credito: Objeto Crédito.
        
    Returns:
        Decimal: Monto de la mora.
    """
    if calcular_estado_credito(credito) == 'Vencido':
        porcentaje_mora = current_app.config.get('MORA_PORCENTAJE', Decimal('5'))
        mora = (credito.saldo_pendiente * porcentaje_mora / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_UP)
        return mora
    return Decimal('0')

# --- Otras Funciones Auxiliares ---

def obtener_hora_local(dt_utc):
    """
    Convierte un datetime UTC a la hora local configurada (si existe).
    
    Args:
        dt_utc: Datetime en UTC.
        
    Returns:
        datetime: Datetime en hora local o el original si no hay timezone.
    """
    timezone_str = current_app.config.get('TIMEZONE')
    if timezone_str and dt_utc:
        try:
            local_tz = pytz.timezone(timezone_str)
            return dt_utc.replace(tzinfo=pytz.utc).astimezone(local_tz)
        except Exception as e:
            print(f"Error al convertir zona horaria: {e}")
            return dt_utc # Devolver UTC si hay error
    return dt_utc

def formatear_hora_local(dt_utc):
    """
    Formatea un datetime UTC a string hh:mm am/pm en hora local.
    
    Args:
        dt_utc: Datetime en UTC.
        
    Returns:
        str: Hora formateada o string vacío.
    """
    dt_local = obtener_hora_local(dt_utc)
    if dt_local:
        return dt_local.strftime('%I:%M %p').lower()
    return ""
