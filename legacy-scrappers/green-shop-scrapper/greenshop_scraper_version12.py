import requests
from bs4 import BeautifulSoup
import re
import os
import pandas as pd 
import json
from urllib.parse import quote

# --- CONFIGURACIÓN DE ENDPOINTS Y AUTENTICACIÓN ---
API_ENDPOINT = "http://localhost:8080/api/item"                       # Endpoint para la llamada POST de guardado
PRODUCTS_API_SEARCH = "http://localhost:8080/api/products/search/best-match" # Nuevo Endpoint para buscar el ID
SUPPLIER_ID = 1                                                         # ID fijo para el campo supplierId

# Token de autenticación requerido para ambas APIs
AUTH_TOKEN = "eyJhbGciOiJIUzUxMiJ9.eyJzdWIiOiIxIiwiYXV0aG9yaXRpZXMiOlt7ImF1dGhvcml0eSI6IlJFQUQifSx7ImF1dGhvcml0eSI6IkRFTEVURSJ9LHsiYXV0aG9yaXR5IjoiQ1JFQVRFIn0seyJhdXRob3JpdHkiOiJVUERBVEUifV0sImlhdCI6MTc2MTIzMDY0MCwiZXhwIjoxNzYxMjU2ODAwfQ.66FkEYEM8EzA_cY3rVXUdNwWldgDTQ1hrS-OSJYv5auHV6D5UggmcbzkpHbkJd1AsUCAfK05bDOTDNX9m90Pyg"

URLS = [
    "https://greenshop.ar/categoria-producto/frutas/todas-las-frutas/",
    "https://greenshop.ar/categoria-producto/frutossecos/",
    "https://greenshop.ar/categoria-producto/vegetales/",
    "https://greenshop.ar/categoria-producto/almacen/",
    "https://greenshop.ar/categoria-producto/quesos/",
    "https://greenshop.ar/categoria-producto/condimentosyespecias/"
]
OUTPUT_FILENAME = "greenshop_datos_finales_limpios.xlsx"

# --- Funciones de Utilidad (sin cambios) ---

def parse_product_title(full_title):
    """
    Separa el nombre del producto, la cantidad y la unidad, y estandariza las unidades.
    """
    match = re.search(r'(\d+)\s*(gr|kilos|kg|un\.|u\.|lb)\.?$', full_title, re.IGNORECASE)
    
    quantity = "N/A"
    unit = "UNIT"
    name = full_title.strip()

    if match:
        raw_quantity = match.group(1).strip()
        raw_unit = match.group(2).strip().lower().replace('.', '')
        
        # Estandarizar la unidad
        if raw_unit in ['gr', 'un', 'u', 'lb']:
            unit = "G"
        elif raw_unit in ['kilos', 'kg']:
            unit = "KG"
        else:
            unit = "UNIT"
            
        quantity = raw_quantity
        
        # Eliminar la parte de cantidad y unidad del nombre
        name = re.sub(r'\s*(\d+)\s*(gr|kilos|kg|un\.|u\.|lb)\.?$', '', full_title, flags=re.IGNORECASE).strip()

    # Si la unidad es UNIT, establecer la cantidad a 1
    if unit == "UNIT":
        quantity = "1"
        
    return name, quantity, unit

def clean_price(price_text):
    """Elimina el símbolo '$', limpia el formato y convierte el precio a float para la API."""
    cleaned_price_str = price_text.replace('$', '').replace('.', '').replace(',', '.').strip()
    
    try:
        numeric_price = float(cleaned_price_str)
        return numeric_price, str(int(numeric_price)) 
    except ValueError:
        return 0.0, price_text.strip()

# --- Funciones de API (MODIFICADA) ---

