@echo off
chcp 65001 > nul
echo ===================================================
echo   Generando archivo de prueba para CommerceHub
echo ===================================================
py crear_reporte_prueba.py
echo.
echo Presiona cualquier tecla para cerrar esta ventana...
pause > nul
