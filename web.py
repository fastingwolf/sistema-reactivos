from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from jinja2_fragments.fastapi import Jinja2Blocks
from sqlalchemy.orm import Session
from models import Usuario, CodigoAutorizacion, Solicitud, Contenedor

from database import get_db
from auth import login, registrar_usuario
from usuarios import buscar_por_correo
from reactivos import (listar_reactivos, buscar_reactivo_por_cas,
                       buscar_contenedor_por_codigo)
from auth_codes import crear_codigo_autorizacion
from solicitudes import (
    listar_solicitudes_pendientes,
    listar_solicitudes_entregadas,
    entregar_solicitud
)
from models import Usuario, CodigoAutorizacion, Solicitud

router = APIRouter()
templates = Jinja2Blocks(directory="templates")


def usuario_actual(request: Request, db: Session):
    """Devuelve el usuario logueado o None, leyendo la cookie."""
    uid = request.cookies.get("usuario_id")
    if not uid:
        return None
    return db.query(Usuario).get(int(uid))

@router.get("/")
def raiz():
    return RedirectResponse(url="/login", status_code=303)

# ============================
#  LOGIN / LOGOUT
# ============================

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
def login_post(request: Request,
               correo: str = Form(...),
               password: str = Form(...),
               db: Session = Depends(get_db)):
    usuario = login(db, correo, password)
    if not usuario:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Credenciales inválidas"
        })
    respuesta = RedirectResponse(url="/menu", status_code=303)
    respuesta.set_cookie("usuario_id", str(usuario.id), httponly=True)
    return respuesta


@router.get("/logout")
def logout():
    respuesta = RedirectResponse(url="/login", status_code=303)
    respuesta.delete_cookie("usuario_id")
    return respuesta


# ============================
#  REGISTRO
# ============================

@router.get("/registro", response_class=HTMLResponse)
def registro_page(request: Request, db: Session = Depends(get_db)):
    docentes = db.query(Usuario).filter_by(rol="docente").all()
    return templates.TemplateResponse("registro.html", {
        "request": request,
        "docentes": docentes
    })


@router.post("/registro")
def registro_post(request: Request,
                  nombre: str = Form(...),
                  correo: str = Form(...),
                  password: str = Form(...),
                  rol: str = Form(...),
                  correo_docente: str = Form(""),
                  db: Session = Depends(get_db)):
    docente_id = None
    if rol == "estudiante" and correo_docente:
        docente = buscar_por_correo(db, correo_docente)
        if docente and docente.rol == "docente":
            docente_id = docente.id

    try:
        registrar_usuario(db, nombre, correo, password, rol, docente_id)
    except ValueError as e:
        docentes = db.query(Usuario).filter_by(rol="docente").all()
        return templates.TemplateResponse("registro.html", {
            "request": request,
            "error": str(e),
            "docentes": docentes
        })

    return RedirectResponse(url="/login", status_code=303)


# ============================
#  MENÚ PRINCIPAL
# ============================

@router.get("/menu", response_class=HTMLResponse)
def menu(request: Request, db: Session = Depends(get_db)):
    usuario = usuario_actual(request, db)
    if not usuario:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("menu.html", {
        "request": request,
        "usuario": usuario
    })


# ============================
#  VISTAS GENERALES
# ============================

@router.get("/reactivos", response_class=HTMLResponse)
def reactivos_page(request: Request, db: Session = Depends(get_db)):
    usuario = usuario_actual(request, db)
    if not usuario:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("reactivos.html", {
        "request": request,
        "usuario": usuario,
        "reactivos": listar_reactivos(db)
    })


@router.get("/usuarios", response_class=HTMLResponse)
def usuarios_page(request: Request, db: Session = Depends(get_db)):
    usuario = usuario_actual(request, db)
    if not usuario:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("usuarios.html", {
        "request": request,
        "usuario": usuario,
        "usuarios": db.query(Usuario).all()
    })


# ============================
#  PANEL DOCENTE
# ============================

@router.get("/docente", response_class=HTMLResponse)
def panel_docente(request: Request, db: Session = Depends(get_db)):
    usuario = usuario_actual(request, db)
    if not usuario or usuario.rol != "docente":
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("docente.html", {
        "request": request,
        "usuario": usuario,
        "reactivos": listar_reactivos(db),
        "estudiantes": db.query(Usuario).filter_by(rol="estudiante").all(),
        "codigos": db.query(CodigoAutorizacion).filter_by(docente_id=usuario.id).all()
    })


