"""
Análisis del histórico de objetos NEO mediante consultas de agregación
de MongoDB.

Ejecuta siete consultas sobre la colección `objetos_neo`, las muestra en
la terminal y guarda cada resultado como CSV en la carpeta `resultados/`
(listos para incluir como tablas o para graficar en el reporte técnico).

Uso:
    python analisis_neo.py
"""

import csv
import logging
from pathlib import Path

from detector_riesgo import UMBRAL_DISTANCIA_LUNAR
from repositorio_mongo import RepositorioMongo

logger = logging.getLogger("observatorio_neo")

CARPETA_RESULTADOS = Path("resultados")


class AnalisisNEO:
    """Agrupa las consultas de agregación sobre el histórico de NEOs."""

    def __init__(self, repositorio: RepositorioMongo):
        self.coleccion = repositorio.objetos

    def resumen_general(self) -> list[dict]:
        """Totales globales de la colección."""
        pipeline = [
            {
                "$group": {
                    "_id": None,
                    "objetos": {"$sum": 1},
                    "potencialmente_peligrosos": {
                        "$sum": {"$cond": ["$es_potencialmente_peligroso", 1, 0]}
                    },
                    "aproximaciones_totales": {
                        "$sum": {"$size": {"$ifNull": ["$aproximaciones", []]}}
                    },
                    "diametro_max_promedio_m": {"$avg": "$diametro_estimado.maximo_m"},
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "objetos": 1,
                    "potencialmente_peligrosos": 1,
                    "aproximaciones_totales": 1,
                    "diametro_max_promedio_m": {
                        "$round": ["$diametro_max_promedio_m", 1]
                    },
                }
            },
        ]
        return list(self.coleccion.aggregate(pipeline))

    def aproximaciones_mas_cercanas(self, limite: int = 10) -> list[dict]:
        """Las aproximaciones que pasaron más cerca de la Tierra."""
        pipeline = [
            {"$unwind": "$aproximaciones"},
            {"$sort": {"aproximaciones.distancia_minima_lunar": 1}},
            {"$limit": limite},
            {
                "$project": {
                    "_id": 0,
                    "nombre": 1,
                    "fecha": "$aproximaciones.fecha_aproximacion",
                    "distancia_lunar": {
                        "$round": ["$aproximaciones.distancia_minima_lunar", 3]
                    },
                    "distancia_km": {
                        "$round": ["$aproximaciones.distancia_minima_km", 0]
                    },
                    "velocidad_kmh": {
                        "$round": ["$aproximaciones.velocidad_relativa_kmh", 0]
                    },
                    "diametro_max_m": {"$round": ["$diametro_estimado.maximo_m", 1]},
                    "peligroso": "$es_potencialmente_peligroso",
                }
            },
        ]
        return list(self.coleccion.aggregate(pipeline))

    def objetos_mas_grandes(self, limite: int = 10) -> list[dict]:
        """Los objetos con mayor diámetro máximo estimado."""
        pipeline = [
            {"$sort": {"diametro_estimado.maximo_m": -1}},
            {"$limit": limite},
            {
                "$project": {
                    "_id": 0,
                    "nombre": 1,
                    "diametro_min_m": {"$round": ["$diametro_estimado.minimo_m", 1]},
                    "diametro_max_m": {"$round": ["$diametro_estimado.maximo_m", 1]},
                    "magnitud_absoluta": 1,
                    "peligroso": "$es_potencialmente_peligroso",
                    "aproximaciones": {"$size": {"$ifNull": ["$aproximaciones", []]}},
                }
            },
        ]
        return list(self.coleccion.aggregate(pipeline))

    def evolucion_mensual(self) -> list[dict]:
        """Aproximaciones, objetos distintos y peligrosos por mes."""
        pipeline = [
            {"$unwind": "$aproximaciones"},
            {
                "$group": {
                    "_id": {"$substrCP": ["$aproximaciones.fecha_aproximacion", 0, 7]},
                    "aproximaciones": {"$sum": 1},
                    "objetos": {"$addToSet": "$neo_reference_id"},
                    "aprox_potencialmente_peligrosos": {
                        "$sum": {"$cond": ["$es_potencialmente_peligroso", 1, 0]}
                    },
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "mes": "$_id",
                    "aproximaciones": 1,
                    "objetos_distintos": {"$size": "$objetos"},
                    "aprox_potencialmente_peligrosos": 1,
                }
            },
            {"$sort": {"mes": 1}},
        ]
        return list(self.coleccion.aggregate(pipeline))

    def comparacion_peligrosos(self) -> list[dict]:
        """Compara aproximaciones de objetos peligrosos y no peligrosos."""
        pipeline = [
            {"$unwind": "$aproximaciones"},
            {
                "$group": {
                    "_id": "$es_potencialmente_peligroso",
                    "aproximaciones": {"$sum": 1},
                    "distancia_lunar_prom": {
                        "$avg": "$aproximaciones.distancia_minima_lunar"
                    },
                    "velocidad_kmh_prom": {
                        "$avg": "$aproximaciones.velocidad_relativa_kmh"
                    },
                    "diametro_max_prom_m": {"$avg": "$diametro_estimado.maximo_m"},
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "potencialmente_peligroso": "$_id",
                    "aproximaciones": 1,
                    "distancia_lunar_prom": {"$round": ["$distancia_lunar_prom", 2]},
                    "velocidad_kmh_prom": {"$round": ["$velocidad_kmh_prom", 0]},
                    "diametro_max_prom_m": {"$round": ["$diametro_max_prom_m", 1]},
                }
            },
            {"$sort": {"potencialmente_peligroso": -1}},
        ]
        return list(self.coleccion.aggregate(pipeline))

    def distribucion_distancias(self) -> list[dict]:
        """Cuántas aproximaciones caen en cada rango de distancia lunar."""
        limites = [0, 1, 5, 10, 20, 50, 100]
        pipeline = [
            {"$unwind": "$aproximaciones"},
            {
                "$bucket": {
                    "groupBy": "$aproximaciones.distancia_minima_lunar",
                    "boundaries": limites,
                    "default": "100 o más",
                    "output": {"aproximaciones": {"$sum": 1}},
                }
            },
        ]
        filas = []
        for doc in self.coleccion.aggregate(pipeline):
            if isinstance(doc["_id"], str):
                rango = doc["_id"]
            else:
                i = next(k for k, v in enumerate(limites) if v == doc["_id"])
                rango = f"{limites[i]} a {limites[i + 1]}"
            filas.append({"rango_distancias_lunares": rango,
                          "aproximaciones": doc["aproximaciones"]})
        return filas

    def alertas_historicas(self, umbral: float = UMBRAL_DISTANCIA_LUNAR) -> list[dict]:
        """Aproximaciones que habrían generado alerta con el criterio del detector."""
        pipeline = [
            {"$match": {"es_potencialmente_peligroso": True}},
            {"$unwind": "$aproximaciones"},
            {"$match": {"aproximaciones.distancia_minima_lunar": {"$lte": umbral}}},
            {"$sort": {"aproximaciones.distancia_minima_lunar": 1}},
            {
                "$project": {
                    "_id": 0,
                    "nombre": 1,
                    "fecha": "$aproximaciones.fecha_aproximacion",
                    "distancia_lunar": {
                        "$round": ["$aproximaciones.distancia_minima_lunar", 3]
                    },
                    "velocidad_kmh": {
                        "$round": ["$aproximaciones.velocidad_relativa_kmh", 0]
                    },
                    "diametro_max_m": {"$round": ["$diametro_estimado.maximo_m", 1]},
                }
            },
        ]
        return list(self.coleccion.aggregate(pipeline))


