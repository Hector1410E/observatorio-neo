"""
Repositorio de persistencia en MongoDB.

Encapsula todas las operaciones de guardado y consulta, para que el resto
del proyecto nunca tenga que escribir queries de Mongo directamente.

Estrategia de guardado: cada ObjetoNEO se guarda como un documento en la
colección "objetos_neo", identificado por su neo_reference_id. Al volver a
consultarlo en días distintos, hacemos upsert: si el objeto ya existe, se
combinan (sin duplicar) sus aproximaciones históricas; si no existe, se crea.
"""

import os
from datetime import datetime

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.collection import Collection

from modelos import ObjetoNEO

load_dotenv()


class RepositorioMongo:
    """Maneja la conexión y las operaciones sobre la base de datos."""

    def __init__(self, uri: str | None = None, nombre_bd: str = "observatorio_neo"):
        uri = uri or os.getenv("MONGODB_URI")
        if not uri:
            raise ValueError("No se encontró MONGODB_URI. Revisa tu archivo .env.")

        self.cliente = MongoClient(uri)
        self.bd = self.cliente[nombre_bd]
        self.objetos: Collection = self.bd["objetos_neo"]

        # Índice único: evita que el mismo asteroide se duplique como
        # documento distinto si se vuelve a consultar en otro rango de fechas.
        self.objetos.create_index("neo_reference_id", unique=True)

    def guardar_objeto(self, objeto: ObjetoNEO) -> None:
        """
        Guarda un ObjetoNEO. Si ya existe (mismo neo_reference_id), fusiona
        sus aproximaciones nuevas con las que ya estaban guardadas, sin
        duplicar fechas repetidas.
        """
        documento_existente = self.objetos.find_one(
            {"neo_reference_id": objeto.neo_reference_id}
        )

        if documento_existente is None:
            self.objetos.insert_one(objeto.model_dump(mode="json"))
            return

        aproximaciones_existentes = documento_existente.get("aproximaciones", [])
        fechas_existentes = {a["fecha_aproximacion"] for a in aproximaciones_existentes}

        aproximaciones_nuevas = [
            a.model_dump(mode="json")
            for a in objeto.aproximaciones
            if a.fecha_aproximacion.isoformat() not in fechas_existentes
        ]

        self.objetos.update_one(
            {"neo_reference_id": objeto.neo_reference_id},
            {
                "$push": {"aproximaciones": {"$each": aproximaciones_nuevas}},
                "$set": {
                    "es_potencialmente_peligroso": objeto.es_potencialmente_peligroso,
                    "fecha_ultima_actualizacion": datetime.utcnow().isoformat(),
                },
            },
        )

    def guardar_muchos(self, objetos: list[ObjetoNEO]) -> None:
        """Guarda una lista de objetos, uno por uno (aplica la fusión de cada uno)."""
        for objeto in objetos:
            self.guardar_objeto(objeto)

    def contar_objetos(self) -> int:
        return self.objetos.count_documents({})

    def obtener_potencialmente_peligrosos(self) -> list[dict]:
        return list(self.objetos.find({"es_potencialmente_peligroso": True}))


if __name__ == "__main__":
    from datetime import date, timedelta

    from cliente_neows import ClienteNeoWs

    cliente_api = ClienteNeoWs()
    repositorio = RepositorioMongo()

    hoy = date.today()
    hace_dos_dias = hoy - timedelta(days=2)

    print(f"Consultando NEOs entre {hace_dos_dias} y {hoy}...")
    objetos = cliente_api.obtener_feed(hace_dos_dias, hoy)

    print(f"Guardando {len(objetos)} objetos en MongoDB...")
    repositorio.guardar_muchos(objetos)

    total = repositorio.contar_objetos()
    peligrosos = repositorio.obtener_potencialmente_peligrosos()
    print(f"\nTotal de objetos distintos en la base de datos: {total}")
    print(f"Objetos potencialmente peligrosos: {len(peligrosos)}")
    for p in peligrosos[:5]:
        print(f"  - {p['nombre']}")
