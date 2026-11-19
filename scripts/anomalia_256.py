"""Experimento de la anomalia de N >= 255 (ejercicio 3, Tabla 13).

1. Seis ejecuciones identicas de termo_ej1.c con N = 250, 255, 256, 257 y 264
   (4800 pasos): con N >= 255 los tiempos son bimodales.
2. termo_ej3_desplazado.c con N = 256 y el buffer 'nueva' desplazado 0, 64,
   1024 y 2048 bytes: al romper el alineamiento los tiempos se estabilizan.
3. Mallas grandes (N = 512 y 2048, 300 pasos) con desplazamiento 0 y 1024:
   el efecto no aparece.

Uso (desde la carpeta del repositorio):
    python scripts/anomalia_256.py
Guarda en resultados/ ej3_anomalia_256_<fecha>.txt
"""
import datetime
import os
import re
import subprocess

EXT = ".exe" if os.name == "nt" else ""
SEC = "termo_secuencial" + EXT
DESP = "termo_ej3_desplazado" + EXT
COMPILAR = [
    ["gcc", "-Wall", "-Wextra", "-O2", "-std=c11", "termo_ej1.c", "-o", SEC, "-lm"],
    ["gcc", "-Wall", "-Wextra", "-O2", "-std=c11", "termo_ej3_desplazado.c",
     "-o", DESP, "-lm"],
]


def tiempo(orden):
    salida = subprocess.run([os.path.abspath(orden[0])] + orden[1:],
                            capture_output=True, text=True, check=True).stdout
    return re.search(r"Tiempo=([0-9.]+)", salida).group(1)


def fila(etiqueta, orden, veces, f):
    t = [tiempo(orden) for _ in range(veces)]
    linea = f"{etiqueta}: " + " ".join(t)
    print(linea, flush=True)
    f.write(linea + "\n")


def main():
    for orden in COMPILAR:
        subprocess.run(orden, check=True)
    os.makedirs("resultados", exist_ok=True)
    ruta = f"resultados/ej3_anomalia_256_{datetime.datetime.now():%Y%m%d_%H%M}.txt"
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(f"# {datetime.datetime.now():%Y-%m-%d %H:%M}  Anomalia de la malla pequena\n")
        f.write("# " + " && ".join(" ".join(o) for o in COMPILAR) + "\n")
        f.write("# 1) termo_secuencial N 4800 0 fijo, 6 ejecuciones identicas (Tiempo en s)\n")
        for n in ("250", "255", "256", "257", "264"):
            fila(f"N={n}", [SEC, n, "4800", "0", "fijo"], 6, f)
        f.write("# 2) termo_ej3_desplazado 256 4800 0 fijo DESPLAZAMIENTO, 6 ejecuciones\n")
        for d in ("0", "64", "1024", "2048"):
            fila(f"N=256 desplazamiento={d}", [DESP, "256", "4800", "0", "fijo", d], 6, f)
        f.write("# 3) mallas grandes, 300 pasos, desplazamiento 0 frente a 1024, 3 ejecuciones\n")
        for n in ("512", "2048"):
            for d in ("0", "1024"):
                fila(f"N={n} desplazamiento={d}", [DESP, n, "300", "0", "fijo", d], 3, f)
    print(f"\nGuardado en {ruta}")


if __name__ == "__main__":
    main()