def imprimir_tabla(titulo: str, filas: list[dict]) -> None:
    """Muestra una lista de diccionarios como tabla de texto alineada."""
    print(f"\n=== {titulo} ===")
    if not filas:
        print("(sin resultados)")
        return

    columnas = list(filas[0].keys())
    anchos = {
        c: max(len(str(c)), *(len(str(fila.get(c, ""))) for fila in filas))
        for c in columnas
    }
    print("  ".join(str(c).ljust(anchos[c]) for c in columnas))
    print("  ".join("-" * anchos[c] for c in columnas))
    for fila in filas:
        print("  ".join(str(fila.get(c, "")).ljust(anchos[c]) for c in columnas))


def exportar_csv(nombre_archivo: str, filas: list[dict]) -> None:
    """Guarda los resultados en resultados/<nombre_archivo>.csv."""
    if not filas:
        return
    CARPETA_RESULTADOS.mkdir(exist_ok=True)
    ruta = CARPETA_RESULTADOS / f"{nombre_archivo}.csv"
    # utf-8-sig para que Excel abra bien los acentos
    with open(ruta, "w", newline="", encoding="utf-8-sig") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=list(filas[0].keys()))
        escritor.writeheader()
        escritor.writerows(filas)


def main() -> None:
    try:
        repositorio = RepositorioMongo()
    except Exception as e:
        print(f"No se pudo conectar a MongoDB: {e}")
        return

    analisis = AnalisisNEO(repositorio)
    consultas = [
        ("1_resumen_general", "Resumen general", analisis.resumen_general),
        ("2_aproximaciones_mas_cercanas", "10 aproximaciones más cercanas",
         analisis.aproximaciones_mas_cercanas),
        ("3_objetos_mas_grandes", "10 objetos más grandes",
         analisis.objetos_mas_grandes),
        ("4_evolucion_mensual", "Evolución mensual (el primer y el último mes "
         "pueden estar incompletos)", analisis.evolucion_mensual),
        ("5_comparacion_peligrosos", "Peligrosos vs. no peligrosos",
         analisis.comparacion_peligrosos),
        ("6_distribucion_distancias", "Distribución por distancia lunar",
         analisis.distribucion_distancias),
        ("7_alertas_historicas", "Aproximaciones que habrían generado alerta",
         analisis.alertas_historicas),
    ]

    for archivo, titulo, consulta in consultas:
        filas = consulta()
        imprimir_tabla(titulo, filas)
        exportar_csv(archivo, filas)

    print(f"\nResultados guardados como CSV en la carpeta '{CARPETA_RESULTADOS}'.")


if __name__ == "__main__":
    main()
