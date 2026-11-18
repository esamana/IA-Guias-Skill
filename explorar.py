"""Explora cualquier pantalla de Alexia con Playwright: login + acciones encadenadas + capturas.

Las credenciales y la URL se leen SOLO de variables de entorno (nunca de archivos):
    ALEXIA_URL       URL de login, p. ej. https://chileXX.ci-alexia.com/ACWeb/logon.aspx?id=1234
    ALEXIA_USUARIO   usuario de prueba
    ALEXIA_PASSWORD  contraseña

Uso:
    python explorar.py -p <proyecto> [--ver] accion1 accion2 ...

Ejemplo:
    python explorar.py -p comunicados "dump:00_inicio" "click:text=Comunicados" "dump:01_menu" "foto:paso01"

Salidas (dentro de proyectos/<proyecto>/):
    explorar/<nombre>.png / .json   con dump: y shot: (captura + lista de elementos clicables)
    capturas/<nombre>.png           con foto: (1920x1080, datos reemplazados por ficticios)
    ficticios.json                  mapa {"texto real": "texto ficticio"} que usa foto:

Acciones:
    dump:NOMBRE        captura + elementos visibles (id, texto) de todos los frames
    foto:NOMBRE        captura final para el video, con datos ficticios (reemplaza en el DOM y restaura)
    click:SELECTOR     clic (busca en todos los frames). Se BLOQUEA si el elemento dice pagar, firmar,
                       eliminar, borrar, anular, enviar, publicar... Para esos casos usar
    click!:SELECTOR    clic sin bloqueo: SOLO con confirmación explícita del usuario
    check:SELECTOR     marca una casilla
    escribir:SELECTOR=TEXTO   llena un campo (usar solo datos ficticios)
    select:SELECTOR=ETIQUETA  elige una opción de un desplegable
    hasta:SELECTOR     espera (hasta 3 min) a que el elemento sea visible
    ir:TEXTO[+N]       desplaza la página hasta el encabezado que empieza con TEXTO
    scroll:SELECTOR    desplaza hasta el elemento
    pestana:NOMBRE     cambia a la última pestaña abierta (popup) y la vuelca como dump:
    shot:NOMBRE        captura de página completa (para leer, no para el video)
    goto:URL           navega a una URL
    js:CODIGO          evalúa JavaScript en la página e imprime el resultado
    wait:MS            espera en milisegundos

Selectores de Playwright: "#id", "text=Guardar", "button:has-text('Siguiente')", etc.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

RAIZ = Path(__file__).resolve().parent
PROYECTOS = RAIZ / "proyectos"

# Textos de botones que tienen efectos reales (pagos, firmas, envíos a familias, borrados).
PELIGROSO = re.compile(
    r"\bpagar|pago en l[ií]nea|\bfirmar|firma digital|eliminar|borrar|anular|\benviar|\benv[ií]o\b|"
    r"publicar|suscribir|confirmar (pago|matr)|dar de baja|cobrar",
    re.IGNORECASE,
)

DUMP_JS = """() => {
  const vis = e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  return [...document.querySelectorAll('input,button,a,select,textarea,label,[onclick],[role=button],[role=tab],[role=menuitem],h1,h2,h3')]
    .filter(vis).slice(0, 300).map(e => {
      const r = e.getBoundingClientRect();
      return {
        tag: e.tagName, id: e.id, name: e.getAttribute('name'), type: e.getAttribute('type'),
        cls: (e.className || '').toString().slice(0, 50),
        txt: (e.innerText || e.value || '').trim().replace(/\\s+/g, ' ').slice(0, 90),
        centro: [Math.round(r.x + r.width / 2), Math.round(r.y + r.height / 2)],
      };
    });
}"""

FICTICIO_JS = r"""(mapa) => {
  const pares = Object.entries(mapa).sort((a, b) => b[0].length - a[0].length);
  const cambiar = s => {
    let r = s; for (const [real, fict] of pares) r = r.split(real).join(fict);
    return r.replace(/\d{2,3}[•·*]{3,}[\dkK]/g, '123•••••9');  // RUT enmascarado, p. ej. "174•••••5"
  };
  window.__orig = [];
  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let n; while ((n = w.nextNode())) {
    const nuevo = cambiar(n.nodeValue);
    if (nuevo !== n.nodeValue) { window.__orig.push([n, 'text', n.nodeValue]); n.nodeValue = nuevo; }
  }
  for (const e of document.querySelectorAll('input,textarea')) {
    const nuevo = cambiar(e.value || '');
    if (nuevo !== e.value) { window.__orig.push([e, 'value', e.value]); e.value = nuevo; }
  }
  return window.__orig.length;
}"""

RESTAURAR_JS = """() => {
  for (const [n, tipo, v] of (window.__orig || [])) { if (tipo === 'text') n.nodeValue = v; else n.value = v; }
  window.__orig = [];
}"""


def entorno(nombre: str) -> str:
    valor = os.environ.get(nombre, "").strip()
    if not valor:
        sys.exit(f"Falta la variable de entorno {nombre}. Pedísela al usuario y pasala solo en el comando.")
    return valor


def localizar(page, selector: str):
    """Primer elemento visible que coincide, en la página o en cualquiera de sus frames."""
    for frame in page.frames:
        loc = frame.locator(selector)
        try:
            for i in range(loc.count()):
                if loc.nth(i).is_visible():
                    return loc.nth(i)
        except Exception:
            continue
    raise SystemExit(f"No encontré un elemento visible para: {selector}")


def esperar_carga(page, ms: int = 2500) -> None:
    try:
        page.wait_for_load_state("load", timeout=60000)
    except Exception:
        pass
    page.wait_for_timeout(ms)


def con_ficticios(page, mapa: dict[str, str], accion) -> None:
    for fr in page.frames:
        try:
            fr.evaluate(FICTICIO_JS, mapa)
        except Exception:
            pass
    page.wait_for_timeout(300)
    try:
        accion()
    finally:
        for fr in page.frames:
            try:
                fr.evaluate(RESTAURAR_JS)
            except Exception:
                pass


def dump(page, carpeta: Path, nombre: str) -> None:
    page.wait_for_timeout(1500)
    page.screenshot(path=str(carpeta / f"{nombre}.png"))
    frames = []
    for f in page.frames:
        try:
            frames.append({"url": f.url, "elementos": f.evaluate(DUMP_JS)})
        except Exception as e:
            frames.append({"url": f.url, "error": str(e)})
    (carpeta / f"{nombre}.json").write_text(json.dumps(frames, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"== {nombre}  {page.url}")
    for fr in frames:
        print("  frame:", fr["url"][:150])
        for e in fr.get("elementos", []):
            if e["txt"] or e["id"]:
                tipo = f"[{e['type']}]" if e["type"] else ""
                print("   ", e["tag"], e["id"] or e["name"] or "", tipo, e["centro"], "|", e["txt"])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-p", "--proyecto", required=True, help="nombre en proyectos/ o ruta")
    ap.add_argument("--ver", action="store_true", help="abre el navegador visible (para mirar lo que hace)")
    ap.add_argument("--sin-login", action="store_true", help="no completa el login (la URL ya es la pantalla)")
    ap.add_argument("acciones", nargs="*")
    args = ap.parse_args()

    proyecto = Path(args.proyecto) if Path(args.proyecto).is_dir() else PROYECTOS / args.proyecto
    if not proyecto.is_dir():
        sys.exit(f"No existe el proyecto {proyecto}. Crealo con: python tutor.py nuevo {args.proyecto}")
    carpeta_exp = proyecto / "explorar"
    carpeta_cap = proyecto / "capturas"
    carpeta_exp.mkdir(exist_ok=True)
    carpeta_cap.mkdir(exist_ok=True)
    ruta_mapa = proyecto / "ficticios.json"
    mapa = json.loads(ruta_mapa.read_text(encoding="utf-8")) if ruta_mapa.exists() else {}

    url = entorno("ALEXIA_URL")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.ver)
        ctx = browser.new_context(viewport={"width": 1920, "height": 1080}, ignore_https_errors=True, locale="es-CL")
        page = ctx.new_page()
        page.goto(url, wait_until="load", timeout=60000)
        if not args.sin_login:
            page.fill("#txtUsuario", entorno("ALEXIA_USUARIO"))
            page.fill("#txtPassword", entorno("ALEXIA_PASSWORD"))
            page.click("#btnAceptar")
            esperar_carga(page)
            if page.locator("#txtPassword").count() and page.locator("#txtPassword").is_visible():
                dump(page, carpeta_exp, "login_fallido")
                sys.exit("El login no avanzó: revisá URL, usuario y contraseña (ver explorar/login_fallido.png).")

        for accion in args.acciones:
            tipo, _, arg = accion.partition(":")
            if tipo in ("click", "click!"):
                loc = localizar(page, arg)
                texto = (loc.inner_text(timeout=2000) if loc.evaluate("e => e.tagName") != "INPUT"
                         else loc.get_attribute("value") or "") or ""
                if tipo == "click" and PELIGROSO.search(f"{texto} {arg}"):
                    sys.exit(f"BLOQUEADO: '{texto.strip()[:60]}' parece un botón con efectos reales "
                             "(pago, firma, envío o borrado). Confirmá con el usuario y usá click!: si autoriza.")
                loc.click()
                esperar_carga(page)
            elif tipo == "check":
                localizar(page, arg).check(force=True)
                page.wait_for_timeout(600)
            elif tipo == "escribir":
                sel, _, valor = arg.partition("=")
                localizar(page, sel).fill(valor)
                page.wait_for_timeout(400)
            elif tipo == "select":
                sel, _, valor = arg.partition("=")
                localizar(page, sel).select_option(label=valor)
                esperar_carga(page)
            elif tipo == "foto":
                destino = carpeta_cap / f"{arg}.png"
                con_ficticios(page, mapa, lambda: page.screenshot(path=str(destino)))
                print("foto", destino.relative_to(RAIZ))
            elif tipo == "pestana":
                page = ctx.pages[-1]
                print("pestañas:", [pg.url[:100] for pg in ctx.pages])
                esperar_carga(page, 4000)
                page.set_viewport_size({"width": 1920, "height": 1080})
                dump(page, carpeta_exp, arg)
            elif tipo == "hasta":
                page.wait_for_selector(arg, state="visible", timeout=180000)
                page.wait_for_timeout(1500)
                print("visible:", arg)
            elif tipo == "ir":
                texto, _, extra = arg.partition("+")
                page.evaluate("""([t, extra]) => {
                  const e = [...document.querySelectorAll('button,h1,h2,h3,label,div')]
                    .find(b => (b.innerText||'').trim().startsWith(t));
                  if (!e) return false; e.scrollIntoView({block: 'start'}); window.scrollBy(0, -30 + extra); return true;
                }""", [texto, int(extra or 0)])
                page.wait_for_timeout(800)
            elif tipo == "scroll":
                localizar(page, arg).scroll_into_view_if_needed()
                page.wait_for_timeout(800)
            elif tipo == "shot":
                page.screenshot(path=str(carpeta_exp / f"{arg}.png"), full_page=True)
            elif tipo == "wait":
                page.wait_for_timeout(int(arg))
            elif tipo == "goto":
                page.goto(arg, wait_until="load", timeout=60000)
                esperar_carga(page)
            elif tipo == "js":
                print("js:", page.evaluate(arg))
            elif tipo == "dump":
                dump(page, carpeta_exp, arg)
            else:
                sys.exit(f"Acción desconocida: {accion}")
        browser.close()


if __name__ == "__main__":
    main()
