"""Figuras del ejercicio 4 (escalabilidad debil).

Uso (desde la carpeta del repositorio):
    python scripts/figuras_ej4.py CSV_DEBIL CSV_FUERTE_2048
Ejemplo:
    python scripts/figuras_ej4.py resultados/ej4_debil_*.csv resultados/ej3_fuerte_2048_*.csv

Genera en figuras/:
    fig10_tiempo_debil.png        tiempo frente a hilos con la linea plana ideal
    fig11_eficiencia_debil_fuerte.png  eficiencia debil frente a fuerte
    fig12_coste_por_celda.png     ns por celda y paso (secuencial) frente a la memoria
"""
import csv
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

AZUL, NARANJA = "#2a78d6", "#eb6834"
TINTA, TINTA_2, REJILLA = "#0b0b0b", "#52514e", "#e4e3df"
HILOS = [1, 2, 4, 8, 12, 16, 20, 24]


def coma(x, d):
    return f"{x:.{d}f}".replace(".", ",")


def leer(ruta):
    with open(ruta, encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if r["hilos"] != "sec"]


def estilo(ax, ticks_hilos=True):
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color(TINTA_2)
    ax.tick_params(colors=TINTA_2, labelsize=10)
    ax.grid(True, color=REJILLA, linewidth=0.8)
    ax.set_axisbelow(True)
    if ticks_hilos:
        ax.set_xticks(HILOS)


def main():
    debil = leer(sys.argv[1])
    fuerte = leer(sys.argv[2])
    os.makedirs("figuras", exist_ok=True)
    plt.rcParams["font.family"] = "DejaVu Sans"

    p = [int(r["hilos"]) for r in debil]
    n = [int(r["N"]) for r in debil]
    tp = [float(r["tiempo_par_s"]) for r in debil]

    # ---------- Figura 10: tiempo frente a hilos ----------
    fig, ax = plt.subplots(figsize=(7.5, 4.6), dpi=200)
    estilo(ax)
    ax.axhline(tp[0], color=TINTA_2, linestyle="--", linewidth=1.2,
               label=f"Ideal: tiempo constante ({coma(tp[0], 2)} s)")
    ax.plot(p, tp, color=AZUL, linewidth=2, marker="o", markersize=7,
            label="Tiempo medido")
    for i, (x, y, m) in enumerate(zip(p, tp, n)):
        ax.annotate(f"N={m}", (x, y), textcoords="offset points",
                    xytext=(0, -15) if i == 0 else (0, 9),
                    ha="center", fontsize=8, color=TINTA_2)
    ax.annotate(f"{coma(tp[-1], 2)} s", (p[-1], tp[-1]), textcoords="offset points",
                xytext=(0, -16), ha="center", fontsize=9, color=TINTA)
    ax.set_xlim(0, 25.5)
    ax.set_ylim(0, max(tp) * 1.18)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: coma(v, 0)))
    ax.set_xlabel("Número de hilos (la malla crece como N = 1024·√p)", color=TINTA)
    ax.set_ylabel("Tiempo de 300 pasos (s)", color=TINTA)
    ax.set_title("Escalabilidad débil: mismo trabajo por hilo", color=TINTA,
                 fontsize=11, loc="left")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    fig.tight_layout()
    fig.savefig("figuras/fig10_tiempo_debil.png", facecolor="white")
    plt.close(fig)

    # ---------- Figura 11: eficiencia debil frente a fuerte ----------
    fig, ax = plt.subplots(figsize=(7.5, 4.5), dpi=200)
    estilo(ax)
    e_d = [float(r["eficiencia_debil_rel"]) * 100 for r in debil]
    pf = [int(r["hilos"]) for r in fuerte]
    e_f = [float(r["eficiencia_abs"]) * 100 for r in fuerte]
    ax.plot(pf, e_f, color=AZUL, linewidth=2, marker="o", markersize=7,
            label="Fuerte (N = 2048 fijo)")
    ax.plot(p, e_d, color=NARANJA, linewidth=2, marker="^", markersize=7,
            label="Débil (N = 1024·√p)")
    for serie, xs in ((e_f, pf), (e_d, p)):
        ax.annotate(f"{coma(serie[-1], 1)} %", (xs[-1], serie[-1]),
                    textcoords="offset points", xytext=(7, 0), va="center",
                    fontsize=9, color=TINTA)
    ax.set_xlim(0, 26.5)
    ax.set_ylim(0, 110)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f} %"))
    ax.set_xlabel("Número de hilos", color=TINTA)
    ax.set_ylabel("Eficiencia", color=TINTA)
    ax.set_title("Eficiencia débil frente a fuerte", color=TINTA, fontsize=11,
                 loc="left")
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    fig.tight_layout()
    fig.savefig("figuras/fig11_eficiencia_debil_fuerte.png", facecolor="white")
    plt.close(fig)

    # ---------- Figura 12: coste por celda frente a la memoria ----------
    fig, ax = plt.subplots(figsize=(7.5, 4.3), dpi=200)
    estilo(ax, ticks_hilos=False)
    mem = [float(r["memoria_MB"]) for r in debil]
    ns = [float(r["ns_celda_paso_sec"]) for r in debil]
    ax.axvline(24, color=TINTA_2, linestyle=":", linewidth=1.2)
    ax.text(28, 0.25, "L3 = 24 MB", fontsize=9, color=TINTA_2)
    ax.plot(mem, ns, color=AZUL, linewidth=2, marker="o", markersize=7)
    for i, (x, y, m) in enumerate(zip(mem, ns, n)):
        ax.annotate(f"N={m}\n{coma(y, 2)} ns", (x, y), textcoords="offset points",
                    xytext=(14, -28) if i == 0 else (0, 10), ha="center",
                    fontsize=8, color=TINTA)
    ax.set_xlim(0, 440)
    ax.set_ylim(0, max(ns) * 1.35)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: coma(v, 1)))
    ax.set_xlabel("Memoria de los dos buffers (MB)", color=TINTA)
    ax.set_ylabel("ns por celda y paso (secuencial)", color=TINTA)
    ax.set_title("Coste por celda según el tamaño de la malla", color=TINTA,
                 fontsize=11, loc="left")
    fig.tight_layout()
    fig.savefig("figuras/fig12_coste_por_celda.png", facecolor="white")
    plt.close(fig)

    print("Generadas figuras/fig10_tiempo_debil.png, fig11_eficiencia_debil_fuerte.png "
          "y fig12_coste_por_celda.png")


if __name__ == "__main__":
    main()
