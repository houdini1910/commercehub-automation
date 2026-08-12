"""
diagnostico_login.py - v4 (Playwright)
Detecta campos de login SSO en CommerceHub utilizando Playwright (con soporte nativo para Shadow DOM).
Ejecutar: python diagnostico_login.py
"""

import sys
import time
import json

# Forzar UTF-8 en la consola de Windows
sys.stdout.reconfigure(encoding="utf-8")

from playwright.sync_api import sync_playwright

BRAVE_PATH = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
URL_SSO    = "https://sso.auth.commercehub.com/oauth/account/login?appId=7cdb563a-d175-4af2-94f1-a6aa81cffeeb"


def main():
    print("Iniciando Playwright...")
    with sync_playwright() as p:
        import os
        if os.path.exists(BRAVE_PATH):
            browser = p.chromium.launch(executable_path=BRAVE_PATH, headless=False)
        else:
            browser = p.chromium.launch(headless=False)

        page = browser.new_page()

        print(f"Navegando a: {URL_SSO}")
        page.goto(URL_SSO)

        print("Esperando que cargue la pagina (hasta 20 seg)...")
        time.sleep(3)

        print(f"\nURL final: {page.url}")

        # Playwright consulta de inputs y botones en el DOM (incluyendo Shadow DOM automáticamente)
        inputs = page.locator("input").all()
        buttons = page.locator("button").all()

        print(f"\n{'='*60}")
        print(f"  INPUTS encontrados por Playwright (incluyendo Shadow DOM): {len(inputs)}")
        print(f"{'='*60}")

        for i, inp in enumerate(inputs):
            try:
                type_attr = inp.get_attribute("type") or ""
                id_attr = inp.get_attribute("id") or ""
                name_attr = inp.get_attribute("name") or ""
                ph_attr = inp.get_attribute("placeholder") or ""
                print(f"  [{i}] type={type_attr!r} | id={id_attr!r} | name={name_attr!r} | placeholder={ph_attr!r}")
            except Exception as e:
                print(f"  [{i}] Error al inspeccionar elemento: {e}")

        print(f"\n{'='*60}")
        print(f"  BUTTONS encontrados por Playwright (incluyendo Shadow DOM): {len(buttons)}")
        print(f"{'='*60}")

        for i, btn in enumerate(buttons):
            try:
                text = btn.inner_text().strip()
                type_attr = btn.get_attribute("type") or ""
                id_attr = btn.get_attribute("id") or ""
                print(f"  [{i}] text={text!r} | type={type_attr!r} | id={id_attr!r}")
            except Exception as e:
                print(f"  [{i}] Error al inspeccionar boton: {e}")

        print("\nDiagnostico completado con exito.")
        browser.close()


if __name__ == "__main__":
    main()
