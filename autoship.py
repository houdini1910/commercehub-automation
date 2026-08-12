"""
autoship.py
-----------
Script principal de automatización para CommerceHub DSM utilizando Playwright.

FLUJO DE USO:
1. Ejecutar: python autoship.py reportes\reporte.htm
2. El script parsea el HTML y muestra las ordenes a procesar.
3. El script abre el navegador (Brave/Chromium) mediante Playwright.
4. Inicia sesion automaticamente o te permite completar la navegacion.
5. Rellena automaticamente: Invoice#, Tracking#, Shipping Method y Ship Quantity.
"""

import sys
import time
import logging
import os
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright, Page, Browser, TimeoutError as PlaywrightTimeoutError

from parse_html import parse_reporte, mostrar_resumen, CLIENTE_OBJETIVO
import config

UPS_GROUND_TEXTO = "UPS Ground"
TIMEOUT_SEGUNDOS = 15000  # ms for Playwright


def configurar_log() -> logging.Logger:
    """Configura el sistema de logging para consola y archivo."""
    Path("logs").mkdir(exist_ok=True)
    nombre_log = f"logs/autoship_{datetime.now().strftime('%Y%m%m_%H%M%S')}.log"

    logger = logging.getLogger("autoship")
    logger.setLevel(logging.INFO)

    formato = logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s", datefmt="%H:%M:%S")

    fh = logging.FileHandler(nombre_log, encoding="utf-8")
    fh.setFormatter(formato)
    logger.addHandler(fh)

    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formato)
    logger.addHandler(ch)

    return logger


def obtener_ruta_brave() -> str:
    """Retorna la ruta al ejecutable de Brave encontrada en el sistema."""
    rutas = [
        r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
        r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
    ]
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        rutas.append(str(Path(local_app_data) / "BraveSoftware" / "Brave-Browser" / "Application" / "brave.exe"))
    
    for r in rutas:
        if os.path.exists(r):
            return r
    return r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"


BRAVE_PATH = obtener_ruta_brave()


def abrir_navegador(playwright_instance) -> tuple[Browser, Page]:
    """Abre una instancia de navegador (Brave o Chromium default) mediante Playwright."""
    brave_path = obtener_ruta_brave()
    if os.path.exists(brave_path):
        browser = playwright_instance.chromium.launch(
            executable_path=brave_path,
            headless=False,
            args=["--start-maximized"]
        )
    else:
        browser = playwright_instance.chromium.launch(
            headless=False,
            args=["--start-maximized"]
        )
    context = browser.new_context(no_viewport=True)
    page = context.new_page()
    return browser, page


# ─────────────────────────────────────────────
#  PLAYWRIGHT — LOGIN AUTOMATICO
# ─────────────────────────────────────────────