@router.post("/docente/generar-codigo")
def generar_codigo_web(request: Request,
                       cas_reactivo: str = Form(...),
                       cantidad_maxima: float = Form(...),
                       horas_vigencia: int = Form(24),
                       usos: int = Form(1),
                       correo_estudiante: str = Form(""),
                       db: Session = Depends(get_db)):
    usuario = usuario_actual(request, db)
    if not usuario or usuario.rol != "docente":
        return RedirectResponse(url="/login", status_code=303)

    reactivo = buscar_reactivo_por_cas(db, cas_reactivo)
    if not reactivo:
        return RedirectResponse(url="/docente", status_code=303)

    estudiante = None
    if correo_estudiante:
        estudiante = buscar_por_correo(db, correo_estudiante)

    cod = crear_codigo_autorizacion(db, usuario, reactivo,
                                    cantidad_maxima, horas_vigencia,
                                    usos, estudiante)

    return templates.TemplateResponse("docente.html", {
        "request": request,
        "usuario": usuario,
        "reactivos": listar_reactivos(db),
        "estudiantes": db.query(Usuario).filter_by(rol="estudiante").all(),
        "codigos": db.query(CodigoAutorizacion).filter_by(docente_id=usuario.id).all(),
        "codigo_generado": cod.codigo,
        "mensaje": "Código generado exitosamente"
    })


# ============================
#  PANEL ESTUDIANTE
# ============================

# web.py (ruta del estudiante, modificada)
@router.post("/estudiante/solicitar")
def solicitar_web(request: Request,
                  cas_reactivo: str = Form(...),
                  cantidad: float = Form(...),
                  laboratorio_destino: str = Form(...),
                  codigo_autorizacion: str = Form(...),
                  db: Session = Depends(get_db)):
    usuario = usuario_actual(request, db)
    if not usuario or usuario.rol != "estudiante":
        return RedirectResponse(url="/login", status_code=303)

    reactivo = buscar_reactivo_por_cas(db, cas_reactivo)
    if not reactivo:
        msg = None
        err = "Reactivo no encontrado"
    else:
        try:
            crear_solicitud(db, usuario, codigo_autorizacion, reactivo,
                            cantidad, laboratorio_destino)
            msg = "Solicitud creada exitosamente"
            err = None
        except ValueError as e:
            msg = None
            err = str(e)

    solicitudes = db.query(Solicitud).filter_by(estudiante_id=usuario.id).all()
    return templates.TemplateResponse("estudiante.html", {
        "request": request,
        "usuario": usuario,
        "reactivos": listar_reactivos(db),
        "solicitudes": solicitudes,
        "mensaje": msg,
        "error": err
    })

# ============================
#  PANEL DEPÓSITO
# ============================

@router.get("/deposito", response_class=HTMLResponse)
def panel_deposito(request: Request, db: Session = Depends(get_db)):
    usuario = usuario_actual(request, db)
    if not usuario or usuario.rol != "deposito":
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("deposito.html", {
        "request": request,
        "usuario": usuario,
        "pendientes": listar_solicitudes_pendientes(db)
        "entregadas": listar_solicitudes_entregadas(db)
    })


@router.post("/deposito/entregar")
def entregar_web(request: Request,
                 solicitud_id: int = Form(...),
                 codigo_contenedor: str = Form(...),
                 db: Session = Depends(get_db)):
    usuario = usuario_actual(request, db)
    if not usuario or usuario.rol != "deposito":
        return RedirectResponse(url="/login", status_code=303)

    solicitud = db.query(Solicitud).get(solicitud_id)
    contenedor = buscar_contenedor_por_codigo(db, codigo_contenedor)

    msg = None
    err = None
    if not solicitud or solicitud.estado != "pendiente":
        err = "Solicitud no válida"
    elif not contenedor:
        err = "Contenedor no encontrado"
    else:
        try:
            entregar_solicitud(db, solicitud, usuario, contenedor)
            msg = "Solicitud entregada"
        except ValueError as e:
            err = str(e)

    return templates.TemplateResponse("deposito.html", {
        "request": request,
        "usuario": usuario,
        "pendientes": listar_solicitudes_pendientes(db),
        "mensaje": msg,
        "error": err
    })

@router.get("/")
def raiz():
    return RedirectResponse(url="/login", status_code=303)

# ============================
#  PANEL ESTUDIANTE
# ============================

@router.get("/estudiante", response_class=HTMLResponse)
def panel_estudiante(request: Request, db: Session = Depends(get_db)):
    usuario = usuario_actual(request, db)
    if not usuario or usuario.rol != "estudiante":
        return RedirectResponse(url="/login", status_code=303)
    solicitudes = db.query(Solicitud).filter_by(estudiante_id=usuario.id).all()
    return templates.TemplateResponse("estudiante.html", {
        "request": request,
        "usuario": usuario,
        "reactivos": listar_reactivos(db),
        "solicitudes": solicitudes
    })


