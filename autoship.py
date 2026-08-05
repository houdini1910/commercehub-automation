"""
autoship.py
-----------
Script principal de automatizacion para CommerceHub DSM.

FLUJO DE USO:
1. Ejecutar: python autoship.py reportes\reporte.htm
2. El script parsea el HTML y muestra las ordenes a procesar.
3. El script abre Brave automaticamente.
4. TU: Inicia sesion, navega hasta el formulario quickship de la primera orden.
5. TU: Presiona ENTER en la consola para indicar que ya estas en el formulario.
6. El script rellena automaticamente: Invoice#, Tracking# y selecciona UPS Ground.
7. TU: Verificas y haces clic en GUARDAR/SHIP en el portal.
8. TU: Navegas al siguiente formulario y presionas ENTER nuevamente.
9. Repetir hasta completar todas las ordenes.

IMPORTANTE:
- El script NO hace clic en Guardar. Solo rellena los campos.
- Si un campo no se encuentra, el script lo avisa sin interrumpir el proceso.
"""

import sys
import time
import logging
from datetime import datetime
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    ElementNotInteractableException,
)
from webdriver_manager.chrome import ChromeDriverManager

from parse_html import parse_reporte, mostrar_resumen
import config


# ─────────────────────────────────────────────
#  CONFIGURACION
# ─────────────────────────────────────────────

# Texto exacto que aparece en el dropdown de Shipping Method para UPS Ground.
# Si el portal usa un texto ligeramente diferente, cambialo aqui.
UPS_GROUND_TEXTO = "UPS Ground"

# Tiempo maximo (segundos) para esperar a que aparezca un elemento en la pagina.
TIMEOUT_SEGUNDOS = 15

# Carpeta donde se guardan los logs
CARPETA_LOGS = Path("logs")


# ─────────────────────────────────────────────
#  LOGGING
# ─────────────────────────────────────────────

def configurar_log() -> logging.Logger:
    CARPETA_LOGS.mkdir(exist_ok=True)
    fecha_hoy = datetime.now().strftime("%Y-%m-%d_%H-%M")
    ruta_log = CARPETA_LOGS / f"autoship_{fecha_hoy}.txt"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.FileHandler(ruta_log, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    log = logging.getLogger("autoship")
    log.info(f"Log guardado en: {ruta_log}")
    return log


# ─────────────────────────────────────────────
#  SELENIUM — ABRIR BRAVE
# ─────────────────────────────────────────────

# Ruta al ejecutable de Brave (ruta estandar en Windows)
BRAVE_PATH = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"

def abrir_brave() -> webdriver.Chrome:
    """Abre una ventana de Brave controlada por el script."""
    opciones = webdriver.ChromeOptions()
    # Apuntar al ejecutable de Brave
    opciones.binary_location = BRAVE_PATH
    # Evitar que Brave se cierre al terminar el script
    opciones.add_experimental_option("detach", True)
    # Deshabilitar mensaje de "Brave is being controlled by automated software"
    opciones.add_experimental_option("excludeSwitches", ["enable-automation"])
    opciones.add_experimental_option("useAutomationExtension", False)
    # Aumentar tamano de ventana para mejor visibilidad
    opciones.add_argument("--start-maximized")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opciones)
    return driver


# ─────────────────────────────────────────────
#  SELENIUM — LOGIN AUTOMATICO
# ─────────────────────────────────────────────