def hacer_login(page: Page, log: logging.Logger) -> bool:
    """
    Navega al portal e inicia sesión automáticamente con las credenciales de config.py.
    Retorna True si el login fue exitoso, False si hubo algún problema.
    """
    log.info(f"Navegando a: {config.URL_PORTAL}")
    try:
        page.goto(config.URL_PORTAL, timeout=TIMEOUT_SEGUNDOS)
    except Exception as e:
        log.error(f"Error al cargar la página: {e}")

    # ── Campo Email / Usuario ──────────────────────────────────────────────
    selectores_email = [
        "#email",
        "#username",
        "#Email",
        "input[name='email']",
        "input[name='username']",
        "input[name='Email']",
        "input[type='email']",
        "input[placeholder*='email' i]",
        "input[placeholder*='usuario' i]",
        "input[placeholder*='user' i]",
    ]

    campo_email = None
    for selector in selectores_email:
        loc = page.locator(selector).first
        if loc.count() > 0 and loc.is_visible():
            campo_email = loc
            break

    if not campo_email:
        # Fallback a búsqueda flexible en Shadow DOM o DOM visible
        loc = page.locator("input[type='email'], input[name='email'], input[name='username']").first
        if loc.count() > 0:
            campo_email = loc

    if not campo_email:
        log.error("  ❌ No se encontró el campo de email/usuario en la página de login.")
        return False

    campo_email.fill(config.EMAIL)
    log.info(f"  ✅ Email ingresado: {config.EMAIL}")

    # ── Campo Password ─────────────────────────────────────────────────────
    selectores_pass = [
        "#password",
        "#Password",
        "input[name='password']",
        "input[name='Password']",
        "input[type='password']",
    ]

    campo_pass = None
    for selector in selectores_pass:
        loc = page.locator(selector).first
        if loc.count() > 0 and loc.is_visible():
            campo_pass = loc
            break

    if not campo_pass:
        log.error("  ❌ No se encontró el campo de password en la página de login.")
        return False

    campo_pass.fill(config.PASSWORD)
    log.info("  ✅ Password ingresado.")

    # ── Boton de Login ─────────────────────────────────────────────────────
    selectores_boton = [
        "button[type='submit']",
        "input[type='submit']",
        "button:has-text('Login')",
        "button:has-text('login')",
        "button:has-text('Sign')",
        "button:has-text('Entrar')",
        "#loginButton",
        "#submitButton",
    ]

    boton = None
    for selector in selectores_boton:
        loc = page.locator(selector).first
        if loc.count() > 0 and loc.is_visible():
            boton = loc
            break

    if not boton:
        log.error("  ❌ No se encontró el botón de login.")
        return False

    boton.click()
    log.info("  ✅ Clic en botón de login. Esperando que cargue el portal...")

    # Esperar a que la URL cambie (salir de la página de login)
    try:
        page.wait_for_url(lambda url: config.URL_PORTAL not in url and "login" not in url.lower(), timeout=TIMEOUT_SEGUNDOS)
        log.info(f"  ✅ Login exitoso. URL actual: {page.url}")
        return True
    except PlaywrightTimeoutError:
        log.warning("  ⚠️  El portal no redireccionó después del login. Puede que requiera un paso extra (ej. 2FA).")
        log.warning("      Revisa el navegador y presiona ENTER cuando estés dentro del portal.")
        input("  > Presiona ENTER cuando hayas completado el login manualmente: ")
        return True


# ─────────────────────────────────────────────
#  PLAYWRIGHT — RELLENAR FORMULARIO
# ─────────────────────────────────────────────

