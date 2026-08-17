"""
test_ordenes_variadas.py
-------------------------
Suite de pruebas automatizadas para verificar el procesamiento de:
- 1 sola orden (Single order test)
- Lotes de múltiples órdenes (Batch orders test)
- Filtrado de errores y filas inválidas (Error handling verification)
- Variaciones de formato en números de orden (PO Numbers)
"""

import os
import pytest
from pathlib import Path
from parse_html import parse_reporte
from crear_reporte_prueba import (
    generar_html_prueba,
    generar_prueba_single,
    generar_prueba_batch,
    generar_prueba_errores,
)


def test_single_order_parsing():
    """Verifica que una prueba con exactamente 1 número de orden funcione correctamente."""
    po_unico = "PO-SINGLE-999"
    ruta_html = generar_prueba_single(po=po_unico)

    assert os.path.exists(ruta_html), "El archivo HTML de 1 orden debe crearse."
    ordenes = parse_reporte(str(ruta_html))

    assert len(ordenes) == 1, f"Se esperaba exactamente 1 orden, se obtuvieron {len(ordenes)}"
    assert ordenes[0]["po"] == po_unico
    assert ordenes[0]["invoice"] == "INV-1001"
    assert ordenes[0]["tracking"] == "1Z99999999991001"


def test_multiple_orders_batch():
    """Verifica el procesamiento de un lote de múltiples números de orden."""
    pos = ["PO-101", "PO-102", "PO-103", "PO-104", "PO-105"]
    ruta_html = generar_prueba_batch(pos=pos)

    ordenes = parse_reporte(str(ruta_html))

    assert len(ordenes) == 5, f"Se esperaban 5 órdenes en el lote, se obtuvieron {len(ordenes)}"
    for i, po_esperado in enumerate(pos):
        assert ordenes[i]["po"] == po_esperado


def test_error_rows_filtering():
    """
    Verifica que las filas defectuosas o de otros clientes no causen fallos
    y sean filtradas correctamente.
    """
    ruta_html = generar_prueba_errores()
    ordenes = parse_reporte(str(ruta_html))

    # El generador incluye 2 órdenes válidas ("PO-VALIDO-101", "PO-VALIDO-102")
    # y 3 filas de error (otro cliente, sin PO, sin tracking/invoice)
    assert len(ordenes) == 2, f"Deben filtrarse los errores y quedar 2 órdenes válidas, pero se encontraron {len(ordenes)}"
    
    pos_resultantes = [o["po"] for o in ordenes]
    assert "PO-VALIDO-101" in pos_resultantes
    assert "PO-VALIDO-102" in pos_resultantes
    assert "PO-IGNORAR-OTRO-CLIENTE" not in pos_resultantes
    assert "PO-SIN-TRACKING-NI-INVOICE" not in pos_resultantes


@pytest.mark.parametrize("po_test", [
    "123456789",          # Numérico estándar
    "PO-2026-9876",       # Con guiones
    "000045612",          # Con ceros a la izquierda
    "CUST_ORDER_ALPHA",   # Alfanumérico con guion bajo
    "PO #8899",           # Con espacio y numeral
])
def test_po_format_variations(po_test):
    """Verifica que diversos formatos y caracteres en los números de orden sean procesados correctamente."""
    ruta_html = generar_html_prueba(pos=[po_test], nombre_archivo="reporte_test_format.htm")
    ordenes = parse_reporte(str(ruta_html))

    assert len(ordenes) == 1
    assert ordenes[0]["po"] == po_test
