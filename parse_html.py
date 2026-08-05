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

from bs4 import BeautifulSoup


CLIENTE_OBJETIVO = "08461"


def parse_reporte(ruta_html: str) -> list[dict]:
    """
    Lee el HTML y devuelve una lista de ordenes para el cliente 08461.
    
    Args:
        ruta_html: Ruta al archivo .htm de la empresa.
    
    Returns:
        Lista de dicts con claves: 'invoice', 'tracking', 'po'
    """
    with open(ruta_html, "r", encoding="utf-8", errors="ignore") as f:
        contenido = f.read()

    soup = BeautifulSoup(contenido, "html.parser")
    tabla = soup.find("table", {"id": "Table1"})

    if not tabla:
        # Intentar encontrar cualquier tabla si no tiene el id
        tabla = soup.find("table")

    if not tabla:
        raise ValueError("No se encontro ninguna tabla en el archivo HTML.")

    filas = tabla.find_all("tr")
    ordenes = []

    # La primera fila es el encabezado, se omite
    for fila in filas[1:]:
        celdas = fila.find_all("td")
        if len(celdas) < 8:
            continue  # Fila incompleta, se omite

        # Extraer y limpiar cada columna
        # Orden de columnas: Package# | Invoice# | Invoice Dt | Cus.ID | Cust.P/O# | S/O# | Tracking# | Ship Via
        cus_id   = celdas[3].get_text(strip=True)
        invoice  = celdas[1].get_text(strip=True)
        po       = celdas[4].get_text(strip=True)
        tracking = celdas[6].get_text(strip=True)

        # Solo procesar ordenes del cliente objetivo
        if cus_id == CLIENTE_OBJETIVO:
            ordenes.append({
                "invoice":  invoice,
                "tracking": tracking,
                "po":       po,
            })

    return ordenes


def mostrar_resumen(ordenes: list[dict]) -> None:
    """Muestra en consola un resumen de las ordenes encontradas."""
    total = len(ordenes)
    print(f"\n{'='*60}")
    print(f"  ORDENES ENCONTRADAS PARA CLIENTE {CLIENTE_OBJETIVO}: {total}")
    print(f"{'='*60}")
    print(f"  {'#':<5} {'PO / Cust. P/O#':<25} {'Invoice#':<12} {'Tracking#'}")
    print(f"  {'-'*5} {'-'*25} {'-'*12} {'-'*25}")
    for i, orden in enumerate(ordenes, 1):
        print(f"  {i:<5} {orden['po']:<25} {orden['invoice']:<12} {orden['tracking']}")
    print(f"{'='*60}\n")


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
