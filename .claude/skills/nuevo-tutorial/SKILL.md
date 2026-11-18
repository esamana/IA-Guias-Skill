---
name: nuevo-tutorial
description: Arma un tutorial en video de cualquier módulo de Alexia (narración en voz chilena, cursor animado, resaltados y subtítulos) navegando el Sandbox con Playwright. Usar cuando el usuario quiere crear, rehacer o ajustar una guía/tutorial/video de Alexia.
---

# Nuevo tutorial de Alexia

Quien te habla es de Soporte/Experiencia y probablemente no programa. Vos ejecutás todo; a esa persona solo le pedís datos, decisiones y su revisión. Español simple, mensajes cortos. Respetá siempre las reglas de `CLAUDE.md` (credenciales, nada con efectos reales, datos ficticios).

Antes de empezar leé `docs/guion-y-acciones.md` (formato y estilo) y mirá `ejemplos/matricula-online-corto/guion.json` como referencia de calidad.

## 0. Verificar instalación

Corré `python -c "import edge_tts, PIL, playwright; print('ok')"` y `python tutor.py voces --filtro es-CL`. Si los dos andan, seguí al paso 1.

Si algo falla (falta Python, ffmpeg, Git, alguna librería o el navegador de Playwright):
1. Explicale en una línea qué falta y que lo vas a instalar con `instalar.ps1` (usa winget, se instala para su usuario y puede tardar unos minutos). Pedile el OK.
2. Ejecutá `powershell -NoProfile -ExecutionPolicy Bypass -File instalar.ps1 -SinPausa` con un timeout largo (10 min). Lo ya instalado se salta.
3. Si dice `NO SE PUDO TERMINAR`, leé `instalar.log` y explicale la causa en simple:
   - **falta winget** o **pide administrador**: que instale "Instalador de aplicación" desde Microsoft Store, o que pida a TI instalar Python 3.13 y ffmpeg; pasale los links que muestra el log.
   - **proxy, antivirus o sin internet** (pip, Chromium o la voz no descargan): que lo pruebe en otra red o lo vea con TI.
4. Si terminó bien pero `python` sigue sin encontrarse, es porque esta sesión arrancó antes de la instalación: pedile que **cierre y vuelva a abrir la app de Claude** y retome con `/nuevo-tutorial`.

Si falta ffmpeg en el PATH, `tutor.py` lo busca solo en la carpeta de WinGet, no hace falta reiniciar por eso.

## 1. Pedir los datos (un solo mensaje, en lista numerada)

**Acceso (Sandbox / usuario de prueba):**
1. URL de Alexia para entrar (la del login, por ejemplo `https://chileXX.ci-alexia.com/ACWeb/logon.aspx?id=...`).
2. Usuario.
3. Contraseña.

Aclarale que la contraseña no se guarda en ningún archivo, que solo se usa en los comandos de esta sesión, y que conviene que sea un usuario de prueba.

**Sobre la guía:**
4. Módulo o apartado de Alexia (por ejemplo: Comunicados, Matrícula Online, Notas, Asistencia, Pagos...).
5. Qué tiene que lograr quien mire el video (la tarea concreta, por ejemplo "enviar un comunicado a un curso").
6. Para quién es: apoderado, docente, administrativo del colegio u otro.
7. Cómo se llega: perfil o acceso que hay que elegir después del login y el camino de menús, si lo sabe.
8. Los pasos o pantallas que quiere mostrar, y lo que es importante explicar en cada uno.
9. Botones que **no** se deben presionar en este ambiente, y si se permite guardar algo.
10. Formato: versión completa (explicativa) o corta (una idea por paso, cerca de la mitad de duración); voz femenina (`es-CL-CatalinaNeural`) o masculina (`es-CL-LorenzoNeural`); subtítulos sí o no.

Si algo no lo sabe, seguí con lo razonable y avisá qué supusiste. No inventes funcionalidad de Alexia: lo que diga la narración tiene que verse en pantalla.

## 2. Crear el proyecto

