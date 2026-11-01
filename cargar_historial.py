"""
Carga histórica de objetos NEO.

La API NeoWs solo permite consultar rangos de hasta 7 días, así que este
script recorre el pasado en ventanas consecutivas de 7 días, empezando por
hoy y yendo hacia atrás, y guarda todo con el mismo repositorio que usa el
ciclo diario (sin duplicar objetos ni aproximaciones).

Es seguro correrlo varias veces: lo que ya existe en MongoDB no se duplica.

Uso:
    python cargar_historial.py              # últimos 90 días
    python cargar_historial.py --dias 14    # últimos 14 días (para probar)
"""

import argparse
import logging
import time
from datetime import date, timedelta

from cliente_neows import MAX_DIAS_POR_CONSULTA, ClienteNeoWs
from repositorio_mongo import RepositorioMongo

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("observatorio_neo.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("observatorio_neo")

PAUSA_ENTRE_CONSULTAS = 1.0  # segundos; cortesía con la API de la NASA


def generar_ventanas(hoy: date, dias: int) -> list[tuple[date, date]]:
    """
    Divide los últimos `dias` días (contando hoy) en ventanas de a lo más
    7 días, de la más reciente a la más antigua. Cada ventana es una tupla
    (fecha_inicio, fecha_fin), ambas inclusive.
    """
    ventanas = []
    fin = hoy
    restantes = dias
    while restantes > 0:
        tamano = min(MAX_DIAS_POR_CONSULTA, restantes)
        inicio = fin - timedelta(days=tamano - 1)
        ventanas.append((inicio, fin))
        fin = inicio - timedelta(days=1)
        restantes -= tamano
    return ventanas


def main() -> None:
    parser = argparse.ArgumentParser(description="Carga histórica de objetos NEO.")
    parser.add_argument(
        "--dias",
        type=int,
        default=90,
        help="Cuántos días hacia atrás cargar, contando hoy (por defecto 90).",
    )
    args = parser.parse_args()

    if args.dias < 1:
        parser.error("--dias debe ser al menos 1")

    try:
        cliente_api = ClienteNeoWs()
        repositorio = RepositorioMongo()
    except Exception:
        logger.exception("Error al inicializar los componentes, se detiene la carga.")
        return

    ventanas = generar_ventanas(date.today(), args.dias)
    logger.info(
        "Carga histórica: %d días en %d consultas (de %s a %s).",
        args.dias, len(ventanas), ventanas[-1][0], ventanas[0][1],
    )

    registros_procesados = 0
    ventanas_fallidas = []

    for numero, (inicio, fin) in enumerate(ventanas, start=1):
        try:
            objetos = cliente_api.obtener_feed(inicio, fin)
            repositorio.guardar_muchos(objetos)
            registros_procesados += len(objetos)
            logger.info(
                "[%d/%d] %s a %s: %d objetos procesados.",
                numero, len(ventanas), inicio, fin, len(objetos),
            )
        except Exception as e:
            ventanas_fallidas.append((inicio, fin))
            logger.error(
                "[%d/%d] Falló la ventana %s a %s: %s",
                numero, len(ventanas), inicio, fin, e,
            )
        time.sleep(PAUSA_ENTRE_CONSULTAS)

    total_bd = repositorio.contar_objetos()
    logger.info(
        "Carga terminada. Registros procesados: %d. "
        "Objetos distintos en la base de datos: %d.",
        registros_procesados, total_bd,
    )

    if ventanas_fallidas:
        logger.warning(
            "%d ventana(s) fallaron. Vuelve a correr el script para reintentarlas "
            "(lo ya guardado no se duplica):", len(ventanas_fallidas),
        )
        for inicio, fin in ventanas_fallidas:
            logger.warning("  - %s a %s", inicio, fin)


if __name__ == "__main__":
    main()
