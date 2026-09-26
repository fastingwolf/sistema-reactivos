import pandas as pd
from database import SessionLocal
from reactivos import crear_reactivo, crear_contenedor
from models import Reactivo

ARCHIVO = "reactivos.xlsx"


def cargar_excel(ruta):
    print(f"[i] Leyendo {ruta}...")
    try:
        df = pd.read_excel(ruta, dtype=str)
    except FileNotFoundError:
        print(f"[!] No se encontró el archivo {ruta}")
        return

    # Normalizar encabezados
    df.columns = [c.strip().lower() for c in df.columns]

    obligatorias = ["nombre", "cas"]
    faltantes = [c for c in obligatorias if c not in df.columns]
    if faltantes:
        print(f"[!] Faltan columnas obligatorias: {faltantes}")
        print(f"    Columnas encontradas: {list(df.columns)}")
        return

    db = SessionLocal()
    total = len(df)
    creados = 0
    existentes = 0
    errores = 0

    for i, fila in df.iterrows():
        numero = i + 2
        try:
            nombre = str(fila.get("nombre", "")).strip()
            cas = str(fila.get("cas", "")).strip()

            if not nombre or not cas or nombre == "nan" or cas == "nan":
                print(f"[!] Fila {numero}: nombre o cas vacíos. Se omite.")
                errores += 1
                continue

            # Verificar duplicado por CAS
            existente = db.query(Reactivo).filter_by(cas=cas).first()
            if existente:
                print(f"[i] Fila {numero}: {nombre} (CAS {cas}) ya existe. Se omite.")
                existentes += 1
                continue

            formula = str(fila.get("formula", "")).strip()
            if formula == "nan":
                formula = ""

            unidad = str(fila.get("unidad", "g")).strip() or "g"
            if unidad == "nan":
                unidad = "g"

            peligrosidad = str(fila.get("peligrosidad", "baja")).strip().lower() or "baja"
            if peligrosidad == "nan" or peligrosidad not in ("baja", "media", "alta"):
                peligrosidad = "baja"

            # 1. Crear el reactivo
            reactivo = crear_reactivo(db, nombre, cas, formula,
                                      unidad, peligrosidad)

            # 2. Crear el contenedor (genera el código de barras automáticamente)
            cantidad_raw = fila.get("cantidad", None)
            codigo_generado = None
            if cantidad_raw is not None and str(cantidad_raw).strip() not in ("", "nan"):
                try:
                    cantidad = float(str(cantidad_raw).replace(",", "."))
                except ValueError:
                    print(f"[!] Fila {numero}: cantidad inválida '{cantidad_raw}'. Sin contenedor.")
                    cantidad = None

                if cantidad and cantidad > 0:
                    lote = str(fila.get("lote", "")).strip()
                    if lote == "nan":
                        lote = ""

                    ubicacion = str(fila.get("ubicacion", "Depósito")).strip()
                    if ubicacion == "nan" or not ubicacion:
                        ubicacion = "Depósito"

                    contenedor = crear_contenedor(db, reactivo, cantidad,
                                                  lote, ubicacion=ubicacion)
                    codigo_generado = contenedor.codigo_barras

            if codigo_generado:
                print(f"[+] Fila {numero}: {nombre} creado | contenedor {codigo_generado}")
            else:
                print(f"[+] Fila {numero}: {nombre} creado (sin contenedor)")

            creados += 1

        except Exception as e:
            print(f"[!] Fila {numero}: error → {e}")
            errores += 1

    db.close()

    print()
    print("=" * 50)
    print(f"Total de filas:       {total}")
    print(f"Reactivos creados:    {creados}")
    print(f"Ya existían:          {existentes}")
    print(f"Errores:              {errores}")
    print("=" * 50)


if __name__ == "__main__":
    cargar_excel(ARCHIVO)