def hacer_login(driver: webdriver.Chrome, log: logging.Logger) -> bool:
    """
    Navega al portal e inicia sesion automaticamente con las credenciales de config.py.
    Retorna True si el login fue exitoso, False si hubo algun problema.
    """
    log.info(f"Navegando a: {config.URL_PORTAL}")
    driver.get(config.URL_PORTAL)

    wait = WebDriverWait(driver, TIMEOUT_SEGUNDOS)

    # ── Campo Email / Usuario ──────────────────────────────────────────────
    selectores_email = [
        (By.ID,    "email"),
        (By.ID,    "username"),
        (By.ID,    "Email"),
        (By.NAME,  "email"),
        (By.NAME,  "username"),
        (By.NAME,  "Email"),
        (By.XPATH, "//input[@type='email']"),
        (By.XPATH, "//input[contains(@placeholder,'email') or contains(@placeholder,'Email') or contains(@placeholder,'usuario') or contains(@placeholder,'user')]"),
    ]
    campo_email = None
    for by, valor in selectores_email:
        try:
            campo_email = wait.until(EC.presence_of_element_located((by, valor)))
            break
        except TimeoutException:
            continue

    if not campo_email:
        log.error("  ❌ No se encontro el campo de email/usuario en la pagina de login.")
        return False

    campo_email.clear()
    campo_email.send_keys(config.EMAIL)
    log.info(f"  ✅ Email ingresado: {config.EMAIL}")

    # ── Campo Password ─────────────────────────────────────────────────────
    selectores_pass = [
        (By.ID,    "password"),
        (By.ID,    "Password"),
        (By.NAME,  "password"),
        (By.NAME,  "Password"),
        (By.XPATH, "//input[@type='password']"),
    ]
    campo_pass = None
    for by, valor in selectores_pass:
        try:
            campo_pass = driver.find_element(by, valor)
            break
        except NoSuchElementException:
            continue

    if not campo_pass:
        log.error("  ❌ No se encontro el campo de password en la pagina de login.")
        return False

    campo_pass.clear()
    campo_pass.send_keys(config.PASSWORD)
    log.info("  ✅ Password ingresado.")

    # ── Boton de Login ─────────────────────────────────────────────────────
    selectores_boton = [
        (By.XPATH, "//button[@type='submit']"),
        (By.XPATH, "//input[@type='submit']"),
        (By.XPATH, "//button[contains(text(),'Login') or contains(text(),'login') or contains(text(),'Sign') or contains(text(),'Entrar')]"),
        (By.ID,    "loginButton"),
        (By.ID,    "submitButton"),
    ]
    boton = None
    for by, valor in selectores_boton:
        try:
            boton = driver.find_element(by, valor)
            break
        except NoSuchElementException:
            continue

    if not boton:
        log.error("  ❌ No se encontro el boton de login.")
        return False

    boton.click()
    log.info("  ✅ Clic en boton de login. Esperando que cargue el portal...")

    # Esperar a que la URL cambie (salir de la pagina de login)
    try:
        wait.until(lambda d: d.current_url != config.URL_PORTAL and "login" not in d.current_url.lower())
        log.info(f"  ✅ Login exitoso. URL actual: {driver.current_url}")
        return True
    except TimeoutException:
        log.warning("  ⚠️  El portal no redireccionó después del login. Puede que requiera un paso extra (ej. 2FA).")
        log.warning("      Revisa el navegador y presiona ENTER cuando estés dentro del portal.")
        input("  > Presiona ENTER cuando hayas completado el login manualmente: ")
        return True


# ─────────────────────────────────────────────
#  SELENIUM — RELLENAR FORMULARIO
# ─────────────────────────────────────────────

def encontrar_campo(driver: webdriver.Chrome, selectores: list[tuple], nombre_campo: str, log: logging.Logger):
    """
    Intenta encontrar un campo usando multiples selectores como fallback.
    Retorna el elemento si lo encuentra, None si no.
    """
    wait = WebDriverWait(driver, TIMEOUT_SEGUNDOS)
    for by, valor in selectores:
        try:
            elemento = wait.until(EC.presence_of_element_located((by, valor)))
            return elemento
        except TimeoutException:
            continue
    log.warning(f"  ⚠️  Campo '{nombre_campo}' no encontrado. Verifica los selectores.")
    return None


