"""Anima una captura estática: cursor que se desplaza, halo sobre el objetivo, onda al hacer clic,
tipeo y resaltado con foco y nota.

Se dibuja cuadro a cuadro con Pillow y se envía como video crudo a ffmpeg.

Acciones soportadas (lista en guion.json, campo "acciones" del paso):
    {"tipo": "click",    "x": 957, "y": 636}
    {"tipo": "senalar",  "x": 1390, "y": 170}                 # halo sin clic
    {"tipo": "escribir", "x": 884, "y": 451, "texto": "...", "ancho": 195}
    {"tipo": "esperar",  "seg": 0.5}
    {"tipo": "resaltar", "caja": [x1, y1, x2, y2], "nota": "Texto", "seg": 1.8}   # foco + nota
    {"tipo": "resaltar", "zona": "oblig", ...}                # zona con nombre de una lámina

Cualquier acción acepta "cuando": "<palabras de la narración>". La acción espera hasta el momento
en que la voz dice esas palabras (se calcula con el .srt del paso). Sin "cuando", corre a
continuación de la anterior. Si ninguna acción lo usa, la animación queda al final del audio.
En "nota", "\\n" separa líneas.
"""

from __future__ import annotations

import math
import subprocess
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from PIL import Image, ImageDraw, ImageFont

FPS = 30
SS = 3  # supersampling para bordes suaves

COLOR_HALO = (255, 196, 0)
COLOR_TEXTO = (55, 55, 55)
COLOR_FOCO = (255, 184, 0)
COLOR_NOTA = (22, 52, 84)
FUENTE = Path("C:/Windows/Fonts/segoeui.ttf")
FUENTE_SEMI = Path("C:/Windows/Fonts/seguisb.ttf")

Caja = tuple[float, float, float, float]


