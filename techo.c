// TermoHPC I - Ejercicio 3: techos de la maquina.
//
// Tres experimentos independientes de termo_ej2.c:
//   calculo  -> techo de calculo (apartado IV.C): cada hilo hace EXACTAMENTE el
//               mismo bucle aritmetico, sin accesos a memoria. En una maquina
//               homogenea con nucleos libres el tiempo no cambiaria con los hilos.
//               Techo de speedup = p * T1 / Tp.
//   ancho    -> ancho de banda de memoria con el triad de STREAM (apartado V.G):
//               a[i] = b[i] + f*c[i] sobre vectores que no caben en ninguna cache.
//   barrera  -> coste de una barrera y de abrir/cerrar una region paralela,
//               para compararlo con el tiempo por paso de Jacobi.
//   reloj    -> resolucion de omp_get_wtime() (lo que declara omp_get_wtick()
//               y lo que se observa) frente a la del reloj propio reloj().
//
// Compilacion:
//   gcc -Wall -Wextra -O2 -std=c11 -fopenmp techo.c -o techo.exe -lm
// Uso:
//   techo.exe calculo | ancho | barrera | reloj

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <omp.h>

#ifdef _WIN32
#include <windows.h>
static double reloj(void) {
    static LARGE_INTEGER frecuencia;
    LARGE_INTEGER contador;
    if (frecuencia.QuadPart == 0) {
        QueryPerformanceFrequency(&frecuencia);
    }
    QueryPerformanceCounter(&contador);
    return (double)contador.QuadPart / (double)frecuencia.QuadPart;
}
#else
#include <time.h>
static double reloj(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return (double)t.tv_sec + (double)t.tv_nsec * 1e-9;
}
#endif

static const int RECUENTOS_HILOS[] = {1, 2, 4, 8, 12, 16, 20, 24};
#define NUM_RECUENTOS ((int)(sizeof(RECUENTOS_HILOS) / sizeof(RECUENTOS_HILOS[0])))
#define REPETICIONES 5

static int fijar_hilos(int hilos) {
    omp_set_dynamic(0);
    omp_set_num_threads(hilos);
    int reales = 0;
    #pragma omp parallel default(none) shared(reales)
    {
        #pragma omp single
        reales = omp_get_num_threads();
    }
    return reales;
}

// ---------------------------------------------------------------------------
// Techo de calculo
// ---------------------------------------------------------------------------

// Cadena de operaciones dependientes: cada iteracion necesita el resultado de
// la anterior, asi que el compilador no puede vectorizarla ni eliminarla, y no
// hay ningun acceso a memoria.
static double trabajo_aritmetico(long iteraciones, double semilla) {
    double x = semilla;
    for (long k = 0; k < iteraciones; k++) {
        x = x * 0.999999 + 0.000001;
    }
    return x;
}

static void modo_calculo(void) {

    long iteraciones = 150000000L;   // ~0,5 s con un hilo (sin const: ver nota en modo_ancho)
    double t1 = 0.0;
    double sumidero = 0.0;                 // evita que -O2 elimine el calculo

    printf("# TECHO DE CALCULO: %ld iteraciones por hilo, minimo de %d repeticiones\n",
           iteraciones, REPETICIONES);
    printf("hilos,reales,tiempo_s,techo_speedup\n");

    for (int k = 0; k < NUM_RECUENTOS; k++) {

        int p = RECUENTOS_HILOS[k];
        int reales = fijar_hilos(p);
        double mejor = 1e30;

        for (int r = 0; r < REPETICIONES; r++) {
            double suma = 0.0;
            double inicio = reloj();
            #pragma omp parallel default(none) shared(iteraciones) reduction(+ : suma)
            {
                suma += trabajo_aritmetico(iteraciones,
                                           1.0 + omp_get_thread_num() * 1e-9);
            }
            double t = reloj() - inicio;
            if (t < mejor) {
                mejor = t;
            }
            sumidero += suma;
        }

        if (p == 1) {
            t1 = mejor;
        }
        // Con p hilos se hace p veces el trabajo de un hilo.
        printf("%d,%d,%.6f,%.3f\n", p, reales, mejor, p * t1 / mejor);
        fflush(stdout);
    }

    printf("# comprobacion (ignorar): %.6f\n", sumidero);
}

// ---------------------------------------------------------------------------
// Ancho de banda: triad de STREAM
// ---------------------------------------------------------------------------

