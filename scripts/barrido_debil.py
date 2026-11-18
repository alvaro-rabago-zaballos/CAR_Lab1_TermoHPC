"""Barrido de escalabilidad debil (ejercicio 4).

La malla crece con los hilos como N(p) = N1 * sqrt(p), redondeado al entero mas
proximo, con el numero de pasos fijo: cada hilo conserva el mismo numero de
celdas. Para cada p se mide:
  - la version paralela (termo_ej2.c) con p hilos y malla N(p);
  - la version secuencial (termo_ej1.c) con la misma malla N(p), para saber
    cuanto cuesta esa malla sin paralelismo y comprobar si el tamano de la
    malla (hasta ~400 MB) cambia el coste por celda.
Cada punto se repite REPS veces y se toma el minimo.

Uso (desde la carpeta del repositorio):
    python scripts/barrido_debil.py [N1] [PASOS] [REPS]
Por defecto: N1=1024, PASOS=300, REPS=4.

Guarda en resultados/ ej4_debil_<fecha>.txt (bruto) y .csv (tabla).
"""
import csv
import datetime
import math
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from barrido import COMPILAR, HILOS, PAR, SEC, ejecutar  # noqa: E402


def main():
    n1 = int(sys.argv[1]) if len(sys.argv) > 1 else 1024
    pasos = sys.argv[2] if len(sys.argv) > 2 else "300"
    reps = int(sys.argv[3]) if len(sys.argv) > 3 else 4

    for orden in COMPILAR:
        subprocess.run(orden, check=True)

    os.makedirs("resultados", exist_ok=True)
    marca = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    base = f"resultados/ej4_debil_{marca}"

    filas = []
    with open(base + ".txt", "w", encoding="utf-8") as bruto:
        bruto.write(f"# {datetime.datetime.now():%Y-%m-%d %H:%M}  N(p)=round({n1}*sqrt(p)) "
                    f"pasos={pasos} repeticiones={reps} criterio=minimo\n")
        bruto.write("# " + " && ".join(" ".join(o) for o in COMPILAR) + "\n")

        for p in HILOS:
            n = str(round(n1 * math.sqrt(p)))

            t_par = []
            for _ in range(reps):
                d = ejecutar([PAR, n, pasos, "0", "fijo", str(p)], bruto)
                if int(d["Hilos"]) != p:
                    sys.exit(f"Se pidieron {p} hilos y hubo {d['Hilos']}: fila invalida")
                t_par.append(float(d["Tiempo"]))

            t_sec = [float(ejecutar([SEC, n, pasos, "0", "fijo"], bruto)["Tiempo"])
                     for _ in range(reps)]

            filas.append((p, int(n), min(t_par), min(t_sec)))
            print(f"  {p:2d} hilos  N={n:>5}: paralelo {min(t_par):.4f} s   "
                  f"secuencial {min(t_sec):.4f} s", flush=True)

    t1_par = filas[0][2]
    t1_sec = filas[0][3]
    with open(base + ".csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["hilos", "N", "celdas_por_hilo", "memoria_MB", "tiempo_par_s",
                    "eficiencia_debil_rel", "eficiencia_debil_abs", "tiempo_sec_s",
                    "ns_celda_paso_sec", "speedup_mismo_N"])
        for p, n, tp, ts in filas:
            w.writerow([p, n, f"{n * n / p:.0f}", f"{2 * n * n * 8 / 1e6:.1f}",
                        f"{tp:.6f}", f"{t1_par / tp:.3f}", f"{t1_sec / tp:.3f}",
                        f"{ts:.6f}", f"{ts / (n * n * int(pasos)) * 1e9:.3f}",
                        f"{ts / tp:.3f}"])

    print(f"\nPasos={pasos}  T1 (paralelo, 1 hilo, N={n1}) = {t1_par:.4f} s   "
          f"T1 (secuencial) = {t1_sec:.4f} s")
    print(f"{'hilos':>5} {'N':>5} {'Tp (s)':>8} {'efic. debil':>11} {'ns/celda sec':>12}")
    for p, n, tp, ts in filas:
        print(f"{p:5d} {n:5d} {tp:8.4f} {100 * t1_par / tp:10.1f}% "
              f"{ts / (n * n * int(pasos)) * 1e9:12.3f}")
    print(f"\nGuardado en {base}.txt y {base}.csv")


if __name__ == "__main__":
    main()