def _fuente(ruta: Path, tam: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(str(ruta), tam)
    except OSError:
        return ImageFont.load_default(tam)


@dataclass
class Estado:
    x: float
    y: float
    halo: float = 0.0          # 0..1 opacidad del halo
    onda: float | None = None  # 0..1 progreso de la onda de clic
    presionado: bool = False


def _ease(t: float) -> float:
    return 4 * t**3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def _cuadros(seg: float) -> int:
    return max(1, round(seg * FPS))


# --------------------------------------------------------------------------- sprites y capas


def _sprite_cursor(alto: int = 34) -> Image.Image:
    puntos = [(0, 0), (0, 17), (4, 13.2), (7, 20), (9.6, 18.9), (6.7, 12.3), (12, 12.3)]
    esc = alto / 20 * SS
    borde = 3 * SS
    img = Image.new("RGBA", (int(13 * esc) + 2 * borde, int(21 * esc) + 2 * borde), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    poli = [(borde + px * esc, borde + py * esc) for px, py in puntos]
    sombra = [(px + 2 * SS, py + 3 * SS) for px, py in poli]
    d.polygon(sombra, fill=(0, 0, 0, 70))
    d.polygon(poli, fill=(255, 255, 255, 255), outline=(20, 20, 20, 255), width=int(1.6 * SS))
    return img.resize((img.width // SS, img.height // SS), Image.LANCZOS)


def _circulo(radio: float, relleno: tuple[int, ...] | None, borde: tuple[int, ...] | None, ancho: float) -> Image.Image:
    lado = math.ceil(radio + ancho + 2) * 2
    img = Image.new("RGBA", (lado * SS, lado * SS), (0, 0, 0, 0))
    c = lado * SS / 2
    r = radio * SS
    ImageDraw.Draw(img).ellipse(
        (c - r, c - r, c + r, c + r), fill=relleno, outline=borde, width=int(ancho * SS) if borde else 0
    )
    return img.resize((lado, lado), Image.LANCZOS)


def _pegar_centrado(frame: Image.Image, sprite: Image.Image, x: float, y: float) -> None:
    frame.alpha_composite(sprite, (int(x - sprite.width / 2), int(y - sprite.height / 2)))


def _rotulo(frame: Image.Image, texto: str) -> None:
    """Etiqueta fija arriba a la izquierda, por ejemplo "Paso 4 de 6 · Apoderado económico"."""
    f = _fuente(FUENTE_SEMI, 26)
    w = f.getlength(texto) + 70
    capa = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    d.rounded_rectangle((28, 24, 28 + w, 74), 25, fill=(*COLOR_NOTA, 235))
    d.ellipse((48, 43, 60, 55), fill=(*COLOR_FOCO, 255))
    d.text((74, 49), texto, font=f, fill=(255, 255, 255, 255), anchor="lm")
    frame.alpha_composite(capa)


def _capa_foco(tam: tuple[int, int], caja: Caja, nota: str | None) -> Image.Image:
    """Oscurece la pantalla salvo la caja, le pone un borde y, si hay nota, la dibuja al costado."""
    ancho, alto = tam
    pad = 8
    x1, y1, x2, y2 = caja[0] - pad, caja[1] - pad, caja[2] + pad, caja[3] + pad
    capa = Image.new("RGBA", tam, (10, 20, 35, 125))
    agujero = Image.new("L", tam, 0)
    ImageDraw.Draw(agujero).rounded_rectangle((x1, y1, x2, y2), 12, fill=255)
    capa.putalpha(Image.composite(Image.new("L", tam, 0), capa.getchannel("A"), agujero))
    d = ImageDraw.Draw(capa)
    d.rounded_rectangle((x1, y1, x2, y2), 12, outline=(*COLOR_FOCO, 255), width=4)
    if not nota:
        return capa

    f = _fuente(FUENTE_SEMI, 27)
    lineas = nota.split("\n")
    tw = max(f.getlength(linea) for linea in lineas) + 44
    th = len(lineas) * 36 + 26
    cy = (y1 + y2) / 2
    cx = (x1 + x2) / 2
    if x2 + 30 + tw < ancho - 20:          # a la derecha
        bx, by, punta = x2 + 30, cy - th / 2, "izq"
    elif x1 - 30 - tw > 20:                # a la izquierda
        bx, by, punta = x1 - 30 - tw, cy - th / 2, "der"
    elif y2 + 30 + th < alto - 150:        # abajo, sin tapar los subtítulos
        bx, by, punta = cx - tw / 2, y2 + 30, "arr"
    else:                                  # arriba
        bx, by, punta = cx - tw / 2, y1 - 30 - th, "aba"
    bx = min(max(20, bx), ancho - tw - 20)
    by = min(max(20, by), alto - th - 20)
    d.rounded_rectangle((bx, by, bx + tw, by + th), 14, fill=(*COLOR_NOTA, 248), outline=(*COLOR_FOCO, 255), width=2)
    py = min(max(by + 20, cy), by + th - 20)
    px = min(max(bx + 24, cx), bx + tw - 24)
    flecha = {
        "izq": [(bx + 1, py - 12), (bx - 16, py), (bx + 1, py + 12)],
        "der": [(bx + tw - 1, py - 12), (bx + tw + 16, py), (bx + tw - 1, py + 12)],
        "arr": [(px - 12, by + 1), (px, by - 16), (px + 12, by + 1)],
        "aba": [(px - 12, by + th - 1), (px, by + th + 16), (px + 12, by + th - 1)],
    }[punta]
    d.polygon(flecha, fill=(*COLOR_FOCO, 255))
    ty = by + 13
    for linea in lineas:
        d.text((bx + 22, ty), linea, font=f, fill=(255, 255, 255, 255))
        ty += 36
    return capa


# --------------------------------------------------------------------------- sincronía con la voz


def _normalizar(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn")


def momento(subs: list[tuple[float, float, str]], frase: str) -> float | None:
    """Segundo aproximado en que la narración dice `frase` (interpola dentro de la oración)."""
    buscada = _normalizar(frase)
    for inicio, fin, texto in subs:
        t = _normalizar(texto)
        pos = t.find(buscada)
        if pos >= 0:
            return inicio + (fin - inicio) * pos / max(1, len(t))
    return None


# --------------------------------------------------------------------------- render


class Animador:
    def __init__(
        self,
        captura: Path,
        inicio_cursor: tuple[float, float],
        rotulo: str | None = None,
        cursor: bool = True,
        zonas: dict[str, Caja] | None = None,
    ) -> None:
        self.base = Image.open(captura).convert("RGBA")
        if rotulo:
            _rotulo(self.base, rotulo)
        self.lienzo = self.base.copy()  # acumula lo escrito en campos
        self.cursor = _sprite_cursor()
        self.ver_cursor = cursor
        self.zonas = zonas or {}
        self.estado = Estado(*inicio_cursor)
        self.foco: tuple[Image.Image, float] | None = None  # capa de resaltado y su opacidad
        self.fuente = _fuente(FUENTE, 21)

    @property
    def tamano(self) -> tuple[int, int]:
        return self.base.size

    def dibujar(self) -> bytes:
        e = self.estado
        frame = self.lienzo.copy()
        if self.foco and self.foco[1] > 0:
            capa, opacidad = self.foco
            if opacidad < 1:
                capa = capa.copy()
                capa.putalpha(capa.getchannel("A").point(lambda a: int(a * opacidad)))
            frame.alpha_composite(capa)
        if self.ver_cursor:
            if e.halo > 0:
                alfa = int(95 * e.halo)
                _pegar_centrado(frame, _circulo(26, (*COLOR_HALO, alfa), (*COLOR_HALO, min(255, alfa * 2)), 2), e.x, e.y)
            if e.onda is not None:
                r = 14 + 50 * _ease(e.onda)
                alfa = int(255 * (1 - e.onda) ** 0.7)
                _pegar_centrado(frame, _circulo(r, (*COLOR_HALO, alfa // 5), (*COLOR_HALO, alfa), 6), e.x, e.y)
            cursor = self.cursor
            if e.presionado:
                cursor = cursor.resize((int(cursor.width * 0.88), int(cursor.height * 0.88)), Image.LANCZOS)
            frame.alpha_composite(cursor, (int(e.x - 3), int(e.y - 3)))  # la punta queda sobre (x, y)
        return frame.convert("RGB").tobytes()

    # Cada acción es un generador de cuadros que va modificando el estado.

    def mover(self, x: float, y: float) -> Iterator[bytes]:
        e = self.estado
        x0, y0 = e.x, e.y
        distancia = math.hypot(x - x0, y - y0)
        if distancia < 2:
            return
        n = _cuadros(min(1.1, 0.45 + distancia / 1800))
        curva = min(80.0, distancia * 0.12)  # leve arco, más natural que una recta
        for i in range(1, n + 1):
            t = _ease(i / n)
            arco = math.sin(math.pi * t) * curva
            e.x = x0 + (x - x0) * t
            e.y = y0 + (y - y0) * t - arco
            yield self.dibujar()

    def mostrar_halo(self, seg: float = 0.25) -> Iterator[bytes]:
        n = _cuadros(seg)
        for i in range(1, n + 1):
            self.estado.halo = i / n
            yield self.dibujar()

    def ocultar_halo(self, seg: float = 0.25) -> Iterator[bytes]:
        n = _cuadros(seg)
        for i in range(n - 1, -1, -1):
            self.estado.halo = i / n
            yield self.dibujar()

    def esperar(self, seg: float) -> Iterator[bytes]:
        for _ in range(_cuadros(seg)):
            yield self.dibujar()

    def click(self, x: float, y: float) -> Iterator[bytes]:
        yield from self.mover(x, y)
        yield from self.mostrar_halo()
        yield from self.esperar(0.25)
        e = self.estado
        e.presionado = True
        n = _cuadros(0.55)
        for i in range(n):
            e.onda = i / n
            if i == 4:
                e.presionado = False
            yield self.dibujar()
        e.onda = None
        yield from self.ocultar_halo()

    def senalar(self, x: float, y: float) -> Iterator[bytes]:
        yield from self.mover(x, y)
        yield from self.mostrar_halo()
        yield from self.esperar(0.9)
        yield from self.ocultar_halo()

    def escribir(self, x: float, y: float, texto: str, ancho: float) -> Iterator[bytes]:
        # Tapa el placeholder con el color de fondo del campo y tipea carácter a carácter.
        alto = 30
        fondo = self.base.getpixel((int(x + ancho - 4), int(y)))
        caja = (x - 2, y - alto / 2, x + ancho, y + alto / 2)
        for i in range(1, len(texto) + 1):
            self.lienzo = self.base.copy() if i == 1 else self.lienzo
            d = ImageDraw.Draw(self.lienzo)
            d.rectangle(caja, fill=fondo)
            d.text((x, y), texto[:i], font=self.fuente, fill=COLOR_TEXTO, anchor="lm")
            yield from self.esperar(1 / 14)
        self.base = self.lienzo.copy()

    def resaltar(self, caja: Caja, nota: str | None, seg: float) -> Iterator[bytes]:
        capa = _capa_foco(self.base.size, caja, nota)
        n = _cuadros(0.35)
        for i in range(1, n + 1):
            self.foco = (capa, _ease(i / n))
            yield self.dibujar()
        yield from self.esperar(seg)
        for i in range(n - 1, -1, -1):
            self.foco = (capa, _ease(i / n))
            yield self.dibujar()
        self.foco = None

    def ejecutar(self, accion: dict[str, Any]) -> Iterator[bytes]:
        tipo = accion["tipo"]
        if tipo == "click":
            yield from self.click(accion["x"], accion["y"])
        elif tipo == "senalar":
            yield from self.senalar(accion["x"], accion["y"])
        elif tipo == "escribir":
            yield from self.escribir(accion["x"], accion["y"], accion["texto"], accion.get("ancho", 200))
        elif tipo == "esperar":
            yield from self.esperar(float(accion["seg"]))
        elif tipo == "resaltar":
            if "zona" in accion:
                if accion["zona"] not in self.zonas:
                    raise ValueError(f"zona desconocida: {accion['zona']} (hay: {', '.join(self.zonas)})")
                caja = self.zonas[accion["zona"]]
            else:
                caja = accion["caja"]
            yield from self.resaltar(tuple(caja), accion.get("nota"), float(accion.get("seg", 1.8)))
        else:
            raise ValueError(f"acción desconocida: {tipo}")


def renderizar(
    captura: Path,
    acciones: list[dict[str, Any]],
    duracion_audio: float,
    salida: Path,
    inicio_cursor: tuple[float, float],
    inicio: float | None = None,
    subs: list[tuple[float, float, str]] | None = None,
    rotulo: str | None = None,
    cursor: bool = True,
    zonas: dict[str, Caja] | None = None,
) -> tuple[float, float]:
    """Genera el clip y devuelve la posición final del cursor (para encadenar con el paso siguiente)."""
    anim = Animador(captura, inicio_cursor, rotulo, cursor, zonas)
    primero = anim.dibujar()
    cuadros: list[bytes] = []
    sincronizado = any("cuando" in a for a in acciones)
    for accion in acciones:
        if "cuando" in accion:
            t = momento(subs or [], accion["cuando"])
            if t is None:
                raise ValueError(f"'cuando': no se encontró «{accion['cuando']}» en la narración")
            # Los clics arrancan antes para que el cursor llegue justo cuando la voz lo nombra.
            adelanto = 0.6 if accion["tipo"] in ("click", "senalar") else 0.1
            falta = (t - adelanto) - (len(cuadros) + 1) / FPS
            if falta > 0:
                cuadros += list(anim.esperar(falta))
        cuadros += list(anim.ejecutar(accion))
    cuadros += list(anim.esperar(0.4))
    dur_anim = len(cuadros) / FPS
    if sincronizado:
        espera = 0.0
    else:
        # Por defecto la animación termina justo antes de que acabe la narración.
        espera = inicio if inicio is not None else max(0.5, duracion_audio - dur_anim - 0.2)
    ancho, alto = anim.tamano
    filtro = f"tpad=start_mode=clone:start_duration={espera:.3f}" if espera > 0 else "null"
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{ancho}x{alto}", "-r", str(FPS), "-i", "-",
        "-vf", filtro,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
        str(salida),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    assert proc.stdin is not None
    try:
        for c in [primero, *cuadros]:
            proc.stdin.write(c)
        proc.stdin.close()
    except BrokenPipeError:
        pass
    _, err = proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg falló al animar {captura.name}: {err.decode(errors='replace')[-1500:]}")
    return anim.estado.x, anim.estado.y
