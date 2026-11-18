// TermoHPC I - Ejercicio 6, iteracion 3: una sola region paralela.
//
// Parte de termo_ej6_it2.c y cambia UNA sola cosa: en lugar de abrir y cerrar
// un 'parallel for' en cada paso de tiempo, se abre UNA region paralela que
// envuelve todo el bucle temporal. Dentro, cada paso es un 'omp for' huerfano
// (en paso_jacobi_residuo) mas un 'omp single' que hace la parte secuencial del
// paso (comprobar el residuo e intercambiar los punteros).
//
// Compilacion:
//       gcc -Wall -Wextra -O2 -std=c11 -fopenmp termo_ej6_it3.c -o termo_ej6_it3.exe -lm

#define _POSIX_C_SOURCE 199309L

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#ifdef _OPENMP
#include <omp.h>
#endif

// Tolerancia de la verificacion numerica (ejercicio 2), fijada ANTES de medir.
// Con double y temperaturas de orden 100, el error de redondeo de una celda es
// del orden de 1e-14; una diferencia de 1e-9 ya solo puede ser un error de programa.
#define TOLERANCIA_VERIFICACION 1e-9

// Recuentos de hilos que pide el enunciado para las tablas.
static const int RECUENTOS_HILOS[] = {1, 2, 4, 8, 12, 16, 20, 24};
#define NUM_RECUENTOS ((int)(sizeof(RECUENTOS_HILOS) / sizeof(RECUENTOS_HILOS[0])))

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

// Fija el numero de hilos y devuelve cuantos hay DE VERDAD dentro de una
// region paralela (apartado IV.D del enunciado). Sin OpenMP siempre es 1.
static int fijar_hilos(int hilos) {
#ifdef _OPENMP
    omp_set_dynamic(0);          // que la biblioteca no nos de menos hilos
    omp_set_num_threads(hilos);

    int reales = 0;
    #pragma omp parallel default(none) shared(reales)
    {
        #pragma omp single
        reales = omp_get_num_threads();   // dentro de la region, no fuera
    }
    return reales;
#else
    (void)hilos;
    return 1;
#endif
}

// Hilos por defecto si no se indican en la linea de ordenes.
static int hilos_por_defecto(void) {
#ifdef _OPENMP
    return omp_get_max_threads();
#else
    return 1;
#endif
}

// Reserva una malla de n x n double comprobando el desbordamiento.
static double *reservar_malla(int n) {
    if ((size_t)n > ((size_t)-1 / sizeof(double)) / (size_t)n) {
        fprintf(stderr, "Error: tamano de malla excesivo.\n");
        return NULL;
    }
    double *malla = malloc((size_t)n * n * sizeof(double));
    if (malla == NULL) {
        fprintf(stderr, "Error al reservar memoria.\n");
    }
    return malla;
}

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

// Maximo del residuo de un paso. Es una variable de fichero, asi que es
// COMPARTIDA por todos los hilos de la region paralela de simular(); el
// 'omp for' de abajo hace la reduccion sobre ella.
static double residuo_paso = 0.0;

// Paso de Jacobi + residuo (iteracion 3). No abre ninguna region: es un
// 'omp for' huerfano que se ejecuta dentro de la region paralela de simular().
// Al final del 'omp for' hay una barrera implicita y, tras ella, residuo_paso
// contiene el maximo de todos los hilos.
void paso_jacobi_residuo(const double *actual, double *nueva, int n) {

    #pragma omp for reduction(max : residuo_paso) schedule(dynamic, 16)
    for (int i = 1; i < n - 1; i++) {
        for (int j = 1; j < n - 1; j++) {

            size_t pos = (size_t)i * n + j;

            double valor = (actual[pos - n] +
                            actual[pos + n] +
                            actual[pos - 1] +
                            actual[pos + 1]) / 4.0;
            nueva[pos] = valor;

            double cambio = fabs(valor - actual[pos]);
            if (cambio > residuo_paso) {
                residuo_paso = cambio;
            }
        }
    }
}

