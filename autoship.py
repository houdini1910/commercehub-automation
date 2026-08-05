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
import os
from datetime import datetime
from pathlib import Path

import selenium
import selenium.webdriver
import selenium.webdriver.chrome
import selenium.webdriver.chrome.service
import selenium.webdriver.chrome.options
import selenium.webdriver.chrome.webdriver
import selenium.webdriver.common
import selenium.webdriver.common.by
import selenium.webdriver.remote
import selenium.webdriver.remote.webdriver
import selenium.webdriver.remote.webelement
import selenium.webdriver.support
import selenium.webdriver.support.expected_conditions
import selenium.webdriver.support.ui

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    ElementNotInteractableException,
)
from webdriver_manager.chrome import ChromeDriverManager

from parse_html import parse_reporte, mostrar_resumen
import config

def obtener_ruta_brave() -> str:
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

def abrir_brave() -> webdriver.Chrome:
    """Abre una ventana de Brave controlada por el script."""
    opciones = ChromeOptions()
    opciones.binary_location = obtener_ruta_brave()
    opciones.add_experimental_option("detach", True)
    opciones.add_experimental_option("excludeSwitches", ["enable-automation"])
    opciones.add_experimental_option("useAutomationExtension", False)
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
    Verifica que el PO Number exista en la página web actual antes de rellenar.
    Rellena Invoice# y Tracking# en los campos correspondientes.
    
    Args:
        driver: Instancia del navegador.
        orden:  Diccionario con 'po', 'invoice' y 'tracking'.
        log:    Logger.
    
    Returns:
        True si los campos obligatorios se rellenaron con exito, False si hubo problema o PO no coincide.
    """
    po_target = orden["po"]
    invoice_val = orden["invoice"]
    tracking_val = orden["tracking"]

    log.info(f"  🔍 Verificando PO Number '{po_target}' en la página actual...")

    # ── Paso 0: Validar si el PO Number esta en la pagina ────────────────────
    po_elementos = driver.find_elements(By.XPATH, f"//*[contains(text(), '{po_target}')]")
    
    if not po_elementos:
        # Verificacion secundaria por codigo fuente
        if po_target not in driver.page_source:
            log.error(f"  ❌ ERROR DE COINCIDENCIA: El PO Number '{po_target}' NO fue encontrado en la página actual.")
            log.error(f"     SE OMITIÓ EL LLENADO de esta orden para no ingresar datos erróneos.")
            return False

    log.info(f"  ✅ Coincidencia confirmada para PO Number '{po_target}'.")

    # Intentar obtener el contenedor específico para esta orden si hay varios en pantalla
    search_scope = driver
    if po_elementos:
        try:
            # Buscar el contenedor padre (tabla, formulario o div) mas cercano
            contenedor = po_elementos[0].find_element(
                By.XPATH, "./ancestor::table[contains(@class,'form') or contains(@id,'') or position()=1] | ./ancestor::div[contains(@class,'order') or contains(@id,'order') or position()=1]"
            )
            search_scope = contenedor
        except Exception:
            search_scope = driver

    exito = True

    # ── CAMPO: Invoice Number ──────────────────────────────────────────────
    selectores_invoice = [
        (By.NAME,  "invoiceNumber"),
        (By.NAME,  "invoice_number"),
        (By.NAME,  "invoiceNum"),
        (By.ID,    "invoiceNumber"),
        (By.ID,    "invoice_number"),
        (By.XPATH, ".//input[contains(@name,'invoice') and not(contains(@name,'total'))]"),
        (By.XPATH, ".//label[contains(text(),'Invoice')]/following::input[1]"),
        (By.XPATH, ".//td[contains(text(),'Invoice')]/following-sibling::td/input"),
        (By.XPATH, "//input[contains(@name,'invoice') and not(contains(@name,'total'))]"),
        (By.XPATH, "//td[contains(text(),'Invoice')]/following-sibling::td/input"),
    ]
    
    campo_invoice = None
    for by, valor in selectores_invoice:
        try:
            if search_scope != driver and valor.startswith(".//"):
                elementos = search_scope.find_elements(by, valor)
                if elementos:
                    campo_invoice = elementos[0]
                    break
            else:
                elementos = driver.find_elements(by, valor)
                if elementos:
                    campo_invoice = elementos[0]
                    break
        except Exception:
            continue

    if campo_invoice:
        try:
            campo_invoice.clear()
            campo_invoice.send_keys(invoice_val)
            log.info(f"  ✅ Invoice Number ingresado: {invoice_val}")
        except ElementNotInteractableException:
            log.error(f"  ❌ Campo Invoice Number no interactuable.")
            exito = False
    else:
        log.error(f"  ❌ No se encontró el campo Invoice Number para PO {po_target}.")
        exito = False

    # ── CAMPO: Tracking Number ─────────────────────────────────────────────
    selectores_tracking = [
        (By.NAME,  "trackingNumber"),
        (By.NAME,  "tracking_number"),
        (By.NAME,  "trackingNum"),
        (By.NAME,  "shipTracking"),
        (By.ID,    "trackingNumber"),
        (By.ID,    "tracking_number"),
        (By.XPATH, ".//input[contains(@name,'tracking') or contains(@name,'Tracking')]"),
        (By.XPATH, ".//label[contains(text(),'Tracking')]/following::input[1]"),
        (By.XPATH, ".//td[contains(text(),'Tracking')]/following-sibling::td/input"),
        (By.XPATH, "//input[contains(@name,'tracking') or contains(@name,'Tracking')]"),
        (By.XPATH, "//td[contains(text(),'Tracking')]/following-sibling::td/input"),
    ]

    campo_tracking = None
    for by, valor in selectores_tracking:
        try:
            if search_scope != driver and valor.startswith(".//"):
                elementos = search_scope.find_elements(by, valor)
                if elementos:
                    campo_tracking = elementos[0]
                    break
            else:
                elementos = driver.find_elements(by, valor)
                if elementos:
                    campo_tracking = elementos[0]
                    break
        except Exception:
            continue

    if campo_tracking:
        try:
            campo_tracking.clear()
            campo_tracking.send_keys(tracking_val)
            log.info(f"  ✅ Tracking Number ingresado: {tracking_val}")
        except ElementNotInteractableException:
            log.error(f"  ❌ Campo Tracking Number no interactuable.")
            exito = False
    else:
        log.error(f"  ❌ No se encontró el campo Tracking Number para PO {po_target}.")
        exito = False

    # ── DROPDOWN: Shipping Method ──────────────────────────────────────────
    ship_via_target = orden.get("ship_via", UPS_GROUND_TEXTO) or UPS_GROUND_TEXTO
    selectores_dropdown = [
        (By.NAME,  "shipMethod"),
        (By.NAME,  "shippingMethod"),
        (By.NAME,  "ship_method"),
        (By.NAME,  "carrierMethod"),
        (By.ID,    "shipMethod"),
        (By.ID,    "shippingMethod"),
        (By.XPATH, ".//select[contains(@name,'ship') or contains(@name,'Ship') or contains(@name,'method')]"),
        (By.XPATH, ".//label[contains(text(),'Shipping Method')]/following::select[1]"),
        (By.XPATH, ".//td[contains(text(),'Shipping Method')]/following-sibling::td/select"),
        (By.XPATH, "//select[contains(@name,'ship') or contains(@name,'Ship') or contains(@name,'method')]"),
    ]
    
    campo_dropdown = None
    for by, valor in selectores_dropdown:
        try:
            if search_scope != driver and valor.startswith(".//"):
                elementos = search_scope.find_elements(by, valor)
                if elementos:
                    campo_dropdown = elementos[0]
                    break
            else:
                elementos = driver.find_elements(by, valor)
                if elementos:
                    campo_dropdown = elementos[0]
                    break
        except Exception:
            continue

    if campo_dropdown:
        try:
            select = Select(campo_dropdown)
            encontrado = False
            # 1. Coincidencia exacta
            try:
                select.select_by_visible_text(ship_via_target)
                log.info(f"  ✅ Shipping Method seleccionado: {ship_via_target}")
                encontrado = True
            except Exception:
                pass

            # 2. Coincidencia por texto parcial
            if not encontrado:
                for opcion in select.options:
                    opt_txt = opcion.text.strip()
                    if ship_via_target.lower() in opt_txt.lower() or opt_txt.lower() in ship_via_target.lower():
                        select.select_by_visible_text(opcion.text)
                        log.info(f"  ✅ Shipping Method (parcial): {opcion.text}")
                        encontrado = True
                        break

            # 3. Fallback a UPS Ground si la meta es cliente 08461
            if not encontrado:
                for opcion in select.options:
                    if "ups" in opcion.text.lower() and "ground" in opcion.text.lower():
                        select.select_by_visible_text(opcion.text)
                        log.info(f"  ✅ Shipping Method (fallback UPS Ground): {opcion.text}")
                        encontrado = True
                        break

            if not encontrado:
                opciones = [opt.text for opt in select.options]
                log.warning(f"  ⚠️  No se encontró '{ship_via_target}' en el dropdown. Opciones: {opciones}")
        except ElementNotInteractableException:
            log.warning(f"  ⚠️  Dropdown de Shipping Method no es interactuable (campo de solo lectura).")
    else:
        log.warning(f"  ⚠️  Dropdown de Shipping Method no encontrado en el formulario.")

    # ── CAMPO: Ship Quantity (copiar desde Quantity Remaining) ─────────────
    try:
        inputs_rellenados = 0
        # Buscar tablas de items con cabecera QUANTITY REMAINING o SHIP QUANTITY
        tablas_items = search_scope.find_elements(
            By.XPATH, ".//table[.//th[contains(text(),'QUANTITY') or contains(text(),'SHIP')] or .//td[contains(text(),'QUANTITY') or contains(text(),'SHIP')]]"
        )
        if not tablas_items and search_scope != driver:
            tablas_items = driver.find_elements(
                By.XPATH, "//table[.//th[contains(text(),'QUANTITY') or contains(text(),'SHIP')] or .//td[contains(text(),'QUANTITY') or contains(text(),'SHIP')]]"
            )

        if tablas_items:
            for tabla in tablas_items:
                filas = tabla.find_elements(By.XPATH, ".//tr")
                for fila in filas:
                    celdas = fila.find_elements(By.XPATH, ".//td")
                    if len(celdas) >= 2:
                        # Buscar si hay alguna celda con numero (Quantity Remaining)
                        texto_rem = ""
                        for c in celdas:
                            txt = c.text.strip()
                            if txt.isdigit():
                                texto_rem = txt
                                break
                        
                        if texto_rem:
                            inputs_en_fila = fila.find_elements(By.XPATH, ".//input")
                            if inputs_en_fila:
                                input_ship = inputs_en_fila[0]
                                try:
                                    input_ship.clear()
                                    input_ship.send_keys(texto_rem)
                                    inputs_rellenados += 1
                                    log.info(f"  ✅ Ship Quantity: {texto_rem} (de Quantity Remaining)")
                                except Exception as e_inp:
                                    log.warning(f"  ⚠️ No se pudo escribir Ship Quantity: {e_inp}")
        
        # Fallback si no se hallo tabla con cabecera: buscar inputs de cantidad directamente
        if inputs_rellenados == 0:
            inputs_qty = search_scope.find_elements(
                By.XPATH, ".//td[contains(@class,'ship') or position()=2]//input | .//input[contains(@name,'ship') or contains(@name,'qty') or contains(@name,'Qty')]"
            )
            for inp in inputs_qty:
                try:
                    tr = inp.find_element(By.XPATH, "./ancestor::tr[1]")
                    tds = tr.find_elements(By.XPATH, ".//td")
                    for td in tds:
                        txt = td.text.strip()
                        if txt.isdigit():
                            inp.clear()
                            inp.send_keys(txt)
                            inputs_rellenados += 1
                            log.info(f"  ✅ Ship Quantity (fallback): {txt}")
                            break
                except Exception:
                    continue

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