`python tutor.py nuevo <nombre-en-minusculas-con-guiones>` (por ejemplo `comunicados-envio`). Crea `proyectos/<nombre>/`.

## 3. Explorar Alexia con Playwright

Cada ejecución de `explorar.py` arranca de cero (login + acciones), así que en cada corrida repetí la cadena completa de acciones hasta la pantalla que necesitás. Las credenciales van **solo** en el comando, con la herramienta PowerShell:

```powershell
$env:ALEXIA_URL='<url>'; $env:ALEXIA_USUARIO='<usuario>'; $env:ALEXIA_PASSWORD='<contraseña>'; python explorar.py -p <proyecto> "dump:00_inicio"
```

- `dump:` deja `proyectos/<p>/explorar/NN.png` y lista los elementos con su id, texto y centro `[x, y]`. **Mirá el PNG con Read** para entender la pantalla.
- Avanzá con `click:`, `select:`, `check:`, `escribir:` (datos ficticios), `ir:`, `hasta:`, `pestana:`. Preferí selectores por id (`#ctl00_...`) o por texto (`text=Comunicados`). La lista completa está al inicio de `explorar.py`.
- Si aparece una pantalla de elegir perfil/acceso, elegí el que indicó el usuario.
- **Bloqueos**: si `explorar.py` dice BLOQUEADO, no lo saltes. Preguntale al usuario, nombrando el botón y lo que puede pasar. Solo con un sí explícito usá `click!:` para ese botón.
- Antes de cualquier "Guardar", confirmá con el usuario (regla 4 de `CLAUDE.md`).
- Si el login no avanza, mostrá `explorar/login_fallido.png` y pedí que revise los datos.

## 4. Datos ficticios y capturas finales

1. Mirá los dumps y anotá todos los datos personales visibles: nombres de alumnos, apoderados y funcionarios, RUT, correos, teléfonos, direcciones, montos de una familia.
2. Escribí `proyectos/<p>/ficticios.json` con `{"Texto real": "Texto ficticio"}`, usando nombres y datos chilenos inventados y coherentes (por ejemplo `"María José Pérez Soto"` → `"Camila Rojas Fuentes"`, RUT `12.345.678-9`, `apoderado@ejemplo.cl`). Incluí las variantes que aparezcan (nombre solo, apellido, mayúsculas).
3. Sacá una captura por paso: `foto:paso01`, `foto:paso02`... Quedan en `capturas/` en 1920x1080.
4. **Revisá cada captura con Read.** Si queda algún dato real, agregalo a `ficticios.json` y repetí la foto.

## 5. Escribir el guion

Editá `proyectos/<p>/guion.json` siguiendo `docs/guion-y-acciones.md`:
- `titulo` claro (es el nombre del MP4), `voz`, `rate` (`-5%` completo, `+8%` corto).
- Un paso por pantalla, con `rotulo` ("Paso 2 de 6 · Destinatarios"), `texto` de narración y `acciones`.
- Coordenadas: usá el `centro` de los elementos del dump de esa pantalla. Después generá `python tutor.py -p <p> grilla --paso NN` y **mirá `output/grilla_pasoNN.png`** para confirmar que cada acción cae sobre su botón o campo.
- Usá `resaltar` con `cuando` para sincronizar con la voz, y un `click` al botón con el que se avanza al final de cada paso.

## 6. Generar y revisar

```powershell
python tutor.py -p <p> todo --subs quemados      # o --subs no
```

Revisá que no haya errores (por ejemplo una frase de `cuando` que no está en la narración) y corregí. Entregale al usuario la ruta completa del MP4 en `proyectos/<p>/output/` y pedile que lo mire.

Para ajustar un paso sin rehacer todo: `audio --paso NN`, `capturas --paso NN` y luego `ensamblar`.

## 7. Cierre

Resumí en pocas líneas qué pasos tiene el video, cuánto dura, dónde quedó y qué supuestos hiciste. Recordale que el video es para uso interno hasta revisar que no tenga datos reales, y que no se sube al repo.
