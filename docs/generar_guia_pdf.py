"""Genera docs/Guia-de-uso.pdf (guía rápida para Soporte). Uso: python docs/generar_guia_pdf.py"""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle)

DESTINO = Path(__file__).resolve().parent / "Guia-de-uso.pdf"
FUENTES = Path("C:/Windows/Fonts")
pdfmetrics.registerFont(TTFont("Segoe", str(FUENTES / "segoeui.ttf")))
pdfmetrics.registerFont(TTFont("Segoe-SB", str(FUENTES / "seguisb.ttf")))
pdfmetrics.registerFont(TTFont("Segoe-B", str(FUENTES / "segoeuib.ttf")))
pdfmetrics.registerFontFamily("Segoe", normal="Segoe", bold="Segoe-B", italic="Segoe", boldItalic="Segoe-B")

AZUL = colors.HexColor("#2B7BB9")
AZUL_OSCURO = colors.HexColor("#163454")
AZUL_CLARO = colors.HexColor("#EAF3FA")
AMBAR = colors.HexColor("#FFC400")
AMBAR_CLARO = colors.HexColor("#FFF6D6")
ROJO_CLARO = colors.HexColor("#FDECEC")
GRIS = colors.HexColor("#5B6573")
LINEA = colors.HexColor("#D5DDE6")

ANCHO = A4[0] - 36 * mm

s_titulo = ParagraphStyle("t", fontName="Segoe-B", fontSize=22, leading=27, textColor=colors.white)
s_sub = ParagraphStyle("st", fontName="Segoe", fontSize=11, leading=15, textColor=colors.HexColor("#D8E8F5"))
s_h1 = ParagraphStyle("h1", fontName="Segoe-B", fontSize=14, leading=18, textColor=AZUL_OSCURO, spaceBefore=10, spaceAfter=5)
s_p = ParagraphStyle("p", fontName="Segoe", fontSize=9.6, leading=13.6, textColor=colors.HexColor("#1F2933"))
s_pg = ParagraphStyle("pg", parent=s_p, textColor=GRIS, fontSize=8.8, leading=12)
s_b = ParagraphStyle("b", parent=s_p, leftIndent=10, bulletIndent=0, spaceAfter=1.5)
s_celda = ParagraphStyle("c", parent=s_p, fontSize=9, leading=12.4)
s_celda_b = ParagraphStyle("cb", parent=s_celda, fontName="Segoe-SB")
s_flujo = ParagraphStyle("f", parent=s_p, fontName="Segoe-SB", fontSize=8.4, leading=10.6, alignment=TA_CENTER, textColor=AZUL_OSCURO)
s_num = ParagraphStyle("n", fontName="Segoe-B", fontSize=11, leading=13, alignment=TA_CENTER, textColor=colors.white)
s_cod = ParagraphStyle("code", fontName="Courier-Bold", fontSize=10, leading=13, textColor=AZUL_OSCURO)


def P(t, s=s_p):
    return Paragraph(t, s)


def bullets(items, s=s_b):
    return [Paragraph(i, s, bulletText="•") for i in items]


def caja(contenido, fondo, borde, pad=7):
    t = Table([[contenido]], colWidths=[ANCHO])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), fondo), ("LINEBEFORE", (0, 0), (0, -1), 3, borde),
        ("LEFTPADDING", (0, 0), (-1, -1), pad + 3), ("RIGHTPADDING", (0, 0), (-1, -1), pad),
        ("TOPPADDING", (0, 0), (-1, -1), pad), ("BOTTOMPADDING", (0, 0), (-1, -1), pad),
    ]))
    return t


def pasos_numerados(items):
    filas = [[P(str(i), s_num), P(t)] for i, t in enumerate(items, 1)]
    t = Table(filas, colWidths=[8 * mm, ANCHO - 8 * mm])
    estilo = [("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (1, 0), (1, -1), 8),
              ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5)]
    for i in range(len(filas)):
        estilo.append(("BACKGROUND", (0, i), (0, i), AZUL))
    t.setStyle(TableStyle(estilo))
    return t


def tabla(filas, anchos, cabecera=True):
    datos = [[P(c, s_celda_b if (cabecera and r == 0) or j == 0 else s_celda) for j, c in enumerate(f)]
             for r, f in enumerate(filas)]
    t = Table(datos, colWidths=anchos, repeatRows=1 if cabecera else 0)
    estilo = [("GRID", (0, 0), (-1, -1), 0.5, LINEA), ("VALIGN", (0, 0), (-1, -1), "TOP"),
              ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
              ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6)]
    if cabecera:
        estilo.append(("BACKGROUND", (0, 0), (-1, 0), AZUL_CLARO))
    t.setStyle(TableStyle(estilo))
    return t


