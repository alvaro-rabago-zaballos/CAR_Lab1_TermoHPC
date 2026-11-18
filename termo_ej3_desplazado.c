// TermoHPC I - Ejercicio 3: experimento de la anomalia de N >= 255 (Tabla 13).
//
// Es termo_ej1.c con UN unico cambio: el buffer 'nueva' se coloca desplazado
// 'desplazamiento' bytes respecto al bloque que devuelve malloc, para romper el
// alineamiento de 64 KB que comparten los dos buffers cuando malloc los pide
// directamente al sistema operativo (buffers de mas de ~508 KB).
// El desplazamiento (multiplo de 8, menor que 4096) es el 5.o argumento:
//       termo_ej3_desplazado.exe N pasos tolerancia modo desplazamiento
// Con desplazamiento 0 el programa se comporta igual que termo_ej1.c.
//
// Compilacion:
//       gcc -Wall -Wextra -O2 -std=c11 termo_ej3_desplazado.c -o termo_ej3_desplazado.exe -lm

// Necesario para clock_gettime/CLOCK_MONOTONIC al compilar en Linux con -std=c11.
#define _POSIX_C_SOURCE 199309L

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

// Reloj de pared de alta resolucion que no depende de OpenMP, para que la
// version secuencial de referencia se pueda compilar SIN -fopenmp.
// En Windows (MinGW) omp_get_wtime() solo tiene resolucion de ~1 ms, por eso
// se usa QueryPerformanceCounter; en Linux, clock_gettime(CLOCK_MONOTONIC).
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

// Bytes que se desplaza el buffer 'nueva' (5.o argumento de la linea de ordenes).
static size_t desplazamiento = 0;

// Inicializa la malla.
void inicializar(double *malla, int n) {

    size_t total = (size_t)n * n;

    for (size_t i = 0; i < total; i++) {
        malla[i] = 0.0;
    }

    for (int j = 0; j < n; j++) {
        malla[j] = 100.0;
    }
}

// Calcula un paso de Jacobi.
void paso_jacobi(const double *actual, double *nueva, int n) {

    for (int i = 1; i < n - 1; i++) {
        for (int j = 1; j < n - 1; j++) {

            size_t pos = (size_t)i * n + j;

            nueva[pos] = (actual[pos - n] +
                          actual[pos + n] +
                          actual[pos - 1] +
                          actual[pos + 1]) / 4.0;
        }
    }
}

// Calcula el mayor cambio de temperatura.
double calcular_residuo(const double *actual, const double *nueva, int n) {

    double residuo = 0.0;

    for (int i = 1; i < n - 1; i++) {
        for (int j = 1; j < n - 1; j++) {

            size_t pos = (size_t)i * n + j;
            double cambio = fabs(nueva[pos] - actual[pos]);

            if (cambio > residuo) {
                residuo = cambio;
            }
        }
    }

    return residuo;
}

// Suma las temperaturas interiores.
double sumar_temperaturas_interiores(const double *malla, int n) {

    double suma = 0.0;

    for (int i = 1; i < n - 1; i++) {
        for (int j = 1; j < n - 1; j++) {
            suma += malla[(size_t)i * n + j];
        }
    }

    return suma;
}

// Comprueba los bordes.
int comprobar_bordes(const double *malla, int n) {

    for (int j = 0; j < n; j++) {
        if (malla[j] != 100.0 ||
            malla[(size_t)(n - 1) * n + j] != 0.0) {
            return 0;
        }
    }

    for (int i = 1; i < n - 1; i++) {
        if (malla[(size_t)i * n] != 0.0 ||
            malla[(size_t)i * n + n - 1] != 0.0) {
            return 0;
        }
    }

    return 1;
}

// Comprueba las temperaturas interiores.
int comprobar_temperaturas(const double *malla, int n) {

    for (int i = 1; i < n - 1; i++) {
        for (int j = 1; j < n - 1; j++) {

            double t = malla[(size_t)i * n + j];

            if (!(t >= 0.0 && t <= 100.0)) {
                return 0;
            }
        }
    }

    return 1;
}

