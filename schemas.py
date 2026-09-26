from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import datetime
from typing import Optional


# --- Usuario ---
class UsuarioBase(BaseModel):
    nombre: str
    correo: EmailStr
    rol: str


class UsuarioCreate(UsuarioBase):
    password: str
    docente_id: Optional[int] = None


class UsuarioResponse(UsuarioBase):
    id: int
    activo: bool
    model_config = ConfigDict(from_attributes=True)


# --- Login / Token ---
class LoginRequest(BaseModel):
    correo: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- Reactivo ---
class ReactivoBase(BaseModel):
    nombre: str
    cas: str
    formula: Optional[str] = None
    unidad: str = "g"
    peligrosidad: str = "baja"


class ReactivoCreate(ReactivoBase):
    pass


class ReactivoResponse(ReactivoBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# --- Contenedor ---
class ContenedorCreate(BaseModel):
    reactivo_id: int
    cantidad: float
    lote: Optional[str] = None
    ubicacion: str = "Depósito"


class ContenedorResponse(BaseModel):
    id: int
    codigo_barras: str
    reactivo_id: int
    cantidad_inicial: float
    cantidad_actual: float
    ubicacion: str
    activo: bool
    model_config = ConfigDict(from_attributes=True)


# --- Código de Autorización ---
class CodigoRequest(BaseModel):
    cas_reactivo: str
    cantidad_maxima: float
    horas_vigencia: int = 24
    usos: int = 1
    correo_estudiante: Optional[str] = None
    docente_id: int          # <-- lo pedimos en el body para simplificar


class CodigoResponse(BaseModel):
    codigo: str
    reactivo_id: int
    cantidad_maxima: float
    fecha_expiracion: datetime
    estado: str
    model_config = ConfigDict(from_attributes=True)


# --- Solicitud ---
class SolicitudRequest(BaseModel):
    cas_reactivo: str
    cantidad: float
    laboratorio_destino: str
    codigo_autorizacion: str
    estudiante_id: int       # <-- lo pedimos en el body para simplificar


class SolicitudResponse(BaseModel):
    id: int
    estado: str
    laboratorio_destino: str
    fecha_creacion: datetime
    model_config = ConfigDict(from_attributes=True)


# --- Entrega ---
class EntregaRequest(BaseModel):
    solicitud_id: int
    codigo_contenedor: str
    encargado_id: int

class UsuarioRegistroEstudiante(BaseModel):
    nombre: str
    correo: EmailStr
    password: str
    correo_docente: EmailStr