static void modo_ancho(void) {

    long n = 40000000L;   // 3 vectores x 320 MB = 960 MB
    // n y f no son const: GCC 8 trata las const como compartidas predeterminadas
    // y no deja nombrarlas en shared(), y GCC 9+ si lo exige con default(none).
    double *a = malloc(n * sizeof(double));
    double *b = malloc(n * sizeof(double));
    double *c = malloc(n * sizeof(double));
    if (a == NULL || b == NULL || c == NULL) {
        fprintf(stderr, "Error al reservar memoria.\n");
        free(a); free(b); free(c);
        return;
    }

    for (long i = 0; i < n; i++) {
        a[i] = 0.0;
        b[i] = 1.0;
        c[i] = 2.0;
    }

    double f = 3.0;
    double sumidero = 0.0;

    printf("# ANCHO DE BANDA (triad a=b+f*c): %ld double por vector, minimo de %d repeticiones\n",
           n, REPETICIONES);
    printf("# modelo 24 B: lee b y c, escribe a; modelo 32 B: ademas lee a antes de escribirla\n");
    printf("hilos,reales,tiempo_s,gbs_24B,gbs_32B\n");

    for (int k = 0; k < NUM_RECUENTOS; k++) {

        int p = RECUENTOS_HILOS[k];
        int reales = fijar_hilos(p);
        double mejor = 1e30;

        for (int r = 0; r < REPETICIONES; r++) {
            double inicio = reloj();
            #pragma omp parallel for default(none) shared(a, b, c, n, f) schedule(static)
            for (long i = 0; i < n; i++) {
                a[i] = b[i] + f * c[i];
            }
            double t = reloj() - inicio;
            if (t < mejor) {
                mejor = t;
            }
            sumidero += a[n / 2];
        }

        printf("%d,%d,%.6f,%.2f,%.2f\n", p, reales, mejor,
               24.0 * n / mejor / 1e9, 32.0 * n / mejor / 1e9);
        fflush(stdout);
    }

    printf("# comprobacion (ignorar): %.1f\n", sumidero);
    free(a); free(b); free(c);
}

// ---------------------------------------------------------------------------
// Coste de una barrera y de una region paralela
// ---------------------------------------------------------------------------

static void modo_barrera(void) {

    printf("# COSTE DE SINCRONIZACION, minimo de %d repeticiones\n", REPETICIONES);
    printf("# barrera_us: una '#pragma omp barrier' dentro de una region ya abierta\n");
    printf("# region_us: abrir y cerrar un '#pragma omp parallel for' (lo que hace termo_ej2 dos veces por paso)\n");
    printf("hilos,reales,barrera_us,region_us\n");

    double sumidero = 0.0;

    for (int k = 0; k < NUM_RECUENTOS; k++) {

        int p = RECUENTOS_HILOS[k];
        int reales = fijar_hilos(p);
        // Con mas hilos que procesadores logicos cada barrera es mucho mas
        // lenta, asi que se hacen menos vueltas para no eternizar la medida.
        int vueltas = p <= 16 ? 20000 : 500;
        double mejor_barrera = 1e30;
        double mejor_region = 1e30;

        for (int r = 0; r < REPETICIONES; r++) {

            double inicio = reloj();
            #pragma omp parallel default(none) shared(vueltas)
            {
                for (int v = 0; v < vueltas; v++) {
                    #pragma omp barrier
                }
            }
            double t = (reloj() - inicio) / vueltas;
            if (t < mejor_barrera) {
                mejor_barrera = t;
            }

            double suma = 0.0;
            inicio = reloj();
            for (int v = 0; v < vueltas; v++) {
                #pragma omp parallel for default(none) shared(p) reduction(+ : suma) schedule(static)
                for (int i = 0; i < p; i++) {
                    suma += 1.0;
                }
            }
            t = (reloj() - inicio) / vueltas;
            if (t < mejor_region) {
                mejor_region = t;
            }
            sumidero += suma;
        }

        printf("%d,%d,%.3f,%.3f\n", p, reales, mejor_barrera * 1e6, mejor_region * 1e6);
        fflush(stdout);
    }

    printf("# comprobacion (ignorar): %.0f\n", sumidero);
}

// ---------------------------------------------------------------------------
// Resolucion de los relojes
// ---------------------------------------------------------------------------

// Menor incremento distinto de cero que se observa leyendo el reloj seguido.
static double incremento_minimo(double (*leer)(void)) {
    double menor = 1e30;
    for (int k = 0; k < 200; k++) {
        double t0 = leer();
        double t1 = leer();
        while (t1 == t0) {
            t1 = leer();
        }
        if (t1 - t0 < menor) {
            menor = t1 - t0;
        }
    }
    return menor;
}

static double leer_omp(void) {
    return omp_get_wtime();
}

static void modo_reloj(void) {
    printf("# RESOLUCION DE LOS RELOJES (menor incremento observado en 200 intentos)\n");
    printf("reloj,resolucion_declarada_s,resolucion_observada_s\n");
    printf("omp_get_wtime,%.3e,%.3e\n", omp_get_wtick(), incremento_minimo(leer_omp));
    printf("reloj_propio,,%.3e\n", incremento_minimo(reloj));
}

int main(int argc, char *argv[]) {

    if (argc == 2 && strcmp(argv[1], "calculo") == 0) {
        modo_calculo();
    } else if (argc == 2 && strcmp(argv[1], "ancho") == 0) {
        modo_ancho();
    } else if (argc == 2 && strcmp(argv[1], "barrera") == 0) {
        modo_barrera();
    } else if (argc == 2 && strcmp(argv[1], "reloj") == 0) {
        modo_reloj();
    } else {
        printf("Uso: techo calculo | ancho | barrera | reloj\n");
        return 1;
    }
    return 0;
}
