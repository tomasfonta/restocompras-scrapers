import requests
from bs4 import BeautifulSoup
import re
import os
import pandas as pd 

# Configuración
# Lista COMPLETA de URLs a raspar
URLS = [
    "https://greenshop.ar/categoria-producto/frutas/todas-las-frutas/",
    "https://greenshop.ar/categoria-producto/frutossecos/",
    "https://greenshop.ar/categoria-producto/vegetales/",
    "https://greenshop.ar/categoria-producto/almacen/",
    "https://greenshop.ar/categoria-producto/quesos/",        # NUEVA
    "https://greenshop.ar/categoria-producto/condimentosyespecias/" # NUEVA
]
OUTPUT_FILENAME = "greenshop_datos_totales_filtrados.xlsx"

# --- Funciones de limpieza y extracción ---

def parse_product_title(full_title):
    """
    Separa el nombre del producto, la cantidad y la unidad, y estandariza las unidades.
    """
    # Regex para capturar un número seguido de una unidad (gr, kilos, etc.)
    match = re.search(r'(\d+)\s*(gr|kilos|kg|un\.|u\.|lb)\.?$', full_title, re.IGNORECASE)
    
    quantity = "N/A"
    unit = "UNIT"  # Valor por defecto si no se encuentra unidad
    name = full_title.strip()

    if match:
        raw_quantity = match.group(1).strip()
        raw_unit = match.group(2).strip().lower().replace('.', '')
        
        # 1. Estandarizar la unidad
        if raw_unit in ['gr', 'un', 'u', 'lb']:
            unit = "GR"
        elif raw_unit in ['kilos', 'kg']:
            unit = "KG"
        else:
            unit = "UNIT" 
            
        quantity = raw_quantity
        
        # 2. Eliminar la parte de cantidad y unidad del nombre
        name = re.sub(r'\s*(\d+)\s*(gr|kilos|kg|un\.|u\.|lb)\.?$', '', full_title, flags=re.IGNORECASE).strip()

    return name, quantity, unit

def clean_price(price_text):
    """Elimina el símbolo '$' y convierte el precio a un valor numérico/cadena limpio."""
    cleaned_price = price_text.replace('$', '').replace('.', '').replace(',', '.').strip()
    
    try:
        numeric_price = float(cleaned_price)
        return numeric_price, str(cleaned_price)
    except ValueError:
        return 0.0, price_text.strip()

def scrape_single_category(url):
    """Raspa los productos de una sola URL y aplica el filtrado."""
    category_products_data = []
    
    print(f"-> Raspando URL: {url}")

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.60 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=15)
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
        # Extraer Estado (para filtrar)
        status = "AGOTADO" if item.select_one('.out-of-stock-label') else "EN STOCK"
        
        # Extraer Precio
        price_tag = item.select_one('.price .amount') or item.select_one('.price bdi')
        price_text = price_tag.text.strip() if price_tag else "$0"
        
        # Limpiar y obtener el valor numérico del precio
        numeric_price, final_price_text = clean_price(price_text)

        # 1. FILTRADO: Eliminar si está AGOTADO o si el precio es 0
        if status == "AGOTADO" or numeric_price == 0.0:
            continue # Saltar este producto

        # Continuar con la extracción 
        title_tag = item.select_one('.product-title a')
        full_title = title_tag.text.strip() if title_tag else "N/A"
        
        name, quantity, unit = parse_product_title(full_title)
        
        # Descripción (Categoría)
        category_tag = item.select_one('.box-category a')
        description = category_tag.text.strip() if category_tag else "N/A"
        
        # Campos sin datos visibles
        marca = "" 
        product_id = "" 
            
        # URL de Imagen
        img_tag = item.select_one('.box-image img')
        image_url = img_tag.get('data-src') or img_tag.get('src') if img_tag else ""
        
        if image_url and image_url.startswith('/'):
            image_url = requests.compat.urljoin(url, image_url)
            
        # Añadir datos a la lista
        category_products_data.append({
            "ID": "", 
            "Nombre": name,
            "Marca": marca,
            "Descripción": description,
            "Precio": final_price_text, 
            "Imagen": image_url,
            "Producto ID": product_id,
            "Unidad": unit, 
            "Cantidad": quantity
        })
    
    return category_products_data

def write_to_excel_file(data, filename):
    """Escribe los datos combinados en un archivo de Excel (.xlsx)."""
    try:
        df = pd.DataFrame(data)
        
        # Asegurar el orden de las columnas solicitado
        COLUMNS_ORDER = ["ID", "Nombre", "Marca", "Descripción", "Precio", "Imagen", "Producto ID", "Unidad", "Cantidad"]
        df = df[COLUMNS_ORDER]
        
        # Escribir en Excel
        df.to_excel(filename, index=False, engine='openpyxl')
        
        print(f"\n✅ Extracción y filtrado exitosos.")
        print(f"✅ Productos totales guardados (solo EN STOCK y Precio > 0): {len(data)}")
        print(f"✅ Datos combinados guardados en: {os.path.abspath(filename)}")

    except Exception as e:
        print(f"Ocurrió un error al escribir en el archivo: {e}")

# --- Bloque de ejecución principal ---

if __name__ == "__main__":
    print(f"Iniciando raspado de {len(URLS)} categorías...")
    
    all_products = []
    
    for url in URLS:
        products = scrape_single_category(url)
        all_products.extend(products)
    
    if all_products:
        write_to_excel_file(all_products, OUTPUT_FILENAME)
    else:
        print("\nEl raspado falló, o no se extrajo ningún producto después del filtrado.")