def fetch_product_id(product_name):
    """
    Consulta la API de búsqueda para obtener el ID del producto (best-match).
    Busca específicamente la clave 'productId' en la respuesta.
    Retorna el 'productId' si se encuentra, de lo contrario, retorna None.
    """
    
    encoded_query = quote(product_name)
    search_url = f"{PRODUCTS_API_SEARCH}?query={encoded_query}"
    
    headers = {
        "Authorization": f"Bearer {AUTH_TOKEN}"
    }
    
    try:
        response = requests.get(search_url, headers=headers, timeout=5)
        response.raise_for_status() 

        data = response.json()
        
        # --- CAMBIO CRÍTICO AQUÍ ---
        # Si la respuesta es un objeto y contiene la clave 'productId'
        if isinstance(data, dict) and 'productId' in data and data['productId'] is not None:
            product_id = data['productId']
            # print(f"   -> ID encontrado para '{product_name}': {product_id}")
            return product_id
        # -----------------------------
        
        print(f"   -> ❌ Búsqueda fallida para '{product_name}'. Respuesta no contiene 'productId' o es nulo. Respuesta: {data}")
        return None

    except requests.exceptions.RequestException as e:
        print(f"   -> ❌ API GET FALLÓ para '{product_name}' ({search_url}): {e}")
        return None
    except json.JSONDecodeError:
        print(f"   -> ❌ Respuesta no es JSON válida para '{product_name}'. Texto: {response.text[:100]}...")
        return None


