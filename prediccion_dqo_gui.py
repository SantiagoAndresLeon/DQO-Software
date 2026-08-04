"""
Medición de DQO - Aplicación gráfica

Lee un archivo CSV (por defecto, el primero que encuentre en la carpeta del
programa), calcula el DQO predicho a partir de la señal medida y reconstruye
la marca de tiempo real de cada dato usando la fecha/hora del nombre del
archivo y un intervalo fijo de muestreo.

La ventana muestra: el último dato registrado en una tarjeta destacada, la
tabla completa de datos, una gráfica del Valor de DQO vs Tiempo, y se
actualiza sola cuando el archivo CSV cambia en disco.
"""

import csv
import os
import re
import tkinter as tk
from datetime import datetime, timedelta
from tkinter import ttk, filedialog, messagebox

import matplotlib.dates as mdates
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from leer_csv import detectar_delimitador, encontrar_csv_por_defecto

# DQO = 0.000124 * SEÑAL^2 - 0.713 * SEÑAL + 648.9
COEF_A, COEF_B, COEF_C = 0.000124, -0.713, 648.9
TEXTO_ECUACION = "DQO = |0,000124·SEÑAL² − 0,713·SEÑAL + 648,9|"

INTERVALO_MUESTREO = timedelta(minutes=10)
FORMATO_FECHA = "%d/%m/%Y %H:%M:%S"
# Ej. de nombre de archivo: "05-25-26 09.54.55.csv" -> mes-día-año hora.minuto.segundo
PATRON_FECHA_ARCHIVO = re.compile(r"(\d{2})-(\d{2})-(\d{2})\s+(\d{2})\.(\d{2})\.(\d{2})")

INTERVALO_AUTOACTUALIZACION_MS = 3000

# Paleta de colores de la interfaz (validada para buen contraste)
COLOR_BANNER = "#184f95"
COLOR_BANNER_TEXTO = "#ffffff"
COLOR_BANNER_SUBTEXTO = "#cde2fb"
COLOR_FONDO = "#f9f9f7"
COLOR_SUPERFICIE = "#fcfcfb"
COLOR_ACENTO = "#2a78d6"
COLOR_ACENTO_HOVER = "#184f95"
COLOR_TEXTO = "#0b0b0b"
COLOR_TEXTO_SECUNDARIO = "#52514e"
COLOR_TEXTO_MUTED = "#898781"
COLOR_ENCABEZADO_TABLA = "#b7d3f6"
COLOR_ENCABEZADO_TABLA_TEXTO = "#0b2e5c"
COLOR_FILA_PAR = "#eaf2fc"
COLOR_FILA_IMPAR = "#fcfcfb"
COLOR_SELECCION = "#2a78d6"
COLOR_GRID = "#e1e0d9"
COLOR_EJE = "#c3c2b7"
COLOR_PUNTO_ACTUAL = "#e34948"

COLUMNA_FECHA = "Fecha y Hora"
COLUMNA_SENAL = "Señal"
COLUMNA_DQO = "DQO"


def calcular_dqo(senal: float) -> float:
    return abs(COEF_A * senal**2 + COEF_B * senal + COEF_C)


def _a_numero(valor: str) -> float:
    return float(valor.replace(",", "."))


def _a_texto(valor: float) -> str:
    return f"{valor:.4f}".replace(".", ",")


def extraer_fecha_inicio(ruta: str) -> datetime | None:
    nombre = os.path.splitext(os.path.basename(ruta))[0]
    coincidencia = PATRON_FECHA_ARCHIVO.search(nombre)
    if not coincidencia:
        return None
    mes, dia, anio, hora, minuto, segundo = (int(v) for v in coincidencia.groups())
    try:
        return datetime(2000 + anio, mes, dia, hora, minuto, segundo)
    except ValueError:
        return None


