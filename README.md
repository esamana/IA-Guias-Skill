# Tutoriales de Alexia en video

Arma tutoriales en video de **cualquier módulo de Alexia**, con narración en voz chilena, cursor animado, resaltados y subtítulos. Claude navega el Sandbox, saca las capturas con datos ficticios, escribe el guion y genera el MP4.

## Requisitos

- Windows 10/11 y una suscripción de Claude que incluya **Claude Code** (app de escritorio de Claude, pestaña **Code**).
- Un usuario de **Sandbox / prueba** de Alexia.

## Instalación (una vez)

1. Descargar el repo: en GitHub, **Code > Download ZIP** y descomprimir, o `git clone` (recomendado, para recibir mejoras con `git pull`).
2. En la carpeta, **doble clic en `instalar.bat`**. Instala, solo si falta: Python 3.13, ffmpeg, Git, las librerías de Python y el navegador de Playwright. Se instala para tu usuario, así que en general no pide permisos de administrador, y se puede repetir sin problema.
   - Si no lo hacés, no pasa nada: al escribir `/nuevo-tutorial`, Claude revisa qué falta y te ofrece instalarlo.
   - Si termina con **NO SE PUDO TERMINAR**, el detalle queda en `instalar.log` (falta winget, proxy o antivirus de la empresa: verlo con TI).
   - Después de instalar, cerrá y abrí la app de Claude.

## Crear un tutorial

1. Abrir la app de Claude > pestaña **Code** > elegir esta carpeta.
2. Escribir **`/nuevo-tutorial`**.
3. Claude va a pedir:
   - la URL de Alexia, el usuario y la contraseña de prueba (no se guardan en ningún archivo);
   - el módulo, la tarea que debe aprender quien mire el video, para quién es, los pasos a mostrar, qué botones no tocar y el formato (completo o corto, voz, subtítulos).
4. Claude explora Alexia, arma el video y te pasa la ruta del MP4 en `proyectos/<nombre>/output/`. Pedile los cambios que quieras ("el paso 3 más corto", "resaltá el botón Guardar").

## Reglas

- Solo usuarios de prueba. Las credenciales nunca se escriben en archivos.
- Nunca se paga, firma, envía, elimina ni publica nada: `explorar.py` bloquea esos botones.
- Los datos visibles se reemplazan por ficticios antes de capturar. Revisá igual el video antes de compartirlo.
- `proyectos/` queda solo en tu equipo (no se sube a GitHub).

## Para quien quiera ver el detalle

- `docs/guion-y-acciones.md`: formato del guion, acciones del cursor y estilo de narración.
- `docs/problemas.md`: problemas conocidos.
- Comandos a mano: `python tutor.py -h` y `python explorar.py -h`.
