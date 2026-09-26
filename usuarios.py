from models import Usuario


def listar_usuarios(session):
    return session.query(Usuario).all()


def buscar_por_correo(session, correo):
    return session.query(Usuario).filter_by(correo=correo).first()


def listar_docentes(session):
    return session.query(Usuario).filter_by(rol="docente").all()


def listar_estudiantes(session):
    return session.query(Usuario).filter_by(rol="estudiante").all()


def desactivar_usuario(session, usuario):
    usuario.activo = False
    session.commit()