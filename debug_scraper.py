"""
Script de diagnóstico temporal. Nos dice exactamente qué está pasando:
si la solicitud llega bien, si se encuentra la tabla infobox, y qué
etiquetas (th) contiene esa tabla.
"""

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "ObservatorioNEO-ProyectoEscolar/1.0 (contacto: tu_correo@ejemplo.com)"
}

url = "https://en.wikipedia.org/wiki/99942_Apophis"
respuesta = requests.get(url, headers=HEADERS, timeout=10)

print(f"Status code: {respuesta.status_code}")
print(f"Longitud del HTML recibido: {len(respuesta.text)} caracteres")
print(f"URL final (después de redirecciones, si hubo): {respuesta.url}")
print()

sopa = BeautifulSoup(respuesta.text, "html.parser")

# Busquemos CUALQUIER tabla con "infobox" en alguna de sus clases
tablas_infobox = sopa.find_all("table", class_=lambda c: c and "infobox" in c)
print(f"Tablas encontradas con 'infobox' en su clase: {len(tablas_infobox)}")

if tablas_infobox:
    primera = tablas_infobox[0]
    print(f"Clases exactas de la primera tabla: {primera.get('class')}")
    print()
    print("Etiquetas (th) encontradas en esa tabla:")
    for fila in primera.find_all("tr")[:15]:  # solo las primeras 15 filas
        etiqueta = fila.find("th")
        valor = fila.find("td")
        texto_etiqueta = etiqueta.get_text(strip=True) if etiqueta else None
        texto_valor = valor.get_text(strip=True)[:60] if valor else None
        print(f"  th={texto_etiqueta!r}  td={texto_valor!r}")
else:
    print("No se encontró ninguna tabla con 'infobox' en su clase.")
    print("Primeros 500 caracteres del HTML recibido, para inspeccionar:")
    print(respuesta.text[:500])