def flujo():
    etapas = ["Le pides la guía a Claude", "Claude entra al Sandbox", "Captura con datos ficticios",
              "Guion y voz chilena", "Video MP4", "Guía para el chatbot"]
    celdas, anchos = [], []
    ancho_caja = (ANCHO - 5 * 5 * mm) / 6
    for i, e in enumerate(etapas):
        celdas.append(P(e, s_flujo))
        anchos.append(ancho_caja)
        if i < len(etapas) - 1:
            celdas.append(P("›", ParagraphStyle("fl", parent=s_flujo, fontSize=16, textColor=AZUL)))
            anchos.append(5 * mm)
    t = Table([celdas], colWidths=anchos, rowHeights=[16 * mm])
    estilo = [("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 3),
              ("RIGHTPADDING", (0, 0), (-1, -1), 3)]
    for i in range(0, len(celdas), 2):
        fondo = AMBAR_CLARO if i >= 8 else AZUL_CLARO
        estilo += [("BACKGROUND", (i, 0), (i, 0), fondo), ("BOX", (i, 0), (i, 0), 0.6, LINEA)]
    t.setStyle(TableStyle(estilo))
    return t


def encabezado():
    t = Table([[P("Guías en video de Alexia con Claude", s_titulo)],
               [P("Guía rápida para Soporte y Experiencia · Herramienta IA-Guias-Skill", s_sub)]],
              colWidths=[ANCHO])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), AZUL_OSCURO),
                           ("LEFTPADDING", (0, 0), (-1, -1), 14), ("TOPPADDING", (0, 0), (0, 0), 14),
                           ("BOTTOMPADDING", (0, -1), (-1, -1), 14), ("LINEBELOW", (0, -1), (-1, -1), 4, AMBAR)]))
    return t


def pie(canvas, doc):
    canvas.saveState()
    canvas.setFont("Segoe", 7.5)
    canvas.setFillColor(GRIS)
    canvas.drawString(18 * mm, 10 * mm, "IA-Guias-Skill · Uso interno · Videos y capturas solo con datos ficticios")
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Página {doc.page}")
    canvas.restoreState()