def rellenar_formulario(driver: webdriver.Chrome, orden: dict, log: logging.Logger) -> bool:
    """
    Rellena los campos Invoice#, Tracking# y selecciona UPS Ground en el formulario.
    
    Args:
        driver: Instancia del navegador.
        orden:  Diccionario con 'invoice' y 'tracking'.
        log:    Logger.
    
    Returns:
        True si todos los campos se rellenaron, False si hubo algun problema.
    """
    exito = True

    # ── CAMPO: Invoice Number ──────────────────────────────────────────────
    # Intentamos varios selectores comunes del portal CommerceHub DSM
    selectores_invoice = [
        (By.NAME,  "invoiceNumber"),
        (By.NAME,  "invoice_number"),
        (By.NAME,  "invoiceNum"),
        (By.ID,    "invoiceNumber"),
        (By.ID,    "invoice_number"),
        (By.XPATH, "//input[contains(@name,'invoice') and not(contains(@name,'total'))]"),
        (By.XPATH, "//label[contains(text(),'Invoice Number')]/following::input[1]"),
        (By.XPATH, "//td[contains(text(),'Invoice Number')]/following-sibling::td/input"),
    ]
    campo_invoice = encontrar_campo(driver, selectores_invoice, "Invoice Number", log)
    if campo_invoice:
        try:
            campo_invoice.clear()
            campo_invoice.send_keys(orden["invoice"])
            log.info(f"  ✅ Invoice Number: {orden['invoice']}")
        except ElementNotInteractableException:
            log.error(f"  ❌ El campo Invoice Number existe pero no es interactuable.")
            exito = False
    else:
        exito = False

    # ── CAMPO: Tracking Number ─────────────────────────────────────────────
    selectores_tracking = [
        (By.NAME,  "trackingNumber"),
        (By.NAME,  "tracking_number"),
        (By.NAME,  "trackingNum"),
        (By.NAME,  "shipTracking"),
        (By.ID,    "trackingNumber"),
        (By.ID,    "tracking_number"),
        (By.XPATH, "//input[contains(@name,'tracking') or contains(@name,'Tracking')]"),
        (By.XPATH, "//label[contains(text(),'Tracking Number')]/following::input[1]"),
        (By.XPATH, "//td[contains(text(),'Tracking Number')]/following-sibling::td/input"),
    ]
    campo_tracking = encontrar_campo(driver, selectores_tracking, "Tracking Number", log)
    if campo_tracking:
        try:
            campo_tracking.clear()
            campo_tracking.send_keys(orden["tracking"])
            log.info(f"  ✅ Tracking Number: {orden['tracking']}")
        except ElementNotInteractableException:
            log.error(f"  ❌ El campo Tracking Number existe pero no es interactuable.")
            exito = False
    else:
        exito = False

    # ── DROPDOWN: Shipping Method → UPS Ground ────────────────────────────
    selectores_dropdown = [
        (By.NAME,  "shipMethod"),
        (By.NAME,  "shippingMethod"),
        (By.NAME,  "ship_method"),
        (By.NAME,  "carrierMethod"),
        (By.ID,    "shipMethod"),
        (By.ID,    "shippingMethod"),
        (By.XPATH, "//select[contains(@name,'ship') or contains(@name,'Ship') or contains(@name,'method')]"),
        (By.XPATH, "//label[contains(text(),'Shipping Method')]/following::select[1]"),
        (By.XPATH, "//td[contains(text(),'Shipping Method')]/following-sibling::td/select"),
    ]
    campo_dropdown = encontrar_campo(driver, selectores_dropdown, "Shipping Method (dropdown)", log)
    if campo_dropdown:
        try:
            select = Select(campo_dropdown)
            # Intentar seleccionar por texto visible
            try:
                select.select_by_visible_text(UPS_GROUND_TEXTO)
                log.info(f"  ✅ Shipping Method: {UPS_GROUND_TEXTO}")
            except Exception:
                # Si falla, listar las opciones disponibles para diagnostico
                opciones = [opt.text for opt in select.options]
                log.warning(f"  ⚠️  No se encontro '{UPS_GROUND_TEXTO}' en el dropdown.")
                log.warning(f"      Opciones disponibles: {opciones}")
                # Intentar con texto parcial
                for opcion in select.options:
                    if "ups" in opcion.text.lower() and "ground" in opcion.text.lower():
                        select.select_by_visible_text(opcion.text)
                        log.info(f"  ✅ Shipping Method (coincidencia parcial): {opcion.text}")
                        break
        except ElementNotInteractableException:
            log.error(f"  ❌ El dropdown de Shipping Method no es interactuable.")
            exito = False
    else:
        exito = False

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

    # ── Paso 2: Abrir Brave y hacer login automatico ──────────────────────
    log.info("Abriendo Brave...")
    driver = abrir_brave()

    log.info(f"Iniciando sesion como: {config.EMAIL}")
    login_ok = hacer_login(driver, log)

    if not login_ok:
        log.error("Login fallido. Revisa las credenciales en config.py")
        driver.quit()
        sys.exit(1)

    print("\n" + "="*60)
    print("  LOGIN EXITOSO ✅")
    print("  INSTRUCCIONES:")
    print("  1. Navega hasta el formulario quickship de la PRIMERA orden.")
    print("  2. Regresa aqui y presiona ENTER para que el script rellene los campos.")
    print("  3. Despues de cada orden: Guarda en el portal, ve a la siguiente")
    print("     y presiona ENTER aqui nuevamente.")
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
        print(f"    Cuando estes LISTO presiona ENTER (o escribe 's' para saltarla):")

        respuesta = input("  > ").strip().lower()

        if respuesta == "s":
            log.info(f"  ⏭️  Orden {i} ({orden['po']}) SALTADA por el usuario.")
            fallidas.append({"orden": i, "po": orden["po"], "razon": "Saltada por usuario"})
            continue

        log.info(f"Rellenando orden {i}/{total} — PO: {orden['po']}")
        exito = rellenar_formulario(driver, orden, log)

        if exito:
            procesadas += 1
            log.info(f"  ✅ Orden {i} rellenada correctamente. Haz clic en GUARDAR en el portal.")
        else:
            log.warning(f"  ⚠️  Orden {i} tuvo problemas. Revisa el log para mas detalles.")
            fallidas.append({"orden": i, "po": orden["po"], "razon": "Error al rellenar campos"})

        # Pequena pausa para que el usuario pueda ver los cambios
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

    input("\nPresiona ENTER para cerrar Chrome y terminar el script...")
    driver.quit()


if __name__ == "__main__":
    main()
