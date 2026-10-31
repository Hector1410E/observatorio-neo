"""
Cliente de la API NeoWs (Near Earth Object Web Service) de la NASA.

Consulta el endpoint /feed, que regresa los NEOs que se aproximan a la
Tierra dentro de un rango de fechas (máximo 7 días por consulta, límite
impuesto por la propia API), y convierte la respuesta cruda en instancias
de ObjetoNEO ya validadas.
"""

import os
from datetime import date, datetime, timedelta

import requests
from dotenv import load_dotenv

from modelos import Aproximacion, DiametroEstimado, ObjetoNEO

load_dotenv()

BASE_URL = "https://api.nasa.gov/neo/rest/v1/feed"
MAX_DIAS_POR_CONSULTA = 7  # límite de la propia API NeoWs


class ClienteNeoWs:
    """Encapsula el consumo de la API NeoWs de la NASA."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("NASA_API_KEY")
        if not self.api_key:
            raise ValueError(
                "No se encontró NASA_API_KEY. Revisa tu archivo .env."
            )

    def obtener_feed(self, fecha_inicio: date, fecha_fin: date) -> list[ObjetoNEO]:
        """
        Consulta el feed de la NASA entre fecha_inicio y fecha_fin
        (inclusive) y regresa una lista de ObjetoNEO ya validados.
        """
        self._validar_rango_fechas(fecha_inicio, fecha_fin)

        params = {
            "start_date": fecha_inicio.isoformat(),
            "end_date": fecha_fin.isoformat(),
            "api_key": self.api_key,
        }
        respuesta = requests.get(BASE_URL, params=params, timeout=15)
        respuesta.raise_for_status()
        datos = respuesta.json()

        objetos: list[ObjetoNEO] = []
        neos_por_fecha = datos.get("near_earth_objects", {})
        for lista_neos in neos_por_fecha.values():
            for neo_crudo in lista_neos:
                objetos.append(self._construir_objeto_neo(neo_crudo))

        return objetos

    def obtener_feed_hoy(self) -> list[ObjetoNEO]:
        """Atajo para consultar solo el día de hoy."""
        hoy = date.today()
        return self.obtener_feed(hoy, hoy)

    @staticmethod
    def _validar_rango_fechas(fecha_inicio: date, fecha_fin: date) -> None:
        if fecha_fin < fecha_inicio:
            raise ValueError("fecha_fin no puede ser anterior a fecha_inicio")
        dias = (fecha_fin - fecha_inicio).days + 1
        if dias > MAX_DIAS_POR_CONSULTA:
            raise ValueError(
                f"El rango máximo permitido por la API es de "
                f"{MAX_DIAS_POR_CONSULTA} días; se solicitaron {dias}."
            )

    @staticmethod
    def _construir_objeto_neo(neo_crudo: dict) -> ObjetoNEO:
        """Convierte el JSON crudo de un NEO en un ObjetoNEO validado."""
        diametro_m = neo_crudo["estimated_diameter"]["meters"]
        diametro = DiametroEstimado(
            minimo_m=diametro_m["estimated_diameter_min"],
            maximo_m=diametro_m["estimated_diameter_max"],
        )

        aproximaciones = []
        for aprox_cruda in neo_crudo.get("close_approach_data", []):
            aproximaciones.append(
                Aproximacion(
                    fecha_aproximacion=aprox_cruda["close_approach_date"],
                    distancia_minima_km=float(
                        aprox_cruda["miss_distance"]["kilometers"]
                    ),
                    distancia_minima_lunar=float(
                        aprox_cruda["miss_distance"]["lunar"]
                    ),
                    velocidad_relativa_kmh=float(
                        aprox_cruda["relative_velocity"]["kilometers_per_hour"]
                    ),
                    cuerpo_orbitado=aprox_cruda.get("orbiting_body", "Tierra"),
                )
            )

        return ObjetoNEO(
            neo_reference_id=neo_crudo["neo_reference_id"],
            nombre=neo_crudo["name"],
            magnitud_absoluta=neo_crudo["absolute_magnitude_h"],
            diametro_estimado=diametro,
            es_potencialmente_peligroso=neo_crudo["is_potentially_hazardous_asteroid"],
            aproximaciones=aproximaciones,
            fecha_ultima_actualizacion=datetime.utcnow(),
        )


if __name__ == "__main__":
    cliente = ClienteNeoWs()

    hoy = date.today()
    hace_dos_dias = hoy - timedelta(days=2)

    print(f"Consultando NEOs entre {hace_dos_dias} y {hoy}...")
    objetos = cliente.obtener_feed(hace_dos_dias, hoy)

    print(f"Se encontraron {len(objetos)} objetos.\n")
    for objeto in objetos[:5]:  # solo mostramos los primeros 5
        print(f"- {objeto.nombre}")
        print(f"  Peligroso: {objeto.es_potencialmente_peligroso}")
        print(f"  Aproximaciones registradas: {len(objeto.aproximaciones)}")
        if objeto.aproximaciones:
            primera = objeto.aproximaciones[0]
            print(
                f"  Primera aproximación: {primera.fecha_aproximacion} "
                f"a {primera.distancia_minima_lunar:.1f} distancias lunares"
            )
        print()
