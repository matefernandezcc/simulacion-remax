import requests
import csv
import time
import json
from datetime import datetime
import os
import re
from urllib.parse import urlencode

class RedRemaxAPI:
    def __init__(self, auth_token, base_url=None):
        self.auth_token = auth_token
        self.base_url = base_url or "https://secureservices.redremax.com/v1/webapi/acmprop"
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': auth_token,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Content-Type': 'application/json'
        })
    
    def hacer_peticion(self, pagina=91, tamano_pagina=500, reintentos=3, delay_intentos=10):
        """Hace petición a la API con paginación, con reintentos y delay entre fallos"""

        # Parámetros fijos (los que no son listas)
        params = {
            'radio': 10,
            'type': 'venta',
            'dateFrom': '2015-01-23',
            'dateTo': datetime.now().strftime('%Y-%m-%d'),
            'currency': 'U$S',
            'pagesize': tamano_pagina,
            'orderby': '-approvedAt',
            'page': pagina
        }

        # Parámetros múltiples (listas)
        multi_params = [
            ('polygon[]', '-58.53034973144532,-34.63433785730249'),
            ('polygon[]', '-58.36624145507813,-34.62190760563037'),
            ('polygon[]', '-58.37276458740235,-34.590258562965786'),
            ('polygon[]', '-58.41567993164063,-34.562838485444765'),
            ('polygon[]', '-58.46408843994141,-34.53456089748654'),
            ('polygon[]', '-58.50219726562501,-34.55068030023981'),
            ('polygon[]', '-58.531723022460945,-34.6145615816082'),
            ('propertytype[]', 'Departamento Dúplex'),
            ('propertytype[]', 'Departamento Estándar'),
            ('propertytype[]', 'Departamento Loft'),
            ('propertytype[]', 'Departamento Monoambiente'),
            ('propertytype[]', 'Departamento Penthouse'),
            ('propertytype[]', 'Departamento Piso'),
            ('propertytype[]', 'Departamento SemiPiso'),
            ('propertytype[]', 'Departamento Triplex'),
            ('propertytype[]', 'Casa'),
            ('propertytype[]', 'Casa Dúplex'),
            ('propertytype[]', 'Casa Triplex'),
            ('inStatus[]', 'active'),
            ('inStatus[]', 'completed'),
            ('inStatus[]', 'canceled'),
            ('inStatus[]', 'expired')
        ]

        all_params = list(params.items()) + multi_params

        for intento in range(1, reintentos + 1):
            try:
                print(f"Obteniendo página {pagina} ({tamano_pagina} propiedades)... Intento {intento}/{reintentos}")

                response = self.session.get(self.base_url, params=all_params, timeout=4000)

                if response.status_code == 500:
                    print(f"Error HTTP 500, esperando {delay_intentos} s antes de reintentar...")
                    time.sleep(30)
                    continue  # vuelve a intentar la misma página

                if response.status_code != 200:
                    print(f"Error HTTP: {response.status_code}")
                    return None

                # decodificar JSON
                datos = response.json()
                return datos

            except requests.exceptions.Timeout:
                print(f"Timeout en la página {pagina}, esperando {delay_intentos} s antes de reintentar...")
                time.sleep(delay_intentos)
            except requests.exceptions.RequestException as e:
                print(f"Error en la petición: {e}, esperando {delay_intentos} s antes de reintentar...")
                time.sleep(delay_intentos)
            except json.JSONDecodeError as e:
                print(f"Error decodificando JSON: {e}, esperando {delay_intentos} s antes de reintentar...")
                time.sleep(delay_intentos)

        print(f"No se pudo obtener la página {pagina} después de {reintentos} intentos.")
        return None

    
    def obtener_total_propiedades(self):
        """Obtiene el total de propiedades disponibles"""
        print("Obteniendo total de propiedades...")
        
        datos = self.hacer_peticion(pagina=1, tamano_pagina=1)
        if datos and 'searchFilter' in datos:
            total = datos['searchFilter'].get('totalItems', 0)
            print(f"Total items encontrado: {total}")
            return total
        return 0

