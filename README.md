# Observatorio de objetos cercanos a la Tierra (NEO)

Sistema en Python que consulta diariamente la API NeoWs de la NASA, complementa la información con web scraping, valida los datos con Pydantic, los almacena en MongoDB y genera alertas de objetos potencialmente peligrosos.

Proyecto de la materia de la Maestría en Ciencia de Datos y Optimización.
Autor: Héctor Escobedo Peña.

## Problema

La NASA publica diariamente datos de asteroides que se aproximan a la Tierra, pero la información está dispersa: los datos numéricos de cada aproximación vienen estructurados en la API NeoWs, mientras que datos como la clasificación orbital o las circunstancias de descubrimiento aparecen como texto libre en otras fuentes. No existe un repositorio propio que combine ambas y conserve el histórico de aproximaciones de cada objeto.

Este proyecto construye ese repositorio y lo mantiene actualizado de forma automática.

## Temas del curso que cubre

| Tema | Dónde se aplica |
|---|---|
| Programación Orientada a Objetos | Clases `ClienteNeoWs`, `ScraperFichaTecnica`, `RepositorioMongo`, `DetectorRiesgo` y modelos de Pydantic |
| Expresiones regulares | `scraper_ficha_tecnica.py`: limpieza de referencias, extracción de fechas y detección de la clasificación orbital |
| Web scraping | `scraper_ficha_tecnica.py`: lectura del infobox de Wikipedia con `requests` y `BeautifulSoup` |
| Manejo de bases de datos | `repositorio_mongo.py`: MongoDB (Atlas) con índice único y fusión del histórico |
| Mecanización de tareas | `main.py`: ciclo diario, bitácora de errores y ejecución programada |

## Estructura del proyecto

| Archivo | Función |
|---|---|
| `modelos.py` | Modelos de Pydantic: `ObjetoNEO`, `Aproximacion`, `DiametroEstimado`, `FichaTecnica` |
| `cliente_neows.py` | Cliente de la API NeoWs; convierte el JSON de la NASA en modelos validados |
| `scraper_ficha_tecnica.py` | Scraping de la ficha técnica (fecha y sitio de descubrimiento, clasificación orbital) |
| `repositorio_mongo.py` | Guardado y consulta en MongoDB, sin duplicar objetos ni aproximaciones |
| `detector_riesgo.py` | Criterios de alerta sobre objetos potencialmente peligrosos |
| `main.py` | Orquestador del ciclo diario, con bitácora (`observatorio_neo.log`) |
| `probar_configuracion.py` | Verifica la API key de la NASA y la conexión a MongoDB |
| `debug_scraper.py` | Script de diagnóstico del scraper (opcional) |
| `requirements.txt` | Dependencias |
| `.env.example` | Plantilla de variables de entorno |

## Flujo de datos

1. `ClienteNeoWs` consulta el endpoint `/feed` de la API NeoWs y construye objetos `ObjetoNEO` validados con Pydantic.
2. Si el objeto tiene artículo asociado en `MAPA_WIKIPEDIA`, `ScraperFichaTecnica` obtiene su ficha técnica.
3. `RepositorioMongo` guarda cada objeto en la colección `objetos_neo` (base `observatorio_neo`). Si ya existía, solo agrega las aproximaciones nuevas.
4. `DetectorRiesgo` marca una alerta cuando el objeto es potencialmente peligroso y su aproximación pasa a una distancia igual o menor al umbral (10 distancias lunares por defecto).
5. Cada etapa deja registro en `observatorio_neo.log`.

## Variables guardadas

Identificador de la NASA, nombre, magnitud absoluta, diámetro estimado (mínimo y máximo en metros), condición de potencialmente peligroso, lista de aproximaciones (fecha, distancia en km y en distancias lunares, velocidad relativa), y la ficha técnica opcional (clasificación orbital, fecha y observatorio de descubrimiento, URL de la fuente).

## Requisitos

- Python 3.10 o superior
- Una API key gratuita de la NASA (https://api.nasa.gov)
- Un clúster gratuito de MongoDB Atlas (https://www.mongodb.com/cloud/atlas)

## Instalación

```bash
git clone https://github.com/Hector1410E/observatorio-neo.git
cd observatorio-neo
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux
pip install -r requirements.txt
```

## Configuración

1. Copia `.env.example` como `.env`.
2. Escribe tus valores reales:

```
NASA_API_KEY=tu_api_key
MONGODB_URI=mongodb+srv://usuario:contraseña@cluster0.xxxxx.mongodb.net/?appName=Cluster0
```

El archivo `.env` está en `.gitignore` y nunca debe subirse al repositorio.

3. Verifica la configuración:

```bash
python probar_configuracion.py
```

## Uso

Una ejecución manual del ciclo completo:

```bash
python main.py
```

Salida esperada en la terminal y en `observatorio_neo.log`:

```
[INFO] Iniciando ciclo diario del Observatorio NEO.
[INFO] Se obtuvieron N objetos NEO para hoy (AAAA-MM-DD).
[INFO] Objetos guardados/actualizados en MongoDB correctamente.
[INFO] Ciclo terminado. X objeto(s) generaron alerta de riesgo.
```

Que `X` sea 0 es lo habitual: la alerta exige que el objeto sea potencialmente peligroso y además pase muy cerca.

## Ejecución automática diaria (Windows)

Con el Programador de tareas de Windows se crea una tarea diaria con estos datos:

- Programa o script: ruta completa a `python.exe` dentro del `venv` del proyecto
- Argumentos: `main.py`
- Iniciar en: la carpeta del proyecto (necesario para que encuentre el `.env`)

## Limitaciones y notas

- La API de la NASA limita las consultas por hora: con la clave `DEMO_KEY` son pocas, y con una clave registrada el límite es mayor. El rango máximo por consulta al endpoint `/feed` es de 7 días.
- El scraping solo enriquece los objetos incluidos en `MAPA_WIKIPEDIA`, porque la mayoría de los asteroides del feed diario no tiene artículo en Wikipedia. El mapa se amplía manualmente.
- El contenido de Wikipedia se publica bajo licencia CC BY-SA; los datos tomados de ahí deben citarse como tal. Antes de ampliar el scraping a otros sitios conviene revisar sus términos de uso.
- Los clústeres gratuitos de MongoDB Atlas se pausan tras un periodo de inactividad. Si el ciclo falla con un error de DNS (`NXDOMAIN`), reanuda el clúster desde el panel de Atlas.

## Fuentes de datos

- NASA NeoWs (Near Earth Object Web Service): https://api.nasa.gov
- Wikipedia (infobox de cada asteroide): https://en.wikipedia.org
