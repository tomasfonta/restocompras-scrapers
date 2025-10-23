import requests
from bs4 import BeautifulSoup
import re
import os
import pandas as pd 
import json

# --- CONFIGURACIÓN ---
API_ENDPOINT = "http://localhost:8080/api/item" # Endpoint para la llamada POST
SUPPLIER_ID = 1                              # ID fijo para el campo supplierId
# Token de autenticación requerido para la API
AUTH_TOKEN = "eyJhbGciOiJIUzUxMiJ9.eyJzdWIiOiIxIiwiYXV0aG9yaXRpZXMiOlt7ImF1dGhvcml0eSI6IlJFQUQifSx7ImF1dGhvcml0eSI6IkRFTEVURSJ9LHsiYXV0aG9yaXR5IjoiQ1JFQVRFIn0seyJhdXRob3JpdHkiOiJVUERBVEUifV0sImlhdCI6MTc2MTE2ODEyNCwiZXhwIjoxNzYxMTcwNDAwfQ.I0J15T6sQl45OSNCxrFEsSVCRZtzhJ7XbnsXfrNs-_ja8A1o2rjsfJbUcFu-PuuRH-1WeYgj5NbTndo8_KM_iw"


URLS = [
    "https://greenshop.ar/categoria-producto/frutas/todas-las-frutas/",
    "https://greenshop.ar/categoria-producto/frutossecos/",
    "https://greenshop.ar/categoria-producto/vegetales/",
    "https://greenshop.ar/categoria-producto/almacen/",
    "https://greenshop.ar/categoria-producto/quesos/",
    "https://greenshop.ar/categoria-producto/condimentosyespecias/"
]
OUTPUT_FILENAME = "greenshop_datos_finales_limpios.xlsx"

# --- Funciones de limpieza y extracción ---

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

def post_to_api(product_data):
    """Realiza una llamada POST al endpoint con autenticación Bearer."""
    
    # Encabezados (Headers) para la solicitud, incluyendo la autenticación
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
        "productId": product_data.get("Producto ID", ""), 
        "unit": product_data["Unidad"],
        "quantity": product_data["Cantidad"], 
        "supplierId": product_data["supplierId"]
    }
    
    # NUEVO: Imprimir el cuerpo del request antes de enviarlo
    print("\n   --- Body del Request ---")
    print(json.dumps(payload, indent=2))
    print("   ------------------------")
    
    # Realizar la solicitud POST
    try:
        response = requests.post(API_ENDPOINT, json=payload, headers=headers, timeout=10)
        response.raise_for_status() # Lanza excepción para códigos 4xx/5xx
        print(f"   -> API POST exitoso para {product_data['Nombre']}. Status: {response.status_code}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"   -> ❌ API POST FALLÓ para {product_data['Nombre']}: {e}")
        return False


def scrape_single_category(url):
    """Raspa los productos de una sola URL y aplica el filtrado."""
    category_products_data = []
    
    print(f"\n-> Raspando URL: {url}")

    try:
        # Headers para el web scraping (imitar navegador)
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

        # 1. FILTRADO
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
            
        # Almacenar datos
        product_info = {
            "ID": "", 
            "Nombre": name,
            "Marca": "Green Shop", 
            "Descripción": name,
            "Precio": final_price_str,
            "Precio_Num": numeric_price,
            "Imagen": image_url,
            "Producto ID": "", 
            "Unidad": unit, 
            "Cantidad": quantity,
            "supplierId": SUPPLIER_ID
        }
        category_products_data.append(product_info)
        
        # 2. LLAMADA A LA API (Imprime el body antes de llamar a la API)
        post_to_api(product_info)
    
    return category_products_data

def write_to_excel_file(data, filename):
    """Escribe los datos combinados en un archivo de Excel (.xlsx) después de eliminar duplicados."""
    try:
        initial_count = len(data)
        df = pd.DataFrame(data)
        
        # Limpieza: Eliminar filas duplicadas
        df_cleaned = df.drop_duplicates(subset=["Nombre", "Precio", "Unidad", "Cantidad"])
        final_count = len(df_cleaned)
        duplicates_removed = initial_count - final_count

        # Asegurar el orden de las columnas solicitado (y excluir la columna temporal Precio_Num)
        COLUMNS_ORDER = ["ID", "Nombre", "Marca", "Descripción", "Precio", "Imagen", "Producto ID", "Unidad", "Cantidad", "supplierId"]
        df_cleaned = df_cleaned[COLUMNS_ORDER]
        
        # Escribir en Excel
        df_cleaned.to_excel(filename, index=False, engine='openpyxl')
        
        print(f"\n==========================================")
        print(f"✅ Extracción y procesamiento completados.")
        print(f"   Filas duplicadas eliminadas: {duplicates_removed}")
        print(f"✅ Productos finales guardados (limpios): {final_count}")
        print(f"✅ Datos guardados en: {os.path.abspath(filename)}")
        print(f"==========================================")

    except Exception as e:
        print(f"Ocurrió un error al escribir en el archivo: {e}")

# --- Bloque de ejecución principal ---

if __name__ == "__main__":
    print(f"Iniciando raspado de {len(URLS)} categorías, POST a API con Autenticación y exportación a Excel...")
    
    all_products = []
    
    for url in URLS:
        products = scrape_single_category(url)
        all_products.extend(products)
    
    if all_products:
        write_to_excel_file(all_products, OUTPUT_FILENAME)
    else:
        print("\nEl raspado falló, o no se extrajo ningún producto después del filtrado.")