def post_to_api(product_data):
    """Realiza una llamada POST al endpoint con autenticación Bearer."""
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AUTH_TOKEN}"
    }

    # Cuerpo de la solicitud (Payload)
    payload = {
        "name": product_data["Nombre"],
        "description": product_data["Descripción"],
        "price": product_data["Precio_Num"], 
        "image": product_data["Imagen"],
        "productId": product_data["Producto ID"], # Usando el ID dinámico
        "unit": product_data["Unidad"],
        "quantity": product_data["Cantidad"], 
        "supplierId": product_data["supplierId"]
    }
    
    try:
        response = requests.post(API_ENDPOINT, json=payload, headers=headers, timeout=10)
        response.raise_for_status() 
        print(f"   -> ✅ API POST exitoso para {product_data['Nombre']} (ID: {product_data['Producto ID']}). Status: {response.status_code}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"   -> ❌ API POST FALLÓ para {product_data['Nombre']}: {e}")
        return False


# --- Funciones de Scraping y Utilidades (sin cambios) ---

def scrape_single_category(url):
    """
    Raspa los productos de una sola URL, aplica el filtrado,
    y DEVUELVE la lista de productos.
    """
    category_products_data = []
    
    print(f"\n-> Raspando URL: {url}")

    try:
        headers_scrape = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.60 Safari/537.36'}
        response = requests.get(url, headers=headers_scrape, timeout=15)
        response.raise_for_status() 
    except requests.exceptions.RequestException as e:
        print(f"   Error al obtener la página {url}: {e}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    product_items = soup.select('.product-small')

    if not product_items:
        print(f"   No se encontraron elementos de producto en {url}.")
        return []

    for item in product_items:
        status = "AGOTADO" if item.select_one('.out-of-stock-label') else "EN STOCK"
        price_tag = item.select_one('.price .amount') or item.select_one('.price bdi')
        price_text = price_tag.text.strip() if price_tag else "$0"
        
        numeric_price, final_price_str = clean_price(price_text)

        # FILTRADO
        if status == "AGOTADO" or numeric_price == 0.0:
            continue

        # Extracción
        title_tag = item.select_one('.product-title a')
        full_title = title_tag.text.strip() if title_tag else "N/A"
        name, quantity, unit = parse_product_title(full_title)
            
        img_tag = item.select_one('.box-image img')
        image_url = img_tag.get('data-src') or img_tag.get('src') if img_tag else ""
        if image_url and image_url.startswith('/'):
            image_url = requests.compat.urljoin(url, image_url)
            
        # Almacenar datos (Producto ID se deja temporalmente como None)
        product_info = {
            # Claves de Identificación para Deduplicación
            "Nombre": name,
            "Unidad": unit, 
            "Cantidad": quantity,
            
            # Resto de los datos
            "ID": "", 
            "Marca": "Green Shop", 
            "Descripción": name,
            "Precio": final_price_str,
            "Precio_Num": numeric_price,
            "Imagen": image_url,
            "Producto ID": None, # <-- Se inicializa en None
            "supplierId": SUPPLIER_ID
        }
        category_products_data.append(product_info)
        
    return category_products_data

def deduplicate_products(products_list):
    """
    Elimina los diccionarios duplicados basándose en una clave única
    (Nombre + Unidad + Cantidad)
    """
    unique_products = {}
    
    for product in products_list:
        unique_key = (product["Nombre"], product["Unidad"], product["Cantidad"])
        
        if unique_key not in unique_products:
            unique_products[unique_key] = product
            
    return list(unique_products.values())


def write_to_excel_file(data, filename):
    """Escribe los datos combinados en un archivo de Excel (.xlsx)."""
    try:
        df = pd.DataFrame(data)
        
        # Asegurar el orden de las columnas solicitado (y excluir la columna temporal Precio_Num)
        COLUMNS_ORDER = ["ID", "Nombre", "Marca", "Descripción", "Precio", "Imagen", "Producto ID", "Unidad", "Cantidad", "supplierId"]
        df = df[COLUMNS_ORDER]
        
        # Escribir en Excel
        df.to_excel(filename, index=False, engine='openpyxl')
        
        print(f"✅ Productos finales guardados (limpios): {len(data)}")
        print(f"✅ Datos guardados en: {os.path.abspath(filename)}")

    except Exception as e:
        print(f"Ocurrió un error al escribir en el archivo: {e}")

# --- Bloque de ejecución principal (sin cambios) ---

if __name__ == "__main__":
    print(f"Iniciando raspado de {len(URLS)} categorías, deduplicación, búsqueda de IDs y POST a API...")
    
    all_products_raw = []
    
    # 1. RASPADO (Recolección de datos)
    for url in URLS:
        products = scrape_single_category(url)
        all_products_raw.extend(products)
    
    if not all_products_raw:
        print("\nEl raspado falló, o no se extrajo ningún producto.")
        exit()

    print(f"\n--- TOTAL RASPADO: {len(all_products_raw)} productos ---")
    
    # 2. DEDUPLICACIÓN
    final_unique_products = deduplicate_products(all_products_raw)
    duplicates_removed = len(all_products_raw) - len(final_unique_products)
    
    print(f"--- DEDUPLICACIÓN: {duplicates_removed} duplicados eliminados. Únicos: {len(final_unique_products)} ---")
    
    # 3. BÚSQUEDA DE ID y LLAMADA A LA API (Solo para productos únicos)
    print("\n\n--- INICIANDO BÚSQUEDA DE ID Y LLAMADAS A LA API ---")
    
    products_to_export = []
    api_success_count = 0
    
    for product in final_unique_products:
        product_name = product["Nombre"]
        
        # PASO A: Buscar el ID del producto (ahora busca 'productId')
        product_id = fetch_product_id(product_name)
        
        if product_id is not None:
            # PASO B: Asignar el ID encontrado
            product["Producto ID"] = product_id
            
            # PASO C: Realizar el POST a la API
            if post_to_api(product):
                api_success_count += 1
                products_to_export.append(product)
        else:
            print(f"   -> ⚠️ SKIPPING POST para {product_name}: No se pudo obtener el 'productId'.")
            
    print("\n==========================================")
    print(f"✅ Proceso COMPLETADO.")
    print(f"   Total de productos ÚNICOS procesados: {len(final_unique_products)}")
    print(f"   Llamadas API POST exitosas: {api_success_count}")
    print(f"==========================================")

    # 4. EXPORTACIÓN A EXCEL
    if products_to_export:
        write_to_excel_file(products_to_export, OUTPUT_FILENAME)