historia = [
    encabezado(), Spacer(1, 9),
    P("Con esta herramienta le pides a Claude una guía de cualquier módulo de Alexia y te entrega "
      "<b>un video con narración en voz chilena</b>, cursor animado, resaltados y subtítulos, y además "
      "<b>la misma guía escrita</b>, lista para subir al RAG del chatbot de Alexia. Tú no escribes código: "
      "Claude te pide los datos, navega el Sandbox, arma todo y tú revisas."),
    Spacer(1, 8), flujo(),

    P("1. Antes de empezar", s_h1),
    tabla([["Necesitas", "Detalle"],
           ["Windows 10 u 11", "La herramienta no funciona en Mac."],
           ["App de escritorio de Claude", "Con tu suscripción. Se usa la pestaña <b>Code</b>. Descarga: claude.ai/download"],
           ["Acceso al repositorio", "github.com/esamana/IA-Guias-Skill (privado: pide que te agreguen)."],
           ["Usuario de Sandbox de Alexia", "Un usuario <b>de prueba</b>, nunca uno real de un colegio o familia."]],
          [48 * mm, ANCHO - 48 * mm]),

    P("2. Instalación (solo la primera vez)", s_h1),
    pasos_numerados([
        "En GitHub, botón <b>Code › Download ZIP</b>, y descomprime la carpeta (por ejemplo en Documentos).",
        "Dentro de la carpeta, <b>doble clic en instalar.bat</b>. Instala lo que falte: Python, ffmpeg, Git y el "
        "navegador. Tarda unos minutos y se puede repetir sin problema.",
        "Cuando diga <b>Todo listo</b>, cierra y vuelve a abrir la app de Claude.",
    ]),
    Spacer(1, 4),
    P("Si te lo saltas, no pasa nada: Claude revisa qué falta al empezar y te ofrece instalarlo.", s_pg),

    KeepTogether([
        P("3. Crear una guía", s_h1),
        pasos_numerados([
            "Abre la app de Claude › pestaña <b>Code</b> › elige la carpeta de la herramienta.",
            "Escribe <font name='Courier-Bold' color='#163454'>/nuevo-tutorial</font> y presiona Enter.",
            "Responde lo que te pide Claude (ver la lista de abajo). Si algo no lo sabes, dilo: sigue con lo razonable.",
            "Claude navega el Sandbox, saca las capturas, escribe el guion y genera el video. Puede pedirte "
            "permiso para ejecutar comandos o confirmar un botón: lee y aprueba.",
            "Mira el video y pide cambios con tus palabras. Cuando quede bien, dile que lo apruebas: "
            "te entrega también la guía escrita para el chatbot.",
        ]),
    ]),

    KeepTogether([
        P("4. Lo que te va a pedir Claude (tenlo a mano)", s_h1),
        tabla([["Dato", "Ejemplo"],
               ["URL de Alexia (login)", "https://chileXX.ci-alexia.com/ACWeb/logon.aspx?id=…"],
               ["Usuario y contraseña", "Del usuario de prueba. No se guardan en ningún archivo."],
               ["Módulo o apartado", "Comunicados, Matrícula Online, Notas, Asistencia…"],
               ["Qué debe lograr quien mira", "“Enviar un comunicado a un curso”"],
               ["Para quién es", "Apoderado, docente, administrativo del colegio"],
               ["Cómo se llega", "Perfil a elegir y camino de menús, si lo sabes"],
               ["Pasos a mostrar", "Las pantallas y lo importante a explicar en cada una"],
               ["Qué no tocar", "Botones prohibidos en ese ambiente; si se puede guardar"],
               ["Formato", "Completo o corto · voz femenina o masculina · con o sin subtítulos"]],
              [52 * mm, ANCHO - 52 * mm]),
    ]),

    KeepTogether([
        P("5. Pedir cambios: ejemplos", s_h1),
        *bullets(["“El paso 3 es muy largo, déjalo en una frase.”",
                  "“Resalta el botón Guardar antes del clic.”",
                  "“Usa la voz masculina y hazlo un poco más rápido.”",
                  "“Agrega un paso para adjuntar un archivo.”",
                  "“Haz una versión corta de este mismo video.”",
                  "“En la captura del paso 5 se ve un nombre real: reemplázalo.”"]),
    ]),

    KeepTogether([
        P("6. Dónde quedan los resultados", s_h1),
        tabla([["Archivo", "Dónde"],
               ["Video final (MP4)", "proyectos › <i>nombre-de-la-guia</i> › output"],
               ["Guía para el chatbot (.md)", "proyectos › <i>nombre-de-la-guia</i> › output › rag. Es el archivo que se sube al RAG de Chile."],
               ["Capturas", "proyectos › <i>nombre-de-la-guia</i> › capturas"]],
              [52 * mm, ANCHO - 52 * mm]),
        Spacer(1, 3),
        P("Claude te da la ruta completa al terminar. La carpeta <b>proyectos</b> queda solo en tu equipo.", s_pg),
    ]),

    KeepTogether([
        P("7. Reglas importantes", s_h1),
        caja([*bullets([
            "<b>Solo usuarios de prueba (Sandbox).</b> La contraseña queda en la conversación con Claude: nunca uses una real.",
            "<b>Nunca se paga, firma, envía, elimina ni publica nada.</b> La herramienta bloquea esos botones; "
            "si Claude te pregunta por uno, autorízalo solo si estás seguro de que es un ambiente de prueba.",
            "<b>Datos ficticios:</b> los nombres, RUT, correos y teléfonos se reemplazan antes de capturar. "
            "Igual <b>mira el video completo</b> antes de compartirlo.",
            "Los videos con datos reales son solo de uso local: no se publican.",
        ])], ROJO_CLARO, colors.HexColor("#D64545")),
    ]),

    KeepTogether([
        P("8. Si algo falla", s_h1),
        tabla([["Problema", "Qué hacer"],
               ["instalar.bat dice NO SE PUDO TERMINAR", "Pásale el archivo instalar.log a Claude o a TI. Suele ser un proxy, un antivirus o falta de permisos."],
               ["Claude dice que no encuentra Python", "Cierra y abre la app de Claude (la instalación se hizo con la app abierta)."],
               ["El login no avanza", "Revisa URL, usuario y contraseña. Claude te muestra la captura del error."],
               ["“BLOQUEADO … efectos reales”", "Es a propósito: el botón podría pagar, firmar o enviar. Decide si se puede en ese ambiente."],
               ["Un clic cae fuera del botón", "Dile a Claude en qué paso: lo vuelve a medir."],
               ["Se ve un dato real", "Dile cuál: lo agrega a los datos ficticios y repite la captura."]],
              [58 * mm, ANCHO - 58 * mm]),
    ]),

    KeepTogether([
        P("9. Actualizar la herramienta", s_h1),
        P("Cuando haya mejoras, vuelve a descargar el ZIP y reemplaza los archivos <b>sin borrar tu carpeta proyectos</b>. "
          "Si usas Git, basta con pedirle a Claude: “actualiza la herramienta” (hace <i>git pull</i>)."),
        Spacer(1, 8),
        caja([P("<b>Consejo:</b> empieza con una guía corta de 3 o 4 pasos para conocer el flujo. "
                "Como referencia de calidad, pídele a Claude que te muestre el ejemplo de Matrícula Online.")],
             AMBAR_CLARO, AMBAR),
    ]),
]

doc = SimpleDocTemplate(str(DESTINO), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                        topMargin=16 * mm, bottomMargin=17 * mm,
                        title="Guías en video de Alexia con Claude", author="Educaria", subject="Guía rápida de uso")
doc.build(historia, onFirstPage=pie, onLaterPages=pie)
print(DESTINO)
