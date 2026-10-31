"""
Scraper de fichas técnicas complementarias.

La API NeoWs no incluye datos de descubrimiento (fecha, lugar) ni la
clasificación orbital en texto libre. Este módulo obtiene esos datos
haciendo web scraping de la página de Wikipedia del asteroide (cuando
existe), y usa expresiones regulares para extraer los campos de interés
a partir del texto del "infobox".

Nota: solo los asteroides más conocidos (típicamente los potencialmente
peligrosos) tienen página propia en Wikipedia, así que este scraper no
encontrará ficha técnica para la mayoría de los objetos del feed diario.
"""

import re
import time

import requests
from bs4 import BeautifulSoup

from modelos import ClasificacionOrbital, FichaTecnica

# Wikipedia pide identificar al cliente con un User-Agent descriptivo.
HEADERS = {
    "User-Agent": "ObservatorioNEO-ProyectoEscolar/1.0 (contacto: tu_correo@ejemplo.com)"
}

# Mapa manual de nombres de la API NeoWs -> slug de su artículo en Wikipedia.
# Se puede ampliar según los objetos que quieras enriquecer.
MAPA_WIKIPEDIA = {
    "433 Eros": "433_Eros",
    "99942 Apophis": "99942_Apophis",
    "101955 Bennu": "101955_Bennu",
    "1620 Geographos": "1620_Geographos",
    "4179 Toutatis": "4179_Toutatis",
    "25143 Itokawa": "25143_Itokawa",
}


class ScraperFichaTecnica:
    """Obtiene y parsea la ficha técnica de un asteroide desde Wikipedia."""

    def __init__(self, pausa_entre_solicitudes: float = 1.0):
        # Pausa cortés entre solicitudes, buena práctica de scraping.
        self.pausa = pausa_entre_solicitudes

    def obtener_ficha(self, nombre_neo: str) -> FichaTecnica | None:
        """
        Busca el nombre del NEO en el mapa de Wikipedia y, si existe,
        descarga y parsea su ficha técnica. Regresa None si no hay
        artículo asociado o si ocurre un error de red.
        """
        slug = MAPA_WIKIPEDIA.get(nombre_neo)
        if slug is None:
            return None

        url = f"https://en.wikipedia.org/wiki/{slug}"
        try:
            respuesta = requests.get(url, headers=HEADERS, timeout=10)
            respuesta.raise_for_status()
        except requests.RequestException:
            return None
        finally:
            time.sleep(self.pausa)

        return self._parsear_ficha(respuesta.text, url)

    @staticmethod
    def _parsear_ficha(html: str, url: str) -> FichaTecnica:
        sopa = BeautifulSoup(html, "html.parser")
        infobox = sopa.find("table", class_="infobox")
        campos = ScraperFichaTecnica._extraer_campos_infobox(infobox)

        fecha_descubrimiento = ScraperFichaTecnica._interpretar_fecha(
            campos.get("discovery date")
        )
        observatorio = campos.get("discovery site")
        clasificacion = ScraperFichaTecnica._interpretar_clasificacion(
            campos.get("minor planet category")
        )

        return FichaTecnica(
            clasificacion_orbital=clasificacion,
            fecha_descubrimiento=fecha_descubrimiento,
            observatorio_descubrimiento=observatorio,
            fuente_url=url,
        )

    @staticmethod
    def _extraer_campos_infobox(infobox) -> dict[str, str]:
        """
        Recorre las filas (<tr>) del infobox y arma un diccionario
        {etiqueta_en_minusculas: valor_limpio}. Trabajar sobre la
        estructura de la tabla (en vez de sobre el texto aplanado) es
        más confiable, porque el formato exacto varía entre artículos.
        """
        campos: dict[str, str] = {}
        if infobox is None:
            return campos

        for fila in infobox.find_all("tr"):
            etiqueta = fila.find("th")
            valor = fila.find("td")
            if etiqueta is None or valor is None:
                continue  # filas de encabezado de sección, sin th+td

            texto_etiqueta = etiqueta.get_text(separator=" ", strip=True).lower()
            texto_valor = ScraperFichaTecnica._limpiar_texto(
                valor.get_text(separator=" ")
            )
            campos[texto_etiqueta] = texto_valor

        return campos

    @staticmethod
    def _limpiar_texto(texto: str) -> str:
        """Quita referencias tipo [1], espacios repetidos y saltos de línea."""
        sin_referencias = re.sub(r"\[\s*\d+\s*\]", "", texto)
        sin_espacios_extra = re.sub(r"\s+", " ", sin_referencias)
        return sin_espacios_extra.strip()

    @staticmethod
    def _interpretar_fecha(texto_valor: str | None):
        if not texto_valor:
            return None
        # Se queda solo con la primera fecha si hay varias separadas por texto extra
        patron = r"([A-Za-z]+ \d{1,2},? \d{4}|\d{1,2} [A-Za-z]+ \d{4})"
        coincidencia = re.search(patron, texto_valor)
        if not coincidencia:
            return None
        try:
            from dateutil import parser as fecha_parser
            return fecha_parser.parse(coincidencia.group(1)).date()
        except Exception:
            return None

    @staticmethod
    def _interpretar_clasificacion(texto_valor: str | None) -> ClasificacionOrbital:
        if not texto_valor:
            return ClasificacionOrbital.DESCONOCIDA
        for clasificacion in ClasificacionOrbital:
            # \b asegura que "Aten" no haga match parcial dentro de otra palabra
            patron = rf"\b{re.escape(clasificacion.value)}\b"
            if re.search(patron, texto_valor, re.IGNORECASE):
                return clasificacion
        return ClasificacionOrbital.DESCONOCIDA


if __name__ == "__main__":
    scraper = ScraperFichaTecnica()

    for nombre_prueba in ["99942 Apophis", "433 Eros"]:
        print(f"Buscando ficha técnica de: {nombre_prueba}")
        ficha = scraper.obtener_ficha(nombre_prueba)
        if ficha:
            print(f"  Clasificación orbital: {ficha.clasificacion_orbital}")
            print(f"  Fecha de descubrimiento: {ficha.fecha_descubrimiento}")
            print(f"  Observatorio: {ficha.observatorio_descubrimiento}")
        else:
            print("  No se encontró ficha técnica.")
        print()
