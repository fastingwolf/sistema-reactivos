import secrets
import string
from datetime import datetime, timedelta
from models import CodigoAutorizacion

def generar_codigo():
    alfabeto = string.ascii_uppercase + string.digits
    p1 = ''.join(secrets.choice(alfabeto) for _ in range(4))
    p2 = ''.join(secrets.choice(alfabeto) for _ in range(4))
    return f"AUT-{p1}-{p2}"

def crear_codigo_autorizacion(session, docente, reactivo,
                               cantidad_maxima, horas_vigencia=24,
                               usos=1, estudiante=None):
    if docente.rol != "docente":
        raise PermissionError("Solo un docente puede generar códigos.")

    codigo = generar_codigo()
    expiracion = datetime.utcnow() + timedelta(hours=horas_vigencia)

    registro = CodigoAutorizacion(
        codigo=codigo,
        docente_id=docente.id,
        estudiante_id=estudiante.id if estudiante else None,
        reactivo_id=reactivo.id,
        cantidad_maxima=cantidad_maxima,
        fecha_expiracion=expiracion,
        usos_permitidos=usos,
    )
    session.add(registro)
    session.commit()
    return registro

def validar_codigo(session, codigo_str, estudiante, reactivo, cantidad):
    reg = session.query(CodigoAutorizacion).filter_by(codigo=codigo_str).first()

    if not reg:
        return False, "Código inexistente."
    if reg.estado != "activo":
        return False, f"Código {reg.estado}."
    if reg.fecha_expiracion < datetime.utcnow():
        reg.estado = "expirado"
        session.commit()
        return False, "Código expirado."
    if reg.usos_realizados >= reg.usos_permitidos:
        reg.estado = "agotado"
        session.commit()
        return False, "Código sin usos disponibles."
    if reg.estudiante_id and reg.estudiante_id != estudiante.id:
        return False, "El código no está asignado a este estudiante."
    if reg.reactivo_id != reactivo.id:
        return False, "El reactivo no coincide con el autorizado."
    if cantidad > reg.cantidad_maxima:
        return False, f"Cantidad excede el máximo ({reg.cantidad_maxima})."

    reg.usos_realizados += 1
    if reg.usos_realizados >= reg.usos_permitidos:
        reg.estado = "agotado"
    session.commit()
    return True, "Autorizado."