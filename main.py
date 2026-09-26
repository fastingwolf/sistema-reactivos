import logging
logging.getLogger("passlib").setLevel(logging.ERROR)

from fastapi import FastAPI, APIRouter, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List
from fastapi.responses import RedirectResponse

from database import init_db, get_db, SessionLocal
from auth import login, registrar_usuario
from usuarios import buscar_por_correo, listar_usuarios
from reactivos import (crear_reactivo, listar_reactivos,
                       crear_contenedor, listar_contenedores,
                       buscar_reactivo_por_cas,
                       buscar_contenedor_por_codigo)
from auth_codes import crear_codigo_autorizacion
from solicitudes import (crear_solicitud, entregar_solicitud,
                         listar_solicitudes_pendientes)
from schemas import (LoginRequest, Token, UsuarioCreate, UsuarioResponse,
                     UsuarioRegistroEstudiante,
                     ReactivoCreate, ReactivoResponse,
                     ContenedorCreate, ContenedorResponse,
                     CodigoRequest, CodigoResponse,
                     SolicitudRequest, SolicitudResponse,
                     EntregaRequest)
from models import Usuario, Reactivo, Solicitud

app = FastAPI(title="Sistema de Gestión de Reactivos")
api = APIRouter(prefix="/api")

@api.on_event("startup")
def startup():
    init_db()
    db = SessionLocal()
    try:
        # Si no hay admin, crear uno por defecto
        if not db.query(Usuario).filter_by(rol="admin").first():
            registrar_usuario(db, "Admin", "admin@uni.edu", "admin123", "admin")
            print("[i] Admin creado: admin@uni.edu / admin123")
    finally:
        db.close()

# ============================
#  REGISTRO DE USUARIOS
# ============================

@api.post("/usuarios", response_model=UsuarioResponse,
          summary="Registrar un usuario nuevo (admin, docente o depósito)")
