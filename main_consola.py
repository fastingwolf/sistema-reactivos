import logging
logging.getLogger("passlib").setLevel(logging.ERROR)

from database import init_db, SessionLocal
from auth import registrar_usuario, login
from usuarios import listar_usuarios, buscar_por_correo
from reactivos import (crear_reactivo, listar_reactivos,
                       crear_contenedor, listar_contenedores,
                       buscar_reactivo_por_cas)
from auth_codes import crear_codigo_autorizacion, validar_codigo
from solicitudes import (crear_solicitud, entregar_solicitud,
                         listar_solicitudes_pendientes,
                         listar_solicitudes_por_estudiante)
from movimientos import listar_movimientos_por_contenedor


def inicializar_datos_demo(session):
    """Crea datos de prueba si no existen."""
    from usuarios import buscar_por_correo

    creados = False

    if not buscar_por_correo(session, "admin@uni.edu"):
        registrar_usuario(session, "Admin", "admin@uni.edu", "admin123", "admin")
        creados = True

    docente = buscar_por_correo(session, "perez@uni.edu")
    if not docente:
        docente = registrar_usuario(session, "Dra. Pérez", "perez@uni.edu",
                                    "1234", "docente")
        creados = True

    if not buscar_por_correo(session, "juan@uni.edu"):
        registrar_usuario(session, "Juan López", "juan@uni.edu",
                          "abcd", "estudiante", docente_id=docente.id)
        creados = True

    if not buscar_por_correo(session, "deposito@uni.edu"):
        registrar_usuario(session, "Carlos Depósito", "deposito@uni.edu",
                          "dep123", "deposito")
        creados = True

    if not buscar_reactivo_por_cas(session, "67-64-1"):
        acetona = crear_reactivo(session, "Acetona", "67-64-1",
                                 formula="C3H6O", unidad="mL",
                                 peligrosidad="media")
        crear_contenedor(session, acetona, cantidad=500,
                         lote="L2024-01", ubicacion="Depósito A")
        creados = True

    if creados:
        print("\n[+] Datos de demostración creados.\n")


def menu_principal(session):
    while True:
        print("\n=== SISTEMA DE GESTIÓN DE REACTIVOS ===")
        print("1. Iniciar sesión")
        print("2. Listar usuarios")
        print("3. Listar reactivos")
        print("4. Listar contenedores")
        print("5. Salir")
        op = input("Opción: ").strip()

        if op == "1":
            correo = input("Correo: ").strip()
            password = input("Contraseña: ").strip()
            usuario = login(session, correo, password)
            if not usuario:
                print("❌ Credenciales inválidas.")
                continue
            print(f"✅ Bienvenido, {usuario.nombre} ({usuario.rol})")
            menu_usuario(session, usuario)

        elif op == "2":
            for u in listar_usuarios(session):
                print(f"  [{u.id}] {u.nombre} - {u.correo} ({u.rol})")

        elif op == "3":
            for r in listar_reactivos(session):
                print(f"  [{r.id}] {r.nombre} | CAS: {r.cas} | {r.unidad}")

        elif op == "4":
            for c in listar_contenedores(session):
                print(f"  [{c.id}] {c.codigo_barras} | "
                      f"{c.reactivo.nombre} | {c.cantidad_actual}/{c.cantidad_inicial} "
                      f"{c.reactivo.unidad} | {c.ubicacion}")

        elif op == "5":
            print("Hasta luego.")
            break
        else:
            print("Opción inválida.")


def menu_usuario(session, usuario):
    if usuario.rol == "docente":
        menu_docente(session, usuario)
    elif usuario.rol == "estudiante":
        menu_estudiante(session, usuario)
    elif usuario.rol == "deposito":
        menu_deposito(session, usuario)
    elif usuario.rol == "admin":
        menu_principal(session)


