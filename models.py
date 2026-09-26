from sqlalchemy import (Column, Integer, String, Float, DateTime,
                        ForeignKey, Boolean, Text)
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False)
    correo = Column(String, unique=True, nullable=False)
    rol = Column(String, nullable=False)  # admin, docente, estudiante, deposito
    docente_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    password_hash = Column(String, nullable=False)
    activo = Column(Boolean, default=True)


class Reactivo(Base):
    __tablename__ = "reactivos"
    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False)
    cas = Column(String, unique=True, nullable=False)
    formula = Column(String)
    unidad = Column(String, default="g")
    peligrosidad = Column(String, default="baja")  # baja, media, alta
    contenedores = relationship("Contenedor", back_populates="reactivo")


class Contenedor(Base):
    __tablename__ = "contenedores"
    id = Column(Integer, primary_key=True)
    reactivo_id = Column(Integer, ForeignKey("reactivos.id"), nullable=False)
    codigo_barras = Column(String, unique=True, nullable=False)
    lote = Column(String)
    caducidad = Column(DateTime, nullable=True)
    cantidad_inicial = Column(Float, nullable=False)
    cantidad_actual = Column(Float, nullable=False)
    ubicacion = Column(String, default="Depósito")
    activo = Column(Boolean, default=True)

    reactivo = relationship("Reactivo", back_populates="contenedores")


class CodigoAutorizacion(Base):
    __tablename__ = "codigos_autorizacion"
    id = Column(Integer, primary_key=True)
    codigo = Column(String, unique=True, nullable=False)
    docente_id = Column(Integer, ForeignKey("usuarios.id"))
    estudiante_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    reactivo_id = Column(Integer, ForeignKey("reactivos.id"))
    cantidad_maxima = Column(Float, nullable=False)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    fecha_expiracion = Column(DateTime, nullable=False)
    usos_permitidos = Column(Integer, default=1)
    usos_realizados = Column(Integer, default=0)
    estado = Column(String, default="activo")

    docente = relationship("Usuario", foreign_keys=[docente_id])
    estudiante = relationship("Usuario", foreign_keys=[estudiante_id])
    reactivo = relationship("Reactivo")


class Solicitud(Base):
    __tablename__ = "solicitudes"
    id = Column(Integer, primary_key=True)
    estudiante_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    codigo_id = Column(Integer, ForeignKey("codigos_autorizacion.id"), nullable=False)
    laboratorio_destino = Column(String, nullable=False)
    estado = Column(String, default="pendiente")  # pendiente, entregada, rechazada
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    fecha_entrega = Column(DateTime, nullable=True)

    estudiante = relationship("Usuario", foreign_keys=[estudiante_id])
    codigo = relationship("CodigoAutorizacion")
    detalles = relationship("SolicitudDetalle", back_populates="solicitud")


class SolicitudDetalle(Base):
    __tablename__ = "solicitud_detalle"
    id = Column(Integer, primary_key=True)
    solicitud_id = Column(Integer, ForeignKey("solicitudes.id"), nullable=False)
    reactivo_id = Column(Integer, ForeignKey("reactivos.id"), nullable=False)
    cantidad_solicitada = Column(Float, nullable=False)
    cantidad_entregada = Column(Float, nullable=True)
    contenedor_id = Column(Integer, ForeignKey("contenedores.id"), nullable=True)

    solicitud = relationship("Solicitud", back_populates="detalles")
    reactivo = relationship("Reactivo")
    contenedor = relationship("Contenedor")


class Movimiento(Base):
    __tablename__ = "movimientos"
    id = Column(Integer, primary_key=True)
    contenedor_id = Column(Integer, ForeignKey("contenedores.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    tipo = Column(String, nullable=False)  # entrada, entrega, uso, devolucion, ajuste
    cantidad = Column(Float, nullable=False)
    fecha = Column(DateTime, default=datetime.utcnow)
    solicitud_id = Column(Integer, ForeignKey("solicitudes.id"), nullable=True)
    observaciones = Column(Text, nullable=True)

    contenedor = relationship("Contenedor")
    usuario = relationship("Usuario")