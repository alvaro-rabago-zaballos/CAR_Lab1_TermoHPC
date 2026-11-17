"""Genera las figuras 3 y 4 del Ejercicio 1 a partir de la salida de
`termo_secuencial.exe medir` guardada en resultados/.

Uso:  python scripts/figuras_ej1.py resultados/ej1_secuencial_XXXX.txt
Salida: figuras/fig3_tiempo_vs_N.png y figuras/fig4_coste_normalizado.png
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

PASOS = 300
L3_MIB = 24  # cache L3 del i7-13620H

AZUL = "#2a78d6"
TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
REJILLA = "#e4e3df"


def coma(x, decimales):
    return f"{x:.{decimales}f}".replace(".", ",")


def leer(ruta):
    filas = []
    with open(ruta, encoding="utf-8", errors="replace") as f:
        for linea in f:
            partes = linea.split()
            if len(partes) == 6 and partes[0].isdigit():
                filas.append((int(partes[0]), float(partes[5])))
    return filas


def estilo(ax):
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color(TINTA_2)
    ax.tick_params(colors=TINTA_2, labelsize=10)
    ax.grid(True, which="major", color=REJILLA, linewidth=0.8)
    ax.set_axisbelow(True)


def main():
    ruta = sys.argv[1]
    datos = leer(ruta)
    ns = [n for n, _ in datos]
    ts = [t for _, t in datos]
    os.makedirs("figuras", exist_ok=True)
    plt.rcParams["font.family"] = "DejaVu Sans"

    # ---------- Figura 3: tiempo frente a N (escala log-log) ----------
    fig, ax = plt.subplots(figsize=(7, 4.2), dpi=200)
    estilo(ax)
    ref = [ts[0] * (n / ns[0]) ** 2 for n in ns]
    ax.plot(ns, ref, linestyle="--", color=TINTA_2, linewidth=1.2)
    ax.plot(ns, ts, color=AZUL, linewidth=2, marker="o", markersize=7)
    for n, t in zip(ns, ts):
        ax.annotate(f"{coma(t, 3)} s", (n, t), textcoords="offset points",
                    xytext=(-8, 10), ha="right", fontsize=9, color=TINTA)
    ax.annotate("referencia ∝ N² (desde N = 512)", (ns[-2], ref[-2]),
                textcoords="offset points", xytext=(8, -10), ha="left",
                va="top", fontsize=9, color=TINTA_2)
    ax.set_xscale("log", base=2)
    ax.set_yscale("log")
    ax.set_xticks(ns)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{int(v)}"))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: coma(v, 1 if v < 1 else 0)))
    ax.minorticks_off()
    ax.set_xlabel("Tamaño de malla N (celdas por lado)", color=TINTA)
    ax.set_ylabel("Tiempo mínimo (s), escala log", color=TINTA)
    ax.set_title(f"Tiempo secuencial frente a N ({PASOS} pasos, mínimo de 4)",
                 color=TINTA, fontsize=11, loc="left")
    fig.tight_layout()
    fig.savefig("figuras/fig3_tiempo_vs_N.png", facecolor="white")
    plt.close(fig)

    # ---------- Figura 4: coste por celda y paso ----------
    coste = [t / (n * n * PASOS) * 1e9 for n, t in datos]
    mem = [2 * n * n * 8 / 2**20 for n in ns]
    fig, ax = plt.subplots(figsize=(7, 4.2), dpi=200)
    estilo(ax)
    x = list(range(len(ns)))
    # frontera de la L3: entre el ultimo tamano que cabe y el primero que no
    cabe = [m <= L3_MIB for m in mem]
    if any(cabe) and not all(cabe):
        frontera = max(i for i, c in enumerate(cabe) if c) + 0.5
        ax.axvline(frontera, color=TINTA_2, linestyle="--", linewidth=1.2)
        ax.text(frontera - 0.06, 0.96, "← cabe en L3 (24 MB)", ha="right",
                va="top", fontsize=9, color=TINTA_2,
                transform=ax.get_xaxis_transform())
        ax.text(frontera + 0.06, 0.96, "no cabe: memoria principal →",
                ha="left", va="top", fontsize=9, color=TINTA_2,
                transform=ax.get_xaxis_transform())
    ax.bar(x, coste, width=0.55, color=AZUL)
    for i, c in enumerate(coste):
        ax.text(i, c + 0.03, f"{coma(c, 2)} ns", ha="center", va="bottom",
                fontsize=10, color=TINTA)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{n}\n({coma(m, 0)} MiB)" for n, m in zip(ns, mem)])
    ax.set_ylim(0, max(coste) * 1.3)
    ax.set_yticks([i * 0.5 for i in range(int(max(coste) * 1.3 / 0.5) + 1)])
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: coma(v, 1)))
    ax.grid(False, axis="x")
    ax.set_xlabel("Tamaño de malla N (memoria de los dos buffers)", color=TINTA)
    ax.set_ylabel("T / (N² · pasos)  (ns por celda y paso)", color=TINTA)
    ax.set_title("Coste normalizado por celda y paso", color=TINTA,
                 fontsize=11, loc="left")
    fig.tight_layout()
    fig.savefig("figuras/fig4_coste_normalizado.png", facecolor="white")
    plt.close(fig)
    print("Generadas figuras/fig3_tiempo_vs_N.png y figuras/fig4_coste_normalizado.png")


if __name__ == "__main__":
    main()
