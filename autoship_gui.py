"""
autoship_gui.py
---------------
Aplicación gráfica para CommerceHub AutoShip utilizando Playwright.
Selecciona el archivo .htm, el script inicia sesión automáticamente
y rellena los formularios de cada orden.
El navegador permanece abierto tras rellenar los datos para que el usuario pueda
revisar, guardar en el portal o navegar libremente.

Para regenerar el .exe (PowerShell):
    python -m PyInstaller --noconfirm CommerceHub-AutoShip.spec
"""

import tkinter as tk
from tkinter import filedialog, simpledialog

import os
import sys
import time
import queue
import threading
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright, Page, Browser, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup

from parse_html import parse_reporte, CLIENTE_OBJETIVO
from crear_reporte_prueba import (
    generar_html_prueba,
    generar_prueba_single,
    generar_prueba_batch,
    generar_prueba_errores,
)

def obtener_ruta_brave() -> str:
    """Retorna la ruta al ejecutable de Brave encontrada en el sistema."""
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

# ─────────────────────────────────────────────────────────────────────────────
#  CONFIGURACIÓN
# ─────────────────────────────────────────────────────────────────────────────

EMAIL      = "Sammy@josmo.com"
PASSWORD   = "Panda@2025"
URL_PORTAL = "https://dsm.commercehub.com"

BRAVE_PATH = obtener_ruta_brave()
CLIENTE_OBJETIVO = "08461"
UPS_GROUND_TEXTO = "UPS Ground"
TIMEOUT_SEG = 15000  # ms


# ─────────────────────────────────────────────────────────────────────────────
#  PALETA DE COLORES
# ─────────────────────────────────────────────────────────────────────────────

C_BG       = "#0d1117"   # fondo principal
C_CARD     = "#161b22"   # tarjetas
C_INPUT    = "#21262d"   # inputs / log
C_BORDER   = "#30363d"   # bordes
C_ACCENT   = "#1f6feb"   # azul primario
C_ACCENT_H = "#388bfd"   # hover azul
C_SUCCESS  = "#238636"   # verde
C_SUCCESS_H= "#2ea043"
C_WARN     = "#9e6a03"   # amarillo oscuro
C_DANGER   = "#da3633"   # rojo
C_TEXT     = "#e6edf3"   # texto principal
C_MUTED    = "#8b949e"   # texto secundario
C_HEAD     = "#58a6ff"   # encabezados log


# ─────────────────────────────────────────────────────────────────────────────
#  APLICACIÓN GUI
# ─────────────────────────────────────────────────────────────────────────────