// Ejecuta la simulacion y devuelve el tiempo empleado. Si checksum_salida no
// es NULL, guarda en el el checksum final (para imprimirlo tambien al medir).
double ejecutar_simulacion(int n, int max_pasos, double tolerancia,
                          int modo_convergencia, int mostrar,
                          double *checksum_salida) {

    size_t elementos = (size_t)n * n;

    // Evitamos reservar un tamano que desborde size_t.
    if ((size_t)n > ((size_t)-1 / sizeof(double)) / (size_t)n) {
        fprintf(stderr, "Error: tamano de malla excesivo.\n");
        return -1.0;
    }

    double *actual = malloc(elementos * sizeof(double));
    // Unico cambio: 'nueva' empieza 'desplazamiento' bytes despues del inicio
    // del bloque reservado (se reservan 4096 bytes de margen).
    char *bloque_nueva = malloc(elementos * sizeof(double) + 4096);
    double *nueva = bloque_nueva == NULL ? NULL
                                         : (double *)(bloque_nueva + desplazamiento);

    if (actual == NULL || nueva == NULL) {
        fprintf(stderr, "Error al reservar memoria.\n");
        free(actual);
        free(bloque_nueva);
        return -1.0;
    }

    // Los punteros se intercambian en cada paso: se guarda el bloque original
    // de 'actual' para liberarlo bien al final.
    double *bloque_actual = actual;

    // Inicializacion fuera del cronometro.
    inicializar(actual, n);
    inicializar(nueva, n);

    int pasos_ejecutados = 0;
    double residuo = 0.0;
    double residuo_anterior = 0.0;
    int residuo_decreciente = 1;

    // Comienza el cronometraje.
    double inicio = reloj();

    for (int paso = 1; paso <= max_pasos; paso++) {

        paso_jacobi(actual, nueva, n);

        residuo = calcular_residuo(actual, nueva, n);

        if (paso > 1 && residuo > residuo_anterior) {
            residuo_decreciente = 0;
        }

        residuo_anterior = residuo;

        // Intercambiamos los punteros.
        double *temporal = actual;
        actual = nueva;
        nueva = temporal;

        pasos_ejecutados = paso;

        if (modo_convergencia && residuo < tolerancia) {
            break;
        }
    }

    // Finaliza el cronometraje.
    double tiempo_total = reloj() - inicio;

    // Comprobaciones fuera del cronometro.
    double checksum = sumar_temperaturas_interiores(actual, n);
    int bordes_correctos = comprobar_bordes(actual, n);
    int temperaturas_correctas = comprobar_temperaturas(actual, n);

    if (mostrar) {
        // Resultados principales en una sola linea.
        // Formato clave=valor separado por espacios, facil de procesar
        // con un script (una ejecucion = una linea).
        printf("N=%d Pasos=%d Residuo=%.6e Checksum=%.6f Tiempo=%.6f "
               "Bordes=%s Monotono=%s Rango=%s\n",
               n, pasos_ejecutados, residuo, checksum, tiempo_total,
               bordes_correctos ? "OK" : "FALLO",
               residuo_decreciente ? "OK" : "FALLO",
               temperaturas_correctas ? "OK" : "FALLO");
    }

    if (checksum_salida != NULL) {
        *checksum_salida = checksum;
    }

    free(bloque_actual);
    free(bloque_nueva);

    if (!bordes_correctos || !temperaturas_correctas ||
        !residuo_decreciente || !isfinite(checksum)) {
        fprintf(stderr, "Error: la simulacion no supera las comprobaciones.\n");
        return -1.0;
    }

    return tiempo_total;
}

int main(int argc, char *argv[]) {

    // Modo de medicion del ejercicio 1.
    if (argc == 2 && strcmp(argv[1], "medir") == 0) {

        int tamanos[] = {512, 1024, 2048, 4096};
        int pasos = 300;
        int repeticiones = 4;

        printf("\nMEDICIONES SECUENCIALES (300 pasos, 4 repeticiones, criterio: minimo)\n");
        printf("N     Rep1 (s)     Rep2 (s)     Rep3 (s)     Rep4 (s)     Minimo (s)    Checksum\n");
        printf("------------------------------------------------------------------------------------\n");

        for (int i = 0; i < 4; i++) {

            double tiempos[4];
            double minimo = 0.0;
            double checksum = 0.0;   // se imprime: evita que -O2 elimine el calculo

            for (int r = 0; r < repeticiones; r++) {

                tiempos[r] = ejecutar_simulacion(
                    tamanos[i], pasos, 0.0, 0, 0, &checksum
                );

                if (tiempos[r] < 0.0) {
                    return 1;
                }

                if (r == 0 || tiempos[r] < minimo) {
                    minimo = tiempos[r];
                }
            }

            printf("%-5d %.9f  %.9f  %.9f  %.9f  %.9f  %.6f\n",
                   tamanos[i], tiempos[0], tiempos[1],
                   tiempos[2], tiempos[3], minimo, checksum);

            fflush(stdout);
        }

        return 0;
    }

    // Modos normales de la simulacion.
    if (argc != 6) {
        printf("Uso: termo_ej3_desplazado N pasos tolerancia modo desplazamiento\n");
        printf("   o: termo medir\n");
        return 1;
    }

    int n = atoi(argv[1]);
    int max_pasos = atoi(argv[2]);
    double tolerancia = atof(argv[3]);

    long desp = atol(argv[5]);
    if (desp < 0 || desp >= 4096 || desp % 8 != 0) {
        printf("Error: el desplazamiento debe ser multiplo de 8 y menor que 4096.\n");
        return 1;
    }
    desplazamiento = (size_t)desp;

    int modo_fijo = strcmp(argv[4], "fijo") == 0;
    int modo_convergencia = strcmp(argv[4], "convergencia") == 0;

    if (n < 3 || max_pasos < 1 ||
        (!modo_fijo && !modo_convergencia) ||
        (modo_convergencia && !(tolerancia > 0.0))) {

        printf("Error: parametros incorrectos.\n");
        return 1;
    }

    double tiempo = ejecutar_simulacion(
        n, max_pasos, tolerancia, modo_convergencia, 1, NULL
    );

    return tiempo < 0.0 ? 1 : 0;
}
