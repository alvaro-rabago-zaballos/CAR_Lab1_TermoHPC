"""Barrido de escalabilidad fuerte (ejercicio 3), reutilizable en los ejercicios 4 y 5.

Compila las dos versiones con las ordenes de la memoria, mide T1 con la version
secuencial (termo_ej1.c, sin -fopenmp) y la paralela (termo_ej2.c) con
1, 2, 4, 8, 12, 16, 20 y 24 hilos. Cada punto se repite REPS veces y se toma el
minimo. Comprueba que los hilos reales coinciden con los pedidos y que el
checksum es el mismo en todas las ejecuciones.

Uso (desde la carpeta del repositorio):
    python scripts/barrido.py N PASOS [REPS] [ETIQUETA]
Ejemplo:
    python scripts/barrido.py 2048 300 4 fuerte_2048

Guarda en resultados/:
    ej3_<etiqueta>_<fecha>.txt  salida en bruto de todas las ejecuciones
    ej3_<etiqueta>_<fecha>.csv  tabla final (hilos, tiempo, speedup, eficiencia)
"""
import csv
import datetime
import os
import re
import subprocess
import sys

HILOS = [1, 2, 4, 8, 12, 16, 20, 24]
SEC = "termo_secuencial.exe" if os.name == "nt" else "./termo_secuencial"
PAR = "termo.exe" if os.name == "nt" else "./termo"
COMPILAR = [
    ["gcc", "-Wall", "-Wextra", "-O2", "termo_ej1.c", "-o", SEC, "-lm"],
    ["gcc", "-Wall", "-Wextra", "-O2", "-std=c11", "-fopenmp", "termo_ej2.c",
     "-o", PAR, "-lm"],
]
CLAVE = re.compile(r"(\w+)=(\S+)")


def ejecutar(orden, bruto):
    ejecutable = [os.path.abspath(orden[0])] + orden[1:]
    salida = subprocess.run(ejecutable, capture_output=True, text=True,
                            check=True).stdout
    linea = salida.strip().splitlines()[-1]
    bruto.write(" ".join(orden) + "\n" + linea + "\n")
    datos = dict(CLAVE.findall(linea))
    for comp in ("Bordes", "Monotono", "Rango"):
        if datos.get(comp) != "OK":
            sys.exit(f"Fallo de comprobacion fisica en: {linea}")
    return datos


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    n, pasos = sys.argv[1], sys.argv[2]
    reps = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    etiqueta = sys.argv[4] if len(sys.argv) > 4 else f"fuerte_{n}"

    for orden in COMPILAR:
        subprocess.run(orden, check=True)

    os.makedirs("resultados", exist_ok=True)
    marca = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    base = f"resultados/ej3_{etiqueta}_{marca}"

    with open(base + ".txt", "w", encoding="utf-8") as bruto:
        bruto.write(f"# {datetime.datetime.now():%Y-%m-%d %H:%M}  N={n} pasos={pasos} "
                    f"repeticiones={reps} criterio=minimo\n")
        bruto.write("# " + " && ".join(" ".join(o) for o in COMPILAR) + "\n")

        # Referencia secuencial: T1 para el speedup absoluto.
        tiempos = [float(ejecutar([SEC, n, pasos, "0", "fijo"], bruto)["Tiempo"])
                   for _ in range(reps)]
        t_sec = min(tiempos)
        checksum_ref = None

        filas = []
        for p in HILOS:
            tiempos = []
            for _ in range(reps):
                d = ejecutar([PAR, n, pasos, "0", "fijo", str(p)], bruto)
                if int(d["Hilos"]) != p:
                    sys.exit(f"Se pidieron {p} hilos y hubo {d['Hilos']}: fila invalida")
                if checksum_ref is None:
                    checksum_ref = d["Checksum"]
                elif d["Checksum"] != checksum_ref:
                    bruto.write(f"# aviso: checksum {d['Checksum']} != {checksum_ref}\n")
                tiempos.append(float(d["Tiempo"]))
            filas.append((p, min(tiempos)))
            print(f"  {p:2d} hilos: {min(tiempos):.6f} s", flush=True)

    t1_par = filas[0][1]
    with open(base + ".csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["hilos", "tiempo_s", "tiempo_paso_ms", "speedup_abs",
                    "eficiencia_abs", "speedup_rel"])
        w.writerow(["sec", f"{t_sec:.6f}", f"{t_sec / int(pasos) * 1e3:.4f}",
                    "1.000", "1.000", ""])
        for p, t in filas:
            w.writerow([p, f"{t:.6f}", f"{t / int(pasos) * 1e3:.4f}",
                        f"{t_sec / t:.3f}", f"{t_sec / t / p:.3f}",
                        f"{t1_par / t:.3f}"])

    print(f"\nN={n} pasos={pasos}  T1 secuencial={t_sec:.6f} s")
    print(f"{'hilos':>5} {'tiempo (s)':>11} {'speedup':>8} {'eficiencia':>10}")
    for p, t in filas:
        print(f"{p:5d} {t:11.6f} {t_sec / t:8.2f} {100 * t_sec / t / p:9.1f}%")
    print(f"\nGuardado en {base}.txt y {base}.csv")


if __name__ == "__main__":
    main()