def limpiar_texto(texto):
    """Limpia el texto removiendo saltos de línea y caracteres problemáticos para CSV"""
    if not texto:
        return ""
    
    # Convertir a string si no lo es
    texto = str(texto)
    
    # Remover saltos de línea, tabs y retornos de carro
    texto = re.sub(r'[\r\n\t]+', ' ', texto)
    
    # Remover múltiples espacios consecutivos
    texto = re.sub(r'\s+', ' ', texto)
    
    # Limpiar comillas problemáticas
    texto = texto.replace('"', "'")
    
    return texto.strip()

def procesar_propiedad(propiedad):
    """Extrae los campos principales de una propiedad"""
    
    # Manejar datos anidados de forma segura
    propiedad_data = propiedad.get('data', {})
    precio = propiedad_data.get('publish_price', {})
    direccion = propiedad_data.get('address', {})
    
    # VERIFICACIÓN ROBUSTA PARA SALE_PRICE (solo para propiedades vendidas)
    sale_price_data = propiedad_data.get('sale_price')
    fecha_venta = ''
    precio_venta_usd = ''
    precio_venta_ars = ''
    comision_venta = ''
    
    # Verificar si sale_price existe y tiene datos válidos
    if sale_price_data is not None:
        if isinstance(sale_price_data, dict) and sale_price_data:
            # Es un diccionario con datos de venta
            fecha_venta = sale_price_data.get('Fecha', '')
            precio_venta_usd = sale_price_data.get('USD', '')
            precio_venta_ars = sale_price_data.get('ARS', '')
            comision_venta = sale_price_data.get('commission', '')
        elif sale_price_data:
            # En caso de que sea otro tipo de dato (string, número, etc.)
            fecha_venta = 'Datos disponibles'
            precio_venta_usd = str(sale_price_data)
    
    # Extraer información del historial de precios
    price_history = propiedad_data.get('price_history', [])
    
    # Variables para el historial
    historial_precios = []
    fecha_historial_reciente = ''
    precio_historial_reciente_usd = ''
    
    # Procesar todo el historial de precios
    for i, hist in enumerate(price_history):
        fecha = hist.get('date', '')
        precio_usd = hist.get('USD', '')
        
        # Para el registro más reciente
        if i == 0:
            fecha_historial_reciente = fecha
            precio_historial_reciente_usd = precio_usd
        
        # Agregar al historial completo
        if fecha and precio_usd:
            historial_precios.append(f"{fecha}:{precio_usd}")
    
    # Unir todo el historial en un string
    historial_completo = '; '.join(historial_precios) if historial_precios else ''

    # Extraer dimensiones
    dimensions = propiedad_data.get('dimensions', {})
    
    # Limpiar todos los textos para CSV
    descripcion_limpia = limpiar_texto(propiedad_data.get('description', ''))
    titulo_limpio = limpiar_texto(propiedad_data.get('title', ''))
    direccion_limpia = limpiar_texto(direccion.get('display_address', ''))
    barrio_limpio = limpiar_texto(direccion.get('city', ''))
    ciudad_limpia = limpiar_texto(direccion.get('region', ''))
    
    return {
        'id_oficina': propiedad_data.get('id', ''),
        'titulo': titulo_limpio,
        'tipo_propiedad': propiedad_data.get('propertyType', ''),
        'precio_usd': precio.get('USD', ''),
        'precio_ars': precio.get('ARS', ''),
        'estado': propiedad_data.get('status', ''),
        'fecha_creacion': propiedad_data.get('createdOn', ''),
        'fecha_aprobacion': propiedad_data.get('approvedAt', ''),
        'fecha_expiracion': propiedad_data.get('expiresOn', ''),
        
        # Campos de venta (con verificación robusta)
        'fecha_venta': fecha_venta,
        'precio_venta_USD': precio_venta_usd,
        'precio_venta_ARS': precio_venta_ars,
        'comision_venta': comision_venta,
        
        'direccion': direccion_limpia,
        'barrio': barrio_limpio,
        'ciudad': ciudad_limpia,
        'habitaciones': propiedad_data.get('bedrooms', ''),
        'banios': propiedad_data.get('bathrooms', ''),
        'living': propiedad_data.get('living_area', ''),
        'metros_cubiertos': dimensions.get('covered', ''),
        'metros_totales': dimensions.get('totalBuilt', ''),
        'anio_construccion': propiedad_data.get('yearBuild', ''),
        'apt_credit': propiedad_data.get('aptCredit', ''),
        'descripcion': descripcion_limpia[:300],
        
        # Campos del historial de precios
        'fecha_historial_reciente': fecha_historial_reciente,
        'precio_historial_reciente_usd': precio_historial_reciente_usd,
        'historial_precios_completo': historial_completo,

        #Vistas 
        'vistas': propiedad_data.get('countViews', ''),
        'contactos': propiedad_data.get('countContacts', ''),

    }

