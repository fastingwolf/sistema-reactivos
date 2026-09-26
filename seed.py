from database import init_db, SessionLocal
from auth import registrar_usuario
from reactivos import crear_reactivo, crear_contenedor
from usuarios import buscar_por_correo
from reactivos import buscar_reactivo_por_cas

init_db()
db = SessionLocal()

creados = False

if not buscar_por_correo(db, "admin@uni.edu"):
    registrar_usuario(db, "Admin", "admin@uni.edu", "admin123", "admin")
    creados = True

docente = buscar_por_correo(db, "perez@uni.edu")
if not docente:
    docente = registrar_usuario(db, "Dra. Pérez", "perez@uni.edu",
                                "1234", "docente")
    creados = True

if not buscar_por_correo(db, "juan@uni.edu"):
    registrar_usuario(db, "Juan López", "juan@uni.edu",
                      "abcd", "estudiante", docente_id=docente.id)
    creados = True

if not buscar_por_correo(db, "deposito@uni.edu"):
    registrar_usuario(db, "Carlos Depósito", "deposito@uni.edu",
                      "dep123", "deposito")
    creados = True

if not buscar_reactivo_por_cas(db, "67-64-1"):
    acetona = crear_reactivo(db, "Acetona", "67-64-1",
                             formula="C3H6O", unidad="mL",
                             peligrosidad="media")
    crear_contenedor(db, acetona, cantidad=500,
                     lote="L2024-01", ubicacion="Depósito A")
    creados = True

if creados:
    print("[+] Datos de prueba creados.")
else:
    print("[i] Los datos ya existían.")

db.close()