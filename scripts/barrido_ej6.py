"""Medida de las variantes del ejercicio 6 (optimizacion guiada por medicion).

Variantes (cada una cambia UNA cosa respecto de la anterior):
    base  termo_ej2.c      version del ejercicio 2
    it1   termo_ej6_it1.c  residuo fusionado con el paso de Jacobi
    it2   termo_ej6_it2.c  + schedule(dynamic,16)
    it3   termo_ej6_it3.c  + una sola region paralela para el bucle temporal

Para cada variante:
  1. verificacion completa (modo 'verificar', 1..24 hilos) frente a la
     referencia secuencial; una variante que no verifica aborta el script;
  2. tiempo con la configuracion principal (N=2048, 300 pasos, 12 hilos),
     REPS repeticiones INTERCALADAS entre variantes, minimo;
  3. barrido de 1 a 24 hilos (4 repeticiones intercaladas, minimo);
  4. malla pequena (N=250, 20133 pasos) con 4 y 12 hilos (3 repeticiones).
Se dan dos speedups:
  - frente a la secuencial del ejercicio 1 (termo_ej1.c, dos pasadas por paso);
  - frente a la MEJOR secuencial (apartado V.B del enunciado): termo_ej6_it1.c
    compilado SIN -fopenmp, que tiene el residuo fusionado (una pasada).
Las dos secuenciales se miden intercaladas con las variantes.

Uso (desde la carpeta del repositorio):
    python scripts/barrido_ej6.py [REPS]
Guarda en resultados/ ej6_variantes_<fecha>.txt (bruto) y .csv (tablas).
"""
import csv
import datetime
import os
import re
import subprocess
import sys

EXT = ".exe" if os.name == "nt" else ""
VARIANTES = [
    ("base", "termo_ej2.c"),
    ("it1", "termo_ej6_it1.c"),
    ("it2", "termo_ej6_it2.c"),
    ("it3", "termo_ej6_it3.c"),
]
SEC = "termo_secuencial" + EXT
SEC_FUS = "termo_secuencial_fusionada" + EXT
HILOS = [1, 2, 4, 8, 12, 16, 20, 24]
CLAVE = re.compile(r"(\w+)=(\S+)")


def exe(nombre):
    return f"termo_v_{nombre}{EXT}"


def correr(orden, bruto):
    ejecutable = [os.path.abspath(orden[0])] + orden[1:]
    salida = subprocess.run(ejecutable, capture_output=True, text=True,
                            check=True).stdout
    bruto.write(" ".join(orden) + "\n" + salida.strip() + "\n")
    return salida


def tiempo(orden, bruto):
    d = dict(CLAVE.findall(correr(orden, bruto)))
    if not all(d[c] == "OK" for c in ("Bordes", "Monotono", "Rango")):
        sys.exit(f"Fallo de comprobacion fisica: {' '.join(orden)}")
    if len(orden) > 5 and d["Hilos"] != orden[5]:
        sys.exit(f"Hilos reales {d['Hilos']} != pedidos {orden[5]}")
    return float(d["Tiempo"])