def rellenar_formulario(page: Page, orden: dict, log: logging.Logger) -> bool:
    """
    Verifica que el PO Number exista en la página web actual antes de rellenar.
    Rellena Invoice# y Tracking# en los campos correspondientes.
    """
    po_target = orden["po"]
    invoice_val = orden["invoice"]
    tracking_val = orden["tracking"]

    log.info(f"  🔍 Verificando PO Number '{po_target}' en la página actual...")

    # ── Paso 0: Validar si el PO Number esta en la pagina ────────────────────
    po_loc = page.locator(f"text={po_target}")
    if po_loc.count() == 0:
        content = page.content()
        if po_target not in content:
            log.error(f"  ❌ ERROR DE COINCIDENCIA: El PO Number '{po_target}' NO fue encontrado en la página actual.")
            log.error(f"     SE OMITIÓ EL LLENADO de esta orden para no ingresar datos erróneos.")
            return False

    log.info(f"  ✅ Coincidencia confirmada para PO Number '{po_target}'.")
    exito = True

    # ── CAMPO: Invoice Number ──────────────────────────────────────────────
    selectores_invoice = [
        "input[name='invoiceNumber']",
        "input[name='invoice_number']",
        "input[name='invoiceNum']",
        "#invoiceNumber",
        "#invoice_number",
        "input[name*='invoice']:not([name*='total'])",
        "xpath=//td[contains(text(),'Invoice')]/following-sibling::td/input",
    ]

    campo_invoice = None
    for selector in selectores_invoice:
        loc = page.locator(selector).first
        if loc.count() > 0 and loc.is_visible():
            campo_invoice = loc
            break

    if campo_invoice:
        try:
            campo_invoice.fill(invoice_val)
            log.info(f"  ✅ Invoice Number ingresado: {invoice_val}")
        except Exception as e:
            log.error(f"  ❌ Campo Invoice Number no interactuable: {e}")
            exito = False
    else:
        log.error(f"  ❌ No se encontró el campo Invoice Number para PO {po_target}.")
        exito = False

    # ── CAMPO: Tracking Number ─────────────────────────────────────────────
    selectores_tracking = [
        "input[name='trackingNumber']",
        "input[name='tracking_number']",
        "input[name='trackingNum']",
        "input[name='shipTracking']",
        "#trackingNumber",
        "#tracking_number",
        "input[name*='tracking' i]",
        "xpath=//td[contains(text(),'Tracking')]/following-sibling::td/input",
    ]

    campo_tracking = None
    for selector in selectores_tracking:
        loc = page.locator(selector).first
        if loc.count() > 0 and loc.is_visible():
            campo_tracking = loc
            break

    if campo_tracking:
        try:
            campo_tracking.fill(tracking_val)
            log.info(f"  ✅ Tracking Number ingresado: {tracking_val}")
        except Exception as e:
            log.error(f"  ❌ Campo Tracking Number no interactuable: {e}")
            exito = False
    else:
        log.error(f"  ❌ No se encontró el campo Tracking Number para PO {po_target}.")
        exito = False

    # ── DROPDOWN: Shipping Method ──────────────────────────────────────────
    ship_via_target = orden.get("ship_via", UPS_GROUND_TEXTO) or UPS_GROUND_TEXTO
    selectores_dropdown = [
        "select[name='shipMethod']",
        "select[name='shippingMethod']",
        "select[name='ship_method']",
        "select[name='carrierMethod']",
        "#shipMethod",
        "#shippingMethod",
        "select[name*='ship' i]",
        "xpath=//td[contains(text(),'Shipping Method')]/following-sibling::td/select",
    ]

    campo_dropdown = None
    for selector in selectores_dropdown:
        loc = page.locator(selector).first
        if loc.count() > 0 and loc.is_visible():
            campo_dropdown = loc
            break

    if campo_dropdown:
        try:
            # Intentar seleccion directa por label o value
            try:
                campo_dropdown.select_option(label=ship_via_target)
                log.info(f"  ✅ Shipping Method seleccionado: {ship_via_target}")
            except Exception:
                # Intentar buscar opciones parciales
                opciones = campo_dropdown.locator("option").all_inner_texts()
                encontrado = False
                for opt_txt in opciones:
                    if ship_via_target.lower() in opt_txt.lower() or opt_txt.lower() in ship_via_target.lower():
                        campo_dropdown.select_option(label=opt_txt)
                        log.info(f"  ✅ Shipping Method (parcial): {opt_txt}")
                        encontrado = True
                        break
                if not encontrado:
                    for opt_txt in opciones:
                        if "ups" in opt_txt.lower() and "ground" in opt_txt.lower():
                            campo_dropdown.select_option(label=opt_txt)
                            log.info(f"  ✅ Shipping Method (fallback UPS Ground): {opt_txt}")
                            break
        except Exception as e_select:
            log.warning(f"  ⚠️  Error al seleccionar Shipping Method: {e_select}")
    else:
        log.warning(f"  ⚠️  Dropdown de Shipping Method no encontrado en el formulario.")

    # ── CAMPO: Ship Quantity (copiar desde Quantity Remaining) ─────────────
    try:
        inputs_rellenados = 0
        filas = page.locator("xpath=//table[.//th[contains(text(),'QUANTITY') or contains(text(),'SHIP')] or .//td[contains(text(),'QUANTITY') or contains(text(),'SHIP')]]//tr").all()
        for fila in filas:
            celdas = fila.locator("td").all_inner_texts()
            if len(celdas) >= 2:
                texto_rem = next((txt.strip() for txt in celdas if txt.strip().isdigit()), "")
                if texto_rem:
                    input_ship = fila.locator("input").first
                    if input_ship.count() > 0:
                        try:
                            input_ship.fill(texto_rem)
                            inputs_rellenados += 1
                            log.info(f"  ✅ Ship Quantity: {texto_rem} (de Quantity Remaining)")
                        except Exception as e_inp:
                            log.warning(f"  ⚠️ No se pudo escribir Ship Quantity: {e_inp}")
        if inputs_rellenados == 0:
            log.warning("  ⚠️ No se encontraron campos de Ship Quantity en esta orden.")
    except Exception as e_qty:
        log.warning(f"  ⚠️ Error procesando Ship Quantity: {e_qty}")

    return exito


