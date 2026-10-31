"""
Script principal del Observatorio NEO.

Une las cinco piezas del proyecto en un solo ciclo diario:
  1. Consulta la API NeoWs (Programación Orientada a Objetos + API)
  2. Enriquecimiento opcional con scraping + regex (Wikipedia)
  3. Guardado en MongoDB (manejo de bases de datos)
  4. Detección de riesgo y alertas
  5. Bitácora de errores para la mecanización de tareas

Uso manual (una sola ejecución):
    python main.py

Uso automatizado: ver la sección "Programar la ejecución diaria" más abajo.
"""

import logging
from datetime import date

from cliente_neows import ClienteNeoWs
from detector_riesgo import DetectorRiesgo
from repositorio_mongo import RepositorioMongo
from scraper_ficha_tecnica import MAPA_WIKIPEDIA, ScraperFichaTecnica

# --- Configuración de la bitácora de errores -------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("observatorio_neo.log", encoding="utf-8"),
        logging.StreamHandler(),  # también lo muestra en la terminal
    ],
)
logger = logging.getLogger("observatorio_neo")


def ejecutar_ciclo_diario() -> None:
    """Ejecuta una pasada completa del pipeline. Nunca deja que un error
    de una etapa detenga a las demás sin dejar rastro en la bitácora."""

    logger.info("Iniciando ciclo diario del Observatorio NEO.")

    try:
        cliente_api = ClienteNeoWs()
        repositorio = RepositorioMongo()
        scraper = ScraperFichaTecnica()
        detector = DetectorRiesgo()
    except Exception:
        logger.exception("Error al inicializar los componentes, se detiene el ciclo.")
        return

    hoy = date.today()
    try:
        objetos = cliente_api.obtener_feed(hoy, hoy)
        logger.info("Se obtuvieron %d objetos NEO para hoy (%s).", len(objetos), hoy)
    except Exception as e:
        logger.error("Falló la consulta a la API NeoWs: %s", e)
        return

    # Enriquecemos con la ficha técnica solo los objetos que están en
    # nuestro mapa de Wikipedia (ver scraper_ficha_tecnica.py)
    for objeto in objetos:
        if objeto.nombre in MAPA_WIKIPEDIA:
            try:
                objeto.ficha_tecnica = scraper.obtener_ficha(objeto.nombre)
            except Exception as e:
                logger.warning(
                    "No se pudo obtener la ficha técnica de %s: %s",
                    objeto.nombre, e,
                )

    try:
        repositorio.guardar_muchos(objetos)
        logger.info("Objetos guardados/actualizados en MongoDB correctamente.")
    except Exception as e:
        logger.error("Falló el guardado en MongoDB: %s", e)
        return

    alertas = detector.evaluar(objetos)
    logger.info(
        "Ciclo terminado. %d objeto(s) generaron alerta de riesgo.", len(alertas)
    )


if __name__ == "__main__":
    ejecutar_ciclo_diario()

    # --- Programar la ejecución diaria (opcional, ver notas abajo) --------
    # import schedule
    # import time
    #
    # schedule.every().day.at("08:00").do(ejecutar_ciclo_diario)
    # while True:
    #     schedule.run_pending()
    #     time.sleep(60)
