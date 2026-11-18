# CLAUDE.md

Herramienta para armar **tutoriales en video de Alexia** (cualquier módulo) con narración IA en voz chilena, cursor animado, resaltados y subtítulos. Motor: edge-tts + Pillow + ffmpeg + Playwright. Uso local, en Windows.

La usan personas de Soporte/Experiencia que no programan: hablar en español simple, sin jerga técnica, y hacer vos los comandos. Para crear un tutorial, seguir la skill `/nuevo-tutorial` (`.claude/skills/nuevo-tutorial/SKILL.md`).

## Reglas (obligatorias)

1. **Credenciales**: la URL de Alexia, el usuario y la contraseña se piden al usuario en el chat y se pasan **solo como variables de entorno en el mismo comando** (`$env:ALEXIA_URL=...; $env:ALEXIA_USUARIO=...; $env:ALEXIA_PASSWORD=...; python explorar.py ...`). Nunca escribirlas en archivos, guiones, memoria ni commits. Usar solo usuarios de **Sandbox / prueba**.
2. **Nada con efectos reales**: nunca pagar, firmar, enviar comunicados/correos a familias, eliminar, anular ni publicar. `explorar.py` bloquea esos botones; `click!:` lo salta y solo se usa si el usuario lo autoriza explícitamente para ese botón en particular.
3. **Datos personales**: los videos no muestran datos reales. Antes de cada `foto:` cargar `proyectos/<p>/ficticios.json` con `{"texto real": "texto ficticio"}` para nombres, RUT, correos, teléfonos y direcciones visibles, y revisar la captura. Si se escribe en un campo, con datos ficticios.
4. **No guardar cambios** en Alexia salvo que sea parte necesaria del flujo y el usuario lo apruebe; preferir mostrar sin guardar.
5. Los proyectos (`proyectos/`) son locales y no se suben al repo (tienen capturas de Alexia).

## Archivos

- `tutor.py`: CLI del pipeline (`nuevo`, `audio`, `duraciones`, `capturas`, `grilla`, `ensamblar`, `todo`, `voces`).
- `animar.py`: cursor, halo, onda de clic, tipeo, resaltados y rótulos.
- `lamina.py`: láminas (portada, cierre o pantallas explicativas).
- `exportar.py`: `tutor.py exportar` genera la guía Markdown del tutorial para el RAG del chatbot de Alexia.
- `explorar.py`: navega Alexia con Playwright y saca capturas 1920x1080 con datos ficticios.
- `docs/`: formato del guion, guía de estilo de narración, problemas conocidos.
- `ejemplos/matricula-online-corto/guion.json`: guion de referencia (Matrícula Online, 16 pasos, 1:47).
