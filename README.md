# IA-Guias-Skill · Guías en video de Alexia con Claude

Le pides a Claude una guía de **cualquier módulo de Alexia** y te entrega:

- 🎬 **Un video MP4** con narración en voz chilena, cursor animado, clics, resaltados sincronizados con la voz y subtítulos.
- 📄 **La misma guía escrita** en Markdown, lista para subir al RAG del chatbot de Alexia.

No necesitas programar. Claude te pide los datos, navega el Sandbox, saca las capturas con datos ficticios, escribe el guion, genera el video, y tú lo revisas.

```
Le pides la guía  ›  Claude entra al Sandbox  ›  Captura con datos ficticios  ›  Guion y voz  ›  Video MP4  ›  Guía para el chatbot
```

📘 **Guía rápida en PDF:** [`docs/Guia-de-uso.pdf`](docs/Guia-de-uso.pdf)

---

## 1. Requisitos

| Necesitas | Detalle |
|---|---|
| Windows 10 u 11 | No funciona en Mac |
| App de escritorio de Claude | Con tu suscripción, pestaña **Code**. Descarga: [claude.ai/download](https://claude.ai/download) |
| Acceso a este repositorio | Es privado: pide que te agreguen como colaborador |
| Usuario de **Sandbox** de Alexia | Siempre un usuario de prueba, nunca uno real |

## 2. Instalación (solo la primera vez)

1. Descarga el repositorio: botón verde **Code › Download ZIP** y descomprímelo (por ejemplo en `Documentos`).
   Si usas Git: `git clone https://github.com/esamana/IA-Guias-Skill.git`
2. Dentro de la carpeta, haz **doble clic en `instalar.bat`**. Solo instala lo que falte:
   - Python 3.13
   - ffmpeg
   - Git
   - Las librerías de Python
   - El navegador de Playwright

   Tarda unos minutos y puedes repetirlo cuando quieras.
3. Cuando diga **Todo listo**, cierra y vuelve a abrir la app de Claude.

> Si te saltas este paso, no pasa nada: al empezar, Claude revisa qué falta y te ofrece instalarlo.

## 3. Crear una guía

1. Abre la app de Claude › pestaña **Code** › elige la carpeta de la herramienta.
2. Escribe **`/nuevo-tutorial`** y presiona Enter.
3. Responde lo que te pide Claude (ver la tabla de abajo). Si algo no lo sabes, díselo y él sigue con lo razonable.
4. Claude navega el Sandbox, saca las capturas, escribe el guion y genera el video. Puede pedirte permiso para ejecutar comandos o para presionar un botón sensible: lee y aprueba.
5. Mira el video y pide cambios con tus palabras. Cuando lo apruebes, Claude genera también la guía escrita para el chatbot.

### Lo que te va a pedir Claude (tenlo a mano)

| Dato | Ejemplo |
|---|---|
| URL de Alexia (login) | `https://chileXX.ci-alexia.com/ACWeb/logon.aspx?id=…` |
| Usuario y contraseña | Del usuario de prueba. No se guardan en ningún archivo |
| Módulo o apartado | Comunicados, Matrícula Online, Notas, Asistencia… |
| Qué debe lograr quien mira | "Enviar un comunicado a un curso" |
| Para quién es | Apoderado, docente, administrativo del colegio |
| Cómo se llega | Perfil a elegir y camino de menús, si lo sabes |
| Pasos a mostrar | Las pantallas y lo importante a explicar en cada una |
| Qué no tocar | Botones prohibidos en ese ambiente; si se puede guardar |
| Formato | Completo o corto · voz femenina o masculina · con o sin subtítulos |

### Pedir cambios: ejemplos

- "El paso 3 es muy largo, déjalo en una frase."
- "Resalta el botón Guardar antes del clic."
- "Usa la voz masculina y hazlo un poco más rápido."
- "Agrega un paso para adjuntar un archivo."
- "Haz una versión corta de este mismo video."
- "En la captura del paso 5 se ve un nombre real: reemplázalo."

## 4. Dónde quedan los resultados

| Archivo | Dónde |
|---|---|
| Video final (MP4) | `proyectos/<nombre-de-la-guia>/output/` |
| Guía para el chatbot (`.md`) | `proyectos/<nombre-de-la-guia>/output/rag/`: es el archivo que se sube al RAG de Chile |
| Capturas | `proyectos/<nombre-de-la-guia>/capturas/` |

Claude te da la ruta completa al terminar. La carpeta `proyectos/` queda **solo en tu equipo** y no se sube a GitHub.

### La guía para el chatbot (RAG)

Es un Markdown con:
- Metadatos: módulo, público, palabras clave y video.
- Las preguntas que responde (por ejemplo "¿Cómo envío un comunicado a un curso?").
- Un encabezado por paso con la explicación.

Así el chatbot encuentra la guía aunque el usuario pregunte con otras palabras, y puede responder con los pasos y recomendar el video. El detalle del formato está en [`docs/guion-y-acciones.md`](docs/guion-y-acciones.md#exportar-para-el-rag-del-chatbot).

## 5. Reglas importantes

- **Solo usuarios de prueba (Sandbox).** La contraseña queda escrita en la conversación con Claude: nunca uses una real.
- **Nunca se paga, firma, envía, elimina ni publica nada.** La herramienta bloquea esos botones. Si Claude te pregunta por uno, autorízalo solo si estás seguro de que es un ambiente de prueba.
- **Datos ficticios:** los nombres, RUT, correos y teléfonos se reemplazan antes de capturar. Igual **mira el video completo** antes de compartirlo.
- Los videos con datos reales son solo de uso local: no se publican.

## 6. Si algo falla

| Problema | Qué hacer |
|---|---|
| `instalar.bat` dice **NO SE PUDO TERMINAR** | Pásale el archivo `instalar.log` a Claude o a TI. Suele ser un proxy, un antivirus o falta de permisos |
| Claude dice que no encuentra Python | Cierra y abre la app de Claude (la instalación se hizo con la app abierta) |
| El login no avanza | Revisa URL, usuario y contraseña. Claude te muestra la captura del error |
| "BLOQUEADO … efectos reales" | Es a propósito: ese botón podría pagar, firmar o enviar. Decide si se puede en ese ambiente |
| Un clic cae fuera del botón | Dile a Claude en qué paso: lo vuelve a medir |
| Se ve un dato real | Dile cuál: lo agrega a los datos ficticios y repite la captura |

Más casos en [`docs/problemas.md`](docs/problemas.md).

## 7. Actualizar la herramienta

- **Con ZIP:** vuelve a descargarlo y reemplaza los archivos **sin borrar tu carpeta `proyectos/`**.
- **Con Git:** pídele a Claude "actualiza la herramienta", o ejecuta `git pull`.

---

## Para usuarios avanzados

### Comandos a mano

```powershell
python tutor.py nuevo comunicados-envio                  # crea proyectos/comunicados-envio/
python tutor.py -p comunicados-envio todo --subs quemados # audio + animación + video final
python tutor.py -p comunicados-envio audio --paso 03     # rehace la voz de un paso
python tutor.py -p comunicados-envio grilla --paso 03    # captura con grilla para ubicar coordenadas
python tutor.py -p comunicados-envio exportar            # guía Markdown para el RAG
python tutor.py voces --filtro es-CL                     # voces disponibles

# Explorar y capturar Alexia (credenciales solo por variables de entorno)
$env:ALEXIA_URL='...'; $env:ALEXIA_USUARIO='...'; $env:ALEXIA_PASSWORD='...'
python explorar.py -p comunicados-envio "dump:00_inicio" "click:text=Comunicados" "foto:paso01"
```

Ayuda completa: `python tutor.py -h` y `python explorar.py -h`.

### Cómo funciona

Cada guía es un proyecto con un `guion.json`. Cada paso tiene:
- el **texto** que dice la voz;
- la **captura** de la pantalla;
- las **acciones** del cursor: `click`, `senalar`, `escribir`, `resaltar`, `esperar`. Pueden sincronizarse con frases de la narración usando `cuando`.

El pipeline sigue estos pasos:
1. **Voz:** edge-tts genera un MP3 y un SRT por paso, en voz chilena.
2. **Animación:** Pillow anima el cursor sobre cada captura.
3. **Video:** ffmpeg arma el video final con los subtítulos.

Formato completo: [`docs/guion-y-acciones.md`](docs/guion-y-acciones.md). Ejemplo: [`ejemplos/matricula-online-corto/guion.json`](ejemplos/matricula-online-corto/guion.json).

### Estructura

```
tutor.py          CLI del pipeline (audio, capturas, grilla, ensamblar, exportar)
animar.py         Cursor, halo, onda de clic, tipeo, resaltados y rótulos
lamina.py         Láminas (portada, cierre o pantallas explicativas)
explorar.py       Navega Alexia con Playwright y captura con datos ficticios
exportar.py       Genera la guía Markdown para el RAG
instalar.bat/ps1  Instalador para Windows
CLAUDE.md         Reglas que sigue Claude en esta carpeta
.claude/skills/nuevo-tutorial/   La skill /nuevo-tutorial
docs/             Guía PDF, formato del guion, problemas conocidos
ejemplos/         Guion de referencia (Matrícula Online)
proyectos/        Tus guías (local, no se sube)
```

> La voz usa edge-tts, el servicio de lectura de Microsoft Edge. No es un servicio contratado: necesita internet y podría cambiar sin aviso.
