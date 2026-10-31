"""
Script de verificación inicial.
Comprueba que la API key de la NASA y la conexión a MongoDB Atlas funcionan
antes de construir cualquier otra parte del proyecto.
"""

import os
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

NASA_API_KEY = os.getenv("NASA_API_KEY")
MONGODB_URI = os.getenv("MONGODB_URI")


def probar_api_nasa():
    print("Probando conexión con la API NeoWs...")
    url = "https://api.nasa.gov/neo/rest/v1/feed"
    params = {
        "start_date": "2026-01-01",
        "end_date": "2026-01-02",
        "api_key": NASA_API_KEY,
    }
    respuesta = requests.get(url, params=params, timeout=10)
    if respuesta.status_code == 200:
        datos = respuesta.json()
        total = datos.get("element_count", 0)
        print(f"  OK: se encontraron {total} objetos en el rango de fechas.")
    else:
        print(f"  ERROR ({respuesta.status_code}): {respuesta.text[:200]}")


def probar_mongodb():
    print("Probando conexión con MongoDB Atlas...")
    if not MONGODB_URI:
        print("  ERROR: no se encontró MONGODB_URI en tu archivo .env")
        return
    cliente = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    try:
        cliente.admin.command("ping")
        print("  OK: conexión exitosa con MongoDB Atlas.")
    except Exception as e:
        print(f"  ERROR: no se pudo conectar. Detalle: {e}")


if __name__ == "__main__":
    probar_api_nasa()
    probar_mongodb()