// Suma las temperaturas interiores (checksum).
// reduction(+:suma): las sumas parciales de cada hilo se combinan en un orden
// que depende del numero de hilos. Como la suma en coma flotante no es
// asociativa, el checksum puede variar en las ultimas cifras con los hilos.
double sumar_temperaturas_interiores(const double *malla, int n) {

    double suma = 0.0;

    #pragma omp parallel for default(none) shared(malla, n) \
            reduction(+ : suma) schedule(static)
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

// Resultado de una simulacion.
typedef struct {
    int pasos;
    double residuo;
    double checksum;
    double tiempo;
    int bordes;
    int monotono;
    int rango;
} Resultado;

// Ejecuta la simulacion y devuelve la malla final (la libera quien llama),
// o NULL si falla la reserva de memoria.
double *simular(int n, int max_pasos, double tolerancia,
                int modo_convergencia, Resultado *res) {

    double *actual = reservar_malla(n);
    double *nueva = reservar_malla(n);

    if (actual == NULL || nueva == NULL) {
        free(actual);
        free(nueva);
        return NULL;
    }

    // Inicializacion fuera del cronometro.
    inicializar(actual, n);
    inicializar(nueva, n);

    int pasos_ejecutados = 0;
    double residuo = 0.0;
    double residuo_anterior = 0.0;
    int residuo_decreciente = 1;

    // Comienza el cronometraje.
    double inicio = reloj();

    // Iteracion 3: UNA region paralela para todo el bucle temporal.
    //   - actual, nueva: compartidas; solo las cambia el hilo del 'single', y
    //     los demas las leen despues de su barrera.
    //   - residuo_paso: compartida (variable de fichero), reducida por el 'omp for'.
    //   - residuo, residuo_anterior, residuo_decreciente, pasos_ejecutados,
    //     terminar: compartidas; solo se escriben dentro del 'single'.
    //   - paso: privada (declarada dentro de la region).
    // Cada paso tiene DOS barreras implicitas: la del 'omp for' (la que separa
    // los pasos, imprescindible) y la del 'single' (para que nadie empiece el
    // paso siguiente antes de que se hayan intercambiado los punteros).
    int terminar = 0;
    residuo_paso = 0.0;

    #pragma omp parallel default(none)             shared(actual, nueva, n, max_pasos, tolerancia, modo_convergencia,                    residuo, residuo_anterior, residuo_decreciente,                    pasos_ejecutados, terminar, residuo_paso)
    {
        // Bucle temporal: sigue siendo SECUENCIAL; todos los hilos lo recorren
        // a la vez y se reparten las filas de cada paso.
        for (int paso = 1; paso <= max_pasos; paso++) {

            paso_jacobi_residuo(actual, nueva, n);   // barrera implicita

            #pragma omp single
            {
                residuo = residuo_paso;
                residuo_paso = 0.0;                  // listo para el paso siguiente

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
                    terminar = 1;
                }
            }                                        // barrera implicita

            if (terminar) {
                break;                               // todos ven el mismo valor
            }
        }
    }

    // Finaliza el cronometraje.
    double tiempo_total = reloj() - inicio;

    // Comprobaciones fuera del cronometro.
    res->pasos = pasos_ejecutados;
    res->residuo = residuo;
    res->tiempo = tiempo_total;
    res->checksum = sumar_temperaturas_interiores(actual, n);
    res->bordes = comprobar_bordes(actual, n);
    res->monotono = residuo_decreciente;
    res->rango = comprobar_temperaturas(actual, n);

    free(nueva);
    return actual;
}

static int resultado_correcto(const Resultado *res) {
    return res->bordes && res->monotono && res->rango && isfinite(res->checksum);
}

// ---------------------------------------------------------------------------
// Referencia secuencial para la verificacion: el codigo del ejercicio 1 SIN
// ninguna directiva OpenMP, para comparar el paralelo contra el secuencial
// dentro del mismo ejecutable.
// ---------------------------------------------------------------------------

