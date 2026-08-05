"""
diagnostico_login.py - v3
Detecta campos en Shadow DOM (usado por Frontegg/CommerceHub SSO).
Ejecutar: py diagnostico_login.py
"""

import sys
import time

# Forzar UTF-8 en la consola de Windows
sys.stdout.reconfigure(encoding="utf-8")

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

BRAVE_PATH = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
URL_SSO    = "https://sso.auth.commercehub.com/oauth/account/login?appId=7cdb563a-d175-4af2-94f1-a6aa81cffeeb"

# JavaScript que busca inputs/buttons incluyendo Shadow DOM (varios niveles)
JS_FIND_INPUTS = """
function findAll(root, tag) {
    let results = [];
    try {
        root.querySelectorAll(tag).forEach(el => {
            results.push({
                tag:         el.tagName,
                type:        el.type        || '',
                id:          el.id          || '',
                name:        el.name        || '',
                placeholder: el.placeholder || '',
                className:   el.className   || '',
                text:        el.textContent ? el.textContent.trim().substring(0, 60) : ''
            });
        });
        root.querySelectorAll('*').forEach(el => {
            if (el.shadowRoot) {
                results = results.concat(findAll(el.shadowRoot, tag));
            }
        });
    } catch(e) {}
    return results;
}
return JSON.stringify({
    inputs:  findAll(document, 'input'),
    buttons: findAll(document, 'button'),
    iframes: Array.from(document.querySelectorAll('iframe')).map(f => ({src: f.src, name: f.name}))
});
"""


def main():
    opts = webdriver.ChromeOptions()
    opts.binary_location = BRAVE_PATH
    opts.add_argument("--start-maximized")

    print("Abriendo Brave...")
    service = Service(ChromeDriverManager().install())
    drv = webdriver.Chrome(service=service, options=opts)

    print(f"Navegando a: {URL_SSO}")
    drv.get(URL_SSO)

    # Esperar hasta 30 seg a que haya algun contenido renderizado
    print("Esperando que cargue el JS (hasta 30 seg)...")
    for i in range(30):
        time.sleep(1)
        result_raw = drv.execute_script(JS_FIND_INPUTS)
        import json
        data = json.loads(result_raw)
        if data["inputs"] or data["buttons"]:
            print(f"  -> Elementos encontrados despues de {i+1} seg")
            break
        if i % 5 == 4:
            print(f"  -> {i+1} seg, aun sin elementos...")
    else:
        print("  -> Timeout (30 seg). Tomando snapshot de todas formas.")

    print(f"\nURL final: {drv.current_url}")

    import json
    result_raw = drv.execute_script(JS_FIND_INPUTS)
    data = json.loads(result_raw)

    print(f"\n{'='*60}")
    print(f"  INPUTS encontrados (incluyendo Shadow DOM): {len(data['inputs'])}")
    print(f"{'='*60}")
    for i, el in enumerate(data["inputs"]):
        print(f"\n  [{i}] type        = {el['type']!r}")
        print(f"       id          = {el['id']!r}")
        print(f"       name        = {el['name']!r}")
        print(f"       placeholder = {el['placeholder']!r}")
        print(f"       class       = {el['className']!r}")

    print(f"\n{'='*60}")
    print(f"  BUTTONS encontrados (incluyendo Shadow DOM): {len(data['buttons'])}")
    print(f"{'='*60}")
    for i, el in enumerate(data["buttons"]):
        print(f"\n  [{i}] type  = {el['type']!r}")
        print(f"       id    = {el['id']!r}")
        print(f"       texto = {el['text']!r}")
        print(f"       class = {el['className']!r}")

    print(f"\n{'='*60}")
    print(f"  IFRAMES: {len(data['iframes'])}")
    print(f"{'='*60}")
    for i, fr in enumerate(data["iframes"]):
        print(f"  [{i}] src={fr['src'][:80]!r}  name={fr['name']!r}")

    # HTML del body para referencia
    print(f"\n{'='*60}")
    print("  HTML DEL BODY (primeros 4000 chars):")
    print(f"{'='*60}")
    try:
        body_html = drv.execute_script("return document.body.innerHTML;")
        print(body_html[:4000])
    except Exception as e:
        print(f"  Error: {e}")

    print(f"\n{'='*60}")
    print("  FIN DEL DIAGNOSTICO")
    print(f"{'='*60}")
    input("\nPresiona ENTER para cerrar Brave...")
    drv.quit()


if __name__ == "__main__":
    main()
