"""
test_playwright_migration.py
-----------------------------
Pruebas automatizadas de integracion para verificar la migración a Playwright.
"""

import os
import pytest
from pathlib import Path
from parse_html import parse_reporte
from crear_reporte_prueba import generar_html_prueba

def test_parse_reporte_integration():
    """Verifica que el generador de pruebas y el parser funcionen juntos."""
    pos = ["PO123456", "PO789012"]
    ruta_html = generar_html_prueba(pos)
    assert os.path.exists(ruta_html)

    ordenes = parse_reporte(str(ruta_html))
    assert len(ordenes) == 2
    assert ordenes[0]["po"] == "PO123456"
    assert ordenes[1]["po"] == "PO789012"

def test_playwright_page_fixture(page):
    """Verifica que la fixture de pytest-playwright funcione correctamente."""
    page.goto("data:text/html,<html><body><h1>CommerceHub AutoShip Test</h1></body></html>")
    heading = page.locator("h1")
    assert heading.inner_text() == "CommerceHub AutoShip Test"