static void paso_jacobi_referencia(const double *actual, double *nueva, int n) {
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

static double checksum_referencia(const double *malla, int n) {
    double suma = 0.0;
    for (int i = 1; i < n - 1; i++) {
        for (int j = 1; j < n - 1; j++) {
            suma += malla[(size_t)i * n + j];
        }
    }
    return suma;
}

static double *simular_referencia(int n, int pasos) {
    double *actual = reservar_malla(n);
    double *nueva = reservar_malla(n);
    if (actual == NULL || nueva == NULL) {
        free(actual);
        free(nueva);
        return NULL;
    }
    inicializar(actual, n);
    inicializar(nueva, n);
    for (int paso = 1; paso <= pasos; paso++) {
        paso_jacobi_referencia(actual, nueva, n);
        double *temporal = actual;
        actual = nueva;
        nueva = temporal;
    }
    free(nueva);
    return actual;
}

// ---------------------------------------------------------------------------
// Version INCORRECTA a proposito (fallo provocado del ejercicio 2):
// actualizacion in situ con un solo buffer. Una celda puede leer vecinas ya
// actualizadas en este paso y otras todavia no, y cuales son depende de como
// se repartan las filas entre los hilos. Ademas es una condicion de carrera:
// en la frontera entre dos bloques un hilo lee una fila que otro esta escribiendo.
// ---------------------------------------------------------------------------

static void paso_insitu(double *u, int n) {

    #pragma omp parallel for default(none) shared(u, n) schedule(static)
    for (int i = 1; i < n - 1; i++) {
        for (int j = 1; j < n - 1; j++) {
            size_t pos = (size_t)i * n + j;
            u[pos] = (u[pos - n] + u[pos + n] + u[pos - 1] + u[pos + 1]) / 4.0;
        }
    }
}

static double *simular_insitu(int n, int pasos) {
    double *u = reservar_malla(n);
    if (u == NULL) {
        return NULL;
    }
    inicializar(u, n);
    for (int paso = 1; paso <= pasos; paso++) {
        paso_insitu(u, n);
    }
    return u;
}

// Norma del maximo de la diferencia celda a celda (malla completa).
static double diferencia_maxima(const double *a, const double *b, int n) {
    double dmax = 0.0;
    size_t total = (size_t)n * n;
    for (size_t k = 0; k < total; k++) {
        double d = fabs(a[k] - b[k]);
        if (d > dmax) {
            dmax = d;
        }
    }
    return dmax;
}

// ---------------------------------------------------------------------------
// Modos del programa
// ---------------------------------------------------------------------------

// Tabla de verificacion: paralelo con 1..24 hilos frente a la referencia.
static int modo_verificar(int n, int pasos) {

    double *referencia = simular_referencia(n, pasos);
    if (referencia == NULL) {
        return 1;
    }
    double checksum_ref = checksum_referencia(referencia, n);

    printf("\nVERIFICACION: paralelo frente a referencia secuencial\n");
    printf("N=%d  pasos=%d  tolerancia=%.0e  checksum referencia=%.15e\n",
           n, pasos, TOLERANCIA_VERIFICACION, checksum_ref);
    printf("Hilos  Reales  Dif. maxima campo  Checksum paralelo       "
           "Dif. relativa checksum  Resultado\n");
    printf("------------------------------------------------------------"
           "-------------------------------------\n");

    int todo_correcto = 1;

    for (int k = 0; k < NUM_RECUENTOS; k++) {

        int pedidos = RECUENTOS_HILOS[k];
        int reales = fijar_hilos(pedidos);

        Resultado res;
        double *campo = simular(n, pasos, 0.0, 0, &res);
        if (campo == NULL) {
            free(referencia);
            return 1;
        }

        double dmax = diferencia_maxima(campo, referencia, n);
        double dchk = fabs(res.checksum - checksum_ref) / fabs(checksum_ref);
        int pasa = dmax <= TOLERANCIA_VERIFICACION &&
                   dchk <= TOLERANCIA_VERIFICACION &&
                   reales == pedidos &&
                   resultado_correcto(&res);

        if (!pasa) {
            todo_correcto = 0;
        }

        printf("%-6d %-7d %-18.3e %-23.15e %-23.3e %s\n",
               pedidos, reales, dmax, res.checksum, dchk,
               pasa ? "PASA" : "FALLA");
        fflush(stdout);

        free(campo);
    }

    free(referencia);
    printf("\nVerificacion global: %s\n", todo_correcto ? "PASA" : "FALLA");
    return todo_correcto ? 0 : 1;
}

// Fallo provocado: version in situ frente a la referencia de Jacobi.
static int modo_insitu(int n, int pasos) {

    double *referencia = simular_referencia(n, pasos);
    if (referencia == NULL) {
        return 1;
    }
    double checksum_ref = checksum_referencia(referencia, n);

    double *insitu_1hilo = NULL;

    printf("\nFALLO PROVOCADO: actualizacion in situ (un solo buffer)\n");
    printf("N=%d  pasos=%d  tolerancia=%.0e  checksum Jacobi=%.15e\n",
           n, pasos, TOLERANCIA_VERIFICACION, checksum_ref);
    printf("Hilos  Dif. max. frente a Jacobi  Dif. max. frente a in situ 1 hilo  "
           "Checksum                Verificacion\n");
    printf("------------------------------------------------------------"
           "-----------------------------------------------\n");

    for (int k = 0; k < NUM_RECUENTOS; k++) {

        int pedidos = RECUENTOS_HILOS[k];
        fijar_hilos(pedidos);

        double *campo = simular_insitu(n, pasos);
        if (campo == NULL) {
            free(referencia);
            free(insitu_1hilo);
            return 1;
        }

        double dmax = diferencia_maxima(campo, referencia, n);
        double chk = checksum_referencia(campo, n);
        double dchk = fabs(chk - checksum_ref) / fabs(checksum_ref);
        int pasa = dmax <= TOLERANCIA_VERIFICACION &&
                   dchk <= TOLERANCIA_VERIFICACION;

        double dmax_1hilo = 0.0;
        if (insitu_1hilo == NULL) {
            insitu_1hilo = campo;          // se guarda como base de comparacion
        } else {
            dmax_1hilo = diferencia_maxima(campo, insitu_1hilo, n);
        }

        printf("%-6d %-26.3e %-34.3e %-23.15e %s\n",
               pedidos, dmax, dmax_1hilo, chk, pasa ? "PASA" : "RECHAZADA");
        fflush(stdout);

        if (campo != insitu_1hilo) {
            free(campo);
        }
    }

    free(insitu_1hilo);
    free(referencia);
    return 0;
}

// Tabla de tiempos del ejercicio 1 (con los hilos actuales).
static int modo_medir(void) {

    int tamanos[] = {512, 1024, 2048, 4096};
    int pasos = 300;
    int repeticiones = 4;
    int hilos = fijar_hilos(hilos_por_defecto());

    printf("\nMEDICIONES (300 pasos, 4 repeticiones, criterio: minimo, hilos=%d)\n",
           hilos);
    printf("N     Rep1 (s)     Rep2 (s)     Rep3 (s)     Rep4 (s)     Minimo (s)    Checksum\n");
    printf("------------------------------------------------------------------------------------\n");

    for (int i = 0; i < 4; i++) {

        double tiempos[4];
        double minimo = 0.0;
        double checksum = 0.0;   // se imprime: evita que -O2 elimine el calculo

        for (int r = 0; r < repeticiones; r++) {

            Resultado res;
            double *campo = simular(tamanos[i], pasos, 0.0, 0, &res);
            if (campo == NULL) {
                return 1;
            }
            free(campo);

            if (!resultado_correcto(&res)) {
                fprintf(stderr, "Error: la simulacion no supera las comprobaciones.\n");
                return 1;
            }

            tiempos[r] = res.tiempo;
            checksum = res.checksum;
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

static void uso(void) {
    printf("Uso: termo N pasos tolerancia fijo|convergencia [hilos]\n");
    printf("   o: termo medir\n");
    printf("   o: termo verificar N pasos\n");
    printf("   o: termo insitu N pasos\n");
}

int main(int argc, char *argv[]) {

    if (argc == 2 && strcmp(argv[1], "medir") == 0) {
        return modo_medir();
    }

    if (argc == 4 && (strcmp(argv[1], "verificar") == 0 ||
                      strcmp(argv[1], "insitu") == 0)) {
        int n = atoi(argv[2]);
        int pasos = atoi(argv[3]);
        if (n < 3 || pasos < 1) {
            printf("Error: parametros incorrectos.\n");
            return 1;
        }
        return strcmp(argv[1], "verificar") == 0 ? modo_verificar(n, pasos)
                                                 : modo_insitu(n, pasos);
    }

    // Modos normales de la simulacion.
    if (argc != 5 && argc != 6) {
        uso();
        return 1;
    }

    int n = atoi(argv[1]);
    int max_pasos = atoi(argv[2]);
    double tolerancia = atof(argv[3]);
    int hilos = argc == 6 ? atoi(argv[5]) : hilos_por_defecto();

    int modo_fijo = strcmp(argv[4], "fijo") == 0;
    int modo_convergencia = strcmp(argv[4], "convergencia") == 0;

    if (n < 3 || max_pasos < 1 || hilos < 1 ||
        (!modo_fijo && !modo_convergencia) ||
        (modo_convergencia && !(tolerancia > 0.0))) {

        printf("Error: parametros incorrectos.\n");
        return 1;
    }

    int hilos_reales = fijar_hilos(hilos);
#ifdef _OPENMP
    if (hilos_reales != hilos) {
        fprintf(stderr, "Aviso: se pidieron %d hilos y hay %d.\n",
                hilos, hilos_reales);
    }
#endif

    Resultado res;
    double *campo = simular(n, max_pasos, tolerancia, modo_convergencia, &res);
    if (campo == NULL) {
        return 1;
    }
    free(campo);

    // Una ejecucion = una linea, formato clave=valor.
    printf("N=%d Hilos=%d Pasos=%d Residuo=%.6e Checksum=%.6f Tiempo=%.6f "
           "Bordes=%s Monotono=%s Rango=%s\n",
           n, hilos_reales, res.pasos, res.residuo, res.checksum, res.tiempo,
           res.bordes ? "OK" : "FALLO",
           res.monotono ? "OK" : "FALLO",
           res.rango ? "OK" : "FALLO");

    if (!resultado_correcto(&res)) {
        fprintf(stderr, "Error: la simulacion no supera las comprobaciones.\n");
        return 1;
    }

    return 0;
}