def main():
    reps = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    compilar = [["gcc", "-Wall", "-Wextra", "-O2", "-std=c11", "termo_ej1.c", "-o", SEC, "-lm"],
                ["gcc", "-Wall", "-Wextra", "-Wno-unknown-pragmas", "-O2", "-std=c11",
                 "termo_ej6_it1.c", "-o", SEC_FUS, "-lm"]]
    compilar += [["gcc", "-Wall", "-Wextra", "-O2", "-std=c11", "-fopenmp", f,
                  "-o", exe(v), "-lm"] for v, f in VARIANTES]
    for orden in compilar:
        subprocess.run(orden, check=True)

    os.makedirs("resultados", exist_ok=True)
    marca = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    base = f"resultados/ej6_variantes_{marca}"
    nombres = [v for v, _ in VARIANTES]

    with open(base + ".txt", "w", encoding="utf-8") as bruto:
        bruto.write(f"# {datetime.datetime.now():%Y-%m-%d %H:%M}  repeticiones={reps} "
                    "(intercaladas) criterio=minimo\n")
        bruto.write("# " + " && ".join(" ".join(o) for o in compilar) + "\n")

        # 1. Verificacion
        verif = {}
        for v in nombres:
            salida = correr([exe(v), "verificar", "2048", "300"], bruto)
            verif[v] = "PASA" if "Verificacion global: PASA" in salida else "FALLA"
            if verif[v] != "PASA":
                sys.exit(f"La variante {v} NO verifica: no se mide")
        print("  verificacion: todas PASA", flush=True)

        # 2. Configuracion principal. La secuencial se intercala con las
        #    variantes para que todas se midan en las mismas condiciones
        #    termicas (el portatil pierde turbo tras las rafagas multihilo).
        secuencial = []
        secuencial_fus = []
        principal = {v: [] for v in nombres}
        for _ in range(reps):
            secuencial.append(tiempo([SEC, "2048", "300", "0", "fijo"], bruto))
            secuencial_fus.append(tiempo([SEC_FUS, "2048", "300", "0", "fijo"], bruto))
            for v in nombres:
                principal[v].append(tiempo([exe(v), "2048", "300", "0", "fijo", "12"], bruto))
        t_sec = min(secuencial)
        t_fus = min(secuencial_fus)
        print("  configuracion principal hecha", flush=True)

        # 3. Barrido de hilos
        barrido = {(v, h): [] for v in nombres for h in HILOS}
        for _ in range(4):
            for h in HILOS:
                for v in nombres:
                    barrido[(v, h)].append(
                        tiempo([exe(v), "2048", "300", "0", "fijo", str(h)], bruto))
        print("  barrido de hilos hecho", flush=True)

        # 4. Malla pequena
        pequena = {(v, h): [] for v in nombres for h in (4, 12)}
        for _ in range(3):
            for h in (4, 12):
                for v in nombres:
                    pequena[(v, h)].append(
                        tiempo([exe(v), "250", "20133", "0", "fijo", str(h)], bruto))
        print("  malla pequena hecha", flush=True)

    bytes_paso = 16 * 2046 ** 2
    with open(base + ".csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["# configuracion principal: N=2048, 300 pasos, 12 hilos; "
                    f"T1 secuencial ej1={t_sec:.6f}; "
                    f"T1 mejor secuencial (fusionada)={t_fus:.6f}"])
        w.writerow(["variante", "tiempo_s", "speedup_abs", "speedup_vs_mejor_sec",
                    "mejora_vs_anterior_pct",
                    "mejora_vs_base_pct", "GBs_modelo_16B", "verificacion"])
        anterior = None
        t_base = min(principal["base"])
        for v in nombres:
            t = min(principal[v])
            w.writerow([v, f"{t:.6f}", f"{t_sec / t:.3f}", f"{t_fus / t:.3f}",
                        "" if anterior is None else f"{(t / anterior - 1) * 100:+.1f}",
                        f"{(t / t_base - 1) * 100:+.1f}",
                        f"{bytes_paso / (t / 300) / 1e9:.1f}", verif[v]])
            anterior = t
        w.writerow([])
        w.writerow(["# barrido de hilos: speedup absoluto"])
        w.writerow(["hilos"] + nombres)
        for h in HILOS:
            w.writerow([h] + [f"{t_sec / min(barrido[(v, h)]):.3f}" for v in nombres])
        w.writerow([])
        w.writerow(["# barrido de hilos: speedup frente a la mejor secuencial (fusionada)"])
        w.writerow(["hilos"] + nombres)
        for h in HILOS:
            w.writerow([h] + [f"{t_fus / min(barrido[(v, h)]):.3f}" for v in nombres])
        w.writerow([])
        w.writerow(["# malla pequena N=250, 20133 pasos: tiempo minimo (s)"])
        w.writerow(["hilos"] + nombres)
        for h in (4, 12):
            w.writerow([h] + [f"{min(pequena[(v, h)]):.6f}" for v in nombres])

    print(f"\nT1 secuencial ej1 = {t_sec:.4f} s   "
          f"T1 mejor secuencial (fusionada) = {t_fus:.4f} s")
    print(f"{'variante':<8} {'tiempo':>8} {'S(ej1)':>7} {'S(mejor)':>8} "
          f"{'vs anterior':>11} {'GB/s(16B)':>10}")
    anterior = None
    for v in nombres:
        t = min(principal[v])
        mejora = "" if anterior is None else f"{(t / anterior - 1) * 100:+.1f}%"
        print(f"{v:<8} {t:8.4f} {t_sec / t:7.2f} {t_fus / t:8.2f} {mejora:>11} "
              f"{bytes_paso / (t / 300) / 1e9:10.1f}")
        anterior = t
    print(f"\nGuardado en {base}.txt y {base}.csv")


if __name__ == "__main__":
    main()
