"""
crear_reporte_prueba.py
-----------------------
Genera un archivo HTM de prueba con datos ficticios para el cliente 08461.
Permite probar la automatización sin necesidad de tener un reporte real del día.

Uso:
  py crear_reporte_prueba.py
  py crear_reporte_prueba.py 324483789 324560193
"""

import sys
from pathlib import Path

# Forzar UTF-8 en consola de Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

CARPETA_REPORTES = Path("reportes")

def generar_html_prueba(pos: list[str] = None) -> Path:
    CARPETA_REPORTES.mkdir(exist_ok=True)
    ruta_salida = CARPETA_REPORTES / "reporte_prueba.htm"

    if not pos:
        # POs ficticios por defecto
        pos = ["324483789", "324560193", "999888777"]

    filas_html = ""
    for i, po in enumerate(pos, 1):
        invoice = f"INV-{1000 + i}"
        tracking = f"1Z9999999999{1000 + i}"
        filas_html += f"""
        <tr>
            <td>{i}</td>
            <td>{invoice}</td>
            <td>08/05/2026</td>
            <td>08461</td>
            <td>{po}</td>
            <td>SO-{5000 + i}</td>
            <td>{tracking}</td>
            <td>UPS Ground</td>
        </tr>"""

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
    print("Ordenes generadas:")
    for i, po in enumerate(pos, 1):
        print(f"  {i}. PO: {po} | Invoice: INV-{1000 + i} | Tracking: 1Z9999999999{1000 + i}")
    print("\nPuedes usar este archivo en CommerceHub AutoShip para realizar tus pruebas.")
    return ruta_salida

if __name__ == "__main__":
    pos_argumentos = sys.argv[1:]
    generar_html_prueba(pos_argumentos)