def guardar_propiedades_csv(propiedades, archivo_csv, es_primera_pagina=True):
    """Guarda las propiedades en un archivo CSV con formato correcto"""

    campos = [
        'id_oficina', 'titulo', 'tipo_propiedad', 'precio_usd', 'precio_ars', 
        'estado', 'fecha_creacion', 'fecha_aprobacion', 'fecha_expiracion',
        'fecha_venta', 'precio_venta_USD', 'precio_venta_ARS', 'comision_venta',
        'direccion', 'barrio', 'ciudad', 'habitaciones', 'banios', 'living',
        'metros_cubiertos', 'metros_totales', 'anio_construccion', 'id_oficina',
        'apt_credit', 'descripcion', 'fecha_historial_reciente', 
        'precio_historial_reciente_usd', 'historial_precios_completo','vistas','contactos'
    ]
        
    try:
        modo = 'w' if es_primera_pagina else 'a'
        
        # Usar quoting=csv.QUOTE_ALL para evitar problemas con comas en los textos
        with open(archivo_csv, modo, newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=campos, quoting=csv.QUOTE_ALL)
            
            if es_primera_pagina:
                writer.writeheader()
                print(f"Creando archivo CSV: {archivo_csv}")
            
            # Procesar y escribir cada propiedad
            propiedades_guardadas = 0
            for prop_id, propiedad_data in propiedades.items():
                try:
                    # Crear estructura temporal para procesar
                    prop_temp = {'data': propiedad_data}
                    propiedad_procesada = procesar_propiedad(prop_temp)
                    
                    # Asegurar que todos los valores sean strings y estén limpios
                    for key, value in propiedad_procesada.items():
                        if value is None:
                            propiedad_procesada[key] = ''
                        else:
                            propiedad_procesada[key] = str(value)
                    
                    writer.writerow(propiedad_procesada)
                    propiedades_guardadas += 1
                    
                except Exception as e:
                    print(f"Error procesando propiedad {prop_id}: {e}")
                    continue
            
            print(f"Guardadas {propiedades_guardadas} propiedades en el CSV")
            return propiedades_guardadas
            
    except Exception as e:
        print(f"Error guardando CSV: {e}")
        return 0

def mostrar_preview_csv(archivo_csv, num_lineas=5):
    """Muestra un preview del archivo CSV de forma legible"""
    try:
        print(f"\nPREVIEW del archivo {archivo_csv}:")
        print("="*80)
        
        with open(archivo_csv, 'r', encoding='utf-8-sig') as f:
            lineas = f.readlines()
            
            # Mostrar header
            if lineas:
                print("HEADER:")
                print(lineas[0].strip())
                print("-"*80)
            
            # Mostrar primeras propiedades
            for i, linea in enumerate(lineas[1:num_lineas+1], 1):
                print(f"Línea {i}: {linea.strip()}")
                
        print("="*80)
        print(f"Total de líneas en el archivo: {len(lineas)}")
        
    except Exception as e:
        print(f"Error mostrando preview: {e}")

def mostrar_ejemplo_propiedad():
    """Muestra un ejemplo de cómo se verán los datos en el CSV"""
    AUTH_TOKEN = "TOKEN_AQUI"  # Reemplazar con un token válido
    
    api = RedRemaxAPI(AUTH_TOKEN)
    datos = api.hacer_peticion(pagina=1, tamano_pagina=1)
    
    if datos and 'data' in datos:
        propiedades = datos.get('data', {})
        if propiedades:
            primera_prop_id = next(iter(propiedades.keys()))
            prop_temp = {'data': propiedades[primera_prop_id]}
            ejemplo = procesar_propiedad(prop_temp)
            
            print("📋 EJEMPLO DE UNA PROPIEDAD PROCESADA:")
            print("="*60)
            for key, value in ejemplo.items():
                # Mostrar solo los primeros 50 caracteres para no saturar la pantalla
                valor_recortado = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
                print(f"{key}: {valor_recortado}")
            print("="*60)