def leer_datos(ruta: str) -> tuple[list[str], list[list[str]]]:
    with open(ruta, newline="", encoding="utf-8-sig") as f:
        muestra = f.read(2048)
        f.seek(0)
        delimitador = detectar_delimitador(muestra)
        lector = csv.reader(f, delimiter=delimitador)
        filas = [fila for fila in lector if fila]

    if not filas:
        return [], []

    def es_numero(valor: str) -> bool:
        try:
            _a_numero(valor)
            return True
        except ValueError:
            return False

    primera = filas[0]
    if all(es_numero(v) for v in primera):
        if len(primera) == 2:
            fecha_inicio = extraer_fecha_inicio(ruta)
            if fecha_inicio is not None:
                encabezado = [COLUMNA_FECHA, COLUMNA_SENAL, COLUMNA_DQO]
            else:
                encabezado = ["Tiempo (s)", COLUMNA_SENAL, COLUMNA_DQO]

            datos = []
            for indice, fila in enumerate(filas):
                if fecha_inicio is not None:
                    marca = fecha_inicio + indice * INTERVALO_MUESTREO
                    tiempo_valor = marca.strftime(FORMATO_FECHA)
                else:
                    tiempo_valor = fila[0]
                dqo_predicho = calcular_dqo(_a_numero(fila[1]))
                datos.append([tiempo_valor, fila[1], _a_texto(dqo_predicho)])
        else:
            encabezado = [f"Columna {i + 1}" for i in range(len(primera))]
            datos = filas
    else:
        encabezado = primera
        datos = filas[1:]

    return encabezado, datos