@router.post("/estudiante/solicitar")
def solicitar_web(request: Request,
                  cas_reactivo: str = Form(...),
                  cantidad: float = Form(...),
                  laboratorio_destino: str = Form(...),
                  codigo_autorizacion: str = Form(...),
                  db: Session = Depends(get_db)):
    usuario = usuario_actual(request, db)
    if not usuario or usuario.rol != "estudiante":
        return RedirectResponse(url="/login", status_code=303)

    reactivo = buscar_reactivo_por_cas(db, cas_reactivo)
    if not reactivo:
        msg = None
        err = "Reactivo no encontrado"
    else:
        try:
            crear_solicitud(db, usuario, codigo_autorizacion, reactivo,
                            cantidad, laboratorio_destino)
            msg = "Solicitud creada exitosamente"
            err = None
        except ValueError as e:
            msg = None
            err = str(e)

    solicitudes = db.query(Solicitud).filter_by(estudiante_id=usuario.id).all()
    return templates.TemplateResponse("estudiante.html", {
        "request": request,
        "usuario": usuario,
        "reactivos": listar_reactivos(db),
        "solicitudes": solicitudes,
        "mensaje": msg,
        "error": err
    })

from qr import respuesta_qr, generar_qr_png
from fastapi import Response
from models import Contenedor


# ============================
#  QR DE CONTENEDORES
# ============================

@router.get("/qr/{codigo}.png")
def qr_imagen(codigo: str, request: Request, db: Session = Depends(get_db)):
    """Genera y sirve el QR de un contenedor como imagen PNG."""
    contenedor = buscar_contenedor_por_codigo(db, codigo)
    if not contenedor:
        return Response(content="Contenedor no encontrado",
                        media_type="text/plain", status_code=404)

    # Construimos la URL que abrirá el QR al escanearlo
    base_url = str(request.base_url).rstrip("/")
    url_destino = f"{base_url}/qr/{codigo}"

    return respuesta_qr(url_destino)


@router.get("/qr/{codigo}", response_class=HTMLResponse)
def qr_pagina(codigo: str, request: Request, db: Session = Depends(get_db)):
    """Página que se muestra al escanear el QR."""
    contenedor = buscar_contenedor_por_codigo(db, codigo)
    if not contenedor:
        return HTMLResponse(
            "<h1>Contenedor no encontrado</h1>"
            f"<p>No existe el código <code>{codigo}</code>.</p>",
            status_code=404
        )

    return templates.TemplateResponse("qr_contenedor.html", {
        "request": request,
        "contenedor": contenedor,
        "reactivo": contenedor.reactivo,
    })

# web.py
from fastapi import Request
from fastapi.responses import HTMLResponse

@router.get("/escaner", response_class=HTMLResponse)
def pagina_escaner(request: Request, db: Session = Depends(get_db)):
    # Esta ruta solo muestra la interfaz del escáner
    return templates.TemplateResponse("escaner.html", {"request": request})

@router.post("/escaner/procesar")
def procesar_escaneo(request: Request, codigo: str = Form(...), db: Session = Depends(get_db)):
    # Busca el contenedor por el código escaneado
    contenedor = buscar_contenedor_por_codigo(db, codigo)
    if not contenedor:
        # Renderiza una plantilla con un mensaje de error
        return templates.TemplateResponse("escaner_resultado.html", {
            "request": request,
            "error": f"No se encontró el contenedor {codigo}"
        })
    
    # Renderiza la plantilla con los datos del contenedor
    return templates.TemplateResponse("escaner_resultado.html", {
        "request": request,
        "contenedor": contenedor,
        "reactivo": contenedor.reactivo
    })
@router.get("/escaner", response_class=HTMLResponse)
def pagina_escaner(request: Request, db: Session = Depends(get_db)):
    usuario = usuario_actual(request, db)
    if not usuario:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("escaner.html", {
        "request": request,
        "usuario": usuario
    })


@router.get("/escaner", response_class=HTMLResponse)
def pagina_escaner(request: Request, db: Session = Depends(get_db)):
    usuario = usuario_actual(request, db)
    if not usuario:
        return RedirectResponse(url="/login", status_code=303)
    if usuario.rol not in ("deposito", "admin"):
        return RedirectResponse(url="/menu", status_code=303)
    return templates.TemplateResponse("escaner.html", {
        "request": request,
        "usuario": usuario
    })


@router.post("/escaner/procesar", response_class=HTMLResponse)
def procesar_escaneo(request: Request,
                     codigo: str = Form(...),
                     db: Session = Depends(get_db)):
    usuario = usuario_actual(request, db)
    if not usuario:
        return RedirectResponse(url="/login", status_code=303)
    if usuario.rol not in ("deposito", "admin"):
        return RedirectResponse(url="/menu", status_code=303)

    contenedor = buscar_contenedor_por_codigo(db, codigo)
    if not contenedor:
        return templates.TemplateResponse("escaner_resultado.html", {
            "request": request,
            "usuario": usuario,
            "error": f"No se encontró el contenedor {codigo}"
        })

    return templates.TemplateResponse("escaner_resultado.html", {
        "request": request,
        "usuario": usuario,
        "contenedor": contenedor,
        "reactivo": contenedor.reactivo
    })