def main():
    # Configuración
    AUTH_TOKEN = "TOKEN_AQUI"    
    ARCHIVO_CSV = "propiedades_redremax.csv"
    PROPIEDADES_POR_PAGINA = 500  # Máximo permitido por la API
    DELAY_ENTRE_PAGINAS = 10  # Segundos entre peticiones
    
    # Inicializar API
    api = RedRemaxAPI(AUTH_TOKEN)
    
    print("Iniciando descarga de propiedades de RedRemax...")
    
    # Obtener total de propiedades
    total = api.obtener_total_propiedades()
    if total == 0:
        print("No se pudieron obtener los datos de la API")
        return
    
    print(f"Total de propiedades encontradas: {total}")
    total_paginas = (total + PROPIEDADES_POR_PAGINA - 1) // PROPIEDADES_POR_PAGINA
    print(f"Total de páginas a descargar: {total_paginas}")
    
    # Archivo temporal para evitar corrupción
    archivo_temporal = f"temp_{ARCHIVO_CSV}"
    total_propiedades_guardadas = 0
    time.sleep(10)
    try:
        for pagina in range(1, total_paginas + 1):
            print(f"\nProcesando página {(pagina + 91)} de {total_paginas}...")
            
            # Hacer petición
            datos = api.hacer_peticion((pagina + 91), PROPIEDADES_POR_PAGINA)
            
            if not datos or 'data' not in datos:
                print(f"Error en página {(pagina + 91)}, saltando...")
                continue
            
            propiedades = datos.get('data', {})
            print(f"Página {pagina}: {len(propiedades)} propiedades obtenidas")
            
            if not propiedades:
                print("No hay más propiedades, terminando...")
                break
            
            # Guardar en CSV
            es_primera_pagina = (pagina == 1)
            guardadas = guardar_propiedades_csv(propiedades, archivo_temporal, es_primera_pagina)
            total_propiedades_guardadas += guardadas
            
            # Progress bar simple
            progreso = (pagina / total_paginas) * 100
            print(f"Progreso: {progreso:.1f}% ({pagina}/{total_paginas})")
            print(f"Total acumulado: {total_propiedades_guardadas} propiedades")
            
            # Delay para no saturar la API
            if pagina < total_paginas:
                print(f"Esperando {DELAY_ENTRE_PAGINAS} segundos...")
                time.sleep(DELAY_ENTRE_PAGINAS)
        
        # Renombrar archivo temporal al final
        if os.path.exists(archivo_temporal):
            os.rename(archivo_temporal, ARCHIVO_CSV)
            print(f"\n¡Descarga completada!")
            print(f"Archivo guardado como: {ARCHIVO_CSV}")
            print(f"Total de propiedades descargadas: {total_propiedades_guardadas}")
            
            # Mostrar preview del archivo final
            mostrar_preview_csv(ARCHIVO_CSV)
            
    except KeyboardInterrupt:
        print("\nDescarga interrumpida por el usuario")
        if os.path.exists(archivo_temporal):
            os.rename(archivo_temporal, f"interrumpido_{ARCHIVO_CSV}")
            print(f"Datos parciales guardados en: interrumpido_{ARCHIVO_CSV}")
            mostrar_preview_csv(f"interrumpido_{ARCHIVO_CSV}")
    except Exception as e:
        print(f"\nError inesperado: {e}")
        if os.path.exists(archivo_temporal):
            os.rename(archivo_temporal, f"error_{ARCHIVO_CSV}")

if __name__ == "__main__":
    # Primero mostrar un ejemplo de cómo se verán los datos
    mostrar_ejemplo_propiedad() # Sirve para saber si se esta guardando bien los datos 
    
    # Preguntar si continuar con la descarga completa
    
    respuesta = input("\n¿Deseas continuar con la descarga completa? (s/n): ")
    if respuesta.lower() == 's':
        main()
    else:
      print("Descarga cancelada.")