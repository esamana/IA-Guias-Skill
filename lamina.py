"""Láminas explicativas (1920x1080) dibujadas con Pillow, con el estilo visual de MOL.

Sirven para la portada, el cierre y las pantallas que todavía no se capturaron. En guion.json:

    "lamina": {
      "antetitulo": "Paso 5 de 6",
      "titulo": "Cargos y pagos",
      "subtitulo": "Texto breve bajo el título",
      "tarjetas": [
        {"id": "oblig", "etiqueta": "1", "titulo": "Cargos obligatorios", "texto": "...", "color": "verde"}
      ],
      "pie": {"id": "pie", "texto": "..."}
    }

`dibujar_lamina` devuelve la imagen y las zonas con nombre (id de cada tarjeta, "pie", "titulo"),
que las acciones `resaltar` pueden usar con "zona" en vez de coordenadas.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

ANCHO, ALTO = 1920, 1080
FUENTES = Path("C:/Windows/Fonts")

FONDO = (246, 248, 251)
AZUL = (43, 123, 185)
TEXTO = (52, 61, 74)
TEXTO_SUAVE = (110, 120, 135)
COLORES = {
    "azul": (43, 123, 185),
    "verde": (46, 160, 90),
    "ambar": (230, 160, 20),
    "gris": (140, 150, 165),
    "morado": (110, 90, 190),
}

Zona = tuple[int, int, int, int]


def fuente(peso: str, tam: int) -> ImageFont.FreeTypeFont:
    archivo = {"normal": "segoeui.ttf", "semi": "seguisb.ttf", "bold": "segoeuib.ttf"}[peso]
    try:
        return ImageFont.truetype(str(FUENTES / archivo), tam)
    except OSError:
        return ImageFont.load_default(tam)


def envolver(texto: str, f: ImageFont.FreeTypeFont, ancho: float) -> list[str]:
    lineas: list[str] = []
    for parrafo in texto.split("\n"):
        actual = ""
        for palabra in parrafo.split():
            prueba = f"{actual} {palabra}".strip()
            if f.getlength(prueba) <= ancho or not actual:
                actual = prueba
            else:
                lineas.append(actual)
                actual = palabra
        lineas.append(actual)
    return lineas


def _texto_centrado(d: ImageDraw.ImageDraw, y: float, texto: str, f: ImageFont.FreeTypeFont, color: tuple) -> float:
    for linea in envolver(texto, f, 1300):
        d.text((ANCHO / 2, y), linea, font=f, fill=color, anchor="mt")
        y += f.size * 1.3
    return y


def dibujar_lamina(spec: dict[str, Any]) -> tuple[Image.Image, dict[str, Zona]]:
    img = Image.new("RGB", (ANCHO, ALTO), FONDO)
    d = ImageDraw.Draw(img)
    zonas: dict[str, Zona] = {}

    # Franja superior, como el encabezado de Alexia.
    d.rectangle((0, 0, ANCHO, 74), fill=(255, 255, 255))
    d.line((0, 74, ANCHO, 74), fill=(225, 230, 236), width=2)
    d.text((ANCHO / 2, 37), spec.get("marca", "Matrícula Online 2027"), font=fuente("semi", 26), fill=AZUL, anchor="mm")

    tarjetas = spec.get("tarjetas", [])
    y = 165 if tarjetas else 330
    if spec.get("antetitulo"):
        f = fuente("bold", 24)
        texto = spec["antetitulo"].upper()
        w = f.getlength(texto) + 44
        d.rounded_rectangle((ANCHO / 2 - w / 2, y, ANCHO / 2 + w / 2, y + 44), 22, fill=(225, 238, 248))
        d.text((ANCHO / 2, y + 22), texto, font=f, fill=AZUL, anchor="mm")
        y += 72
    y0 = y
    y = _texto_centrado(d, y, spec["titulo"], fuente("semi", 64), AZUL)
    zonas["titulo"] = (420, int(y0) - 10, 1500, int(y) + 5)
    if spec.get("subtitulo"):
        y = _texto_centrado(d, y + 14, spec["subtitulo"], fuente("normal", 31), TEXTO_SUAVE)

    if tarjetas:
        y = _dibujar_tarjetas(d, tarjetas, y + 50, zonas)

    pie = spec.get("pie")
    if pie:
        f = fuente("semi", 29)
        lineas = envolver(pie["texto"], f, 1180)
        alto = len(lineas) * 40 + 44
        top = max(y + 40, 720) if tarjetas else y + 60
        caja = (330, int(top), 1590, int(top + alto))
        d.rounded_rectangle(caja, 18, fill=(225, 238, 248), outline=(190, 215, 236), width=2)
        ty = top + 22
        for linea in lineas:
            d.text((ANCHO / 2, ty), linea, font=f, fill=(30, 85, 135), anchor="mt")
            ty += 40
        zonas[pie.get("id", "pie")] = caja
    return img, zonas


def _dibujar_tarjetas(d: ImageDraw.ImageDraw, tarjetas: list[dict[str, Any]], y: float, zonas: dict[str, Zona]) -> float:
    por_fila = 3 if len(tarjetas) in (3, 5, 6) or len(tarjetas) > 4 else min(2, len(tarjetas))
    sep = 36
    ancho = min(560, (1500 - sep * (por_fila - 1)) / por_fila)
    f_tit, f_txt, f_num = fuente("semi", 34), fuente("normal", 27), fuente("bold", 26)

    filas = [tarjetas[i : i + por_fila] for i in range(0, len(tarjetas), por_fila)]
    for fila in filas:
        medidas = []
        for t in fila:
            tit = envolver(t["titulo"], f_tit, ancho - 70)
            txt = envolver(t.get("texto", ""), f_txt, ancho - 70) if t.get("texto") else []
            medidas.append((tit, txt))
        alto = max(
            34 + (62 if t.get("etiqueta") else 0) + len(tit) * 44 + (12 + len(txt) * 37 if txt else 0) + 30
            for t, (tit, txt) in zip(fila, medidas)
        )
        total = len(fila) * ancho + (len(fila) - 1) * sep
        x = (ANCHO - total) / 2
        for t, (tit, txt) in zip(fila, medidas):
            color = COLORES.get(t.get("color", "azul"), AZUL)
            caja = (int(x), int(y), int(x + ancho), int(y + alto))
            d.rounded_rectangle((caja[0] + 3, caja[1] + 6, caja[2] + 3, caja[3] + 6), 20, fill=(232, 236, 242))
            d.rounded_rectangle(caja, 20, fill=(255, 255, 255), outline=(222, 228, 236), width=2)
            d.rounded_rectangle((caja[0], caja[1], caja[0] + 10, caja[3]), 5, fill=color)
            ty = y + 34
            tx = x + 44
            if t.get("etiqueta"):
                d.ellipse((tx, ty, tx + 46, ty + 46), fill=color)
                d.text((tx + 23, ty + 23), str(t["etiqueta"]), font=f_num, fill=(255, 255, 255), anchor="mm")
                ty += 62
            for linea in tit:
                d.text((tx, ty), linea, font=f_tit, fill=TEXTO)
                ty += 44
            ty += 12
            for linea in txt:
                d.text((tx, ty), linea, font=f_txt, fill=TEXTO_SUAVE)
                ty += 37
            zonas[t.get("id", f"tarjeta{len(zonas)}")] = caja
            x += ancho + sep
        y = max(z[3] for z in zonas.values()) + sep
    return y - sep


def guardar_lamina(spec: dict[str, Any], destino: Path) -> dict[str, Zona]:
    img, zonas = dibujar_lamina(spec)
    destino.parent.mkdir(parents=True, exist_ok=True)
    img.save(destino)
    return zonas
