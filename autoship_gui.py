"""
autoship_gui.py
---------------
Aplicacion grafica para CommerceHub AutoShip.
Selecciona el archivo .htm, el script inicia sesion automaticamente
y rellena los formularios de cada orden.

Para regenerar el .exe (PowerShell):
    py -m PyInstaller --onefile --windowed --name "CommerceHub-AutoShip" --distpath "./dist" autoship_gui.py
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

# Imports completos de Selenium para PyInstaller
import selenium
import selenium.webdriver
import selenium.webdriver.chrome
import selenium.webdriver.chrome.service
import selenium.webdriver.chrome.options
import selenium.webdriver.chrome.webdriver
import selenium.webdriver.common
import selenium.webdriver.common.by
import selenium.webdriver.remote
import selenium.webdriver.remote.webdriver
import selenium.webdriver.remote.webelement
import selenium.webdriver.support
import selenium.webdriver.support.expected_conditions
import selenium.webdriver.support.ui

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    ElementNotInteractableException,
)
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

from parse_html import parse_reporte, CLIENTE_OBJETIVO
from crear_reporte_prueba import generar_html_prueba

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
#  CONFIGURACION
# ─────────────────────────────────────────────────────────────────────────────

EMAIL      = "Sammy@josmo.com"
PASSWORD   = "Panda@2025"
URL_PORTAL = "https://dsm.commercehub.com"

BRAVE_PATH = obtener_ruta_brave()
CLIENTE_OBJETIVO = "08461"
UPS_GROUND_TEXTO = "UPS Ground"
TIMEOUT_SEG = 15


from parse_html import parse_reporte, CLIENTE_OBJETIVO


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
#  APLICACION GUI
# ─────────────────────────────────────────────────────────────────────────────

class CommerceHubApp:

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("CommerceHub AutoShip")
        self.root.geometry("700x780")
        self.root.minsize(600, 680)
        self.root.configure(bg=C_BG)
        self.root.resizable(True, True)

        # Estado interno
        self.ruta_htm      = tk.StringVar()
        self.driver        = None
        self.log_q         = queue.Queue()
        self.action_event  = threading.Event()
        self.action_result = None   # "rellenar" | "saltar"

        self._build_ui()
        self._poll_logs()

    # ─── Construccion de UI ──────────────────────────────────────────────────

    def _build_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(3, weight=1)   # log se expande

        # ── Header ──────────────────────────────────────────────────────────
        hdr = tk.Frame(self.root, bg=C_CARD, pady=18)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.columnconfigure(0, weight=1)

        tk.Label(hdr, text="🚀  CommerceHub AutoShip",
                 font=("Segoe UI", 20, "bold"),
                 bg=C_CARD, fg=C_TEXT).pack()
        tk.Label(hdr, text="Automatización de órdenes DSM  ·  Cliente 08461",
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
                                   activebackground=C_SUCCESS_H, activeforeground=C_TEXT,
                                   relief="flat", font=("Segoe UI", 13, "bold"),
                                   cursor="hand2", pady=13, bd=0)
        self.btn_start.grid(row=0, column=0, sticky="ew")

        # ── Panel orden activa ───────────────────────────────────────────────
        self.card_orden = tk.Frame(self.root, bg=C_CARD, padx=24, pady=14)
        self.card_orden.grid(row=3, column=0, sticky="nsew", padx=16, pady=(0, 6))
        self.card_orden.columnconfigure(1, weight=1)

        self.lbl_orden_title = tk.Label(self.card_orden,
                                         text="── Sin orden activa ──",
                                         font=("Segoe UI", 11, "bold"),
                                         bg=C_CARD, fg=C_MUTED)
        self.lbl_orden_title.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        self.lbl_po       = self._campo_info(self.card_orden, "PO#:",       row=1)
        self.lbl_invoice  = self._campo_info(self.card_orden, "Invoice#:",  row=2)
        self.lbl_tracking = self._campo_info(self.card_orden, "Tracking#:", row=3)

        # Botones accion
        accion_frame = tk.Frame(self.card_orden, bg=C_CARD)
        accion_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(14, 2))
        accion_frame.columnconfigure(0, weight=1)

        self.btn_rellenar = tk.Button(accion_frame,
                                       text="✅   RELLENAR CAMPOS",
                                       command=lambda: self._accion("rellenar"),
                                       bg=C_SUCCESS, fg=C_TEXT,
                                       activebackground=C_SUCCESS_H,
                                       relief="flat", font=("Segoe UI", 11, "bold"),
                                       cursor="hand2", pady=10, state="disabled", bd=0)
        self.btn_rellenar.grid(row=0, column=0, sticky="ew")

        self.btn_saltar = tk.Button(accion_frame,
                                     text="⏭  Saltar orden",
                                     command=lambda: self._accion("saltar"),
                                     bg=C_INPUT, fg=C_MUTED,
                                     activebackground=C_BORDER,
                                     relief="flat", font=("Segoe UI", 10),
                                     cursor="hand2", pady=10, state="disabled", bd=0)
        self.btn_saltar.grid(row=0, column=1, padx=(10, 0))

        # ── Log de actividad ─────────────────────────────────────────────────
        log_frame = tk.Frame(self.root, bg=C_CARD, padx=24, pady=14)
        log_frame.grid(row=4, column=0, sticky="nsew", padx=16, pady=(0, 6))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(1, weight=1)
        self.root.rowconfigure(4, weight=1)

        tk.Label(log_frame, text="📋  Registro de actividad",
                 font=("Segoe UI", 10, "bold"),
                 bg=C_CARD, fg=C_TEXT).grid(row=0, column=0, sticky="w", pady=(0, 6))

        txt_frame = tk.Frame(log_frame, bg=C_INPUT)
        txt_frame.grid(row=1, column=0, sticky="nsew")
        txt_frame.columnconfigure(0, weight=1)
        txt_frame.rowconfigure(0, weight=1)

        self.log_text = tk.Text(txt_frame, bg=C_INPUT, fg=C_TEXT,
                                 font=("Consolas", 9), relief="flat",
                                 state="disabled", wrap="word", height=10,
                                 padx=8, pady=6)
        scroll_log = tk.Scrollbar(txt_frame, command=self.log_text.yview, bg=C_INPUT)
        self.log_text.configure(yscrollcommand=scroll_log.set)
        scroll_log.grid(row=0, column=1, sticky="ns")
        self.log_text.grid(row=0, column=0, sticky="nsew")

        # Tags de color
        self.log_text.tag_configure("ok",    foreground="#3fb950")
        self.log_text.tag_configure("warn",  foreground="#d29922")
        self.log_text.tag_configure("err",   foreground="#f85149")
        self.log_text.tag_configure("info",  foreground=C_MUTED)
        self.log_text.tag_configure("head",  foreground=C_HEAD,
                                    font=("Consolas", 9, "bold"))

        # ── Barra de estado ──────────────────────────────────────────────────
        self.var_status = tk.StringVar(value="●  Listo — selecciona un archivo .htm y presiona Iniciar")
        tk.Label(self.root, textvariable=self.var_status,
                 bg=C_BG, fg=C_MUTED, font=("Segoe UI", 9),
                 anchor="w", padx=20).grid(row=5, column=0, sticky="ew", pady=(0, 6))

    def _campo_info(self, parent, label, row):
        tk.Label(parent, text=label, font=("Segoe UI", 10, "bold"),
                 bg=C_CARD, fg=C_MUTED, width=11,
                 anchor="w").grid(row=row, column=0, sticky="w", pady=2)
        lbl = tk.Label(parent, text="—", font=("Segoe UI", 10),
                       bg=C_CARD, fg=C_TEXT, anchor="w")
        lbl.grid(row=row, column=1, sticky="w", padx=(6, 0))
        return lbl

    # ─── Helpers UI (seguros desde hilos) ───────────────────────────────────

    def _ui(self, fn):
        """Ejecuta fn en el hilo de UI."""
        self.root.after(0, fn)

    def _set_status(self, txt):
        self._ui(lambda: self.var_status.set(txt))

    def _log(self, msg, tag="info"):
        hora = datetime.now().strftime("%H:%M:%S")
        self.log_q.put((f"[{hora}]  {msg}\n", tag))

    def _poll_logs(self):
        try:
            while True:
                msg, tag = self.log_q.get_nowait()
                self.log_text.configure(state="normal")
                self.log_text.insert("end", msg, tag)
                self.log_text.see("end")
                self.log_text.configure(state="disabled")
        except queue.Empty:
            pass
        self.root.after(80, self._poll_logs)

    def _mostrar_orden(self, orden, i, total):
        def _f():
            self.lbl_orden_title.config(
                text=f"📦  Orden {i} de {total}  —  navega al formulario y presiona RELLENAR",
                fg=C_HEAD)
            self.lbl_po.config(text=orden["po"])
            self.lbl_invoice.config(text=orden["invoice"])
            self.lbl_tracking.config(text=orden["tracking"])
            self.btn_rellenar.config(state="normal")
            self.btn_saltar.config(state="normal")
        self._ui(_f)

    def _bloquear_botones_accion(self, msg="── Procesando... ──"):
        def _f():
            self.btn_rellenar.config(state="disabled")
            self.btn_saltar.config(state="disabled")
            self.lbl_orden_title.config(text=msg, fg=C_MUTED)
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
            self._log(f"Archivo: {Path(ruta).name}", "ok")

    def _generar_prueba_gui(self):
        """Genera un archivo de prueba ficticio y lo selecciona automáticamente."""
        pos_input = simpledialog.askstring(
            "Crear datos de prueba",
            "Opcional: Ingresa los PO Numbers a probar separados por coma\n(o deja en blanco para usar POs de prueba por defecto):",
            parent=self.root
        )

        pos_lista = None
        if pos_input and pos_input.strip():
            pos_lista = [p.strip() for p in pos_input.split(",") if p.strip()]

        try:
            ruta_salida = generar_html_prueba(pos_lista)
            self.ruta_htm.set(str(ruta_salida.resolve()))
            self._log("🧪 Archivo de prueba generado y seleccionado automáticamente:", "head")
            self._log(f"   {ruta_salida.name}", "ok")
            self._set_status(f"●  Prueba lista — {ruta_salida.name} cargado. Presiona Iniciar.")
        except Exception as e:
            self._log(f"❌ Error al generar archivo de prueba: {e}", "err")

    # ─── Arranque ────────────────────────────────────────────────────────────

    def _iniciar(self):
        if not self.ruta_htm.get():
            self._log("⚠️  Selecciona primero el archivo .htm", "warn")
            return
        self._ui(lambda: self.btn_start.config(state="disabled",
                                                text="⏳  Ejecutando..."))
        threading.Thread(target=self._automation_wrapper, daemon=True).start()

    def _automation_wrapper(self):
        try:
            self._automation()
        except Exception as e:
            self._log(f"Error inesperado: {e}", "err")
            self._set_status("●  Error — revisa el log")
        finally:
            self._ui(lambda: self.btn_start.config(state="normal",
                                                    text="▶   INICIAR AUTOMATIZACIÓN"))

    # ─── Automatización (hilo separado) ──────────────────────────────────────

    def _automation(self):
        By_ = By          # alias para legibilidad

        # ═════════════════════════════════════════════════════════
        #  PASO 1 — PARSEAR ARCHIVO
        # ═════════════════════════════════════════════════════════
        self._log("══ PASO 1: Leyendo archivo ══", "head")
        self._set_status("●  Leyendo archivo...")
        ruta = self.ruta_htm.get()

        try:
            ordenes = parse_reporte(ruta)
        except FileNotFoundError:
            self._log(f"❌ Archivo no encontrado: {ruta}", "err")
            self._set_status("●  Error — archivo no encontrado")
            return
        except Exception as e:
            self._log(f"❌ Error al leer el archivo: {e}", "err")
            self._set_status("●  Error al leer el archivo")
            return

        if not ordenes:
            self._log("⚠️  No se encontraron órdenes para el cliente 08461", "warn")
            self._set_status("●  Sin órdenes para cliente 08461")
            return

        total = len(ordenes)
        self._log(f"✅ {total} órdenes encontradas para cliente {CLIENTE_OBJETIVO}", "ok")
        self._set_status(f"●  {total} órdenes — abriendo Brave...")

        # ═════════════════════════════════════════════════════════
        #  PASO 2 — ABRIR BRAVE
        # ═════════════════════════════════════════════════════════
        self._log("══ PASO 2: Abriendo Brave ══", "head")

        opts = ChromeOptions()
        opts.binary_location = obtener_ruta_brave()
        opts.add_experimental_option("detach", True)
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option("useAutomationExtension", False)
        opts.add_argument("--start-maximized")

        try:
            service = Service(ChromeDriverManager().install())
            drv = webdriver.Chrome(service=service, options=opts)
            self._log("✅ Brave abierto", "ok")
        except Exception as e:
            self._log(f"❌ Error al abrir Brave: {e}", "err")
            self._set_status("●  Error — no se pudo abrir Brave")
            return

        wait = WebDriverWait(drv, TIMEOUT_SEG)

        # ═════════════════════════════════════════════════════════
        #  PASO 3 — LOGIN (Shadow DOM + React via JavaScript)
        # ═════════════════════════════════════════════════════════
        self._log("══ PASO 3: Iniciando sesión ══", "head")
        self._set_status("●  Iniciando sesión...")
        drv.get(URL_PORTAL)

        # JavaScript que busca un elemento dentro de Shadow DOM (recursivo)
        JS_FIND = """
            function findEl(root, sel) {
                var el = root.querySelector(sel);
                if (el) return el;
                var nodes = root.querySelectorAll('*');
                for (var i = 0; i < nodes.length; i++) {
                    if (nodes[i].shadowRoot) {
                        el = findEl(nodes[i].shadowRoot, sel);
                        if (el) return el;
                    }
                }
                return null;
            }
            return findEl(document, arguments[0]);
        """

        # JavaScript que escribe en un input de React (Shadow DOM)
        # Usa el setter nativo para que React detecte el cambio
        JS_SET = """
            function findEl(root, sel) {
                var el = root.querySelector(sel);
                if (el) return el;
                var nodes = root.querySelectorAll('*');
                for (var i = 0; i < nodes.length; i++) {
                    if (nodes[i].shadowRoot) {
                        el = findEl(nodes[i].shadowRoot, sel);
                        if (el) return el;
                    }
                }
                return null;
            }
            var el = findEl(document, arguments[0]);
            if (!el) return false;
            var setter = Object.getOwnPropertyDescriptor(
                window.HTMLInputElement.prototype, 'value').set;
            setter.call(el, arguments[1]);
            el.dispatchEvent(new Event('input',  {bubbles: true}));
            el.dispatchEvent(new Event('change', {bubbles: true}));
            el.dispatchEvent(new Event('blur',   {bubbles: true}));
            return true;
        """

        # JavaScript que hace clic en un elemento dentro de Shadow DOM
        JS_CLICK = """
            function findEl(root, sel) {
                var el = root.querySelector(sel);
                if (el) return el;
                var nodes = root.querySelectorAll('*');
                for (var i = 0; i < nodes.length; i++) {
                    if (nodes[i].shadowRoot) {
                        el = findEl(nodes[i].shadowRoot, sel);
                        if (el) return el;
                    }
                }
                return null;
            }
            var el = findEl(document, arguments[0]);
            if (!el) return false;
            el.click();
            return true;
        """

        # Esperar a que el formulario de Frontegg se renderice (Shadow DOM)
        self._log("    Esperando que cargue el formulario SSO...", "info")
        try:
            WebDriverWait(drv, 30).until(
                lambda d: d.execute_script(JS_FIND, "input[name='identifier']") is not None
            )
        except TimeoutException:
            self._log("❌ El formulario de login no cargo en 30 seg", "err")
            drv.quit()
            return

        self._log("    Formulario SSO detectado", "ok")

        # Escribir email usando JS (React setter)
        ok = drv.execute_script(JS_SET, "input[name='identifier']", EMAIL)
        if ok:
            self._log(f"✅ Email: {EMAIL}", "ok")
        else:
            self._log("❌ No se encontró el campo de email", "err")
            drv.quit()
            return

        time.sleep(0.5)

        # Escribir password usando JS (React setter)
        ok = drv.execute_script(JS_SET, "input[name='password']", PASSWORD)
        if ok:
            self._log("✅ Password ingresado", "ok")
        else:
            self._log("❌ No se encontró el campo de password", "err")
            drv.quit()
            return

        time.sleep(0.4)

        # Clic en botón Continue/Submit
        ok = drv.execute_script(JS_CLICK, "button[type='submit']")
        if ok:
            self._log("✅ Clic en Continue — cargando portal...", "ok")
        else:
            self._log("❌ No se encontró el botón de login", "err")
            drv.quit()
            return

        # Esperar redirección post-login (sale del dominio sso.auth.commercehub.com)
        try:
            WebDriverWait(drv, 20).until(
                lambda d: "sso.auth.commercehub.com" not in d.current_url
            )
            self._log("✅ Login exitoso", "ok")
            self._set_status("●  Login exitoso ✅ — navega al formulario de la primera orden")
        except TimeoutException:
            self._log("⚠️  Login pendiente — completa manualmente si hay pasos extra (2FA, etc.)", "warn")
            # Seguimos; el usuario puede completar si hace falta

        # ═════════════════════════════════════════════════════════
        #  PASO 4 — PROCESAR ÓRDENES
        # ═════════════════════════════════════════════════════════
        self._log("══ PASO 4: Procesando órdenes automáticamente ══", "head")
        self._log("👆 Navega al formulario quickship en Brave y presiona RELLENAR CAMPOS", "warn")
        self._set_status("● Navega al formulario quickship en Brave y presiona RELLENAR CAMPOS")

        # Habilitar botón RELLENAR CAMPOS en la interfaz para el usuario
        def _activar_boton():
            self.btn_rellenar.config(state="normal", text="✅  RELLENAR CAMPOS (TODAS LAS ÓRDENES)")
            self.lbl_orden_title.config(
                text=f"📦  {total} Órdenes cargadas — presiona RELLENAR CAMPOS para procesar todas",
                fg=C_HEAD
            )
        self._ui(_activar_boton)

        # Esperar clic del usuario en RELLENAR CAMPOS
        self.action_event.clear()
        self.action_event.wait()

        if self.action_result == "saltar":
            self._log("⏭️ Proceso cancelado por el usuario", "warn")
            return

        self._log(f"🚀 Procesando {total} órdenes en la página...", "head")
        procesadas = 0
        fallidas   = []

        for i, orden in enumerate(ordenes, 1):
            po_target = orden["po"]
            invoice_val = orden["invoice"]
            tracking_val = orden["tracking"]

            self._log(f"─── Orden {i}/{total}  ·  PO: {po_target} ───", "head")

            # 1. Buscar PO Number en la página actual
            po_nodes = drv.find_elements(By_.XPATH, f"//*[contains(text(), '{po_target}')]")
            if not po_nodes:
                if po_target not in drv.page_source:
                    self._log(f"❌ PO '{po_target}' NO fue encontrado en la página web.", "err")
                    fallidas.append({"n": i, "po": po_target, "razon": "PO no existe en la página"})
                    continue

            po_elem = po_nodes[0]
            self._log(f"  ✅ PO '{po_target}' localizado en la página.", "ok")

            # 2. Encontrar el contenedor específico de esta orden (subiendo por ancestros)
            container = None
            parent = po_elem
            for _ in range(6):
                try:
                    parent = parent.find_element(By_.XPATH, "..")
                    txt_p = parent.text
                    if "Invoice" in txt_p or "Tracking" in txt_p:
                        container = parent
                        break
                except Exception:
                    break

            if not container:
                container = drv

            exito = True

            # 3. Rellenar Tracking Number primero (desde Tracking# del .htm)
            campo_trk = None
            selectores_trk = [
                (By_.XPATH, ".//td[contains(text(),'Tracking')]/following-sibling::td//input[not(@type='hidden')]"),
                (By_.XPATH, ".//td[contains(text(),'Tracking')]/following::input[not(@type='hidden')][1]"),
                (By_.XPATH, ".//input[contains(@name,'tracking') or contains(@name,'Tracking')]"),
            ]
            if container != drv:
                campo_trk = self._buscar_elemento_scoped(drv, container, selectores_trk)

            if not campo_trk:
                try:
                    campo_trk = po_elem.find_element(
                        By_.XPATH, "./following::td[contains(text(),'Tracking')][1]/following::input[not(@type='hidden')][1]"
                    )
                except Exception:
                    pass

            if not campo_trk:
                campo_trk = self._buscar_elemento_scoped(drv, drv, selectores_trk)

            if campo_trk:
                try:
                    campo_trk.clear()
                    campo_trk.send_keys(tracking_val)
                    self._log(f"  ✅ Tracking Number: {tracking_val}", "ok")
                except Exception as e_trk:
                    self._log(f"  ❌ Error escribiendo Tracking: {e_trk}", "err")
                    exito = False
            else:
                self._log(f"  ❌ Campo Tracking Number no encontrado para PO {po_target}", "err")
                exito = False

            # 4. Rellenar Invoice Number (desde Invoice# del .htm)
            campo_inv = None
            selectores_inv = [
                (By_.XPATH, ".//td[contains(text(),'Invoice')]/following-sibling::td//input[not(@type='hidden')]"),
                (By_.XPATH, ".//td[contains(text(),'Invoice')]/following::input[not(@type='hidden')][1]"),
                (By_.XPATH, ".//input[contains(@name,'invoice') and not(contains(@name,'total')) and not(contains(@name,'Total'))]"),
            ]
            if container != drv:
                campo_inv = self._buscar_elemento_scoped(drv, container, selectores_inv)

            if not campo_inv:
                try:
                    campo_inv = po_elem.find_element(
                        By_.XPATH, "./following::td[contains(text(),'Invoice')][1]/following::input[not(@type='hidden')][1]"
                    )
                except Exception:
                    pass

            if not campo_inv:
                campo_inv = self._buscar_elemento_scoped(drv, drv, selectores_inv)

            if campo_inv:
                try:
                    campo_inv.clear()
                    campo_inv.send_keys(invoice_val)
                    self._log(f"  ✅ Invoice Number: {invoice_val}", "ok")
                except Exception as e_inv:
                    self._log(f"  ❌ Error escribiendo Invoice: {e_inv}", "err")
                    exito = False
            else:
                self._log(f"  ❌ Campo Invoice Number no encontrado para PO {po_target}", "err")
                exito = False

            if exito:
                procesadas += 1
                self._log(f"  ✅ Orden {i} ({po_target}) rellenada exitosamente.", "ok")
            else:
                fallidas.append({"n": i, "po": po_target, "razon": "Campos incompletos"})

            time.sleep(0.2)

        # ═════════════════════════════════════════════════════════
        #  RESUMEN FINAL
        # ═════════════════════════════════════════════════════════
        self._log("══ PROCESO COMPLETADO ══", "head")
        self._log(f"✅ Procesadas correctamente: {procesadas}/{total}", "ok")
        if fallidas:
            self._log(f"⚠️  Con problemas: {len(fallidas)}", "warn")
            for f in fallidas:
                self._log(f"   · Orden {f['n']}  PO: {f['po']}  — {f['razon']}", "warn")

        self._set_status(f"●  Completado ✅  {procesadas}/{total} órdenes procesadas")
        self._bloquear_botones_accion("── Proceso completado ✅ ──")

    def _buscar_elemento_scoped(self, drv, search_scope, selectores):
        for by, val in selectores:
            try:
                if search_scope != drv and val.startswith(".//"):
                    elems = search_scope.find_elements(by, val)
                    if elems:
                        return elems[0]
                else:
                    elems = drv.find_elements(by, val)
                    if elems:
                        return elems[0]
            except Exception:
                continue
        return None

    def _buscar_elemento(self, drv, selectores, timeout):
        wait = WebDriverWait(drv, timeout)
        for by, val in selectores:
            try:
                return wait.until(EC.presence_of_element_located((by, val)))
            except TimeoutException:
                continue
        return None


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    root = tk.Tk()
    try:
        root.iconbitmap(default="")   # Sin icono personalizado
    except Exception:
        pass
    app = CommerceHubApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
