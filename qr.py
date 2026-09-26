import io
import qrcode
from fastapi import Response
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CARPETA_QR = BASE_DIR / "static" / "qr"
CARPETA_QR.mkdir(parents=True, exist_ok=True)


def generar_qr_png(contenido: str, tamaño: int = 300) -> bytes:
    """Genera un QR en PNG y lo devuelve como bytes."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(contenido)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer.getvalue()


def guardar_qr_archivo(contenido: str, nombre_archivo: str) -> Path:
    """Guarda el QR en static/qr/<nombre_archivo>.png y devuelve la ruta."""
    ruta = CARPETA_QR / f"{nombre_archivo}.png"
    datos = generar_qr_png(contenido)
    ruta.write_bytes(datos)
    return ruta


def respuesta_qr(contenido: str) -> Response:
    """Devuelve el QR como respuesta HTTP (para servirlo directo)."""
    datos = generar_qr_png(contenido)
    return Response(content=datos, media_type="image/png")