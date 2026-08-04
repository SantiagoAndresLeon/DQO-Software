"""
Lee un archivo CSV y muestra su contenido en pantalla en formato de tabla.

Uso:
    python leer_csv.py [ruta_al_csv]

Si no se indica una ruta, el programa busca automáticamente el primer
archivo .csv en la carpeta donde se ejecuta el script.
"""

import csv
import sys
import glob
import os


def detectar_delimitador(muestra: str) -> str:
    lineas = [linea for linea in muestra.splitlines() if linea.strip()]
    if not lineas:
        return ","

    # Se prueban los delimitadores más comunes en orden de prioridad.
    # La coma se deja al final porque en archivos con formato europeo
    # (ej. "1234,56") se usa como separador decimal, no de columnas.
    candidatos = [";", "\t", "|", ","]
    for delim in candidatos:
        conteos = {linea.count(delim) for linea in lineas}
        if len(conteos) == 1 and conteos.pop() > 0:
            return delim

    return ","


def carpeta_del_programa() -> str:
    # Cuando se ejecuta como .exe compilado (PyInstaller), __file__ apunta a
    # una carpeta temporal, así que se usa la ubicación del propio .exe.
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def encontrar_csv_por_defecto() -> str | None:
    archivos = glob.glob(os.path.join(carpeta_del_programa(), "*.csv"))
    return archivos[0] if archivos else None


def leer_csv(ruta: str) -> tuple[list[str], list[list[str]]]:
    with open(ruta, newline="", encoding="utf-8-sig") as f:
        muestra = f.read(2048)
        f.seek(0)
        delimitador = detectar_delimitador(muestra)
        lector = csv.reader(f, delimiter=delimitador)
        filas = [fila for fila in lector if fila]

    if not filas:
        return [], []

    # Heurística simple: si la primera celda de la primera fila no es
    # numérica, se asume que es un encabezado.
    primera = filas[0]
    def es_numero(valor: str) -> bool:
        try:
            float(valor.replace(",", "."))
            return True
        except ValueError:
            return False

    if all(es_numero(v) for v in primera):
        encabezado = [f"Columna {i + 1}" for i in range(len(primera))]
        datos = filas
    else:
        encabezado = primera
        datos = filas[1:]

    return encabezado, datos


def mostrar_tabla(encabezado: list[str], datos: list[list[str]]) -> None:
    if not encabezado:
        print("El archivo CSV está vacío.")
        return

    columnas = len(encabezado)
    anchos = [len(encabezado[i]) for i in range(columnas)]
    for fila in datos:
        for i in range(columnas):
            if i < len(fila):
                anchos[i] = max(anchos[i], len(fila[i]))

    def formatear_fila(fila: list[str]) -> str:
        celdas = []
        for i in range(columnas):
            valor = fila[i] if i < len(fila) else ""
            celdas.append(valor.ljust(anchos[i]))
        return " | ".join(celdas)

    linea_separadora = "-+-".join("-" * a for a in anchos)

    print(formatear_fila(encabezado))
    print(linea_separadora)
    for fila in datos:
        print(formatear_fila(fila))

    print(f"\nTotal de filas: {len(datos)}")


def main() -> None:
    if len(sys.argv) > 1:
        ruta = sys.argv[1]
    else:
        ruta = encontrar_csv_por_defecto()
        if ruta is None:
            print("No se encontró ningún archivo .csv y no se indicó una ruta.")
            print("Uso: python leer_csv.py [ruta_al_csv]")
            sys.exit(1)
        print(f"No se indicó archivo, usando: {os.path.basename(ruta)}\n")

    if not os.path.isfile(ruta):
        print(f"Error: no se encontró el archivo '{ruta}'")
        sys.exit(1)

    encabezado, datos = leer_csv(ruta)
    mostrar_tabla(encabezado, datos)

    # Evita que la ventana se cierre de inmediato al hacer doble clic en el .exe.
    if getattr(sys, "frozen", False):
        input("\nPresiona Enter para salir...")


if __name__ == "__main__":
    main()