def menu_docente(session, docente):
    while True:
        print(f"\n--- MENÚ DOCENTE ({docente.nombre}) ---")
        print("1. Generar código de autorización")
        print("2. Volver")
        op = input("Opción: ").strip()

        if op == "1":
            cas = input("CAS del reactivo: ").strip()
            reactivo = buscar_reactivo_por_cas(session, cas)
            if not reactivo:
                print("❌ Reactivo no encontrado.")
                continue
            cantidad = float(input("Cantidad máxima: "))
            horas = int(input("Vigencia en horas (ej. 24): "))
            usos = int(input("Usos permitidos: "))
            correo_est = input("Correo del estudiante (opcional, Enter para omitir): ").strip()
            estudiante = None
            if correo_est:
                from usuarios import buscar_por_correo
                estudiante = buscar_por_correo(session, correo_est)

            cod = crear_codigo_autorizacion(
                session, docente, reactivo,
                cantidad_maxima=cantidad,
                horas_vigencia=horas,
                usos=usos,
                estudiante=estudiante,
            )
            print(f"✅ Código generado: {cod.codigo}")

        elif op == "2":
            break


def menu_estudiante(session, estudiante):
    while True:
        print(f"\n--- MENÚ ESTUDIANTE ({estudiante.nombre}) ---")
        print("1. Crear solicitud de reactivo")
        print("2. Ver mis solicitudes")
        print("3. Volver")
        op = input("Opción: ").strip()

        if op == "1":
            cas = input("CAS del reactivo: ").strip()
            reactivo = buscar_reactivo_por_cas(session, cas)
            if not reactivo:
                print("❌ Reactivo no encontrado.")
                continue
            cantidad = float(input("Cantidad solicitada: "))
            lab = input("Laboratorio destino: ").strip()
            codigo = input("Código de autorización: ").strip()
            try:
                sol = crear_solicitud(session, estudiante, codigo,
                                      reactivo, cantidad, lab)
                print(f"✅ Solicitud #{sol.id} creada (pendiente de entrega).")
            except ValueError as e:
                print(f"❌ {e}")

        elif op == "2":
            for s in listar_solicitudes_por_estudiante(session, estudiante):
                print(f"  Solicitud #{s.id} | {s.estado} | {s.laboratorio_destino}")

        elif op == "3":
            break


def menu_deposito(session, encargado):
    while True:
        print(f"\n--- MENÚ DEPÓSITO ({encargado.nombre}) ---")
        print("1. Ver solicitudes pendientes")
        print("2. Entregar solicitud")
        print("3. Ver movimientos de un contenedor")
        print("4. Volver")
        op = input("Opción: ").strip()

        if op == "1":
            pendientes = listar_solicitudes_pendientes(session)
            if not pendientes:
                print("  (No hay solicitudes pendientes)")
            for s in pendientes:
                det = s.detalles[0]
                print(f"  #{s.id} | {s.estudiante.nombre} | "
                      f"{det.reactivo.nombre} | {det.cantidad_solicitada} "
                      f"{det.reactivo.unidad} | {s.laboratorio_destino}")

        elif op == "2":
            sid = int(input("ID de la solicitud: "))
            from models import Solicitud
            sol = session.query(Solicitud).get(sid)
            if not sol or sol.estado != "pendiente":
                print("❌ Solicitud no válida.")
                continue
            codigo = input("Código de barras del contenedor: ").strip()
            from reactivos import buscar_contenedor_por_codigo
            cont = buscar_contenedor_por_codigo(session, codigo)
            if not cont:
                print("❌ Contenedor no encontrado.")
                continue
            try:
                entregar_solicitud(session, sol, encargado, cont)
                print(f"✅ Solicitud #{sid} entregada.")
            except ValueError as e:
                print(f"❌ {e}")

        elif op == "3":
            codigo = input("Código de barras del contenedor: ").strip()
            from reactivos import buscar_contenedor_por_codigo
            cont = buscar_contenedor_por_codigo(session, codigo)
            if not cont:
                print("❌ Contenedor no encontrado.")
                continue
            for m in listar_movimientos_por_contenedor(session, cont):
                print(f"  [{m.fecha}] {m.tipo} | {m.cantidad} | {m.usuario.nombre}")

        elif op == "4":
            break


if __name__ == "__main__":
    init_db()
    session = SessionLocal()
    inicializar_datos_demo(session)
    menu_principal(session)
    session.close()