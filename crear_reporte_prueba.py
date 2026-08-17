"""
crear_reporte_prueba.py
-----------------------
Genera archivos HTM de prueba con datos ficticios para el cliente 08461.
Permite probar la automatización con:
  - 1 sola orden (Single order test)
  - Múltiples órdenes (Batch orders test)
  - Casos con errores / bordes (Error handling test)

Uso CLI:
  py crear_reporte_prueba.py --single [PO]
  py crear_reporte_prueba.py --batch
  py crear_reporte_prueba.py --errores
  py crear_reporte_prueba.py 324483789 324560193
"""

import sys
import argparse
from pathlib import Path

# Forzar UTF-8 en consola de Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

CARPETA_REPORTES = Path("reportes")

def generar_html_prueba(pos: list[str] = None, incluir_errores: bool = False, nombre_archivo: str = "reporte_prueba.htm") -> Path:
    """
    Genera un HTML con las órdenes indicadas.
    Si incluir_errores es True, incluye filas inválidas o de otros clientes para probar el filtrado.
    """
    CARPETA_REPORTES.mkdir(exist_ok=True)
    ruta_salida = CARPETA_REPORTES / nombre_archivo

    if pos is None:
        # POs ficticios por defecto (3 órdenes)
        pos = ["324483789", "324560193", "999888777"]

    filas_html = ""
    idx_row = 1

    # Agregar filas válidas
    for po in pos:
        invoice = f"INV-{1000 + idx_row}"
        tracking = f"1Z9999999999{1000 + idx_row}"
        filas_html += f"""
        <tr>
            <td>{idx_row}</td>
            <td>{invoice}</td>
            <td>08/05/2026</td>
            <td>08461</td>
            <td>{po}</td>
            <td>SO-{5000 + idx_row}</td>
            <td>{tracking}</td>
            <td>UPS Ground</td>
        </tr>"""
        idx_row += 1

    # Si se solicitan errores, agregar filas conflictivas/inválidas
    if incluir_errores:
        # 1. Fila de OTRO cliente (debe ser ignorada por el parser)
        filas_html += f"""
        <tr>
            <td>{idx_row}</td>
            <td>INV-ERR-OTHER</td>
            <td>08/05/2026</td>
            <td>99999</td>
            <td>PO-IGNORAR-OTRO-CLIENTE</td>
            <td>SO-ERR1</td>
            <td>1ZERR9999999991</td>
            <td>UPS Ground</td>
        </tr>"""
        idx_row += 1

        # 2. Fila sin PO number (incompleta)
        filas_html += f"""
        <tr>
            <td>{idx_row}</td>
            <td>INV-ERR-NOPO</td>
            <td>08/05/2026</td>
            <td>08461</td>
            <td></td>
            <td>SO-ERR2</td>
            <td>1ZERR9999999992</td>
            <td>UPS Ground</td>
        </tr>"""
        idx_row += 1

        # 3. Fila sin Tracking ni Invoice (incompleta)
        filas_html += f"""
        <tr>
            <td>{idx_row}</td>
            <td></td>
            <td>08/05/2026</td>
            <td>08461</td>
            <td>PO-SIN-TRACKING-NI-INVOICE</td>
            <td>SO-ERR3</td>
            <td></td>
            <td>UPS Ground</td>
        </tr>"""
        idx_row += 1

    contenido_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Reporte de Prueba AutoShip</title>
</head>
<body>
    <h2>Reporte de Envío de Prueba (Cliente 08461)</h2>
    <table id="Table1" border="1" cellpadding="5">
        <thead>
            <tr>
                <th>Package#</th>
                <th>Invoice#</th>
                <th>Invoice Dt</th>
                <th>Cus.ID</th>
                <th>Cust.P/O#</th>
                <th>S/O#</th>
                <th>Tracking#</th>
                <th>Ship Via</th>
            </tr>
        </thead>
        <tbody>
            {filas_html}
        </tbody>
    </table>
</body>
</html>"""

    with open(ruta_salida, "w", encoding="utf-8") as f:
        f.write(contenido_html)

    print(f"\n✅ Reporte de prueba generado exitosamente en: {ruta_salida.resolve()}")
    print("Ordenes válidas incluidas:")
    for i, po in enumerate(pos, 1):
        print(f"  {i}. PO: {po} | Invoice: INV-{1000 + i} | Tracking: 1Z9999999999{1000 + i}")

    if incluir_errores:
        print("\n⚠️ Se incluyeron 3 filas de prueba de errores (otro cliente, sin PO, sin tracking) para verificar filtrado.")

    return ruta_salida

def generar_prueba_single(po: str = "324483789") -> Path:
    """Genera un reporte de prueba con exactamente 1 sola orden."""
    return generar_html_prueba(pos=[po], incluir_errores=False, nombre_archivo="reporte_prueba_single.htm")

def generar_prueba_batch(pos: list[str] = None) -> Path:
    """Genera un reporte de prueba con múltiples órdenes."""
    if not pos:
        pos = ["324483789", "324560193", "999888777", "PO-TEST-004", "PO-TEST-005"]
    return generar_html_prueba(pos=pos, incluir_errores=False, nombre_archivo="reporte_prueba_batch.htm")

def generar_prueba_errores() -> Path:
    """Genera un reporte de prueba combinando órdenes válidas y casos de error."""
    pos_validos = ["PO-VALIDO-101", "PO-VALIDO-102"]
    return generar_html_prueba(pos=pos_validos, incluir_errores=True, nombre_archivo="reporte_prueba_errores.htm")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generador de reportes de prueba para CommerceHub AutoShip.")
    parser.add_argument("--single", nargs="?", const="324483789", help="Generar reporte con 1 sola orden.")
    parser.add_argument("--batch", action="store_true", help="Generar reporte con múltiples órdenes de lote.")
    parser.add_argument("--errores", action="store_true", help="Generar reporte con órdenes válidas y filas con errores.")
    parser.add_argument("pos", nargs="*", help="Lista explícita de PO Numbers para incluir.")

    args = parser.parse_args()

    if args.single:
        generar_prueba_single(args.single)
    elif args.batch:
        generar_prueba_batch(args.pos if args.pos else None)
    elif args.errores:
        generar_prueba_errores()
    elif args.pos:
        generar_html_prueba(args.pos)
    else:
        generar_html_prueba()
