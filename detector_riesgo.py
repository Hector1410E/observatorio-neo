"""
Detector de riesgo.

Aplica criterios simples sobre los ObjetoNEO recién obtenidos para decidir
cuáles ameritan una alerta: que la NASA ya los clasifique como
potencialmente peligrosos, y que además su aproximación más cercana esté
por debajo de un umbral de distancia (en distancias lunares).
"""

import logging

from modelos import ObjetoNEO

logger = logging.getLogger("observatorio_neo")

UMBRAL_DISTANCIA_LUNAR = 10.0  # aproximaciones más cercanas que esto generan alerta


class DetectorRiesgo:
    """Evalúa una lista de ObjetoNEO y separa los que ameritan alerta."""

    def __init__(self, umbral_distancia_lunar: float = UMBRAL_DISTANCIA_LUNAR):
        self.umbral_distancia_lunar = umbral_distancia_lunar

    def evaluar(self, objetos: list[ObjetoNEO]) -> list[ObjetoNEO]:
        """Regresa el subconjunto de objetos que ameritan alerta."""
        alertas = [obj for obj in objetos if self._amerita_alerta(obj)]
        for objeto in alertas:
            self._registrar_alerta(objeto)
        return alertas

    def _amerita_alerta(self, objeto: ObjetoNEO) -> bool:
        if not objeto.es_potencialmente_peligroso:
            return False
        if not objeto.aproximaciones:
            return False

        distancia_minima = min(
            a.distancia_minima_lunar for a in objeto.aproximaciones
        )
        return distancia_minima <= self.umbral_distancia_lunar

    def _registrar_alerta(self, objeto: ObjetoNEO) -> None:
        distancia_minima = min(
            a.distancia_minima_lunar for a in objeto.aproximaciones
        )
        logger.warning(
            "ALERTA: %s es potencialmente peligroso y se aproximará a "
            "%.2f distancias lunares (diámetro estimado: %.0f-%.0f m).",
            objeto.nombre,
            distancia_minima,
            objeto.diametro_estimado.minimo_m,
            objeto.diametro_estimado.maximo_m,
        )
