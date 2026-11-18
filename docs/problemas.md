# Problemas conocidos

| Problema | Solución |
|---|---|
| ffmpeg no aparece después de instalarlo con winget | `tutor.py` lo busca solo en la carpeta de WinGet. Si igual falla, cerrar y abrir Claude |
| Captura en blanco después del login o timeouts | `explorar.py` espera `load` + 2,5 s; agregar `wait:3000` o `hasta:SELECTOR` |
| El login no avanza | Revisar URL, usuario y contraseña; mirar `explorar/login_fallido.png` |
| `No encontré un elemento visible` | Hacer `dump:` antes, mirar el PNG y usar el id o el texto exacto del elemento |
| `BLOQUEADO: ... efectos reales` | Es a propósito. Solo con autorización explícita del usuario usar `click!:` |
| Un acordeón o paso no abre | Algunos pasos se habilitan solo con el botón de avanzar ("Guardar y siguiente") |
| Clics fuera del botón | Medir con `python tutor.py -p X grilla --paso NN` y mirar `output/grilla_pasoNN.png` |
| `cuando` no encuentra la frase | La frase tiene que estar textual en `texto` del paso (sin importar tildes) |
| Quedó un dato real en la captura | Agregarlo a `ficticios.json` y repetir `foto:` |
| `python` abre la Microsoft Store | Desactivar los alias de "python.exe" en Configuración > Aplicaciones > Alias de ejecución, o correr `instalar.ps1` |
