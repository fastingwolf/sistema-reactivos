from models import Movimiento


def listar_movimientos_por_contenedor(session, contenedor):
    return (session.query(Movimiento)
            .filter_by(contenedor_id=contenedor.id)
            .order_by(Movimiento.fecha)
            .all())


def listar_movimientos_por_usuario(session, usuario):
    return (session.query(Movimiento)
            .filter_by(usuario_id=usuario.id)
            .order_by(Movimiento.fecha)
            .all())


def historial_completo(session):
    return session.query(Movimiento).order_by(Movimiento.fecha).all()