"""Figuras del ejercicio 6.

Uso (desde la carpeta del repositorio):
    python scripts/figuras_ej6.py CSV_VARIANTES TXT_TECHO_ANCHO
Ejemplo:
    python scripts/figuras_ej6.py resultados/ej6_variantes_*.csv resultados/ej3_techo_ancho_*.txt

Genera en figuras/:
    fig15_variantes.png       tiempo de cada variante (N=2048, 12 hilos)
    fig16_speedup_variantes.png  speedup absoluto de cada variante frente a los hilos
    fig17_ancho_banda.png     ancho de banda conseguido frente al techo medido
"""
import csv
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

AZUL, NARANJA, AQUA, AMARILLO = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
TINTA, TINTA_2, REJILLA = "#0b0b0b", "#52514e", "#e4e3df"
COLORES = {"base": AZUL, "it1": NARANJA, "it2": AQUA, "it3": AMARILLO}
NOMBRES = {"base": "Base (ejercicio 2)", "it1": "It. 1: residuo fusionado",
           "it2": "It. 2: + dynamic,16", "it3": "It. 3: + región única"}


def coma(x, d):
    return f"{x:.{d}f}".replace(".", ",")


def estilo(ax):
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color(TINTA_2)
    ax.tick_params(colors=TINTA_2, labelsize=10)
    ax.set_axisbelow(True)


def leer_bloques(ruta):
    bloques, actual = [], []
    with open(ruta, encoding="utf-8") as f:
        for fila in csv.reader(f):
            if not fila:
                if actual:
                    bloques.append(actual)
                actual = []
            elif not fila[0].startswith("#"):
                actual.append(fila)
    if actual:
        bloques.append(actual)
    return [[dict(zip(b[0], r)) for r in b[1:]] for b in bloques]


def techo_ancho(ruta):
    mejor = 0.0
    with open(ruta, encoding="utf-8") as f:
        for linea in f:
            partes = linea.strip().split(",")
            if len(partes) == 5 and partes[0].isdigit():
                mejor = max(mejor, float(partes[3]))
    return mejor


def main():
    variantes, barrido, _ = leer_bloques(sys.argv[1])
    techo = techo_ancho(sys.argv[2])
    os.makedirs("figuras", exist_ok=True)
    plt.rcParams["font.family"] = "DejaVu Sans"
    claves = [r["variante"] for r in variantes]

    # ---------- Figura 15: tiempo por variante ----------
    fig, ax = plt.subplots(figsize=(7.5, 4.3), dpi=200)
    estilo(ax)
    ax.grid(True, axis="x", color=REJILLA, linewidth=0.8)
    y = list(range(len(claves)))[::-1]
    t = [float(r["tiempo_s"]) for r in variantes]
    ax.barh(y, t, height=0.6, color=[COLORES[c] for c in claves],
            edgecolor="white", linewidth=2)
    for yi, r in zip(y, variantes):
        extra = (f"  ({r['mejora_vs_anterior_pct'].replace('.', ',')} % frente a la anterior)"
                 if r["mejora_vs_anterior_pct"] else "")
        ax.text(float(r["tiempo_s"]) + 0.01, yi,
                f"{coma(float(r['tiempo_s']), 3)} s · speedup {coma(float(r['speedup_abs']), 2)}{extra}",
                va="center", fontsize=9, color=TINTA)
    ax.set_yticks(y)
    ax.set_yticklabels([NOMBRES[c] for c in claves], fontsize=10, color=TINTA)
    ax.set_xlim(0, max(t) * 1.95)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: coma(v, 1)))
    ax.set_xlabel("Tiempo de 300 pasos (s), N = 2048, 12 hilos, mínimo de 6", color=TINTA)
    ax.set_title("Variantes del ejercicio 6 (todas verifican)", color=TINTA,
                 fontsize=11, loc="left")
    fig.tight_layout()
    fig.savefig("figuras/fig15_variantes.png", facecolor="white")
    plt.close(fig)

    # ---------- Figura 16: speedup frente a hilos ----------
    fig, ax = plt.subplots(figsize=(7.5, 4.6), dpi=200)
    estilo(ax)
    ax.grid(True, color=REJILLA, linewidth=0.8)
    h = [int(r["hilos"]) for r in barrido]
    for c, marca in zip(claves, ("o", "s", "^", "D")):
        s = [float(r[c]) for r in barrido]
        ax.plot(h, s, color=COLORES[c], linewidth=2, marker=marca, markersize=6,
                label=NOMBRES[c])
        dy = {"it1": 7, "it2": -7}.get(c, 0)   # separa etiquetas muy proximas
        ax.annotate(coma(s[-1], 2), (h[-1], s[-1]), textcoords="offset points",
                    xytext=(7, dy), va="center", fontsize=9, color=TINTA)
    ax.set_xticks(h)
    ax.set_xlim(0, 27)
    ax.set_ylim(0, 7)
    ax.set_xlabel("Número de hilos", color=TINTA)
    ax.set_ylabel("Speedup absoluto (N = 2048, 300 pasos)", color=TINTA)
    ax.set_title("Speedup de cada variante", color=TINTA, fontsize=11, loc="left")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    fig.tight_layout()
    fig.savefig("figuras/fig16_speedup_variantes.png", facecolor="white")
    plt.close(fig)

    # ---------- Figura 17: ancho de banda conseguido ----------
    fig, ax = plt.subplots(figsize=(7.5, 4.2), dpi=200)
    estilo(ax)
    ax.grid(True, axis="y", color=REJILLA, linewidth=0.8)
    gbs = [float(r["GBs_modelo_16B"]) for r in variantes]
    x = list(range(len(claves)))
    ax.bar(x, gbs, width=0.6, color=[COLORES[c] for c in claves],
           edgecolor="white", linewidth=2)
    ax.axhline(techo, color=TINTA_2, linestyle="--", linewidth=1.2)
    ax.text(len(claves) - 0.5, techo + 1, f"techo medido (triad): {coma(techo, 1)} GB/s",
            ha="right", fontsize=9, color=TINTA_2)
    for xi, g in zip(x, gbs):
        ax.text(xi, g - 4, f"{coma(g, 1)}\n({coma(100 * g / techo, 0)} %)",
                ha="center", va="top", fontsize=9, color="white")
    ax.set_xticks(x)
    ax.set_xticklabels([NOMBRES[c] for c in claves], fontsize=9, color=TINTA)
    ax.set_ylim(0, techo * 1.2)
    ax.set_ylabel("GB/s (modelo de 16 bytes por celda)", color=TINTA)
    ax.set_title("Ancho de banda conseguido (12 hilos) frente al techo",
                 color=TINTA, fontsize=11, loc="left")
    fig.tight_layout()
    fig.savefig("figuras/fig17_ancho_banda.png", facecolor="white")
    plt.close(fig)

    print("Generadas figuras/fig15_variantes.png, fig16_speedup_variantes.png "
          "y fig17_ancho_banda.png")


if __name__ == "__main__":
    main()