class AppDQO(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Medición de DQO")
        self.minsize(920, 580)
        self.configure(bg=COLOR_FONDO)

        self.ruta_actual: str | None = None
        self.mtime_actual: float | None = None

        self._configurar_estilos()
        self._construir_interfaz()
        self._centrar_ventana(1200, 760)

        ruta_inicial = encontrar_csv_por_defecto()
        if ruta_inicial:
            self.cargar_archivo(ruta_inicial)

        self._verificar_actualizacion()

    def _centrar_ventana(self, ancho: int, alto: int) -> None:
        self.update_idletasks()
        x = (self.winfo_screenwidth() - ancho) // 2
        y = (self.winfo_screenheight() - alto) // 3
        self.geometry(f"{ancho}x{alto}+{x}+{y}")

    def _configurar_estilos(self) -> None:
        estilo = ttk.Style(self)
        estilo.theme_use("clam")

        estilo.configure("TFrame", background=COLOR_FONDO)
        estilo.configure("TPanedwindow", background=COLOR_FONDO)

        estilo.configure(
            "Acento.TButton",
            background=COLOR_ACENTO,
            foreground="white",
            font=("Segoe UI", 10, "bold"),
            padding=(14, 8),
            borderwidth=0,
            focuscolor=COLOR_ACENTO,
        )
        estilo.map(
            "Acento.TButton",
            background=[("active", COLOR_ACENTO_HOVER), ("pressed", COLOR_ACENTO_HOVER)],
        )

        estilo.configure(
            "Formula.TButton",
            background="#ffffff",
            foreground=COLOR_BANNER,
            font=("Segoe UI", 9, "bold"),
            padding=(12, 6),
            borderwidth=0,
            focuscolor="#ffffff",
        )
        estilo.map(
            "Formula.TButton",
            background=[("active", COLOR_BANNER_SUBTEXTO), ("pressed", COLOR_BANNER_SUBTEXTO)],
        )

        estilo.configure(
            "Archivo.TLabel",
            background=COLOR_FONDO,
            foreground=COLOR_TEXTO_SECUNDARIO,
            font=("Segoe UI", 10),
        )
        estilo.configure(
            "Auto.TLabel",
            background=COLOR_FONDO,
            foreground=COLOR_TEXTO_MUTED,
            font=("Segoe UI", 9),
        )

        estilo.configure(
            "Estado.TLabel",
            background=COLOR_BANNER,
            foreground=COLOR_BANNER_SUBTEXTO,
            font=("Segoe UI", 9),
            padding=(10, 6),
        )

        estilo.configure(
            "Panel.TLabelframe",
            background=COLOR_SUPERFICIE,
            bordercolor=COLOR_EJE,
        )
        estilo.configure(
            "Panel.TLabelframe.Label",
            background=COLOR_SUPERFICIE,
            foreground=COLOR_TEXTO_SECUNDARIO,
            font=("Segoe UI", 10, "bold"),
        )

        estilo.configure(
            "Treeview",
            background=COLOR_SUPERFICIE,
            fieldbackground=COLOR_SUPERFICIE,
            foreground=COLOR_TEXTO,
            rowheight=26,
            font=("Segoe UI", 10),
            borderwidth=0,
        )
        estilo.configure(
            "Treeview.Heading",
            background=COLOR_ENCABEZADO_TABLA,
            foreground=COLOR_ENCABEZADO_TABLA_TEXTO,
            font=("Segoe UI", 10, "bold"),
            padding=(8, 8),
            relief="flat",
        )
        estilo.map("Treeview.Heading", background=[("active", COLOR_ENCABEZADO_TABLA)])
        estilo.map(
            "Treeview",
            background=[("selected", COLOR_SELECCION)],
            foreground=[("selected", "white")],
        )

    # ------------------------------------------------------------------
    # Construcción de la interfaz
    # ------------------------------------------------------------------

    def _construir_interfaz(self) -> None:
        self._construir_banner()
        self._construir_tarjeta_ultimo_dato()
        self._construir_barra_herramientas()
        self._construir_panel_principal()

        self.label_estado = ttk.Label(self, text="", style="Estado.TLabel", anchor="w")
        self.label_estado.pack(fill="x", side="bottom")

    def _construir_banner(self) -> None:
        banner = tk.Frame(self, bg=COLOR_BANNER)
        banner.pack(fill="x")

        boton_formula = ttk.Button(
            banner,
            text="ƒ(x)  Fórmula",
            style="Formula.TButton",
            command=self.mostrar_formula,
        )
        boton_formula.place(relx=1.0, rely=0.5, anchor="e", x=-20)

        titulo = tk.Label(
            banner,
            text="Medición de DQO",
            font=("Segoe UI", 24, "bold"),
            bg=COLOR_BANNER,
            fg=COLOR_BANNER_TEXTO,
        )
        titulo.pack(pady=(16, 4))

        subtitulo = tk.Label(
            banner,
            text="Santiago Leon",
            font=("Segoe UI", 10, "italic"),
            bg=COLOR_BANNER,
            fg=COLOR_BANNER_SUBTEXTO,
        )
        subtitulo.pack(pady=(0, 14))

    def mostrar_formula(self) -> None:
        ventana = tk.Toplevel(self)
        ventana.title("Fórmula de DQO")
        ventana.configure(bg=COLOR_SUPERFICIE)
        ventana.resizable(False, False)
        ventana.transient(self)

        tk.Label(
            ventana,
            text="Fórmula utilizada",
            font=("Segoe UI", 11, "bold"),
            bg=COLOR_SUPERFICIE,
            fg=COLOR_TEXTO_SECUNDARIO,
        ).pack(padx=28, pady=(22, 8))
        tk.Label(
            ventana,
            text=TEXTO_ECUACION,
            font=("Segoe UI", 14, "bold"),
            bg=COLOR_SUPERFICIE,
            fg=COLOR_ACENTO,
        ).pack(padx=28, pady=(0, 22))
        ttk.Button(
            ventana, text="Cerrar", style="Acento.TButton", command=ventana.destroy
        ).pack(pady=(0, 22))

        ventana.update_idletasks()
        ancho, alto = ventana.winfo_width(), ventana.winfo_height()
        x = self.winfo_x() + (self.winfo_width() - ancho) // 2
        y = self.winfo_y() + (self.winfo_height() - alto) // 2
        ventana.geometry(f"+{x}+{y}")

        ventana.grab_set()

    def _construir_tarjeta_ultimo_dato(self) -> None:
        envoltorio = tk.Frame(self, bg=COLOR_FONDO)
        envoltorio.pack(fill="x", padx=16, pady=(14, 8))

        tarjeta = tk.Frame(
            envoltorio, bg=COLOR_SUPERFICIE, highlightbackground=COLOR_EJE, highlightthickness=1
        )
        tarjeta.pack(fill="x")

        info = tk.Frame(tarjeta, bg=COLOR_SUPERFICIE)
        info.pack(side="left", fill="both", expand=True, padx=22, pady=14)

        tk.Label(
            info,
            text="ÚLTIMO DATO REGISTRADO",
            font=("Segoe UI", 9, "bold"),
            bg=COLOR_SUPERFICIE,
            fg=COLOR_TEXTO_SECUNDARIO,
        ).pack(anchor="w")

        fila = tk.Frame(info, bg=COLOR_SUPERFICIE)
        fila.pack(anchor="w", pady=(8, 0))

        col_fecha = tk.Frame(fila, bg=COLOR_SUPERFICIE)
        col_fecha.pack(side="left", padx=(0, 34))
        tk.Label(
            col_fecha, text="Fecha y Hora", font=("Segoe UI", 8), bg=COLOR_SUPERFICIE, fg=COLOR_TEXTO_MUTED
        ).pack(anchor="w")
        self.label_fecha_ultimo = tk.Label(
            col_fecha, text="—", font=("Segoe UI", 15, "bold"), bg=COLOR_SUPERFICIE, fg=COLOR_TEXTO
        )
        self.label_fecha_ultimo.pack(anchor="w")

        col_senal = tk.Frame(fila, bg=COLOR_SUPERFICIE)
        col_senal.pack(side="left")
        tk.Label(
            col_senal, text="Señal", font=("Segoe UI", 8), bg=COLOR_SUPERFICIE, fg=COLOR_TEXTO_MUTED
        ).pack(anchor="w")
        self.label_senal_ultimo = tk.Label(
            col_senal, text="—", font=("Segoe UI", 15, "bold"), bg=COLOR_SUPERFICIE, fg=COLOR_TEXTO
        )
        self.label_senal_ultimo.pack(anchor="w")

        chip = tk.Frame(tarjeta, bg=COLOR_ENCABEZADO_TABLA)
        chip.pack(side="right", fill="y")
        interior_chip = tk.Frame(chip, bg=COLOR_ENCABEZADO_TABLA)
        interior_chip.pack(padx=34, pady=14)
        tk.Label(
            interior_chip,
            text="DQO",
            font=("Segoe UI", 9, "bold"),
            bg=COLOR_ENCABEZADO_TABLA,
            fg=COLOR_ENCABEZADO_TABLA_TEXTO,
        ).pack(anchor="center")
        self.label_dqo_ultimo = tk.Label(
            interior_chip,
            text="—",
            font=("Segoe UI", 34, "bold"),
            bg=COLOR_ENCABEZADO_TABLA,
            fg=COLOR_ENCABEZADO_TABLA_TEXTO,
        )
        self.label_dqo_ultimo.pack()

    def _construir_barra_herramientas(self) -> None:
        barra = ttk.Frame(self)
        barra.pack(fill="x", padx=16, pady=(0, 10))
        ttk.Button(
            barra, text="Abrir CSV...", style="Acento.TButton", command=self.abrir_archivo
        ).pack(side="left")
        self.label_archivo = ttk.Label(barra, text="Ningún archivo cargado", style="Archivo.TLabel")
        self.label_archivo.pack(side="left", padx=14)
        self.label_auto = ttk.Label(barra, text="", style="Auto.TLabel", anchor="e")
        self.label_auto.pack(side="right")

    def _construir_panel_principal(self) -> None:
        panel = ttk.Panedwindow(self, orient="horizontal")
        panel.pack(fill="both", expand=True, padx=16, pady=(0, 10))

        marco_tabla = ttk.LabelFrame(panel, text="Datos", style="Panel.TLabelframe")
        marco_grafica = ttk.LabelFrame(panel, text="Valor de DQO", style="Panel.TLabelframe")
        panel.add(marco_tabla, weight=2)
        panel.add(marco_grafica, weight=3)

        self._construir_tabla(marco_tabla)
        self._construir_grafica(marco_grafica)

    def _construir_tabla(self, parent: tk.Widget) -> None:
        contenedor = ttk.Frame(parent)
        contenedor.pack(fill="both", expand=True, padx=6, pady=6)

        self.tabla = ttk.Treeview(contenedor, show="headings")
        scroll_y = ttk.Scrollbar(contenedor, orient="vertical", command=self.tabla.yview)
        scroll_x = ttk.Scrollbar(contenedor, orient="horizontal", command=self.tabla.xview)
        self.tabla.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        self.tabla.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="ew")
        contenedor.rowconfigure(0, weight=1)
        contenedor.columnconfigure(0, weight=1)

        self.tabla.tag_configure("par", background=COLOR_FILA_PAR)
        self.tabla.tag_configure("impar", background=COLOR_FILA_IMPAR)

    def _construir_grafica(self, parent: tk.Widget) -> None:
        contenedor = ttk.Frame(parent)
        contenedor.pack(fill="both", expand=True, padx=6, pady=6)

        self.figura = Figure(figsize=(5, 4), dpi=100, facecolor=COLOR_SUPERFICIE)
        self.ax = self.figura.add_subplot(111)

        self.canvas_grafica = FigureCanvasTkAgg(self.figura, master=contenedor)
        self.canvas_grafica.get_tk_widget().pack(side="top", fill="both", expand=True)

        barra_herramientas = NavigationToolbar2Tk(self.canvas_grafica, contenedor, pack_toolbar=False)
        barra_herramientas.config(background=COLOR_SUPERFICIE)
        barra_herramientas.update()
        barra_herramientas.pack(side="bottom", fill="x")

        self._dibujar_grafica_vacia()

    # ------------------------------------------------------------------
    # Carga y refresco de datos
    # ------------------------------------------------------------------

    def abrir_archivo(self) -> None:
        ruta = filedialog.askopenfilename(
            title="Selecciona un archivo CSV",
            filetypes=[("Archivos CSV", "*.csv"), ("Todos los archivos", "*.*")],
        )
        if ruta:
            self.cargar_archivo(ruta)

    def cargar_archivo(self, ruta: str, mostrar_error: bool = True) -> None:
        try:
            encabezado, datos = leer_datos(ruta)
        except Exception as error:
            if mostrar_error:
                messagebox.showerror("Error al leer el archivo", str(error))
            return

        self._llenar_tabla(encabezado, datos)
        self._actualizar_tarjeta_ultimo_dato(encabezado, datos)
        self._actualizar_grafica(encabezado, datos)

        self.ruta_actual = ruta
        try:
            self.mtime_actual = os.path.getmtime(ruta)
        except OSError:
            self.mtime_actual = None

        self.label_archivo.config(text=os.path.basename(ruta))
        self.label_estado.config(text=f"{len(datos)} filas cargadas  —  {ruta}")

    def _llenar_tabla(self, encabezado: list[str], datos: list[list[str]]) -> None:
        self.tabla.delete(*self.tabla.get_children())
        self.tabla["columns"] = encabezado
        for columna in encabezado:
            self.tabla.heading(columna, text=columna)
            ancho = 170 if "Fecha" in columna else 130
            self.tabla.column(columna, width=ancho, anchor="center")

        for indice, fila in enumerate(datos):
            etiqueta = "par" if indice % 2 == 0 else "impar"
            self.tabla.insert("", "end", values=fila, tags=(etiqueta,))

    def _actualizar_tarjeta_ultimo_dato(self, encabezado: list[str], datos: list[list[str]]) -> None:
        if not datos or COLUMNA_DQO not in encabezado:
            self.label_fecha_ultimo.config(text="—")
            self.label_senal_ultimo.config(text="—")
            self.label_dqo_ultimo.config(text="—")
            return

        ultima = datos[-1]
        idx_dqo = encabezado.index(COLUMNA_DQO)
        idx_senal = encabezado.index(COLUMNA_SENAL) if COLUMNA_SENAL in encabezado else 1
        self.label_fecha_ultimo.config(text=ultima[0])
        self.label_senal_ultimo.config(text=ultima[idx_senal])
        self.label_dqo_ultimo.config(text=ultima[idx_dqo])

    def _series_para_grafica(
        self, encabezado: list[str], datos: list[list[str]]
    ) -> tuple[list, list[float], bool]:
        if COLUMNA_DQO not in encabezado:
            return [], [], False

        es_fecha = encabezado[0] == COLUMNA_FECHA
        idx_dqo = encabezado.index(COLUMNA_DQO)
        xs: list = []
        ys: list[float] = []
        for fila in datos:
            try:
                y = _a_numero(fila[idx_dqo])
                x = datetime.strptime(fila[0], FORMATO_FECHA) if es_fecha else _a_numero(fila[0])
            except (ValueError, IndexError):
                continue
            xs.append(x)
            ys.append(y)
        return xs, ys, es_fecha

    def _dibujar_grafica_vacia(self) -> None:
        self.ax.clear()
        self.ax.set_facecolor(COLOR_SUPERFICIE)
        self.ax.text(
            0.5,
            0.5,
            "Sin datos para graficar",
            ha="center",
            va="center",
            transform=self.ax.transAxes,
            color=COLOR_TEXTO_MUTED,
            fontsize=11,
        )
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        for lado in ("top", "right", "left", "bottom"):
            self.ax.spines[lado].set_visible(False)
        self.figura.tight_layout()
        self.canvas_grafica.draw()

    def _actualizar_grafica(self, encabezado: list[str], datos: list[list[str]]) -> None:
        xs, ys, es_fecha = self._series_para_grafica(encabezado, datos)
        if not xs:
            self._dibujar_grafica_vacia()
            return

        self.ax.clear()
        self.ax.set_facecolor(COLOR_SUPERFICIE)

        self.ax.plot(
            xs,
            ys,
            color=COLOR_ACENTO,
            linewidth=2,
            marker="o",
            markersize=5,
            markerfacecolor=COLOR_ACENTO,
            markeredgecolor=COLOR_SUPERFICIE,
            markeredgewidth=1,
            zorder=2,
        )
        self.ax.scatter(
            [xs[-1]],
            [ys[-1]],
            color=COLOR_PUNTO_ACTUAL,
            s=90,
            zorder=3,
            edgecolor=COLOR_SUPERFICIE,
            linewidth=1.5,
        )
        self.ax.annotate(
            _a_texto(ys[-1]),
            (xs[-1], ys[-1]),
            textcoords="offset points",
            xytext=(10, 8),
            fontsize=9,
            fontweight="bold",
            color=COLOR_PUNTO_ACTUAL,
        )

        self.ax.set_xlabel(COLUMNA_FECHA if es_fecha else "Tiempo (s)", fontsize=10, color=COLOR_TEXTO_MUTED)
        self.ax.set_ylabel(COLUMNA_DQO, fontsize=10, color=COLOR_TEXTO_MUTED)
        self.ax.grid(True, axis="y", color=COLOR_GRID, linewidth=0.8)
        self.ax.spines["top"].set_visible(False)
        self.ax.spines["right"].set_visible(False)
        self.ax.spines["left"].set_color(COLOR_EJE)
        self.ax.spines["bottom"].set_color(COLOR_EJE)
        self.ax.tick_params(colors=COLOR_TEXTO_MUTED, labelsize=8)

        if es_fecha:
            self.ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m %H:%M"))
            self.figura.autofmt_xdate(rotation=30, ha="right")

        self.figura.tight_layout()
        self.canvas_grafica.draw()

    # ------------------------------------------------------------------
    # Actualización automática
    # ------------------------------------------------------------------

    def _verificar_actualizacion(self) -> None:
        if self.ruta_actual and os.path.isfile(self.ruta_actual):
            try:
                mtime = os.path.getmtime(self.ruta_actual)
            except OSError:
                mtime = None

            if mtime is not None and mtime != self.mtime_actual:
                self.cargar_archivo(self.ruta_actual, mostrar_error=False)

            self.label_auto.config(
                text=f"Auto-actualización activa — última comprobación: {datetime.now().strftime('%H:%M:%S')}"
            )
        else:
            self.label_auto.config(text="Auto-actualización en espera de un archivo CSV")

        self.after(INTERVALO_AUTOACTUALIZACION_MS, self._verificar_actualizacion)


def main() -> None:
    app = AppDQO()
    app.mainloop()


if __name__ == "__main__":
    main()
