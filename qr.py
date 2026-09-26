import io
import qrcode
from fastapi import Response


def generar_qr_png(contenido: str, tamaño: int = 300) -> bytes:
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


def respuesta_qr(contenido: str) -> Response:
    datos = generar_qr_png(contenido)
    return Response(content=datos, media_type="image/png")