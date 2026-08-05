"""
parse_html.py
-------------
Lee el archivo HTML generado por la empresa y extrae SOLO las ordenes
del cliente Cus. ID = 08461.

Retorna una lista de diccionarios con:
  - invoice  : Numero de factura (Invoice#)
  - tracking : Numero de tracking (Tracking#)
  - po       : Numero de orden / PO (Cust. P/O#)
"""

import sys
from bs4 import BeautifulSoup

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

CLIENTE_OBJETIVO = "08461"


def parse_reporte(ruta_html: str) -> list[dict]:
    """
    Lee el HTML y devuelve una lista de ordenes para el cliente 08461.
    Usa detección dinámica por encabezados de columna.
    
    Mapeo esperado:
      - Invoice#   -> invoice
      - Cus. ID    -> cliente (08461)
      - Cust. P/O# -> po (PO Number)
      - Tracking#  -> tracking
      - Ship Via   -> ship_via
    """
    with open(ruta_html, "r", encoding="utf-8", errors="ignore") as f:
        contenido = f.read()

    soup = BeautifulSoup(contenido, "html.parser")
    tabla = soup.find("table", {"id": "Table1"}) or soup.find("table")

    if not tabla:
        raise ValueError("No se encontro ninguna tabla en el archivo HTML.")

    filas = tabla.find_all("tr")
    if not filas:
        return []

    # Índices por defecto (fallback)
    idx_invoice  = 1
    idx_cus      = 3
    idx_po       = 4
    idx_tracking = 6
    idx_ship_via = 7

    # Mapeo dinámico leyendo la fila 0 de encabezados
    encabezados_celdas = filas[0].find_all(["td", "th"])
    if encabezados_celdas:
        encabezados = [c.get_text(strip=True).upper() for c in encabezados_celdas]
        for idx, h in enumerate(encabezados):
            if "P/O" in h or "PO" in h:
                idx_po = idx
            elif "TRACKING" in h or "TRACK" in h:
                idx_tracking = idx
            elif "INVOICE" in h and "DT" not in h and "DATE" not in h:
                idx_invoice = idx
            elif "CUS" in h or "CLIENTE" in h:
                idx_cus = idx
            elif "SHIP VIA" in h or "VIA" in h:
                idx_ship_via = idx

    ordenes = []

    for fila in filas[1:]:
        celdas = fila.find_all("td")
        if len(celdas) < 4:
            continue

        textos = [c.get_text(strip=True) for c in celdas]

        # Comprobar si la fila corresponde al cliente 08461
        es_cliente = False
        if idx_cus < len(textos) and CLIENTE_OBJETIVO in textos[idx_cus]:
            es_cliente = True
        elif CLIENTE_OBJETIVO in textos:
            es_cliente = True

        if es_cliente:
            invoice  = textos[idx_invoice] if idx_invoice < len(textos) else ""
            po       = textos[idx_po] if idx_po < len(textos) else ""
            tracking = textos[idx_tracking] if idx_tracking < len(textos) else ""
            ship_via = textos[idx_ship_via] if idx_ship_via < len(textos) else "UPS Ground"

            if po and (invoice or tracking):
                ordenes.append({
                    "invoice":  invoice,
                    "tracking": tracking,
                    "po":       po,
                    "ship_via": ship_via or "UPS Ground",
                })

    return ordenes


def mostrar_resumen(ordenes: list[dict]) -> None:
    """Muestra en consola un resumen de las ordenes encontradas."""
    total = len(ordenes)
    print(f"\n{'='*75}")
    print(f"  ORDENES ENCONTRADAS PARA CLIENTE {CLIENTE_OBJETIVO}: {total}")
    print(f"{'='*75}")
    print(f"  {'#':<5} {'PO / Cust. P/O#':<20} {'Invoice#':<12} {'Tracking#':<25} {'Ship Via'}")
    print(f"  {'-'*5} {'-'*20} {'-'*12} {'-'*25} {'-'*12}")
    for i, orden in enumerate(ordenes, 1):
        ship_via = orden.get('ship_via', 'UPS Ground')
        print(f"  {i:<5} {orden['po']:<20} {orden['invoice']:<12} {orden['tracking']:<25} {ship_via}")
    print(f"{'='*75}\n")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Uso: python parse_html.py <ruta_al_archivo.htm>")
        print("Ejemplo: python parse_html.py reportes\\reporte.htm")
        sys.exit(1)

    ruta = sys.argv[1]
    try:
        ordenes = parse_reporte(ruta)
        mostrar_resumen(ordenes)
    except FileNotFoundError:
        print(f"[ERROR] No se encontro el archivo: {ruta}")
    except ValueError as e:
        print(f"[ERROR] {e}")
