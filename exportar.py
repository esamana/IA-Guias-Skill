"""Exporta el guion de un tutorial como documento para el RAG del chatbot de Alexia.

    python tutor.py -p <proyecto> exportar

Deja proyectos/<p>/output/rag/<titulo>.md: un Markdown con metadatos (frontmatter YAML), las
preguntas que responde y los pasos con su narración, pensado para que el chunker lo corte por
encabezados y el LLM pueda responder "¿cómo hago X en Alexia?" citando la guía y el video.

Datos opcionales en guion.json (los escribe Claude con la skill):

    "rag": {
      "modulo": "Matrícula Online",
      "publico": "Apoderados",
      "objetivo": "Completar la matrícula online de los hijos para el próximo año.",
      "preguntas": ["¿Cómo matriculo a mi hijo en Alexia?", "¿Qué es PAC y PAT?"],
      "palabras_clave": ["matrícula", "PAC", "PAT", "firma digital"],
      "requisitos": ["Usuario y contraseña de apoderado en Alexia"],
      "notas": ["El pago se hace al final, después de firmar."],
      "video_url": "https://..."
    }

y por paso `"texto_rag"` para reemplazar la narración cuando lo hablado no sirve escrito.
"""
from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

NUMEROS = "uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce|\\d+"
# "Paso tres: elige..." / "Etapa cuatro, ..." al inicio de la narración: en el documento ya va como encabezado.
PREFIJO_HABLADO = re.compile(rf"^(paso|etapa)\s+({NUMEROS})\s*[:,.]\s*", re.IGNORECASE)


def _yaml(valor: Any) -> str:
    return json.dumps(valor, ensure_ascii=False)  # JSON es YAML válido y evita problemas de escape


def _limpiar(texto: str) -> str:
    texto = PREFIJO_HABLADO.sub("", texto.strip())
    return texto[:1].upper() + texto[1:]


def _etapa(rotulo: str | None) -> str | None:
    """"Paso 3 de 5 · Apoderado económico" -> "Apoderado económico"."""
    if not rotulo:
        return None
    partes = [p.strip() for p in rotulo.split("·")]
    return partes[-1] if len(partes) > 1 else rotulo.strip()


def generar_markdown(datos: dict[str, Any], nombre_video: str | None, duracion_seg: float | None) -> str:
    rag = datos.get("rag", {})
    titulo = re.sub(r"\s*\((versi[oó]n )?(corta|completa)\)\s*$", "", datos.get("titulo", "Tutorial de Alexia"))
    pasos = datos.get("pasos", [])

    meta = {
        "titulo": titulo,
        "tipo": "guia_paso_a_paso",
        "producto": "Alexia",
        "modulo": rag.get("modulo"),
        "publico": rag.get("publico"),
        "objetivo": rag.get("objetivo"),
        "palabras_clave": rag.get("palabras_clave"),
        "pasos": len(pasos),
        "video": rag.get("video_url") or nombre_video,
        "duracion_video_seg": round(duracion_seg) if duracion_seg else None,
        "pais": "Chile",
        "actualizado": dt.date.today().isoformat(),
        "fuente": "Guion del tutorial en video (IA-Guias-Skill)",
    }
    lineas = ["---"] + [f"{k}: {_yaml(v)}" for k, v in meta.items() if v not in (None, [], "")] + ["---", ""]

    lineas += [f"# {titulo}", ""]
    resumen = []
    if rag.get("objetivo"):
        resumen.append(rag["objetivo"])
    if rag.get("modulo"):
        resumen.append(f"Módulo de Alexia: {rag['modulo']}.")
    if rag.get("publico"):
        resumen.append(f"Dirigida a: {rag['publico']}.")
    if resumen:
        lineas += [" ".join(resumen), ""]

    if rag.get("preguntas"):
        lineas += ["## Preguntas que responde esta guía", ""] + [f"- {q}" for q in rag["preguntas"]] + [""]
    if rag.get("requisitos"):
        lineas += ["## Antes de empezar", ""] + [f"- {r}" for r in rag["requisitos"]] + [""]

    lineas += ["## Paso a paso", ""]
    for n, paso in enumerate(pasos, 1):
        nombre = paso.get("titulo") or f"Paso {n}"
        lineas.append(f"### Paso {n}. {nombre}")
        etapa = _etapa(paso.get("rotulo"))
        if etapa and etapa.lower() != nombre.lower():
            lineas.append(f"*Etapa: {etapa}*")
        lineas += ["", _limpiar(paso.get("texto_rag") or paso.get("texto", ""))]
        notas = [a["nota"].replace("\n", " ") for a in paso.get("acciones", []) if a.get("nota")]
        if notas:
            final = "" if notas[-1][-1:] in ".?!" else "."
            lineas += ["", "En pantalla se destaca: " + "; ".join(notas) + final]
        lineas.append("")

    if rag.get("notas"):
        lineas += ["## Importante", ""] + [f"- {x}" for x in rag["notas"]] + [""]
    if meta["video"]:
        lineas += ["## Video", "", f"Esta guía tiene un video tutorial con narración: {meta['video']}", ""]
    return "\n".join(lineas).rstrip() + "\n"


def exportar(guion_json: Path, destino_dir: Path, video: Path | None, duracion_seg: float | None) -> Path:
    datos = json.loads(guion_json.read_text(encoding="utf-8"))
    texto = generar_markdown(datos, video.name if video and video.exists() else None, duracion_seg)
    titulo = re.sub(r'[<>:"/\\|?*]', "", datos.get("titulo", guion_json.parent.name)).strip()
    destino_dir.mkdir(parents=True, exist_ok=True)
    destino = destino_dir / f"{titulo}.md"
    destino.write_text(texto, encoding="utf-8")
    return destino
