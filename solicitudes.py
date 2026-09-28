from datetime import datetime
from models import Solicitud, SolicitudDetalle, Movimiento
from auth_codes import validar_codigo


def crear_solicitud(session, estudiante, codigo_str, reactivo, cantidad,
                    laboratorio_destino):
    """Crea una solicitud validando el código de autorización."""
    ok, msg = validar_codigo(session, codigo_str, estudiante, reactivo, cantidad)
    if not ok:
        raise ValueError(f"Solicitud rechazada: {msg}")

    # Recuperamos el código ya validado para asociarlo
    from models import CodigoAutorizacion
    codigo = session.query(CodigoAutorizacion).filter_by(codigo=codigo_str).first()

    solicitud = Solicitud(
        estudiante_id=estudiante.id,
        codigo_id=codigo.id,
        laboratorio_destino=laboratorio_destino,
        estado="pendiente",
    )
    
    # Asignación manual para forzar la lectura en Jinja en memoria
    solicitud.cantidad_solicitada = cantidad
    
    session.add(solicitud)
    session.commit()

    detalle = SolicitudDetalle(
        solicitud_id=solicitud.id,
        reactivo_id=reactivo.id,
        cantidad_solicitada=cantidad,
    )
    session.add(detalle)
    session.commit()
    return solicitud


def entregar_solicitud(session, solicitud, encargado, contenedor):
    """El encargado del depósito marca la solicitud como entregada."""
    detalle = solicitud.detalles[0]
    cantidad = detalle.cantidad_solicitada

    if contenedor.cantidad_actual < cantidad:
        raise ValueError("No hay suficiente cantidad en el contenedor.")

    contenedor.cantidad_actual -= cantidad
    detalle.cantidad_entregada = cantidad
    detalle.contenedor_id = contenedor.id
    solicitud.estado = "entregada"
    solicitud.fecha_entrega = datetime.utcnow()

    mov = Movimiento(
        contenedor_id=contenedor.id,
        usuario_id=encargado.id,
        tipo="entrega",
        cantidad=cantidad,
        solicitud_id=solicitud.id,
        observaciones=f"Entregado a {solicitud.estudiante.nombre}",
    )
    session.add(mov)
    session.commit()
    return solicitud


def listar_solicitudes_pendientes(session):
    return session.query(Solicitud).filter_by(estado="pendiente").all()


def listar_solicitudes_por_estudiante(session, estudiante):
    return session.query(Solicitud).filter_by(estudiante_id=estudiante.id).all()

def listar_solicitudes_entregadas(session, limite: int = 50):
    """Devuelve las últimas solicitudes entregadas para trazabilidad del depósito."""
    return (
        session.query(Solicitud)
        .filter(Solicitud.estado == "entregada")
        .order_by(Solicitud.fecha_entrega.desc())
        .limit(limite)
        .all()
    )