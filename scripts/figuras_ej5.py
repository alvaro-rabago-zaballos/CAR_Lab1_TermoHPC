"""Figuras del ejercicio 5 (planificaciones).

Uso (desde la carpeta del repositorio):
    python scripts/figuras_ej5.py CSV_PLANIF TXT_CONFIRMACION
Ejemplo:
    python scripts/figuras_ej5.py resultados/ej5_planif_*.csv resultados/ej5_confirmacion_*.txt

Genera en figuras/:
    fig13_planificaciones.png   tiempo de cada planificacion (12 hilos, N=2048)
    fig14_static_dynamic.png    static frente a dynamic,16 segun los hilos
"""
import csv
import os
import re
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

AZUL, NARANJA, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
TINTA, TINTA_2, REJILLA = "#0b0b0b", "#52514e", "#e4e3df"
COLOR = {"static": AZUL, "dynamic": NARANJA, "guided": AQUA}


def coma(x, d):
    return f"{x:.{d}f}".replace(".", ",")


def estilo(ax):
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color(TINTA_2)
    ax.tick_params(colors=TINTA_2, labelsize=10)
    ax.set_axisbelow(True)


def main():
    with open(sys.argv[1], encoding="utf-8") as f:
        filas = list(csv.DictReader(f))
    os.makedirs("figuras", exist_ok=True)
    plt.rcParams["font.family"] = "DejaVu Sans"

    # ---------- Figura 13: barras por planificacion ----------
    nombres = [r["planificacion"] for r in filas]
    tiempos = [float(r["tiempo_s"]) for r in filas]
    familias = [n.split(",")[0] for n in nombres]
    t_static = tiempos[nombres.index("static")]

    fig, ax = plt.subplots(figsize=(7.5, 5), dpi=200)
    estilo(ax)
    ax.grid(True, axis="x", color=REJILLA, linewidth=0.8)
    y = list(range(len(nombres)))[::-1]
    ax.barh(y, tiempos, height=0.62, color=[COLOR[f] for f in familias],
            edgecolor="white", linewidth=2)
    ax.axvline(t_static, color=TINTA_2, linestyle="--", linewidth=1.2)
    for yi, t, r in zip(y, tiempos, filas):
        ax.text(max(t, t_static) + 0.012, yi, f"{coma(t, 3)} s  ({r['vs_static_pct'].replace('.', ',')} %)",
                va="center", fontsize=9, color=TINTA)
    ax.set_yticks(y)
    ax.set_yticklabels(nombres, fontsize=10, color=TINTA)
    ax.set_xlim(0, max(tiempos) * 1.32)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: coma(v, 1)))
    ax.set_xlabel("Tiempo de 300 pasos (s), mínimo de 4 repeticiones", color=TINTA)
    ax.set_title("Planificaciones con 12 hilos, N = 2048 (todas verifican)",
                 color=TINTA, fontsize=11, loc="left")
    leyenda = [plt.Rectangle((0, 0), 1, 1, color=COLOR[k]) for k in COLOR]
    ax.legend(leyenda, ["static", "dynamic", "guided"], frameon=False, fontsize=9,
              loc="lower right")
    fig.tight_layout()
    fig.savefig("figuras/fig13_planificaciones.png", facecolor="white")
    plt.close(fig)

    # ---------- Figura 14: static frente a dynamic,16 segun los hilos ----------
    datos = {}
    with open(sys.argv[2], encoding="utf-8") as f:
        for linea in f:
            m = re.match(r"hilos=(\d+) (\S+):(.*)", linea)
            if m:
                datos[(int(m[1]), m[2])] = min(float(x) for x in m[3].split())
    hilos = sorted({h for h, _ in datos})
    s = [datos[(h, "static")] for h in hilos]
    d = [datos[(h, "dynamic,16")] for h in hilos]

    fig, ax = plt.subplots(figsize=(7.5, 4.3), dpi=200)
    estilo(ax)
    ax.grid(True, axis="y", color=REJILLA, linewidth=0.8)
    x = range(len(hilos))
    ancho = 0.36
    ax.bar([i - ancho / 2 for i in x], s, width=ancho, color=AZUL,
           edgecolor="white", linewidth=2, label="static")
    ax.bar([i + ancho / 2 for i in x], d, width=ancho, color=NARANJA,
           edgecolor="white", linewidth=2, label="dynamic,16")
    for i, (a, b) in enumerate(zip(s, d)):
        ax.text(i + ancho / 2, b + 0.01, f"{coma(100 * (b / a - 1), 1)} %",
                ha="center", fontsize=9, color=TINTA)
    ax.set_xticks(list(x))
    ax.set_xticklabels([f"{h} hilos" for h in hilos], color=TINTA)
    ax.set_ylim(0, max(s) * 1.2)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: coma(v, 1)))
    ax.set_ylabel("Tiempo de 300 pasos (s)", color=TINTA)
    ax.set_title("static frente a dynamic,16 (N = 2048, mínimo de 6 repeticiones)",
                 color=TINTA, fontsize=11, loc="left")
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    fig.tight_layout()
    fig.savefig("figuras/fig14_static_dynamic.png", facecolor="white")
    plt.close(fig)

    print("Generadas figuras/fig13_planificaciones.png y fig14_static_dynamic.png")


if __name__ == "__main__":
    main()