# ─────────────────────────────────────────────
#  FLUJO PRINCIPAL
# ─────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("\nUso: python autoship.py <ruta_al_archivo.htm>")
        print("Ejemplo: python autoship.py reportes\\reporte.htm\n")
        sys.exit(1)

    ruta_html = sys.argv[1]
    log = configurar_log()

    # ── Paso 1: Parsear el HTML ────────────────────────────────────────────
    log.info(f"Leyendo archivo: {ruta_html}")
    try:
        ordenes = parse_reporte(ruta_html)
    except FileNotFoundError:
        log.error(f"Archivo no encontrado: {ruta_html}")
        sys.exit(1)

    if not ordenes:
        log.warning("No se encontraron ordenes para el cliente 08461 en el archivo.")
        sys.exit(0)

    mostrar_resumen(ordenes)
    total = len(ordenes)

    # ── Paso 2: Abrir Navegador e Iniciar Sesion ───────────────────────────
    log.info("Iniciando Playwright y abriendo navegador...")
    with sync_playwright() as playwright_instance:
        browser, page = abrir_navegador(playwright_instance)

        log.info(f"Iniciando sesion como: {config.EMAIL}")
        login_ok = hacer_login(page, log)

        if not login_ok:
            log.error("Login fallido. Revisa las credenciales en config.py")
            browser.close()
            sys.exit(1)

        print("\n" + "="*60)
        print("  LOGIN EXITOSO ✅")
        print("  INSTRUCCIONES:")
        print("  1. Navega hasta el formulario quickship de la PRIMERA orden.")
        print("  2. Regresa aquí y presiona ENTER para que el script rellene los campos.")
        print("  3. Después de cada orden: Guarda en el portal, ve a la siguiente")
        print("     y presiona ENTER aquí nuevamente.")
        print("="*60)

        # ── Paso 3: Procesar cada orden ────────────────────────────────────────
        procesadas = 0
        fallidas = []

        for i, orden in enumerate(ordenes, 1):
            print(f"\n{'─'*60}")
            print(f"  ORDEN {i} de {total}")
            print(f"  PO:       {orden['po']}")
            print(f"  Invoice:  {orden['invoice']}")
            print(f"  Tracking: {orden['tracking']}")
            print(f"{'─'*60}")
            print(f"  ► Navega al formulario quickship para esta orden.")
            print(f"    Cuando estés LISTO presiona ENTER (o escribe 's' para saltarla):")

            respuesta = input("  > ").strip().lower()

            if respuesta == "s":
                log.info(f"  ⏭️  Orden {i} ({orden['po']}) SALTADA por el usuario.")
                fallidas.append({"orden": i, "po": orden["po"], "razon": "Saltada por usuario"})
                continue

            log.info(f"Rellenando orden {i}/{total} — PO: {orden['po']}")
            exito = rellenar_formulario(page, orden, log)

            if exito:
                procesadas += 1
                log.info(f"  ✅ Orden {i} rellenada correctamente. Haz clic en GUARDAR en el portal.")
            else:
                log.warning(f"  ⚠️  Orden {i} tuvo problemas. Revisa el log para más detalles.")
                fallidas.append({"orden": i, "po": orden["po"], "razon": "Error al rellenar campos"})

            time.sleep(0.5)

        # ── Paso 4: Resumen final ──────────────────────────────────────────────
        print(f"\n{'='*60}")
        print(f"  PROCESO COMPLETADO")
        print(f"  Total ordenes:    {total}")
        print(f"  Rellenadas:       {procesadas}")
        print(f"  Con problemas:    {len(fallidas)}")
        if fallidas:
            print(f"\n  Ordenes con problemas:")
            for f in fallidas:
                print(f"    - Orden {f['orden']} | PO: {f['po']} | {f['razon']}")
        print(f"{'='*60}")
        log.info("Script finalizado.")

        input("\nPresiona ENTER para cerrar el navegador y terminar el script...")
        browser.close()


if __name__ == "__main__":
    main()
