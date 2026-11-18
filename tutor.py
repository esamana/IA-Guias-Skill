"""Tutoriales en video con voz IA: guion JSON -> narración (edge-tts) -> clips -> MP4 final.

Cada tutorial es un proyecto en proyectos/<nombre>/ con su guion.json. Uso:
    python tutor.py nuevo comunicados                 # crea proyectos/comunicados/
    python tutor.py -p matricula-online voces --filtro es-CL
    python tutor.py -p matricula-online audio [--paso 03] [--forzar]
    python tutor.py -p matricula-online duraciones
    python tutor.py -p matricula-online capturas [--paso 04]   # anima capturas -> clips
    python tutor.py -p matricula-online grilla --paso 04       # captura con grilla para ubicar clics
    python tutor.py -p matricula-online ensamblar [--subs quemados|archivo|no]
    python tutor.py -p matricula-online todo [--subs ...]      # audio + capturas + ensamblar
    python tutor.py -p matricula-online dummy [--forzar]       # clips de prueba sin grabar
    python tutor.py -p matricula-online exportar               # guía en Markdown para el RAG del chatbot
"""

from __future__ import annotations

import argparse
import asyncio
import glob
import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import edge_tts

RAIZ = Path(__file__).resolve().parent
PROYECTOS = RAIZ / "proyectos"

ANCHO, ALTO, FPS = 1920, 1080, 30
LOUDNORM = "loudnorm=I=-16:TP=-1.5:LRA=11"
WINGET_FFMPEG = "winget install --id Gyan.FFmpeg -e"
# En ASS el alfa va invertido: &H40 = ~75 % opaco. Con BorderStyle=3 el "Outline" es el relleno de la caja.
# Colores en &HAABBGGRR. Caja azul noche, como las notas de animar.py.
ESTILO_SUBS = (
    # Ojo: los márgenes y el tamaño van en la escala de PlayRes del SRT (384x288), no en píxeles.
    "FontName=Segoe UI Semibold,FontSize=12,PrimaryColour=&H00FFFFFF,BorderStyle=3,"
    "OutlineColour=&H30543416,BackColour=&H30543416,Outline=3,Shadow=0,MarginV=14,MarginL=40,MarginR=40"
)
# Un subtítulo profesional no supera ~2 líneas: se cortan las oraciones largas.
MAX_CARACTERES_SUB = 84

log = logging.getLogger("tutor")


class PipelineError(Exception):
    """Error esperado (archivo faltante, guion inválido, ffmpeg falló...)."""


# --------------------------------------------------------------------------- proyecto


@dataclass(frozen=True)
class Proyecto:
    dir: Path

    @property
    def nombre(self) -> str:
        return self.dir.name

    @property
    def guion(self) -> Path:
        return self.dir / "guion.json"

    def sub(self, nombre: str) -> Path:
        return self.dir / nombre

    @property
    def clips(self) -> Path:
        return self.sub("clips")

    @property
    def audio(self) -> Path:
        return self.sub("audio")

    @property
    def subs(self) -> Path:
        return self.sub("subs")

    @property
    def output(self) -> Path:
        return self.sub("output")

    @property
    def capturas(self) -> Path:
        return self.sub("capturas")

    @property
    def tmp(self) -> Path:
        return self.output / "tmp"

    @property
    def cache(self) -> Path:
        return self.audio / ".cache.json"

    def rel(self, ruta: Path) -> str:
        return ruta.relative_to(self.dir).as_posix()


def resolver_proyecto(valor: str | None) -> Proyecto:
    """-p acepta un nombre de proyectos/ o una ruta; sin -p se usa la carpeta actual."""
    if valor is None:
        candidato = Path.cwd()
    elif (PROYECTOS / valor).is_dir():
        candidato = PROYECTOS / valor
    else:
        candidato = Path(valor).resolve()
    if not (candidato / "guion.json").exists():
        disponibles = ", ".join(sorted(g.parent.name for g in PROYECTOS.glob("*/guion.json")))
        raise PipelineError(
            f"no hay guion.json en {candidato}. Usá -p <proyecto> (disponibles: {disponibles or 'ninguno'}) "
            "o creá uno con 'python tutor.py nuevo <nombre>'"
        )
    return Proyecto(candidato)


# --------------------------------------------------------------------------- guion


