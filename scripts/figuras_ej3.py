"""Figuras del ejercicio 3 a partir de los ficheros de resultados/.

Uso (desde la carpeta del repositorio):
    python scripts/figuras_ej3.py CSV_GRANDE CSV_PEQUENA TECHO_CALCULO TECHO_BARRERA
Ejemplo:
    python scripts/figuras_ej3.py resultados/ej3_fuerte_2048_*.csv \
        resultados/ej3_fuerte_250_*.csv resultados/ej3_techo_calculo_*.txt \
        resultados/ej3_techo_barrera_*.txt

Genera en figuras/:
    fig7_speedup_fuerte.png     speedup absoluto, diagonal ideal y techo medido
    fig8_eficiencia_fuerte.png  eficiencia de las dos mallas y del techo
    fig9_paso_vs_sincro.png     tiempo por paso de la malla pequena frente al
                                coste de sincronizacion de un paso
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
HILOS = [1, 2, 4, 8, 12, 16, 20, 24]


def coma(x, d):
    return f"{x:.{d}f}".replace(".", ",")


def leer_barrido(ruta):
    with open(ruta, encoding="utf-8") as f:
        filas = [r for r in csv.DictReader(f) if r["hilos"] != "sec"]
    nombre = os.path.basename(ruta)
    n = re.search(r"fuerte_(\d+)", nombre).group(1)
    return n, filas


def leer_techo(ruta):
    filas = []
    with open(ruta, encoding="utf-8") as f:
        cabecera = None
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#"):
                continue
            if cabecera is None:
                cabecera = linea.split(",")
                continue
            filas.append(dict(zip(cabecera, linea.split(","))))
    return filas


def estilo(ax):
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color(TINTA_2)
    ax.tick_params(colors=TINTA_2, labelsize=10)
    ax.grid(True, color=REJILLA, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_xticks(HILOS)


def etiqueta_final(ax, x, y, texto, color, dy=0):
    ax.annotate(texto, (x, y), textcoords="offset points", xytext=(6, dy),
                va="center", fontsize=9, color=TINTA)
    ax.plot([], [], color=color)


def main():
    n_g, grande = leer_barrido(sys.argv[1])
    n_p, pequena = leer_barrido(sys.argv[2])
    techo = leer_techo(sys.argv[3])
    sincro = leer_techo(sys.argv[4])
    os.makedirs("figuras", exist_ok=True)
    plt.rcParams["font.family"] = "DejaVu Sans"

    p = [int(r["hilos"]) for r in grande]
    s_g = [float(r["speedup_abs"]) for r in grande]
    s_p = [float(r["speedup_abs"]) for r in pequena]
    s_t = [float(r["techo_speedup"]) for r in techo]

    # ---------- Figura 7: speedup ----------
    fig, ax = plt.subplots(figsize=(7.5, 4.8), dpi=200)
    estilo(ax)
    ax.plot(p, p, linestyle="--", color=TINTA_2, linewidth=1.2, label="Ideal (lineal)")
    ax.plot(p, s_t, color=AQUA, linewidth=2, marker="s", markersize=6,
            label="Techo de cálculo medido")
    ax.plot(p, s_g, color=AZUL, linewidth=2, marker="o", markersize=7,
            label=f"TermoHPC N = {n_g}")
    ax.plot(p, s_p, color=NARANJA, linewidth=2, marker="^", markersize=7,
            label=f"TermoHPC N = {n_p}")
    for serie, txt in ((s_t, "techo"), (s_g, f"N={n_g}"), (s_p, f"N={n_p}")):
        ax.annotate(f"{coma(serie[-1], 2)}", (p[-1], serie[-1]),
                    textcoords="offset points", xytext=(7, 0), va="center",
                    fontsize=9, color=TINTA)
    imax = max(range(len(s_g)), key=lambda i: s_g[i])
    if imax != len(s_g) - 1:
        ax.annotate(f"máx. {coma(s_g[imax], 2)}", (p[imax], s_g[imax]),
                    textcoords="offset points", xytext=(0, 9), ha="center",
                    fontsize=9, color=TINTA)
    imax = max(range(len(s_p)), key=lambda i: s_p[i])
    ax.annotate(f"máx. {coma(s_p[imax], 2)}", (p[imax], s_p[imax]),
                textcoords="offset points", xytext=(0, -14), ha="center",
                fontsize=9, color=TINTA)
    ax.set_xlim(0, 26.5)
    ax.set_ylim(0, 16)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}"))
    ax.set_xlabel("Número de hilos", color=TINTA)
    ax.set_ylabel("Speedup absoluto (T secuencial / T paralelo)", color=TINTA)
    ax.set_title("Escalabilidad fuerte: speedup frente al techo de la máquina",
                 color=TINTA, fontsize=11, loc="left")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    fig.tight_layout()
    fig.savefig("figuras/fig7_speedup_fuerte.png", facecolor="white")
    plt.close(fig)

    # ---------- Figura 8: eficiencia ----------
    fig, ax = plt.subplots(figsize=(7.5, 4.5), dpi=200)
    estilo(ax)
    e_t = [s / q * 100 for s, q in zip(s_t, p)]
    e_g = [s / q * 100 for s, q in zip(s_g, p)]
    e_p = [s / q * 100 for s, q in zip(s_p, p)]
    ax.plot(p, e_t, color=AQUA, linewidth=2, marker="s", markersize=6,
            label="Techo de cálculo medido")
    ax.plot(p, e_g, color=AZUL, linewidth=2, marker="o", markersize=7,
            label=f"TermoHPC N = {n_g}")
    ax.plot(p, e_p, color=NARANJA, linewidth=2, marker="^", markersize=7,
            label=f"TermoHPC N = {n_p}")
    ax.axvline(16, color=TINTA_2, linestyle=":", linewidth=1.2)
    ax.text(16.3, 45, "16 hilos lógicos", fontsize=9, color=TINTA_2, va="top")
    ax.set_xlim(0, 25)
    ax.set_ylim(0, 110)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f} %"))
    ax.set_xlabel("Número de hilos", color=TINTA)
    ax.set_ylabel("Eficiencia (speedup / hilos)", color=TINTA)
    ax.set_title("Escalabilidad fuerte: eficiencia", color=TINTA, fontsize=11,
                 loc="left")
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    fig.tight_layout()
    fig.savefig("figuras/fig8_eficiencia_fuerte.png", facecolor="white")
    plt.close(fig)

    # ---------- Figura 9: tiempo por paso de la malla pequena ----------
    fig, ax = plt.subplots(figsize=(7.5, 4.5), dpi=200)
    estilo(ax)
    paso_us = [float(r["tiempo_paso_ms"]) * 1000 for r in pequena]
    sincro_us = [2 * float(r["region_us"]) for r in sincro]
    ax.plot(p, paso_us, color=NARANJA, linewidth=2, marker="^", markersize=7,
            label=f"Tiempo medido por paso (N = {n_p})")
    ax.plot(p, sincro_us, color=TINTA_2, linewidth=2, marker="o", markersize=6,
            linestyle="--",
            label="Coste de abrir y cerrar 2 regiones parallel for (medido)")
    trabajo = float(pequena[0]["tiempo_paso_ms"]) * 1000
    ideal = [trabajo / q for q in p]
    ax.plot(p, ideal, color=AZUL, linewidth=1.5, linestyle=":",
            label="Trabajo de un paso repartido idealmente (T1 / p)")
    ax.set_xlim(0, 25)
    ax.set_ylim(0, max(paso_us) * 1.15)
    ax.set_xlabel("Número de hilos", color=TINTA)
    ax.set_ylabel("Microsegundos por paso", color=TINTA)
    ax.set_title(f"Malla pequeña (N = {n_p}): el coste de sincronizar domina",
                 color=TINTA, fontsize=11, loc="left")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    fig.tight_layout()
    fig.savefig("figuras/fig9_paso_vs_sincro.png", facecolor="white")
    plt.close(fig)

    print("Generadas figuras/fig7_speedup_fuerte.png, fig8_eficiencia_fuerte.png "
          "y fig9_paso_vs_sincro.png")


if __name__ == "__main__":
    main()
