import uuid
from datetime import datetime
from models import Reactivo, Contenedor


def crear_reactivo(session, nombre, cas, formula=None, unidad="g",
                   peligrosidad="baja"):
    existente = session.query(Reactivo).filter_by(cas=cas).first()
    if existente:
        raise ValueError(f"Ya existe un reactivo con CAS {cas}.")
    r = Reactivo(nombre=nombre, cas=cas, formula=formula,
                 unidad=unidad, peligrosidad=peligrosidad)
    session.add(r)
    session.commit()
    return r


def buscar_reactivo_por_cas(session, cas):
    return session.query(Reactivo).filter_by(cas=cas).first()


def listar_reactivos(session):
    return session.query(Reactivo).all()


def crear_contenedor(session, reactivo, cantidad, lote=None,
                     caducidad=None, ubicacion="Depósito"):
    """Crea un frasco físico con un código de barras único."""
    codigo = f"CNT-{uuid.uuid4().hex[:8].upper()}"
    c = Contenedor(
        reactivo_id=reactivo.id,
        codigo_barras=codigo,
        lote=lote,
        caducidad=caducidad,
        cantidad_inicial=cantidad,
        cantidad_actual=cantidad,
        ubicacion=ubicacion,
    )
    session.add(c)
    session.commit()
    return c


def buscar_contenedor_por_codigo(session, codigo):
    return session.query(Contenedor).filter_by(codigo_barras=codigo).first()


def listar_contenedores(session, reactivo=None):
    q = session.query(Contenedor).filter_by(activo=True)
    if reactivo:
        q = q.filter_by(reactivo_id=reactivo.id)
    return q.all()