@dataclass(frozen=True)
class Paso:
    proyecto: Proyecto
    id: str
    titulo: str
    texto: str
    voz: str
    rate: str
    pitch: str
    captura: str | None = None
    acciones: list[dict[str, Any]] = field(default_factory=list)
    inicio_animacion: float | None = None
    lamina: dict[str, Any] | None = None  # si está, la captura se dibuja con lamina.py
    rotulo: str | None = None  # etiqueta fija arriba a la izquierda
    cursor: bool = True

    @property
    def nombre(self) -> str:
        return f"paso{self.id}"

    @property
    def mp3(self) -> Path:
        return self.proyecto.audio / f"{self.nombre}.mp3"

    @property
    def srt(self) -> Path:
        return self.proyecto.subs / f"{self.nombre}.srt"

    @property
    def clip(self) -> Path:
        return self.proyecto.clips / f"{self.nombre}.mp4"

    @property
    def ruta_captura(self) -> Path | None:
        return self.proyecto.dir / self.captura if self.captura else None

    def hash_tts(self) -> str:
        datos = json.dumps([self.texto, self.voz, self.rate, self.pitch], ensure_ascii=False)
        return hashlib.sha256(datos.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Guion:
    proyecto: Proyecto
    titulo: str
    pausa_final_seg: float
    pasos: list[Paso]

    @property
    def salida(self) -> Path:
        nombre = re.sub(r'[<>:"/\\|?*]', "", self.titulo).strip() or self.proyecto.nombre
        return self.proyecto.output / f"{nombre}.mp4"

    def filtrar(self, paso_id: str | None) -> list[Paso]:
        if paso_id is None:
            return self.pasos
        elegidos = [p for p in self.pasos if p.id == paso_id.zfill(2)]
        if not elegidos:
            raise PipelineError(f"el paso '{paso_id}' no existe en guion.json")
        return elegidos


def cargar_guion(proyecto: Proyecto) -> Guion:
    try:
        datos = json.loads(proyecto.guion.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise PipelineError(f"guion.json no es JSON válido: {e}") from e

    voz = datos.get("voz", "es-CL-CatalinaNeural")
    rate = datos.get("rate", "+0%")
    pitch = datos.get("pitch", "+0Hz")
    pasos = [
        Paso(
            proyecto=proyecto,
            id=str(p["id"]).zfill(2),
            titulo=p.get("titulo", ""),
            texto=p["texto"].strip(),
            voz=p.get("voz", voz),
            rate=p.get("rate", rate),
            pitch=p.get("pitch", pitch),
            captura=p.get("captura") or (f"capturas/lamina{str(p['id']).zfill(2)}.png" if p.get("lamina") else None),
            acciones=p.get("acciones", []),
            inicio_animacion=p.get("inicio_animacion"),
            lamina=p.get("lamina"),
            rotulo=p.get("rotulo"),
            cursor=p.get("cursor", not p.get("lamina")),
        )
        for p in datos.get("pasos", [])
    ]
    if not pasos:
        raise PipelineError("guion.json no tiene pasos")
    ids = [p.id for p in pasos]
    if len(ids) != len(set(ids)):
        raise PipelineError("guion.json tiene ids de paso repetidos")
    return Guion(
        proyecto=proyecto,
        titulo=datos.get("titulo", proyecto.nombre),
        pausa_final_seg=float(datos.get("pausa_final_seg", 0.8)),
        pasos=pasos,
    )


PLANTILLA_GUION = {
    "titulo": "Nuevo tutorial de Alexia",
    "voz": "es-CL-CatalinaNeural",
    "rate": "-5%",
    "pitch": "+0Hz",
    "pausa_final_seg": 0.8,
    "pasos": [
        {
            "id": "01",
            "titulo": "Ingreso",
            "texto": "Ingresa a Alexia con tu usuario y contraseña.",
            "captura": "capturas/paso01.png",
            "acciones": [{"tipo": "click", "x": 957, "y": 636}],
        },
        {
            "id": "02",
            "titulo": "Segundo paso",
            "texto": "Texto de la narración del segundo paso.",
        },
    ],
}


def crear_proyecto(nombre: str) -> Proyecto:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", nombre):
        raise PipelineError("el nombre del proyecto va en minúsculas, números y guiones (ej: comunicados-envio)")
    destino = PROYECTOS / nombre
    if destino.exists():
        raise PipelineError(f"ya existe proyectos/{nombre}")
    for sub in ("capturas", "clips", "audio", "subs", "output"):
        (destino / sub).mkdir(parents=True)
    (destino / "guion.json").write_text(json.dumps(PLANTILLA_GUION, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    log.info("Creado proyectos/%s. Editá su guion.json y poné las capturas en capturas/ o los clips en clips/.", nombre)
    return Proyecto(destino)


# --------------------------------------------------------------------------- ffmpeg


def asegurar_ffmpeg() -> None:
    """Busca ffmpeg en el PATH y, si no está, en la carpeta de winget (sirve sin reabrir la terminal)."""
    if shutil.which("ffmpeg") and shutil.which("ffprobe"):
        return
    patron = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg*\*\bin\ffmpeg.exe")
    encontrados = glob.glob(patron)
    if encontrados:
        os.environ["PATH"] = str(Path(encontrados[0]).parent) + os.pathsep + os.environ["PATH"]
        return
    raise PipelineError(f"no se encontró ffmpeg/ffprobe. Instalalo con:\n    {WINGET_FFMPEG}")


def ejecutar(cmd: list[str], cwd: Path | None = None) -> None:
    log.debug("$ %s", " ".join(cmd))
    res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if res.returncode != 0:
        raise PipelineError(f"falló {cmd[0]}:\n{res.stderr.strip()[-2000:]}")


def ffmpeg(*args: str, cwd: Path | None = None) -> None:
    ejecutar(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], cwd=cwd)


def duracion(ruta: Path) -> float:
    if not ruta.exists():
        raise PipelineError(f"falta {ruta}")
    res = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(ruta)],
        capture_output=True,
        text=True,
    )
    try:
        return float(res.stdout.strip())
    except ValueError as e:
        raise PipelineError(f"ffprobe no pudo leer la duración de {ruta.name}: {res.stderr.strip()}") from e


# --------------------------------------------------------------------------- srt


@dataclass(frozen=True)
class Subtitulo:
    inicio: float
    fin: float
    texto: str


_TIEMPO = r"(\d+):(\d{2}):(\d{2})[,.](\d{3})"
_BLOQUE = re.compile(rf"{_TIEMPO}\s*-->\s*{_TIEMPO}\s*\n(.*?)(?:\n\s*\n|\Z)", re.S)


def _seg(h: str, m: str, s: str, ms: str) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def _fmt(t: float) -> str:
    ms = round(t * 1000)
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def leer_srt(ruta: Path) -> list[Subtitulo]:
    contenido = ruta.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    return [
        Subtitulo(_seg(*g[0:4]), _seg(*g[4:8]), g[8].strip())
        for g in _BLOQUE.findall(contenido)
        if g[8].strip()
    ]


def escribir_srt(ruta: Path, subs: list[Subtitulo]) -> None:
    bloques = [f"{i}\n{_fmt(s.inicio)} --> {_fmt(s.fin)}\n{s.texto}\n" for i, s in enumerate(subs, 1)]
    ruta.write_text("\n".join(bloques), encoding="utf-8")


def partir_subtitulo(s: Subtitulo, maximo: int = MAX_CARACTERES_SUB) -> list[Subtitulo]:
    """Corta una oración larga en bloques de ~2 líneas, preferentemente en comas o dos puntos.

    El tiempo se reparte en proporción a los caracteres de cada bloque.
    """
    texto = " ".join(s.texto.split())
    if len(texto) <= maximo:
        return [Subtitulo(s.inicio, s.fin, texto)]
    partes: list[str] = []
    resto = texto
    while len(resto) > maximo:
        ventana = resto[: maximo + 1]
        corte = max(ventana.rfind(", "), ventana.rfind(": "), ventana.rfind("; "))
        if corte < maximo * 0.4:  # coma muy al principio: mejor cortar en un espacio cerca del medio
            mitad = min(maximo, len(resto) // 2 + 10)
            corte = resto.rfind(" ", 0, mitad)
            partes.append(resto[:corte].strip())
            resto = resto[corte:].strip()
        else:
            partes.append(resto[: corte + 1].strip())
            resto = resto[corte + 1 :].strip()
    partes.append(resto)
    total = sum(len(p) for p in partes)
    bloques, t = [], s.inicio
    for p in partes:
        dur = (s.fin - s.inicio) * len(p) / total
        bloques.append(Subtitulo(t, t + dur, p))
        t += dur
    return bloques


def combinar_srt(pasos: list[Paso], offsets: list[float], destino: Path) -> None:
    todos: list[Subtitulo] = []
    for paso, offset in zip(pasos, offsets):
        if not paso.srt.exists():
            raise PipelineError(f"falta subs/{paso.srt.name} (corré el comando 'audio')")
        for s in leer_srt(paso.srt):
            todos += partir_subtitulo(Subtitulo(s.inicio + offset, s.fin + offset, s.texto))
    # edge-tts solapa unos ms las oraciones: cada subtítulo termina cuando empieza el siguiente.
    sin_solape = [
        Subtitulo(s.inicio, min(s.fin, sig.inicio), s.texto) for s, sig in zip(todos, todos[1:])
    ] + todos[-1:]
    escribir_srt(destino, sin_solape)


# --------------------------------------------------------------------------- audio (edge-tts)


def leer_cache(proyecto: Proyecto) -> dict[str, str]:
    try:
        return json.loads(proyecto.cache.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def guardar_cache(proyecto: Proyecto, cache: dict[str, str]) -> None:
    proyecto.cache.write_text(json.dumps(cache, indent=2, sort_keys=True), encoding="utf-8")


async def sintetizar(paso: Paso) -> None:
    comunicador = edge_tts.Communicate(paso.texto, paso.voz, rate=paso.rate, pitch=paso.pitch)
    submaker = edge_tts.SubMaker()
    with paso.mp3.open("wb") as mp3:
        async for chunk in comunicador.stream():
            if chunk["type"] == "audio":
                mp3.write(chunk["data"])
            elif chunk["type"] in ("WordBoundary", "SentenceBoundary"):
                submaker.feed(chunk)
    paso.srt.write_text(submaker.get_srt(), encoding="utf-8")


async def generar_audios(proyecto: Proyecto, pasos: list[Paso], forzar: bool) -> None:
    proyecto.audio.mkdir(exist_ok=True)
    proyecto.subs.mkdir(exist_ok=True)
    cache = leer_cache(proyecto)
    for paso in pasos:
        h = paso.hash_tts()
        al_dia = cache.get(paso.id) == h and paso.mp3.exists() and paso.srt.exists()
        if al_dia and not forzar:
            log.info("[%s] sin cambios, se usa el audio existente", paso.id)
            continue
        log.info("[%s] generando audio (%s, %s)...", paso.id, paso.voz, paso.rate)
        try:
            await sintetizar(paso)
        except Exception as e:  # edge-tts lanza errores de red/servicio variados
            raise PipelineError(f"edge-tts falló en el paso {paso.id}: {e}") from e
        cache[paso.id] = h
        guardar_cache(proyecto, cache)
    log.info("Audios listos en audio/ y subtítulos en subs/")


async def listar_voces(filtro: str) -> None:
    voces = await edge_tts.list_voices()
    f = filtro.lower()
    elegidas = sorted(
        (v for v in voces if f in v["ShortName"].lower() or f in v["Locale"].lower()),
        key=lambda v: v["ShortName"],
    )
    if not elegidas:
        log.info("No hay voces que coincidan con '%s'", filtro)
        return
    for v in elegidas:
        log.info("%-34s %-7s %s", v["ShortName"], v["Gender"], v["Locale"])


# --------------------------------------------------------------------------- duraciones


def mostrar_duraciones(guion: Guion) -> None:
    pausa = guion.pausa_final_seg
    log.info("%-4s %-28s %8s %12s %8s  %s", "Paso", "Título", "Audio", "Clip mínimo", "Clip", "Estado")
    total = 0.0
    for paso in guion.pasos:
        audio = duracion(paso.mp3)
        minimo = audio + pausa
        if paso.clip.exists():
            clip = duracion(paso.clip)
            estado = "ok" if clip >= minimo else f"se congela {minimo - clip:.1f}s"
            clip_txt = f"{clip:.1f}s"
        else:
            clip, estado, clip_txt = 0.0, "sin grabar", "-"
        total += max(clip, minimo)
        log.info("%-4s %-28s %7.1fs %11.1fs %8s  %s", paso.id, paso.titulo[:28], audio, minimo, clip_txt, estado)
    log.info("Duración estimada del video: %.1fs (pausa final por paso: %.1fs)", total, pausa)


# --------------------------------------------------------------------------- capturas animadas


def animar_capturas(guion: Guion, pasos: list[Paso]) -> None:
    from animar import renderizar  # Pillow solo hace falta para este comando

    guion.proyecto.clips.mkdir(exist_ok=True)
    cursor = (ANCHO * 0.72, ALTO * 0.78)
    con_captura = [p for p in pasos if p.ruta_captura]
    if not con_captura:
        log.info("Ningún paso tiene 'captura' en guion.json; no hay nada que animar.")
    for paso in con_captura:
        assert paso.ruta_captura is not None
        zonas = preparar_lamina(paso)
        if not paso.ruta_captura.exists():
            raise PipelineError(f"falta {guion.proyecto.rel(paso.ruta_captura)}")
        log.info("[%s] animando %s (%d acciones)", paso.id, paso.captura, len(paso.acciones))
        subs = [(s.inicio, s.fin, s.texto) for s in leer_srt(paso.srt)] if paso.srt.exists() else []
        try:
            cursor = renderizar(
                paso.ruta_captura, paso.acciones, duracion(paso.mp3), paso.clip, cursor, paso.inicio_animacion,
                subs=subs, rotulo=paso.rotulo, cursor=paso.cursor, zonas=zonas,
            )
        except (RuntimeError, ValueError, KeyError) as e:
            raise PipelineError(f"paso {paso.id}: {e}") from e


def preparar_lamina(paso: Paso) -> dict[str, tuple[int, int, int, int]]:
    """Si el paso es una lámina, la dibuja en capturas/ y devuelve sus zonas con nombre."""
    if not paso.lamina or not paso.ruta_captura:
        return {}
    from lamina import guardar_lamina

    return guardar_lamina(paso.lamina, paso.ruta_captura)


def generar_grilla(paso: Paso, destino: Path) -> None:
    """Captura con grilla cada 50 px y etiquetas cada 100 px, para leer las coordenadas de los clics."""
    from PIL import Image, ImageDraw

    zonas = preparar_lamina(paso)
    if not paso.ruta_captura or not paso.ruta_captura.exists():
        raise PipelineError(f"el paso {paso.id} no tiene captura")
    img = Image.open(paso.ruta_captura).convert("RGB")
    d = ImageDraw.Draw(img, "RGBA")
    for x in range(0, img.width, 50):
        d.line([(x, 0), (x, img.height)], fill=(255, 0, 0, 140 if x % 100 == 0 else 50))
        if x % 100 == 0:
            d.text((x + 2, 2), str(x), fill=(200, 0, 0, 255))
    for y in range(0, img.height, 50):
        d.line([(0, y), (img.width, y)], fill=(255, 0, 0, 140 if y % 100 == 0 else 50))
        if y % 100 == 0:
            d.text((2, y + 2), str(y), fill=(200, 0, 0, 255))
    for a in paso.acciones:
        if "x" in a:
            d.ellipse((a["x"] - 8, a["y"] - 8, a["x"] + 8, a["y"] + 8), outline=(0, 160, 255, 255), width=3)
        caja = zonas.get(a["zona"]) if "zona" in a else a.get("caja")
        if caja:
            d.rectangle(tuple(caja), outline=(0, 160, 255, 255), width=3)
    for nombre, caja in zonas.items():
        d.text((caja[0] + 4, caja[1] + 4), nombre, fill=(0, 120, 220, 255))
    img.save(destino)
    log.info("Grilla en %s (círculos azules = acciones actuales)", destino)


# --------------------------------------------------------------------------- ensamblado


def filtro_video(relleno: float) -> str:
    return (
        f"[0:v]scale={ANCHO}:{ALTO}:force_original_aspect_ratio=decrease,"
        f"pad={ANCHO}:{ALTO}:(ow-iw)/2:(oh-ih)/2:color=black,"
        f"setsar=1,fps={FPS},format=yuv420p,"
        f"tpad=stop_mode=clone:stop_duration={relleno:.3f}[v]"
    )


def filtro_audio() -> str:
    # loudnorm trabaja a 192 kHz internamente: se vuelve a 48 kHz y luego se rellena con silencio.
    return f"[1:a]{LOUDNORM},aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,apad[a]"


def ensamblar_paso(paso: Paso, pausa: float, destino: Path) -> float:
    clip, audio = duracion(paso.clip), duracion(paso.mp3)
    objetivo = max(clip, audio + pausa)
    relleno = objetivo - clip
    detalle = f"congela {relleno:.1f}s" if relleno > 0.01 else f"silencio {objetivo - audio:.1f}s"
    log.info("[%s] clip %.1fs + audio %.1fs -> %.1fs (%s)", paso.id, clip, audio, objetivo, detalle)
    ffmpeg(
        "-i", str(paso.clip),
        "-i", str(paso.mp3),
        "-filter_complex", f"{filtro_video(relleno + 0.5)};{filtro_audio()}",
        "-map", "[v]", "-map", "[a]",
        "-t", f"{objetivo:.3f}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-r", str(FPS),
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-movflags", "+faststart",
        str(destino),
    )
    return duracion(destino)


def concatenar(lista: Path, segmentos: list[Path], destino: Path) -> None:
    lista.write_text("".join(f"file '{s.as_posix()}'\n" for s in segmentos), encoding="utf-8")
    ffmpeg("-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy", "-movflags", "+faststart", str(destino))


def quemar_subtitulos(video: Path, srt: Path, destino: Path) -> None:
    # Se ejecuta con cwd en la carpeta del .srt para evitar el escape de rutas de Windows en el filtro.
    ffmpeg(
        "-i", str(video),
        "-vf", f"subtitles={srt.name}:force_style='{ESTILO_SUBS}'",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-c:a", "copy", "-movflags", "+faststart",
        str(destino),
        cwd=srt.parent,
    )


def agregar_pista_subtitulos(video: Path, srt: Path, destino: Path) -> None:
    ffmpeg(
        "-i", str(video), "-i", str(srt),
        "-map", "0", "-map", "1",
        "-c:v", "copy", "-c:a", "copy", "-c:s", "mov_text",
        "-metadata:s:s:0", "language=spa",
        "-movflags", "+faststart",
        str(destino),
    )


def ensamblar(guion: Guion, modo_subs: str) -> Path:
    pr = guion.proyecto
    for carpeta in (pr.output, pr.subs, pr.tmp):
        carpeta.mkdir(exist_ok=True)

    faltantes = [pr.rel(p.clip) for p in guion.pasos if not p.clip.exists()]
    faltantes += [pr.rel(p.mp3) for p in guion.pasos if not p.mp3.exists()]
    if faltantes:
        raise PipelineError("faltan archivos:\n  " + "\n  ".join(faltantes))

    segmentos: list[Path] = []
    offsets: list[float] = []
    inicio = 0.0
    for paso in guion.pasos:
        segmento = pr.tmp / f"seg{paso.id}.mp4"
        offsets.append(inicio)
        inicio += ensamblar_paso(paso, guion.pausa_final_seg, segmento)
        segmentos.append(segmento)

    log.info("Concatenando %d segmentos...", len(segmentos))
    unido = pr.tmp / "unido.mp4"
    concatenar(pr.tmp / "concat.txt", segmentos, unido)

    srt = pr.subs / "combinado.srt"
    combinar_srt(guion.pasos, offsets, srt)

    salida = guion.salida
    if modo_subs == "quemados":
        log.info("Quemando subtítulos...")
        quemar_subtitulos(unido, srt, salida)
    elif modo_subs == "archivo":
        log.info("Agregando pista de subtítulos y copiando el .srt junto al video...")
        agregar_pista_subtitulos(unido, srt, salida)
        shutil.copyfile(srt, salida.with_suffix(".srt"))
    else:
        shutil.move(unido, salida)

    shutil.rmtree(pr.tmp, ignore_errors=True)
    log.info("Listo: %s (%.1fs)", pr.rel(salida), duracion(salida))
    return salida


# --------------------------------------------------------------------------- clips dummy


COLORES = ["0x1f4e79", "0x2e7d32", "0x6a1b9a", "0xc62828", "0xef6c00", "0x00838f", "0x4e342e", "0x37474f"]


def generar_dummies(guion: Guion, forzar: bool) -> None:
    """Clips de prueba con duraciones variadas (algunos más cortos que el audio, otros más largos)."""
    guion.proyecto.clips.mkdir(exist_ok=True)
    fuente = "C\\:/Windows/Fonts/arial.ttf"
    for i, paso in enumerate(guion.pasos):
        if paso.clip.exists() and not forzar:
            log.info("[%s] ya existe %s, no se pisa (usá --forzar)", paso.id, paso.clip.name)
            continue
        dur = [3, 9, 5, 12, 4, 10, 6, 8][i % 8]
        tam = "1280x720" if i % 3 == 2 else "1920x1080"  # algunos en 720p para probar el escalado
        texto = f"Paso {paso.id}  {paso.titulo}".replace(":", "\\:").replace("'", "")
        log.info("[%s] clip dummy %ss %s", paso.id, dur, tam)
        ffmpeg(
            "-f", "lavfi", "-i", f"color=c={COLORES[i % len(COLORES)]}:s={tam}:r=30:d={dur}",
            "-vf",
            f"drawtext=fontfile='{fuente}':text='{texto}':fontcolor=white:fontsize=h/12:"
            "x=(w-tw)/2:y=(h-th)/2,"
            f"drawtext=fontfile='{fuente}':text='%{{pts\\:hms}}':fontcolor=white@0.7:fontsize=h/20:"
            "x=(w-tw)/2:y=h*0.7",
            "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
            str(paso.clip),
        )


# --------------------------------------------------------------------------- CLI


def crear_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Tutoriales en video con voz IA")
    parser.add_argument("-p", "--proyecto", help="nombre en proyectos/ o ruta (por defecto, la carpeta actual)")
    parser.add_argument("-v", "--verbose", action="store_true", help="muestra los comandos ffmpeg")
    sub = parser.add_subparsers(dest="comando", required=True)

    nuevo = sub.add_parser("nuevo", help="crea un proyecto nuevo en proyectos/")
    nuevo.add_argument("nombre", help="ej: comunicados-envio")

    voces = sub.add_parser("voces", help="lista voces de edge-tts")
    voces.add_argument("--filtro", default="es-", help="ej: es-CL, es-AR, Catalina")

    audio = sub.add_parser("audio", help="genera MP3 + SRT por paso")
    audio.add_argument("--paso", help="id del paso (ej: 03); por defecto todos")
    audio.add_argument("--forzar", action="store_true", help="regenera aunque el texto no haya cambiado")

    sub.add_parser("duraciones", help="duración de cada audio y cuánto debe durar cada grabación")

    capturas = sub.add_parser("capturas", help="anima las capturas (cursor y clics) y las deja en clips/")
    capturas.add_argument("--paso", help="id del paso; por defecto todos los que tienen 'captura'")

    grilla = sub.add_parser("grilla", help="guarda la captura con una grilla para ubicar coordenadas")
    grilla.add_argument("--paso", required=True)

    for nombre, ayuda in (("ensamblar", "arma el video final"), ("todo", "audio + capturas + ensamblar")):
        p = sub.add_parser(nombre, help=ayuda)
        p.add_argument("--subs", choices=["quemados", "archivo", "no"], default="quemados")

    sub.add_parser("exportar", help="exporta el guion como guía Markdown para el RAG (output/rag/)")

    dummy = sub.add_parser("dummy", help="genera clips de prueba en clips/")
    dummy.add_argument("--forzar", action="store_true", help="pisa clips existentes")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = crear_parser().parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(message)s")
    try:
        if args.comando == "voces":
            asyncio.run(listar_voces(args.filtro))
            return 0
        if args.comando == "nuevo":
            crear_proyecto(args.nombre)
            return 0
        proyecto = resolver_proyecto(args.proyecto)
        guion = cargar_guion(proyecto)
        if args.comando == "exportar":
            from exportar import exportar

            duracion_video = None
            if guion.salida.exists():
                asegurar_ffmpeg()
                duracion_video = duracion(guion.salida)
            destino = exportar(proyecto.guion, proyecto.output / "rag", guion.salida, duracion_video)
            log.info("Guía para el RAG: %s", destino)
            return 0
        if args.comando == "audio":
            asyncio.run(generar_audios(proyecto, guion.filtrar(args.paso), args.forzar))
            return 0
        asegurar_ffmpeg()
        if args.comando == "duraciones":
            mostrar_duraciones(guion)
        elif args.comando == "capturas":
            animar_capturas(guion, guion.filtrar(args.paso))
        elif args.comando == "grilla":
            paso = guion.filtrar(args.paso)[0]
            proyecto.output.mkdir(exist_ok=True)
            generar_grilla(paso, proyecto.output / f"grilla_{paso.nombre}.png")
        elif args.comando == "ensamblar":
            ensamblar(guion, args.subs)
        elif args.comando == "todo":
            asyncio.run(generar_audios(proyecto, guion.pasos, forzar=False))
            animar_capturas(guion, guion.pasos)
            ensamblar(guion, args.subs)
        elif args.comando == "dummy":
            generar_dummies(guion, args.forzar)
    except PipelineError as e:
        log.error("Error: %s", e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
