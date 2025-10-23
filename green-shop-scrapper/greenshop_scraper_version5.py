import requests
from bs4 import BeautifulSoup
import re
import os
import pandas as pd 

# Configuración
URL = "https://greenshop.ar/categoria-producto/frutas/todas-las-frutas/"
OUTPUT_FILENAME = "greenshop_frutas_filtrado_estandarizado.xlsx"

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
            unit = "UNIT" # Si encuentra algo pero no lo mapea
            
        quantity = raw_quantity
        
        # 2. Eliminar la parte de cantidad y unidad del nombre
        # Usamos la misma expresión regular para limpiar el título
        name = re.sub(r'\s*(\d+)\s*(gr|kilos|kg|un\.|u\.|lb)\.?$', '', full_title, flags=re.IGNORECASE).strip()

    # Manejar el caso de títulos que son solo la fruta sin cantidad/unidad explícita
    if not match:
        # Se asume que el nombre es el título completo, y la unidad es "UNIT"
        pass 

    return name, quantity, unit

def clean_price(price_text):
    """Elimina el símbolo '$' y convierte el precio a un valor numérico/cadena limpio."""
    # Eliminar '$', reemplazar el punto de miles por nada, y el separador decimal (si existe) por punto.
    cleaned_price = price_text.replace('$', '').replace('.', '').replace(',', '.').strip()
    
    try:
        numeric_price = float(cleaned_price)
        # Devolver el precio limpio como string para el Excel, y el valor numérico para la lógica
        return numeric_price, str(cleaned_price)
    except ValueError:
        return 0.0, price_text.strip() # En caso de error, asumir 0.0 y mantener el texto original

def scrape_products(url):
    """Filtra y extrae los datos del producto."""
    products_data = []

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.60 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status() 
    except requests.exceptions.RequestException as e:
        print(f"Error al obtener la página: {e}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    product_items = soup.select('.product-small')

    if not product_items:
        print("No se encontraron elementos de producto.")
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

        # Continuar con la extracción si el producto no fue filtrado
        title_tag = item.select_one('.product-title a')
        full_title = title_tag.text.strip() if title_tag else "N/A"
        
        name, quantity, unit = parse_product_title(full_title)
        
        # Descripción (Categoría)
        category_tag = item.select_one('.box-category a')
        description = category_tag.text.strip() if category_tag else "Fruta"
        
        # Campos sin datos visibles
        marca = "" 
        product_id = "" 
            
        # URL de Imagen
        img_tag = item.select_one('.box-image img')
        image_url = img_tag.get('data-src') or img_tag.get('src') if img_tag else ""
        
        if image_url and image_url.startswith('/'):
            image_url = requests.compat.urljoin(url, image_url)
            
        # Añadir datos a la lista
        products_data.append({
            "ID": "", 
            "Nombre": name,
            "Marca": marca,
            "Descripción": description,
            "Precio": final_price_text, 
            "Imagen": image_url,
            "Producto ID": product_id,
            "Unidad": unit, # Unidad estandarizada
            "Cantidad": quantity
        })
    
    return products_data

def write_to_excel_file(data, filename):
    """Escribe los datos filtrados y estandarizados en un archivo de Excel (.xlsx)."""
    try:
        df = pd.DataFrame(data)
        
        # Asegurar el orden de las columnas solicitado
        COLUMNS_ORDER = ["ID", "Nombre", "Marca", "Descripción", "Precio", "Imagen", "Producto ID", "Unidad", "Cantidad"]
        df = df[COLUMNS_ORDER]
        
        # Escribir en Excel
        df.to_excel(filename, index=False, engine='openpyxl')
        
        print(f"\n✅ Extracción y filtrado exitosos.")
        print(f"✅ Productos guardados (solo EN STOCK y Precio > 0): {len(data)}")
        print(f"✅ Datos guardados en: {os.path.abspath(filename)}")

    except Exception as e:
        print(f"Ocurrió un error al escribir en el archivo: {e}")

# Bloque de ejecución principal
if __name__ == "__main__":
    print(f"Iniciando raspado y estandarización de unidades para: {URL}")
    products = scrape_products(URL)
    
    if products:
        write_to_excel_file(products, OUTPUT_FILENAME)
    else:
        print("El raspado falló, no se extrajo ningún dato, o todos los productos fueron filtrados.")