def crear_usuario_endpoint(data: UsuarioCreate, db: Session = Depends(get_db)):
    """
    Registra un usuario nuevo.
    - Roles permitidos: admin, docente, deposito.
    - Para estudiantes, usa /usuarios/estudiante.
    """
    if data.rol == "estudiante":
        raise HTTPException(
            status_code=400,
            detail="Para registrar estudiantes usa POST /usuarios/estudiante"
        )
    try:
        return registrar_usuario(db, data.nombre, data.correo,
                                 data.password, data.rol, data.docente_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@api.post("/usuarios/estudiante", response_model=UsuarioResponse,
          summary="Registrar un estudiante vinculado a un docente")
def registrar_estudiante_endpoint(data: UsuarioRegistroEstudiante,
                                  db: Session = Depends(get_db)):
    """
    Registra un estudiante y lo vincula a un docente existente.
    El campo `correo_docente` debe ser el correo de un docente activo.
    """
    docente = db.query(Usuario).filter_by(correo=data.correo_docente,
                                          rol="docente",
                                          activo=True).first()
    if not docente:
        raise HTTPException(status_code=404,
                            detail=f"No existe un docente con correo {data.correo_docente}")

    try:
        return registrar_usuario(db, data.nombre, data.correo,
                                 data.password, "estudiante", docente.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@api.get("/usuarios", response_model=List[UsuarioResponse],
         summary="Listar todos los usuarios")
def listar_usuarios_endpoint(db: Session = Depends(get_db)):
    return db.query(Usuario).all()


@api.get("/usuarios/docentes", response_model=List[UsuarioResponse],
         summary="Listar solo docentes activos")
def listar_docentes_endpoint(db: Session = Depends(get_db)):
    return db.query(Usuario).filter_by(rol="docente", activo=True).all()

# ============================
#  AUTENTICACIÓN
# ============================

@api.post("/login", response_model=Token)
def login_endpoint(data: LoginRequest, db: Session = Depends(get_db)):
    usuario = login(db, data.correo, data.password)
    if not usuario:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    return Token(access_token=f"token-{usuario.id}")


@api.post("/usuarios", response_model=UsuarioResponse)
def crear_usuario_endpoint(data: UsuarioCreate, db: Session = Depends(get_db)):
    try:
        return registrar_usuario(db, data.nombre, data.correo,
                                 data.password, data.rol, data.docente_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================
#  REACTIVOS Y CONTENEDORES
# ============================

@api.get("/reactivos", response_model=List[ReactivoResponse])
def obtener_reactivos(db: Session = Depends(get_db)):
    return listar_reactivos(db)


@api.post("/reactivos", response_model=ReactivoResponse)
def agregar_reactivo(data: ReactivoCreate, db: Session = Depends(get_db)):
    try:
        return crear_reactivo(db, data.nombre, data.cas,
                              data.formula, data.unidad, data.peligrosidad)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@api.post("/contenedores", response_model=ContenedorResponse)
def agregar_contenedor(data: ContenedorCreate, db: Session = Depends(get_db)):
    reactivo = db.query(Reactivo).get(data.reactivo_id)
    if not reactivo:
        raise HTTPException(status_code=404, detail="Reactivo no encontrado")
    return crear_contenedor(db, reactivo, data.cantidad,
                            data.lote, ubicacion=data.ubicacion)


# ============================
#  CÓDIGOS DE AUTORIZACIÓN
# ============================

@api.post("/codigos", response_model=CodigoResponse)
def generar_codigo(data: CodigoRequest, db: Session = Depends(get_db)):
    docente = db.query(Usuario).get(data.docente_id)
    if not docente or docente.rol != "docente":
        raise HTTPException(status_code=403,
                            detail="Solo docentes pueden generar códigos")

    reactivo = buscar_reactivo_por_cas(db, data.cas_reactivo)
    if not reactivo:
        raise HTTPException(status_code=404, detail="Reactivo no encontrado")

    estudiante = None
    if data.correo_estudiante:
        estudiante = buscar_por_correo(db, data.correo_estudiante)

    cod = crear_codigo_autorizacion(
        db, docente, reactivo,
        cantidad_maxima=data.cantidad_maxima,
        horas_vigencia=data.horas_vigencia,
        usos=data.usos,
        estudiante=estudiante
    )
    return cod


# ============================
#  SOLICITUDES
# ============================

@api.post("/solicitudes", response_model=SolicitudResponse)
def nueva_solicitud(data: SolicitudRequest, db: Session = Depends(get_db)):
    estudiante = db.query(Usuario).get(data.estudiante_id)
    if not estudiante or estudiante.rol != "estudiante":
        raise HTTPException(status_code=403, detail="Usuario no es estudiante")

    reactivo = buscar_reactivo_por_cas(db, data.cas_reactivo)
    if not reactivo:
        raise HTTPException(status_code=404, detail="Reactivo no encontrado")

    try:
        return crear_solicitud(
            db, estudiante, data.codigo_autorizacion,
            reactivo, data.cantidad, data.laboratorio_destino
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@api.get("/solicitudes/pendientes", response_model=List[SolicitudResponse])
def obtener_pendientes(db: Session = Depends(get_db)):
    return listar_solicitudes_pendientes(db)


@api.post("/entregas")
def entregar_endpoint(data: EntregaRequest, db: Session = Depends(get_db)):
    solicitud = db.query(Solicitud).get(data.solicitud_id)
    if not solicitud or solicitud.estado != "pendiente":
        raise HTTPException(status_code=404, detail="Solicitud no válida")

    contenedor = buscar_contenedor_por_codigo(db, data.codigo_contenedor)
    if not contenedor:
        raise HTTPException(status_code=404, detail="Contenedor no encontrado")

    encargado = db.query(Usuario).get(data.encargado_id)
    if not encargado or encargado.rol != "deposito":
        raise HTTPException(status_code=403, detail="Usuario no autorizado")

    try:
        entregar_solicitud(db, solicitud, encargado, contenedor)
        return {"mensaje": "Solicitud entregada",
                "solicitud_id": data.solicitud_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================
#  HEALTH CHECK
# ============================

@api.get("/")
def api_root():
    return {"mensaje": "API de Gestión de Reactivos funcionando"}

# Montar archivos estáticos (CSS, imágenes)
from fastapi.staticfiles import StaticFiles
app.mount("/static", StaticFiles(directory="static"), name="static")

# Incluir las rutas de la API bajo /api/...
app.include_router(api)

# Incluir las rutas de la interfaz web (sin prefijo)
from web import router as web_router
app.include_router(web_router)

from fastapi.responses import RedirectResponse

@app.get("/")
def raiz():
    return RedirectResponse(url="/login", status_code=303)