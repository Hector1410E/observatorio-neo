"""
Modelos de datos del proyecto, basados en Pydantic.

Estos modelos cumplen dos funciones:
1. Documentan la forma exacta de los datos que maneja el proyecto.
2. Validan automáticamente los datos antes de guardarlos en MongoDB
   (tipos correctos, campos obligatorios, valores dentro de rango, etc.).
"""

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ClasificacionOrbital(str, Enum):
    """Familias orbitales más comunes de los NEO."""
    APOLO = "Apollo"
    ATON = "Aten"
    AMOR = "Amor"
    ATIRA = "Atira"
    DESCONOCIDA = "Desconocida"


class DiametroEstimado(BaseModel):
    """Rango de diámetro estimado, en metros."""
    minimo_m: float = Field(..., ge=0, description="Diámetro mínimo estimado en metros")
    maximo_m: float = Field(..., ge=0, description="Diámetro máximo estimado en metros")

    @field_validator("maximo_m")
    @classmethod
    def maximo_no_menor_que_minimo(cls, v, info):
        minimo = info.data.get("minimo_m")
        if minimo is not None and v < minimo:
            raise ValueError("el diámetro máximo no puede ser menor que el mínimo")
        return v


class Aproximacion(BaseModel):
    """Un evento de aproximación de un NEO a la Tierra."""
    fecha_aproximacion: date
    distancia_minima_km: float = Field(..., gt=0)
    distancia_minima_lunar: float = Field(..., gt=0)
    velocidad_relativa_kmh: float = Field(..., gt=0)
    cuerpo_orbitado: str = Field(default="Tierra")


class FichaTecnica(BaseModel):
    """
    Datos complementarios obtenidos por web scraping (JPL Small-Body
    Database / Minor Planet Center), extraídos con expresiones regulares
    a partir de texto libre.
    """
    clasificacion_orbital: ClasificacionOrbital = ClasificacionOrbital.DESCONOCIDA
    fecha_descubrimiento: Optional[date] = None
    observatorio_descubrimiento: Optional[str] = None
    fuente_url: Optional[str] = None


class ObjetoNEO(BaseModel):
    """
    Representa un objeto cercano a la Tierra (Near-Earth Object),
    combinando los datos de la API NeoWs con la ficha técnica
    obtenida por scraping.
    """
    neo_reference_id: str = Field(..., description="ID de referencia de la NASA")
    nombre: str
    magnitud_absoluta: float
    diametro_estimado: DiametroEstimado
    es_potencialmente_peligroso: bool
    aproximaciones: list[Aproximacion] = Field(default_factory=list)
    ficha_tecnica: Optional[FichaTecnica] = None
    fecha_ultima_actualizacion: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "use_enum_values": True,
    }


if __name__ == "__main__":
    # Ejemplo rápido de uso y validación
    objeto_ejemplo = ObjetoNEO(
        neo_reference_id="2000433",
        nombre="433 Eros",
        magnitud_absoluta=10.31,
        diametro_estimado=DiametroEstimado(minimo_m=13400, maximo_m=30000),
        es_potencialmente_peligroso=False,
        aproximaciones=[
            Aproximacion(
                fecha_aproximacion="2026-01-31",
                distancia_minima_km=26_700_000,
                distancia_minima_lunar=69.5,
                velocidad_relativa_kmh=17800,
            )
        ],
    )
    print(objeto_ejemplo.model_dump_json(indent=2))
