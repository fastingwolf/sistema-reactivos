import bcrypt
from models import Usuario


def hashear_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verificar_password(password: str, hash_guardado: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hash_guardado.encode("utf-8"))


def registrar_usuario(session, nombre, correo, password, rol,
                      docente_id=None):
    """
    Registra un usuario nuevo con validaciones.
    - El correo debe ser único.
    - El rol debe ser válido.
    - Si es estudiante, debe tener un docente válido (opcional pero recomendado).
    """
    roles_validos = ("admin", "docente", "estudiante", "deposito")
    if rol not in roles_validos:
        raise ValueError(f"Rol inválido. Debe ser uno de: {roles_validos}")

    if session.query(Usuario).filter_by(correo=correo).first():
        raise ValueError(f"El correo {correo} ya está registrado.")

    if len(password) < 4:
        raise ValueError("La contraseña debe tener al menos 4 caracteres.")

    # Si es estudiante y se especifica docente, validar que exista y sea docente
    if rol == "estudiante" and docente_id is not None:
        docente = session.query(Usuario).get(docente_id)
        if not docente:
            raise ValueError(f"No existe usuario con id {docente_id}.")
        if docente.rol != "docente":
            raise ValueError(f"El usuario {docente_id} no es docente.")

    usuario = Usuario(
        nombre=nombre,
        correo=correo,
        rol=rol,
        docente_id=docente_id,
        password_hash=hashear_password(password),
    )
    session.add(usuario)
    session.commit()
    session.refresh(usuario)
    return usuario


def login(session, correo, password):
    usuario = session.query(Usuario).filter_by(correo=correo, activo=True).first()
    if not usuario:
        return None
    if not verificar_password(password, usuario.password_hash):
        return None
    return usuario