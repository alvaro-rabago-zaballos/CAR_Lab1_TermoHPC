"""Comparacion de planificaciones (ejercicio 5).

Ejecuta termo_ej5.c (schedule(runtime)) con 12 hilos y la configuracion
principal (N=2048, 300 pasos) para cada planificacion, fijada con la variable
de entorno OMP_SCHEDULE. Comprueba en cada ejecucion que la planificacion
impresa por el programa (Planif=) es la pedida, y verifica el campo de cada
planificacion frente a la referencia secuencial (modo 'verificar').

Las repeticiones se intercalan (rep 1 de todas, rep 2 de todas...) para que
una deriva lenta del equipo no favorezca a ninguna planificacion. Se toma el
minimo de REPS.

Uso (desde la carpeta del repositorio):
    python scripts/barrido_planif.py [N] [PASOS] [HILOS] [REPS]
Por defecto: 2048 300 12 4.

Guarda en resultados/ ej5_planif_<fecha>.txt (bruto) y .csv (tabla).
"""
import csv
import datetime
import math
import os
import re
import subprocess
import sys

PLANIFICACIONES = [
    "static", "static,1", "static,4", "static,16", "static,64",
    "dynamic,1", "dynamic,4", "dynamic,16", "dynamic,64", "guided",
]
EXE = "termo_ej5.exe" if os.name == "nt" else "./termo_ej5"
SEC = "termo_secuencial.exe" if os.name == "nt" else "./termo_secuencial"
COMPILAR = [
    ["gcc", "-Wall", "-Wextra", "-O2", "termo_ej1.c", "-o", SEC, "-lm"],
    ["gcc", "-Wall", "-Wextra", "-O2", "-std=c11", "-fopenmp", "termo_ej5.c",
     "-o", EXE, "-lm"],
]
CLAVE = re.compile(r"(\w+)=(\S+)")


def correr(orden, planif, bruto):
    entorno = dict(os.environ)
    if planif is not None:
        entorno["OMP_SCHEDULE"] = planif
    ejecutable = [os.path.abspath(orden[0])] + orden[1:]
    salida = subprocess.run(ejecutable, capture_output=True, text=True,
                            check=True, env=entorno).stdout
    bruto.write(f"OMP_SCHEDULE={planif} " + " ".join(orden) + "\n" + salida.strip() + "\n")
    return salida


def esperado(planif):
    # Como lo imprime el programa: guided sin trozo -> guided,1
    return "guided,1" if planif == "guided" else planif


def main():
    n = sys.argv[1] if len(sys.argv) > 1 else "2048"
    pasos = sys.argv[2] if len(sys.argv) > 2 else "300"
    hilos = sys.argv[3] if len(sys.argv) > 3 else "12"
    reps = int(sys.argv[4]) if len(sys.argv) > 4 else 4

    for orden in COMPILAR:
        subprocess.run(orden, check=True)

    os.makedirs("resultados", exist_ok=True)
    marca = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    base = f"resultados/ej5_planif_{marca}"

    tiempos = {p: [] for p in PLANIFICACIONES}
    with open(base + ".txt", "w", encoding="utf-8") as bruto:
        bruto.write(f"# {datetime.datetime.now():%Y-%m-%d %H:%M}  N={n} pasos={pasos} "
                    f"hilos={hilos} repeticiones={reps} (intercaladas) criterio=minimo\n")
        bruto.write("# " + " && ".join(" ".join(o) for o in COMPILAR) + "\n")

        t_sec = min(float(dict(CLAVE.findall(
            correr([SEC, n, pasos, "0", "fijo"], None, bruto)))["Tiempo"])
            for _ in range(reps))

        for r in range(reps):
            for planif in PLANIFICACIONES:
                d = dict(CLAVE.findall(
                    correr([EXE, n, pasos, "0", "fijo", hilos], planif, bruto)))
                if d["Planif"] != esperado(planif):
                    sys.exit(f"Se pidio {planif} y el programa uso {d['Planif']}")
                if d["Hilos"] != hilos:
                    sys.exit(f"Se pidieron {hilos} hilos y hubo {d['Hilos']}")
                if not all(d[c] == "OK" for c in ("Bordes", "Monotono", "Rango")):
                    sys.exit(f"Fallo de comprobacion fisica con {planif}")
                tiempos[planif].append(float(d["Tiempo"]))
            print(f"  repeticion {r + 1}/{reps} hecha", flush=True)

        verif = {}
        for planif in PLANIFICACIONES:
            salida = correr([EXE, "verificar", n, pasos, hilos], planif, bruto)
            fila = [l for l in salida.splitlines() if l.startswith(hilos + " ")][0].split()
            verif[planif] = (float(fila[2]), float(fila[4]), fila[5])

    filas_interiores = int(n) - 2
    t_static = min(tiempos["static"])
    with open(base + ".csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["planificacion", "tiempo_s", "speedup_abs", "vs_static_pct",
                    "trozos_por_paso", "dif_max_campo", "dif_rel_checksum", "verificacion"])
        for planif in PLANIFICACIONES:
            t = min(tiempos[planif])
            trozo = int(planif.split(",")[1]) if "," in planif else 0
            if planif == "static":
                trozos = int(hilos)
            elif planif == "guided":
                trozos = ""
            else:
                trozos = math.ceil(filas_interiores / trozo)
            trozos_paso = 2 * trozos if trozos != "" else ""
            dmax, dchk, res = verif[planif]
            w.writerow([planif, f"{t:.6f}", f"{t_sec / t:.3f}",
                        f"{(t / t_static - 1) * 100:+.1f}", trozos_paso,
                        f"{dmax:.3e}", f"{dchk:.3e}", res])

    print(f"\nN={n} pasos={pasos} hilos={hilos}  T1 secuencial={t_sec:.4f} s")
    print(f"{'planificacion':<13} {'tiempo (s)':>10} {'speedup':>8} {'vs static':>9} "
          f"{'dif. campo':>10} verif.")
    for planif in PLANIFICACIONES:
        t = min(tiempos[planif])
        dmax, _, res = verif[planif]
        print(f"{planif:<13} {t:10.4f} {t_sec / t:8.2f} {(t / t_static - 1) * 100:+8.1f}% "
              f"{dmax:10.1e} {res}")
    print(f"\nGuardado en {base}.txt y {base}.csv")


if __name__ == "__main__":
    main()
