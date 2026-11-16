
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

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

// Ejecuta la simulacion y devuelve el tiempo empleado.
double ejecutar_simulacion(int n, int max_pasos, double tolerancia,
                          int modo_convergencia, int mostrar) {

    size_t elementos = (size_t)n * n;

    // Evitamos reservar un tamano que desborde size_t.
    if ((size_t)n > ((size_t)-1 / sizeof(double)) / (size_t)n) {
        fprintf(stderr, "Error: tamano de malla excesivo.\n");
        return -1.0;
    }

    double *actual = malloc(elementos * sizeof(double));
    double *nueva = malloc(elementos * sizeof(double));

    if (actual == NULL || nueva == NULL) {
        fprintf(stderr, "Error al reservar memoria.\n");
        free(actual);
        free(nueva);
        return -1.0;
    }

    // Inicializacion fuera del cronometro.
    inicializar(actual, n);
    inicializar(nueva, n);

    int pasos_ejecutados = 0;
    double residuo = 0.0;
    double residuo_anterior = 0.0;
    int residuo_decreciente = 1;

    // Comienza el cronometraje.
    double inicio = omp_get_wtime();

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
    double tiempo_total = omp_get_wtime() - inicio;

    // Comprobaciones fuera del cronometro.
    double checksum = sumar_temperaturas_interiores(actual, n);
    int bordes_correctos = comprobar_bordes(actual, n);
    int temperaturas_correctas = comprobar_temperaturas(actual, n);

    if (mostrar) {
        // Resultados principales en una sola linea.
        printf("Pasos=%d Residuo=%.6f Checksum=%.6f Tiempo=%.9f\n",
               pasos_ejecutados, residuo, checksum, tiempo_total);

        printf("Bordes: %s\n",
               bordes_correctos ? "CORRECTOS" : "INCORRECTOS");

        printf("Residuo decreciente: %s\n",
               residuo_decreciente ? "CORRECTO" : "INCORRECTO");

        printf("Temperaturas entre 0 y 100: %s\n",
               temperaturas_correctas ? "CORRECTO" : "INCORRECTO");
    }

    free(actual);
    free(nueva);

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
        printf("N     Rep1 (s)     Rep2 (s)     Rep3 (s)     Rep4 (s)     Minimo (s)\n");
        printf("----------------------------------------------------------------------\n");

        for (int i = 0; i < 4; i++) {

            double tiempos[4];
            double minimo = 0.0;

            for (int r = 0; r < repeticiones; r++) {

                tiempos[r] = ejecutar_simulacion(
                    tamanos[i], pasos, 0.0, 0, 0
                );

                if (tiempos[r] < 0.0) {
                    return 1;
                }

                if (r == 0 || tiempos[r] < minimo) {
                    minimo = tiempos[r];
                }
            }

            printf("%-5d %.9f  %.9f  %.9f  %.9f  %.9f\n",
                   tamanos[i], tiempos[0], tiempos[1],
                   tiempos[2], tiempos[3], minimo);

            fflush(stdout);
        }

        return 0;
    }

    // Modos normales de la simulacion.
    if (argc != 5) {
        printf("Uso: termo N pasos tolerancia modo\n");
        printf("   o: termo medir\n");
        return 1;
    }

    int n = atoi(argv[1]);
    int max_pasos = atoi(argv[2]);
    double tolerancia = atof(argv[3]);

    int modo_fijo = strcmp(argv[4], "fijo") == 0;
    int modo_convergencia = strcmp(argv[4], "convergencia") == 0;

    if (n < 3 || max_pasos < 1 ||
        (!modo_fijo && !modo_convergencia) ||
        (modo_convergencia && !(tolerancia > 0.0))) {

        printf("Error: parametros incorrectos.\n");
        return 1;
    }

    double tiempo = ejecutar_simulacion(
        n, max_pasos, tolerancia, modo_convergencia, 1
    );

    return tiempo < 0.0 ? 1 : 0;
}
