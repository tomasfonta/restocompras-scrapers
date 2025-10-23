import requests
from bs4 import BeautifulSoup
import re
import os
import pandas as pd 

# Configuración
URL = "https://greenshop.ar/categoria-producto/frutas/todas-las-frutas/"
OUTPUT_FILENAME = "greenshop_frutas_filtrado.xlsx"

def parse_product_title(full_title):
    """
    Separa el nombre del producto, la cantidad y la unidad.
    """
    # Regex para capturar un número seguido de una unidad (gr, kilos, etc.)
    match = re.search(r'(\d+)\s*(gr|kilos|kg|un\.|u\.|lb)\.?$', full_title, re.IGNORECASE)
    
    if match:
        quantity = match.group(1).strip()
        unit = match.group(2).strip()
        # Eliminar la parte de cantidad y unidad del nombre
        name = re.sub(r'\s*(\d+)\s*(gr|kilos|kg|un\.|u\.|lb)\.?$', '', full_title, flags=re.IGNORECASE).strip()
    else:
        name = full_title.strip()
        quantity = "N/A"
        unit = "N/A"

    return name, quantity, unit

def clean_price(price_text):
    """Elimina el símbolo '$' y convierte el precio a un valor numérico/cadena limpio."""
    cleaned_price = price_text.replace('$', '').replace('.', '').replace(',', '.').strip()
    # Intentar convertir a flotante para manejar la comparación a 0
    try:
        return float(cleaned_price), str(cleaned_price)
    except ValueError:
        return 0.0, str(cleaned_price) # Devolver 0.0 si no es convertible (ej. si es solo texto)

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
        # Extraer Estado (para filtrar primero)
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
        
        # Descripción/Marca/Producto ID
        category_tag = item.select_one('.box-category a')
        description = category_tag.text.strip() if category_tag else "Fruta"
        
        # En esta web no hay un campo 'Marca' ni 'Producto ID' visible, se dejan vacíos o con datos genéricos
        marca = "" 
        product_id = "" 
            
        # URL de Imagen
        img_tag = item.select_one('.box-image img')
        image_url = img_tag.get('data-src') or img_tag.get('src') if img_tag else ""
        
        if image_url and image_url.startswith('/'):
            image_url = requests.compat.urljoin(url, image_url)
            
        # Añadir datos a la lista
        products_data.append({
            "ID": "", # Se deja en blanco según solicitud
            "Nombre": name,
            "Marca": marca,
            "Descripción": description,
            "Precio": final_price_text, # Precio limpio sin '$'
            "Imagen": image_url,
            "Producto ID": product_id,
            "Unidad": unit,
            "Cantidad": quantity
        })
    
    return products_data

def write_to_excel_file(data, filename):
    """Escribe los datos filtrados en un archivo de Excel (.xlsx)."""
    try:
        # Convertir la lista de diccionarios a un pandas DataFrame
        df = pd.DataFrame(data)
        
        # Asegurar el orden de las columnas solicitado
        COLUMNS_ORDER = ["ID", "Nombre", "Marca", "Descripción", "Precio", "Imagen", "Producto ID", "Unidad", "Cantidad"]
        df = df[COLUMNS_ORDER]
        
        # Escribir en Excel
        df.to_excel(filename, index=False, engine='openpyxl')
        
        print(f"\n✅ Extracción y filtrado exitosos.")
        print(f"✅ Productos guardados (solo EN STOCK y Precio > 0): {len(data)}")
        print(f"✅ Datos guardados en: {os.path.abspath(filename)}")

    except IOError as e:
        print(f"Error al escribir en el archivo: {e}")
    except Exception as e:
        print(f"Ocurrió un error inesperado: {e}")

# Bloque de ejecución principal
if __name__ == "__main__":
    print(f"Iniciando raspado y filtrado de: {URL}")
    products = scrape_products(URL)
    
    if products:
        write_to_excel_file(products, OUTPUT_FILENAME)
    else:
        print("El raspado falló, no se extrajo ningún dato, o todos los productos fueron filtrados.")