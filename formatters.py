# /formatters.py

from decimal import Decimal, ROUND_HALF_UP

def formatear_numero_python(numero, decimales=0):
    """
    Formatea un número para mostrar separadores de miles (puntos) y comas decimales.
    
    Args:
        numero: El número a formatear (puede ser int, float, Decimal, o string).
        decimales: Número de decimales a mostrar.
        
    Returns:
        str: El número formateado.
    """
    try:
        # Intentar convertir a Decimal
        numero_decimal = Decimal(str(numero))
        
        # Formatear con separadores de miles y decimales
        # Usar un formato temporal con comas para miles y punto para decimal
        formato_temp = f",.{decimales}f"
        numero_formateado_temp = format(numero_decimal, formato_temp)
        
        # Reemplazar coma por punto y punto por coma (formato español)
        # Usar un carácter intermedio para evitar reemplazos incorrectos
        return numero_formateado_temp.replace(',', '#').replace('.', ',').replace('#', '.')
    except Exception as e:
        # print(f"Error formateando número {numero}: {e}") # Descomentar para depurar
        return str(numero) # Devolver original si hay error

def desformatear_numero_python(numero_formateado):
    """
    Convierte un número formateado (con puntos como separadores de miles y coma decimal)
    a un número Decimal.
    
    Args:
        numero_formateado: El número formateado a convertir (string).
        
    Returns:
        Decimal: El número sin formato.
    """
    if numero_formateado is None:
        return Decimal('0')
    
    # Si ya es un número, convertirlo a Decimal
    if isinstance(numero_formateado, (int, float, Decimal)):
        return Decimal(str(numero_formateado))
    
    # Si no es string, intentar convertir
    if not isinstance(numero_formateado, str):
        try:
            return Decimal(str(numero_formateado))
        except:
             return Decimal('0')

    # Eliminar puntos de miles y cambiar coma decimal por punto
    try:
        numero_limpio = numero_formateado.replace('.', '').replace(',', '.')
        # Manejar string vacío después de limpiar
        if not numero_limpio:
            return Decimal('0')
        return Decimal(numero_limpio)
    except Exception as e:
        # print(f"Error desformateando número {numero_formateado}: {e}") # Descomentar para depurar
        return Decimal('0')

def convertir_a_numero(valor):
    """
    Alias para desformatear_numero_python.
    Convierte un valor (posiblemente formateado) a número decimal.
    
    Args:
        valor: El valor a convertir.
        
    Returns:
        Decimal: El valor convertido a número decimal.
    """
    return desformatear_numero_python(valor)
