# Formato de `guion.json` y estilo de narración

Ejemplo completo: `ejemplos/matricula-online-corto/guion.json`.

```json
{
  "titulo": "Envío de comunicados en Alexia",
  "voz": "es-CL-CatalinaNeural",
  "rate": "-5%",
  "pausa_final_seg": 0.8,
  "pasos": [
    {
      "id": "04",
      "titulo": "Destinatarios",
      "rotulo": "Paso 4 de 6 · Destinatarios",
      "texto": "Elige a quién va dirigido el comunicado y presiona Siguiente.",
      "captura": "capturas/paso04.png",
      "acciones": [
        { "tipo": "resaltar", "caja": [480, 300, 1440, 620], "nota": "Cursos y grupos", "seg": 1.2, "cuando": "a quién va dirigido" },
        { "tipo": "escribir", "x": 884, "y": 451, "texto": "Primero básico A", "ancho": 260 },
        { "tipo": "click",    "x": 1669, "y": 973, "cuando": "Siguiente" }
      ]
    }
  ]
}
```

- Cada paso puede sobrescribir `voz`, `rate` o `pitch`.
- `captura`, `acciones`, `rotulo` e `inicio_animacion` son opcionales. Sin `captura`, el clip tiene que existir en `clips/pasoXX.mp4`.
- Las coordenadas están en píxeles de la captura (1920x1080) y apuntan al **centro** del botón o campo. Salen del `centro` que lista `explorar.py dump:` y se verifican con `python tutor.py -p X grilla --paso NN`.
- Por defecto la animación termina justo cuando termina la voz. `inicio_animacion` (segundos) la adelanta.

## Acciones

| Tipo | Efecto | Campos |
|---|---|---|
| `click` | El cursor se desplaza, aparece un halo, presiona y sale una onda | `x`, `y` |
| `senalar` | Halo de ~0,9 s sin clic, para un campo que nombra la narración | `x`, `y` |
| `escribir` | Tapa el placeholder y tipea el texto. **Solo datos ficticios** | `x` (inicio del texto), `y`, `texto`, `ancho` |
| `esperar` | Pausa | `seg` |
| `resaltar` | Oscurece la pantalla salvo la caja, borde ámbar y nota opcional al costado (`\n` = salto de línea) | `caja` [x1,y1,x2,y2] o `zona` (de una lámina), `nota`, `seg` |

Todas aceptan `"cuando": "palabras de la narración"`: la acción espera a que la voz diga esas palabras (se busca en el `.srt` del paso, sin distinguir tildes). Si falla, el error dice qué frase no encontró.

## Láminas (opcional)

`"lamina": {...}` en un paso dibuja una pantalla con `lamina.py` (portada, cierre o resumen): `antetitulo`, `titulo`, `subtitulo`, `tarjetas` (`id`, `etiqueta`, `titulo`, `texto`, `color`) y `pie`. Los `id` sirven como `zona` para `resaltar`. Preferir siempre capturas reales de Alexia.

## Estilo de narración

- Tuteo chileno, tono profesional y cercano. Frases cortas.
- Abrir cada paso con dónde estamos ("Paso dos: destinatarios"), explicar para qué sirve lo importante de la pantalla y cerrar con el botón que hay que presionar.
- Nombrar los botones y campos **tal como aparecen en pantalla**.
- No usar `¿?` en medio de una oración (corta el subtítulo). Escribir los números como se leen si hace falta ("Paso uno").
- Versión completa: `rate -5%`, 2 a 4 resaltados por paso. Versión corta: `rate +8%`, `pausa_final_seg 0.3`, una idea por paso y 1 a 3 resaltados.
- Voces chilenas: `es-CL-CatalinaNeural` (femenina, la usada hasta ahora) y `es-CL-LorenzoNeural` (masculina).