class CommerceHubApp:

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("CommerceHub AutoShip (Playwright)")
        self.root.geometry("700x780")
        self.root.minsize(600, 680)
        self.root.configure(bg=C_BG)
        self.root.resizable(True, True)

        # Estado interno
        self.ruta_htm            = tk.StringVar()
        self.log_q               = queue.Queue()
        self.action_event        = threading.Event()
        self.close_browser_event = threading.Event()
        self.action_result       = None   # "rellenar" | "saltar" | "cerrar_browser"

        self.root.protocol("WM_DELETE_WINDOW", self._on_close_window)

        self._build_ui()
        self._poll_logs()

    def _on_close_window(self):
        """Cierra únicamente la ventana GUI de la aplicación manteniendo abierta la ventana del navegador."""
        try:
            self.root.destroy()
        except Exception:
            pass

    # ─── Construcción de UI ──────────────────────────────────────────────────

    def _build_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(4, weight=1)   # El log se expande en row 4

        # ── Header ──────────────────────────────────────────────────────────
        hdr = tk.Frame(self.root, bg=C_CARD, pady=18)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.columnconfigure(0, weight=1)

        tk.Label(hdr, text="🚀  CommerceHub AutoShip",
                 font=("Segoe UI", 20, "bold"),
                 bg=C_CARD, fg=C_TEXT).pack()
        tk.Label(hdr, text="Automatización de órdenes DSM  ·  Playwright Python",
                 font=("Segoe UI", 10),
                 bg=C_CARD, fg=C_MUTED).pack(pady=(2, 0))

        sep = tk.Frame(self.root, bg=C_BORDER, height=1)
        sep.grid(row=0, column=0, sticky="sew")

        # ── Selección de archivo ─────────────────────────────────────────────
        card_file = tk.Frame(self.root, bg=C_CARD, padx=24, pady=16)
        card_file.grid(row=1, column=0, sticky="ew", padx=16, pady=(14, 6))
        card_file.columnconfigure(1, weight=1)

        tk.Label(card_file, text="📄  Archivo de órdenes (.htm)",
                 font=("Segoe UI", 11, "bold"),
                 bg=C_CARD, fg=C_TEXT).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))

        self.entry_file = tk.Entry(card_file, textvariable=self.ruta_htm,
                                   bg=C_INPUT, fg=C_TEXT, insertbackground=C_TEXT,
                                   relief="flat", font=("Segoe UI", 10),
                                   state="readonly", readonlybackground=C_INPUT)
        self.entry_file.grid(row=1, column=0, columnspan=2, sticky="ew", ipady=7, ipadx=6)

        btn_files_frame = tk.Frame(card_file, bg=C_CARD)
        btn_files_frame.grid(row=1, column=2, padx=(10, 0))

        tk.Button(btn_files_frame, text="📁 Buscar archivo",
                  command=self._buscar_archivo,
                  bg=C_ACCENT, fg=C_TEXT,
                  activebackground=C_ACCENT_H, activeforeground=C_TEXT,
                  relief="flat", font=("Segoe UI", 10, "bold"),
                  cursor="hand2", padx=12, pady=5,
                  bd=0).pack(side="left", padx=(0, 5))

        tk.Button(btn_files_frame, text="🧪 Crear datos de prueba",
                  command=self._generar_prueba_gui,
                  bg=C_INPUT, fg=C_HEAD,
                  activebackground=C_BORDER, activeforeground=C_TEXT,
                  relief="flat", font=("Segoe UI", 9, "bold"),
                  cursor="hand2", padx=10, pady=5,
                  bd=0).pack(side="left")

        # ── Botón INICIAR ────────────────────────────────────────────────────
        btn_frame = tk.Frame(self.root, bg=C_BG, padx=16)
        btn_frame.grid(row=2, column=0, sticky="ew", pady=(0, 6))
        btn_frame.columnconfigure(0, weight=1)

        self.btn_start = tk.Button(btn_frame,
                                   text="▶   INICIAR AUTOMATIZACIÓN",
                                   command=self._iniciar,
                                   bg=C_SUCCESS, fg=C_TEXT,
                                   relief="flat", font=("Segoe UI", 13, "bold"),
                                   cursor="hand2", pady=13, bd=0)
        self.btn_start.grid(row=0, column=0, sticky="ew")

        # ── Panel orden activa ───────────────────────────────────────────────
        self.card_orden = tk.Frame(self.root, bg=C_CARD, padx=24, pady=14)
        self.card_orden.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 6))
        self.card_orden.columnconfigure(0, weight=1)

        self.lbl_orden_title = tk.Label(self.card_orden,
                                         text="── Sin orden activa ──",
                                         font=("Segoe UI", 11, "bold"),
                                         bg=C_CARD, fg=C_MUTED)
        self.lbl_orden_title.grid(row=0, column=0, sticky="w", pady=(0, 8))

        # Botones acción (Duales: Rellenar y Re-Rellenar)
        accion_frame = tk.Frame(self.card_orden, bg=C_CARD)
        accion_frame.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        accion_frame.columnconfigure(0, weight=1)
        accion_frame.columnconfigure(1, weight=1)

        self.btn_rellenar = tk.Button(accion_frame,
                                       text="✅   RELLENAR CAMPOS",
                                       command=lambda: self._accion("rellenar"),
                                       bg=C_SUCCESS, fg=C_TEXT,
                                       activebackground=C_SUCCESS_H,
                                       relief="flat", font=("Segoe UI", 10, "bold"),
                                       cursor="hand2", pady=10, state="disabled", bd=0)
        self.btn_rellenar.grid(row=0, column=0, sticky="ew", padx=(0, 5))

        self.btn_rerellenar = tk.Button(accion_frame,
                                         text="🔄   RE-RELLENAR CAMPOS",
                                         command=lambda: self._accion("rerellenar"),
                                         bg=C_ACCENT, fg=C_TEXT,
                                         activebackground=C_ACCENT_H,
                                         relief="flat", font=("Segoe UI", 10, "bold"),
                                         cursor="hand2", pady=10, state="disabled", bd=0)
        self.btn_rerellenar.grid(row=0, column=1, sticky="ew", padx=(5, 0))

        # ── Log de actividad ─────────────────────────────────────────────────
        log_frame = tk.Frame(self.root, bg=C_CARD, padx=24, pady=14)
        log_frame.grid(row=4, column=0, sticky="nsew", padx=16, pady=(0, 6))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(1, weight=1)

        tk.Label(log_frame, text="📋  Registro de actividad",
                 font=("Segoe UI", 10, "bold"),
                 bg=C_CARD, fg=C_TEXT).grid(row=0, column=0, sticky="w", pady=(0, 6))

        txt_frame = tk.Frame(log_frame, bg=C_INPUT)
        txt_frame.grid(row=1, column=0, sticky="nsew")

        self.txt_log = tk.Text(txt_frame, bg=C_INPUT, fg=C_TEXT,
                               font=("Consolas", 9), relief="flat",
                               state="disabled", wrap="word", bd=0, padx=10, pady=10)
        self.txt_log.pack(side="left", fill="both", expand=True)

        scroll = tk.Scrollbar(txt_frame, command=self.txt_log.yview, bg=C_CARD, bd=0)
        scroll.pack(side="right", fill="y")
        self.txt_log.config(yscrollcommand=scroll.set)

        # Tags de formato para el log
        self.txt_log.tag_config("head", foreground=C_HEAD, font=("Consolas", 9, "bold"))
        self.txt_log.tag_config("ok",   foreground="#3fb950")
        self.txt_log.tag_config("warn", foreground="#d29922")
        self.txt_log.tag_config("err",  foreground="#f85149", font=("Consolas", 9, "bold"))
        self.txt_log.tag_config("info", foreground=C_MUTED)

        # ── Barra de estado ──────────────────────────────────────────────────
        self.lbl_status = tk.Label(self.root, text="● Listo — Selecciona un archivo .htm e inicia",
                                   font=("Segoe UI", 9), bg=C_BG, fg=C_MUTED, anchor="w", padx=20, pady=6)
        self.lbl_status.grid(row=5, column=0, sticky="ew")

    # ─── Métodos auxiliares UI y Hilos ───────────────────────────────────────

    def _ui(self, func):
        self.root.after(0, func)

    def _log(self, text: str, tag: str = None):
        self.log_q.put((text, tag))

    def _poll_logs(self):
        while not self.log_q.empty():
            text, tag = self.log_q.get_nowait()
            ts = datetime.now().strftime("[%H:%M:%S] ")
            self.txt_log.config(state="normal")
            self.txt_log.insert("end", ts, "info")
            if tag:
                self.txt_log.insert("end", text + "\n", tag)
            else:
                self.txt_log.insert("end", text + "\n")
            self.txt_log.see("end")
            self.txt_log.config(state="disabled")
        self.root.after(100, self._poll_logs)

    def _set_status(self, msg: str):
        self._ui(lambda: self.lbl_status.config(text=msg))

    def _bloquear_botones_accion(self, msg="── Procesando... ──"):
        def _f():
            self.btn_rellenar.config(state="disabled")
            self.btn_rerellenar.config(state="disabled")
            self.lbl_orden_title.config(text=msg, fg=C_MUTED)
        self._ui(_f)

    def _activar_botones_accion(self, total_ordenes=None):
        def _f():
            self.btn_rellenar.config(state="normal", bg=C_SUCCESS, activebackground=C_SUCCESS_H)
            self.btn_rerellenar.config(state="normal", bg=C_ACCENT, activebackground=C_ACCENT_H)
            if total_ordenes:
                self.lbl_orden_title.config(
                    text=f"📦  {total_ordenes} Órdenes cargadas — navega en CommerceHub y presiona un botón para procesar",
                    fg=C_HEAD
                )
            else:
                self.lbl_orden_title.config(
                    text="🌐  Navegador Abierto — Presiona RELLENAR o RE-RELLENAR CAMPOS",
                    fg=C_SUCCESS
                )
        self._ui(_f)

    def _accion(self, resultado):
        self.action_result = resultado
        self._bloquear_botones_accion()
        self.action_event.set()

    # ─── Selección de archivo ─────────────────────────────────────────────────

    def _buscar_archivo(self):
        ruta = filedialog.askopenfilename(
            title="Seleccionar archivo de órdenes",
            filetypes=[("Archivos HTM/HTML", "*.htm *.html"), ("Todos", "*.*")]
        )
        if ruta:
            self.ruta_htm.set(ruta)
            self._log(f"Archivo seleccionado: {Path(ruta).name}", "ok")

    def _generar_prueba_gui(self):
        """Genera un archivo de prueba ficticio para 1 o varias órdenes ingresadas por el usuario."""
        pos_input = simpledialog.askstring(
            "Crear Datos de Prueba",
            "Ingresa el o los PO Numbers a probar:\n(Para 1 sola orden: 324483789  |  Para varias órdenes: 324483789, 324560193)\n\nDejar en blanco para usar datos de prueba por defecto:",
            parent=self.root
        )

        if pos_input is None:
            return

        pos_lista = None
        if pos_input.strip():
            pos_lista = [p.strip() for p in pos_input.split(",") if p.strip()]

        try:
            ruta_salida = generar_html_prueba(pos_lista)
            self.ruta_htm.set(str(ruta_salida.resolve()))
            if pos_lista and len(pos_lista) == 1:
                self._log(f"✅ Datos de prueba generados (1 orden: {pos_lista[0]}): {ruta_salida.name}", "ok")
            elif pos_lista:
                self._log(f"✅ Datos de prueba generados ({len(pos_lista)} órdenes): {ruta_salida.name}", "ok")
            else:
                self._log(f"✅ Datos de prueba generados por defecto: {ruta_salida.name}", "ok")
        except Exception as e:
            self._log(f"❌ Error al generar datos de prueba: {e}", "err")

    # ─── Arranque ────────────────────────────────────────────────────────────

    def _iniciar(self):
        if not self.ruta_htm.get():
            self._log("⚠️  Selecciona primero el archivo .htm", "warn")
            return
        self.close_browser_event.clear()
        self.action_event.clear()
        self.action_result = None

        self._ui(lambda: self.btn_start.config(state="disabled", text="⏳  Ejecutando..."))
        threading.Thread(target=self._automation_wrapper, daemon=False).start()

    def _automation_wrapper(self):
        try:
            self._automation()
        except Exception as e:
            self._log(f"Error inesperado en automatización: {e}", "err")
            self._set_status("●  Error — revisa el log")
        finally:
            self._ui(lambda: self.btn_start.config(state="normal", text="▶   INICIAR AUTOMATIZACIÓN"))

    # ─── Rellenado de Formulario ─────────────────────────────────────────────

    def _get_contexts(self, page: Page):
        """Retorna una lista con [page] + page.frames para poder buscar elementos dentro de cualquier iframe."""
        try:
            return [page] + list(page.frames)
        except Exception:
            return [page]

    def _rellenar_formulario_gui(self, page: Page, orden: dict) -> bool:
        """
        Rellena la orden en la página actual (PO, Invoice, Tracking, Ship Method, Quantity).
        Realiza una validación estricta y delimitación exclusiva dentro del contenedor del PO.
        Si el PO no está en la página web actual o no tiene contenedor válido, se aborta sin tocar ninguna casilla.
        """
        try:
            if page.is_closed():
                self._log("⚠️ La página del navegador está cerrada.", "warn")
                return False
        except Exception:
            return False

        po_target = orden["po"]
        po_base = po_target.split("_")[0]
        invoice_val = orden["invoice"]
        tracking_val = orden["tracking"]
        ship_via_target = orden.get("ship_via", UPS_GROUND_TEXTO) or UPS_GROUND_TEXTO

        contexts = self._get_contexts(page)

        # 1. Validación ultra-rápida en JS de coincidencia del PO en la página (0.001s)
        po_presente = False
        for ctx in contexts:
            try:
                has_po = ctx.evaluate("""([target, base]) => {
                    const txt = document.body ? document.body.innerText : '';
                    return txt.includes(target) || txt.includes(base);
                }""", [po_target, po_base])
                if has_po:
                    po_presente = True
                    break
            except Exception:
                continue

        if not po_presente:
            return False

        exito = True

        # 3. Rellenado inteligente vía JavaScript (delimitado por el contenedor del PO específico)
        js_fill_all = """({ invoiceVal, trackingVal, shipViaTarget, poTarget, poBase }) => {
            const result = {
                trackingOk: false,
                invoiceOk: false,
                shipMethodOk: false,
                shipMethodText: '',
                quantitiesFilled: 0,
                quantitiesDetails: []
            };

            // ── Función auxiliar: disparar eventos DOM ──
            function fireEvents(el) {
                el.focus();
                el.dispatchEvent(new Event('input',  { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
                el.dispatchEvent(new Event('blur',   { bubbles: true }));
            }

            // ── 1. Encontrar el contenedor de la orden específica ──
            // Buscar el elemento de texto que contiene el PO
            let poEl = null;
            const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
            let node;
            while ((node = walker.nextNode())) {
                const t = node.textContent.trim();
                if (t.includes(poTarget) || t.includes(poBase)) {
                    poEl = node.parentElement;
                    break;
                }
            }

            // Si no encontramos el nodo, probar con querySelector de texto
            if (!poEl) {
                const allEls = Array.from(document.querySelectorAll('*'));
                for (const el of allEls) {
                    if (el.children.length === 0) {
                        const t = (el.innerText || el.textContent || '').trim();
                        if (t === poTarget || t === poBase || t.includes(poTarget)) {
                            poEl = el;
                            break;
                        }
                    }
                }
            }

            // Subir en el DOM hasta encontrar un contenedor que tenga inputs de invoice/tracking
            let container = null;
            if (poEl) {
                let el = poEl;
                for (let depth = 0; depth < 15; depth++) {
                    el = el.parentElement;
                    if (!el || el === document.body) break;
                    // Verificar si este contenedor tiene inputs de invoice o tracking
                    const inputs = el.querySelectorAll('input:not([type="hidden"])');
                    if (inputs.length >= 1) {
                        container = el;
                        break;
                    }
                }
            }

            // Si no se encontró contenedor específico, usar body (fallback)
            const scope = container || document.body;

            // ── A. TRACKING NUMBER (dentro del contenedor del PO) ──
            const trackingInputs = Array.from(scope.querySelectorAll('input:not([type="hidden"])')).filter(inp => {
                const n = (inp.name || '').toLowerCase();
                const id = (inp.id || '').toLowerCase();
                const placeholder = (inp.placeholder || '').toLowerCase();
                return n.includes('tracking') || id.includes('tracking') ||
                       n.includes('shiptracking') || placeholder.includes('tracking');
            });
            if (trackingInputs.length > 0) {
                const trk = trackingInputs[0];
                trk.value = trackingVal;
                fireEvents(trk);
                result.trackingOk = true;
            }

            // ── B. INVOICE NUMBER (dentro del contenedor del PO) ──
            const invoiceInputs = Array.from(scope.querySelectorAll('input:not([type="hidden"])')).filter(inp => {
                const n = (inp.name || '').toLowerCase();
                const id = (inp.id || '').toLowerCase();
                return (n.includes('invoice') || id.includes('invoice')) &&
                       !n.includes('total') && !id.includes('total');
            });
            if (invoiceInputs.length > 0) {
                const inv = invoiceInputs[0];
                inv.value = invoiceVal;
                fireEvents(inv);
                result.invoiceOk = true;
            }

            // ── C. SHIPPING METHOD (dentro del contenedor del PO) ──
            const allSelects = Array.from(scope.querySelectorAll('select'));
            let shipSelect = null;

            // Buscar por opciones de transportistas
            for (const sel of allSelects) {
                const optTexts = Array.from(sel.options).map(o => (o.text || '').toLowerCase());
                const hasCarrierOpts = optTexts.some(t =>
                    t.includes('ups') || t.includes('fedex') || t.includes('usps') ||
                    t.includes('ground') || t.includes('priority') || t.includes('standard') ||
                    t.includes('express') || t.includes('freight') || t.includes('parcel') ||
                    t.includes('2nd day') || t.includes('next day') || t.includes('air')
                );
                if (hasCarrierOpts) { shipSelect = sel; break; }
            }

            // Buscar por nombre/id si no se encontró por opciones
            if (!shipSelect) {
                for (const sel of allSelects) {
                    const n = (sel.name || '').toLowerCase();
                    const id = (sel.id || '').toLowerCase();
                    if ((n.includes('ship') || n.includes('carrier') || n.includes('method') || n.includes('via') ||
                         id.includes('ship') || id.includes('carrier') || id.includes('method') || id.includes('via')) &&
                        !n.includes('carb') && !n.includes('compliance') && !n.includes('cancel')) {
                        shipSelect = sel; break;
                    }
                }
            }

            if (shipSelect) {
                const target = (shipViaTarget || 'UPS Ground').toLowerCase().trim();
                let bestOption = null;

                // Coincidencia exacta
                for (const opt of shipSelect.options) {
                    const txt = (opt.text || '').toLowerCase().trim();
                    if (txt === target) { bestOption = opt; break; }
                }
                // Coincidencia parcial
                if (!bestOption) {
                    for (const opt of shipSelect.options) {
                        const txt = (opt.text || '').toLowerCase().trim();
                        if (txt.includes(target) || target.includes(txt)) { bestOption = opt; break; }
                    }
                }
                // UPS Ground como fallback
                if (!bestOption) {
                    for (const opt of shipSelect.options) {
                        const txt = (opt.text || '').toLowerCase().trim();
                        if (txt.includes('ups') && txt.includes('ground')) { bestOption = opt; break; }
                    }
                }
                // Primera opción válida
                if (!bestOption && shipSelect.options.length > 1) {
                    for (const opt of shipSelect.options) {
                        if (opt.value && opt.text.trim()) { bestOption = opt; break; }
                    }
                }

                if (bestOption) {
                    shipSelect.value = bestOption.value;
                    bestOption.selected = true;
                    fireEvents(shipSelect);
                    result.shipMethodOk = true;
                    result.shipMethodText = bestOption.text;
                }
            }

            // ── D. SHIP QUANTITY para filas de productos del contenedor ──
            const allTables = Array.from(scope.querySelectorAll('table'));
            let colRem = -1, colShip = -1;

            for (const tbl of allTables) {
                for (const r of tbl.querySelectorAll('tr')) {
                    const headers = Array.from(r.querySelectorAll('th, td'));
                    for (let i = 0; i < headers.length; i++) {
                        const txt = (headers[i].innerText || '').toUpperCase().trim();
                        if (txt.includes('REMAINING') || txt.includes('QTY REM')) colRem = i;
                        if ((txt.includes('SHIP QUANTITY') || txt.includes('SHIP QTY') ||
                             (txt.includes('SHIP') && !txt.includes('METHOD') && !txt.includes('VIA') &&
                              !txt.includes('CHARGE') && !txt.includes('TO'))) && !txt.includes('CANCEL')) {
                            colShip = i;
                        }
                    }
                }
            }

            for (const tbl of allTables) {
                for (const row of tbl.querySelectorAll('tr')) {
                    const cells = Array.from(row.querySelectorAll('td'));
                    if (cells.length < 2) continue;

                    const rowText = (row.innerText || '').toUpperCase();
                    if (rowText.includes('INVOICE NUMBER') || rowText.includes('TRACKING NUMBER') ||
                        rowText.includes('SHIPPING CHARGE') || rowText.includes('SSCC ID')) continue;

                    const inputs = Array.from(row.querySelectorAll(
                        'input:not([type="hidden"]):not([type="checkbox"]):not([type="radio"]):not([type="submit"]):not([type="button"])'
                    ));
                    if (inputs.length === 0) continue;

                    let shipInput = null;
                    let qtyVal = '';

                    if (colShip !== -1 && colShip < cells.length) {
                        const inp = cells[colShip].querySelector('input:not([type="hidden"])');
                        if (inp) shipInput = inp;
                    }
                    if (!shipInput) {
                        for (const inp of inputs) {
                            const n = (inp.name || '').toLowerCase();
                            const id = (inp.id || '').toLowerCase();
                            if ((n.includes('ship') || id.includes('ship') || n.includes('qty') || id.includes('qty')) &&
                                !n.includes('cancel') && !id.includes('cancel') && !n.includes('track') && !n.includes('inv')) {
                                shipInput = inp; break;
                            }
                        }
                    }
                    if (!shipInput && inputs.length > 0) {
                        const fi = inputs[0];
                        const n = (fi.name || '').toLowerCase();
                        if (!n.includes('cancel') && !n.includes('track') && !n.includes('inv')) shipInput = fi;
                    }
                    if (!shipInput) continue;

                    if (colRem !== -1 && colRem < cells.length) {
                        const remTxt = cells[colRem].innerText.trim();
                        const match = remTxt.match(/\\d+/);
                        if (match && parseInt(match[0]) > 0) qtyVal = match[0];
                    }
                    if (!qtyVal) {
                        for (let c = 0; c < cells.length; c++) {
                            if (cells[c].contains(shipInput)) break;
                            const m = cells[c].innerText.trim().match(/^\\d{1,4}$/);
                            if (m && parseInt(m[0]) > 0) qtyVal = m[0];
                        }
                    }
                    if (!qtyVal || parseInt(qtyVal) <= 0) qtyVal = '1';

                    shipInput.value = qtyVal;
                    fireEvents(shipInput);
                    result.quantitiesFilled++;
                    result.quantitiesDetails.push({ qty: qtyVal, desc: row.innerText.replace(/\s+/g, ' ').substring(0, 30) });
                }
            }

            return result;
        }"""

        # Ejecutar en page o contexts
        res_js = None
        for ctx in contexts:
            try:
                res_js = ctx.evaluate(js_fill_all, {
                    "invoiceVal": invoice_val,
                    "trackingVal": tracking_val,
                    "shipViaTarget": ship_via_target,
                    "poTarget": po_target,
                    "poBase": po_base
                })
                if res_js and (res_js.get("trackingOk") or res_js.get("invoiceOk") or res_js.get("shipMethodOk") or res_js.get("quantitiesFilled", 0) > 0):
                    break
            except Exception as e_run_js:
                self._log(f"  ⚠️ Intento JS: {e_run_js}", "info")

        if res_js:
            if res_js.get("trackingOk"):
                self._log(f"  ✅ Tracking Number: {tracking_val}", "ok")
            if res_js.get("invoiceOk"):
                self._log(f"  ✅ Invoice Number: {invoice_val}", "ok")
            if res_js.get("shipMethodOk"):
                self._log(f"  ✅ Shipping Method: {res_js.get('shipMethodText') or ship_via_target}", "ok")
            if res_js.get("quantitiesFilled", 0) > 0:
                detalles = ", ".join([f"Fila {i+1}: {d['qty']}" for i, d in enumerate(res_js.get("quantitiesDetails", []))])
                self._log(f"  ✅ Ship Quantity rellenado en {res_js['quantitiesFilled']} fila(s) ({detalles})", "ok")

        # Fallback para Tracking Number si JS no lo rellenó
        if not (res_js and res_js.get("trackingOk")):
            selectores_tracking = [
                "input[name='trackingNumber']", "input[name='tracking_number']",
                "input[name='trackingNum']", "input[name='shipTracking']",
                "#trackingNumber", "#tracking_number", "input[name*='tracking' i]"
            ]
            for selector in selectores_tracking:
                try:
                    loc = page.locator(selector).first
                    if loc.count() > 0 and loc.is_visible():
                        loc.fill(tracking_val)
                        self._log(f"  ✅ Tracking Number: {tracking_val}", "ok")
                        break
                except Exception:
                    continue

        # Fallback para Invoice Number si JS no lo rellenó
        if not (res_js and res_js.get("invoiceOk")):
            selectores_invoice = [
                "input[name='invoiceNumber']", "input[name='invoice_number']",
                "input[name='invoiceNum']", "#invoiceNumber", "#invoice_number",
                "input[name*='invoice']:not([name*='total'])"
            ]
            for selector in selectores_invoice:
                try:
                    loc = page.locator(selector).first
                    if loc.count() > 0 and loc.is_visible():
                        loc.fill(invoice_val)
                        self._log(f"  ✅ Invoice Number: {invoice_val}", "ok")
                        break
                except Exception:
                    continue

        # Fallback para Shipping Method si JS no lo rellenó
        if not (res_js and res_js.get("shipMethodOk")):
            try:
                for ctx in contexts:
                    sels = ctx.locator("select")
                    for i in range(sels.count()):
                        cand = sels.nth(i)
                        if cand.is_visible():
                            try:
                                cand.select_option(label=ship_via_target)
                                self._log(f"  ✅ Shipping Method: {ship_via_target}", "ok")
                                break
                            except Exception:
                                pass
            except Exception:
                pass

        return exito

    # ─── Automatización con Playwright (hilo separado) ───────────────────────

    def _automation(self):
        self._log("══ PASO 1: Leyendo archivo ══", "head")
        self._set_status("●  Leyendo archivo...")
        ruta = self.ruta_htm.get()
        try:
            ordenes = parse_reporte(ruta)
        except Exception as e:
            self._log(f"❌ Error al leer el archivo: {e}", "err")
            return

        if not ordenes:
            self._log("⚠️  No se encontraron órdenes", "warn")
            return

        total = len(ordenes)
        self._log(f"✅ {total} órdenes encontradas.", "ok")

        self._log("══ PASO 2: Abriendo Navegador (Playwright) ══", "head")
        with sync_playwright() as playwright_instance:
            brave_path = obtener_ruta_brave()
            try:
                browser = playwright_instance.chromium.launch(
                    executable_path=brave_path if os.path.exists(brave_path) else None,
                    headless=False,
                    args=["--start-maximized"]
                )
                context = browser.new_context(no_viewport=True)
                page = context.new_page()
                self._log("✅ Navegador abierto exitosamente", "ok")
            except Exception as e:
                self._log(f"❌ Error al abrir el navegador: {e}", "err")
                self._set_status("●  Error — no se pudo abrir el navegador")
                return

            # ═════════════════════════════════════════════════════════
            #  PASO 3 — LOGIN SSO (2 PASOS)
            # ═════════════════════════════════════════════════════════
            self._log("══ PASO 3: Iniciando sesión ══", "head")
            self._set_status("●  Iniciando sesión...")

            try:
                page.goto(URL_PORTAL, timeout=TIMEOUT_SEG)
            except Exception as e_nav:
                self._log(f"⚠️  Navegación inicial: {e_nav}", "warn")

            self._log("    Esperando campos de login SSO...", "info")

            # Paso 1: Email / Username
            email_loc = page.locator("input[name='identifier'], input[type='email'], input[name='email'], input[name='username'], #email, #username").first
            try:
                email_loc.wait_for(state="visible", timeout=20000)
                email_loc.fill(EMAIL)
                self._log(f"✅ Email ingresado: {EMAIL}", "ok")

                btn_next = page.locator("button[type='submit'], input[type='submit'], button:has-text('Next'), button:has-text('Continuar')").first
                if btn_next.count() > 0 and btn_next.is_visible():
                    btn_next.click()
                else:
                    email_loc.press("Enter")
                time.sleep(1.0)
            except Exception as e_email:
                self._log(f"⚠️ Nota sobre email: {e_email}", "warn")

            # Paso 2: Password
            pass_loc = page.locator("input[name='password'], input[type='password'], #password").first
            try:
                pass_loc.wait_for(state="visible", timeout=15000)
                pass_loc.fill(PASSWORD)
                self._log("✅ Password ingresado", "ok")

                btn_login = page.locator("button[type='submit'], input[type='submit'], button:has-text('Login'), button:has-text('Sign In')").first
                if btn_login.count() > 0 and btn_login.is_visible():
                    btn_login.click()
                    self._log("✅ Clic en Submit/Login...", "ok")
                else:
                    pass_loc.press("Enter")
            except Exception as e_pass:
                self._log(f"⚠️ Nota sobre password (o login ya completado): {e_pass}", "info")

            try:
                page.wait_for_url(lambda url: "sso.auth.commercehub.com" not in url, timeout=15000)
                self._log("✅ Login exitoso", "ok")
                self._set_status("●  Login exitoso ✅ — navega al formulario de la primera orden")
            except Exception:
                self._log("⚠️  Login pendiente — completa manualmente", "warn")

            # ═════════════════════════════════════════════════════════
            #  PASO 4 — PROCESAR ÓRDENES CONTINUAMENTE (50+ ÓRDENES)
            # ═════════════════════════════════════════════════════════
            self._log("══ PASO 4: Procesando órdenes automáticamente ══", "head")
            self._log("👆 Navega a la orden en CommerceHub y presiona RELLENAR o RE-RELLENAR CAMPOS", "warn")
            self._set_status("● Navega a la orden en CommerceHub y presiona un botón para procesar")

            self._activar_botones_accion(total)

            self.action_result = None
            while True:
                try:
                    self.action_event.clear()
                    self.action_event.wait(timeout=0.5)

                    if self.close_browser_event.is_set():
                        break

                    if self.action_result in ("rellenar", "rerellenar"):
                        self.action_result = None
                        if page.is_closed():
                            self._log("⚠️ La página del navegador fue cerrada por el usuario.", "warn")
                            break

                        # 1. Lectura instantánea del DOM de la página para identificar el PO actual (5ms)
                        try:
                            page_text = page.evaluate("() => document.body ? document.body.innerText : ''")
                        except Exception:
                            page_text = ""

                        # 2. Filtrar de inmediato las órdenes que realmente corresponden a la página actual
                        ordenes_en_pantalla = [
                            (idx, ord_item) for idx, ord_item in enumerate(ordenes, 1)
                            if ord_item["po"] in page_text or ord_item["po"].split("_")[0] in page_text
                        ]

                        if not ordenes_en_pantalla:
                            self._log("⚠️ El PO visible en pantalla no coincide con ninguna orden del archivo.", "warn")
                            self._log("   Verifica que estés en la orden correcta en CommerceHub.", "info")
                            self._set_status("● PO no coincide — navega a la orden y presiona un botón")
                            self._activar_botones_accion(total)
                            continue

                        procesadas = 0
                        for i, orden in ordenes_en_pantalla:
                            if self.close_browser_event.is_set() or page.is_closed():
                                break
                            self._log(f"─── Orden {i}/{total}  ·  PO: {orden['po']} ───", "head")
                            exito = self._rellenar_formulario_gui(page, orden)
                            if exito:
                                procesadas += 1
                                self._log(f"  ✅ Orden {i} ({orden['po']}) rellenada exitosamente.", "ok")

                        self._log(f"══ PROCESO COMPLETADO ══  ✅ {procesadas} orden(es) rellenada(s) al instante.", "ok")
                        self._log("   Revisa y guarda en CommerceHub. Pasa a la siguiente orden y presiona un botón.", "info")
                        self._set_status(f"● Completado ✅ — Listo para guardar en CommerceHub.")
                        self._activar_botones_accion(total)
                except Exception as e_loop:
                    self._activar_botones_accion()
                    time.sleep(0.5)

            try:
                browser.close()
            except Exception:
                pass


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    root = tk.Tk()
    try:
        root.iconbitmap(default="")
    except Exception:
        pass
    app = CommerceHubApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
