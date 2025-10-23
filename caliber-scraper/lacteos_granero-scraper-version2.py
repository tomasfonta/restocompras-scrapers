import requests
from bs4 import BeautifulSoup
import re
import json
import pandas as pd 
from urllib.parse import quote, urljoin
import logging
import time

# --- CONFIGURACIÓN DEL LOGGING ---
# Usamos DEBUG para que los mensajes INFO (incluyendo URLs y respuestas) se vean claramente.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- REQUISITOS DE SELENIUM ---
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

# ----------------------------------------------------------------------
# --- CONSTANTES HARDCODEADAS (JWT ACTUALIZADO) ---
# ----------------------------------------------------------------------

def get_config():
    """Función para centralizar los valores fijos hardcodeados."""
    return {
        "URL_BASE": "https://lacteos-garnero-rosario.callbell.shop/",
        "API_POST_ENDPOINT": "http://localhost:8080/api/item",
        "API_SEARCH_ENDPOINT": "http://localhost:8080/api/products/search/best-match",
        "SUPPLIER_ID": 1,
        "MARCA": "Lácteos Garnero",
        # 🔑 NUEVO JWT PROPORCIONADO
        "AUTH_TOKEN": "eyJhbGciOiJIUzUxMiJ9.eyJzdWIiOiIxIiwiYXV0aG9yaXRpZXMiOlt7ImF1dGhvcml0eSI6IlJFQUQifSx7ImF1dGhvcml0eSI6IkRFTEVURSJ9LHsiYXV0aG9yaXR5IjoiQ1JFQVRFIn0seyJhdXRob3JpdHkiOiJVUERBVEUifV0sImlhdCI6MTc2MTE3MjA3MCwiZXhwIjoxNzYxMjU2ODAwfQ.bbf1z0sgq7XESrCnVolueU_oFSuWfh4evq9PnmHVYe86B57llE39BXHcfu_lJJzjZJ_7DcgpdACgXWhWZ4HDAQ",
        "OUTPUT_FILENAME": "lacteos_garnero_final_export.xlsx",
        "WAIT_TIME": 30,
        "PRODUCT_LIST_SELECTOR": '.product',
        "NAME_SELECTOR": '.product__details__top__name',
        "PRICE_SELECTOR": '.product__details__price--legacy__current--legacy',
        "IMAGE_SELECTOR": '.image-gallery-image'
    }

# ----------------------------------------------------------------------
# --- Funciones de Utilidad (sin cambios) ---
# ----------------------------------------------------------------------

def parse_product_title(full_title):
    """Limpia nombre (código de 3 cifras, 'por kilo') y separa unidad/cantidad."""
    name = full_title.strip()
    name = re.sub(r'^\s*\d{3}\s+', '', name).strip()
    match = re.search(r'(\d+)\s*(gr|kilos|kg|un\.|u\.|lb)\.?$', name, re.IGNORECASE)
    quantity = "1"
    unit = "UNIT"
    if match:
        raw_quantity = match.group(1).strip()
        raw_unit = match.group(2).strip().lower().replace('.', '')
        if raw_unit in ['gr', 'un', 'u', 'lb']: unit = "G"
        elif raw_unit in ['kilos', 'kg']: unit = "KG"
        quantity = raw_quantity
        name = re.sub(r'\s*(\d+)\s*(gr|kilos|kg|un\.|u\.|lb)\.?$', '', name, flags=re.IGNORECASE).strip()
    name = re.sub(r'\s*por\s*kilo$', '', name, flags=re.IGNORECASE).strip()
    return name, quantity, unit

def clean_price(price_text):
    """Limpia el precio y lo convierte a float."""
    cleaned_price_str = str(price_text).replace('$', '').replace('US$', '').replace('.', '').replace(',', '.').strip()
    try:
        numeric_price = float(cleaned_price_str)
        return numeric_price, str(int(numeric_price)) 
    except ValueError:
        return 0.0, price_text.strip()

# ----------------------------------------------------------------------
# --- Funciones de API (LOGS MEJORADOS) ---
# ----------------------------------------------------------------------

def perform_api_search(query):
    """Función auxiliar para realizar la búsqueda real en la API (hardcodeado)."""
    config = get_config()
    search_url = f"{config['API_SEARCH_ENDPOINT']}?query={quote(query)}"
    headers = {"Authorization": f"Bearer {config['AUTH_TOKEN']}"}
    
    # LOG DE LA URL ENVIADA
    logging.info(f"\n      🔎 URL GET: {search_url}")
    
    try:
        response = requests.get(search_url, headers=headers, timeout=5)
        response.raise_for_status() 
        data = response.json()
        
        # Log de respuesta exitosa
        logging.info(f"      ✅ GET Response (ID Found): {response.status_code}")
        
        if isinstance(data, dict) and 'productId' in data and data['productId'] is not None:
            return data['productId']
        return None
    except Exception as e:
        # Log de error
        logging.error(f"      🚨 GET Error: {e}")
        return None

def fetch_product_id(product_name):
    """Estrategia de búsqueda doble para el ID."""
    
    # Intento 1: Nombre completo limpio
    product_id = perform_api_search(product_name)
    if product_id is not None:
        return product_id

    # Intento 2: Nombre corto (dos primeras palabras)
    words = product_name.split()
    if len(words) >= 2:
        short_name = " ".join(words[:2])
        logging.warning(f"\n      ⚠️ Primer intento fallido. Probando con nombre corto: '{short_name}'")
        product_id = perform_api_search(short_name)
        if product_id is not None:
            return product_id

    logging.warning(f"\n      ❌ Falló la búsqueda de ID para '{product_name}' (ambos intentos).")
    return None


def post_to_api(product_data):
    """Realiza una llamada POST al endpoint (hardcodeado), logueando la respuesta."""
    config = get_config()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config['AUTH_TOKEN']}"
    }
    payload = {
        "name": product_data["Nombre"],
        "description": product_data["Descripción"],
        "price": product_data["Precio_Num"], 
        "image": product_data["Imagen"],
        "productId": product_data["Producto ID"], 
        "unit": product_data["Unidad"],
        "quantity": product_data["Cantidad"], 
        "supplierId": config['SUPPLIER_ID'] 
    }
    
    try:
        response = requests.post(config['API_POST_ENDPOINT'], json=payload, headers=headers, timeout=10)
        
        # LOG DE RESPUESTA Y CÓDIGO
        print(f"\n      ✅ POST exitoso para {product_data['Nombre']} (ID: {product_data['Producto ID']}). Status: {response.status_code}")
        
        try:
            # Pegar el código de respuesta (cuerpo del JSON)
            print(f"      Cuerpo de Respuesta: {response.json()}")
        except json.JSONDecodeError:
            print(f"      Cuerpo de Respuesta (Texto): {response.text}")

        response.raise_for_status() # Lanza excepción si el código es 4xx o 5xx
        return True
    
    except requests.exceptions.RequestException as e:
        print(f"\n      ❌ POST FALLÓ para {product_data['Nombre']}: {e}")
        
        # Intentar pegar el cuerpo de la respuesta en caso de fallo (ej. 400 Bad Request)
        if response.content:
             try:
                print(f"      Cuerpo de Error: {response.json()}")
             except:
                print(f"      Cuerpo de Error: {response.text}")

        return False

# ----------------------------------------------------------------------
# --- FUNCIÓN DE RASPADO CON SELENIUM (Logs Mejorados) ---
# ----------------------------------------------------------------------

def scrape_with_selenium():
    """Usa Selenium para cargar la URL base hardcodeada y raspar el contenido."""
    config = get_config()
    products_data = []
    
    print("\n" + "="*70)
    print(f" ⚙️  INICIANDO RASPADO DINÁMICO (SELENIUM) para {config['MARCA']}")
    print("="*70)

    try:
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

        driver = webdriver.Chrome(options=options)
        logging.info("\n 🌐  WebDriver inicializado en modo Headless.")
        driver.get(config['URL_BASE'])
        
    except WebDriverException as e:
        logging.critical(f"\n 🛑  ERROR de WebDriver. Verifique la configuración. Detalles: {e}")
        return []

    print(f"\n ⏱️  Esperando que el contenido cargue (máx. {config['WAIT_TIME']} segundos)...")
    try:
        WebDriverWait(driver, config['WAIT_TIME']).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, config['PRODUCT_LIST_SELECTOR']))
        )
        logging.info(" ✅  Selector de producto encontrado. Contenido listo.")
    except TimeoutException:
        logging.error(f" 🔴  TIMEOUT: El selector no apareció en {config['WAIT_TIME']} segundos. La página no cargó correctamente.")
        driver.quit()
        return []

    logging.info("\n ⏬  Desplazando la página para asegurar la carga completa...")
    scroll_attempts = 0
    last_height = driver.execute_script("return document.body.scrollHeight")
    while scroll_attempts < 3:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2) 
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
        scroll_attempts += 1
    logging.info(" ⏫  Desplazamiento completado.")

    html_content = driver.page_source
    driver.quit()
    logging.info("\n ✖️  WebDriver cerrado.")

    soup = BeautifulSoup(html_content, 'html.parser')
    product_items = soup.select(config['PRODUCT_LIST_SELECTOR'])
    
    if not product_items:
        logging.error(" ❌  BeautifulSoup no encontró productos en el HTML final.")
        return []
        
    logging.info(f"\n 🔍  Encontrados {len(product_items)} elementos. Procesando datos...")

    for i, item in enumerate(product_items):
        
        title_tag = item.select_one(config['NAME_SELECTOR'])
        full_title = title_tag.text.strip() if title_tag else "N/A"
        
        price_tag = item.select_one(config['PRICE_SELECTOR'])
        price_text = price_tag.text.strip() if price_tag else "$0"
        
        numeric_price, final_price_str = clean_price(price_text)
        
        if numeric_price == 0.0 or full_title == "N/A":
            logging.debug(f"Producto ignorado por datos inválidos: {full_title}")
            continue

        name, quantity, unit = parse_product_title(full_title)
            
        img_tag = item.select_one(config['IMAGE_SELECTOR'])
        image_url = urljoin(config['URL_BASE'], img_tag.get('src')) if img_tag and img_tag.get('src') else ""
            
        product_info = {
            "Nombre": name,
            "Unidad": unit, 
            "Cantidad": quantity,
            "ID": "", 
            "Marca": config['MARCA'], 
            "Descripción": name,
            "Precio": final_price_str,
            "Precio_Num": numeric_price,
            "Imagen": image_url,
            "Producto ID": None, 
            "supplierId": config['SUPPLIER_ID']
        }
        products_data.append(product_info)
        
    logging.info(f"\n 📊  Extracción completada. Total de productos válidos: {len(products_data)}")
    return products_data

# ----------------------------------------------------------------------
# --- Funciones de Procesamiento y Exportación (sin cambios) ---
# ----------------------------------------------------------------------

def deduplicate_products(products_list):
    """Elimina duplicados basados en Nombre, Unidad y Cantidad."""
    unique_products = {}
    for product in products_list:
        unique_key = (product["Nombre"], product["Unidad"], product["Cantidad"])
        if unique_key not in unique_products:
            unique_products[unique_key] = product
    return list(unique_products.values())

def write_to_excel_file(data):
    """Escribe los datos finales en un archivo de Excel (hardcodeado)."""
    config = get_config()
    try:
        df = pd.DataFrame(data)
        COLUMNS_ORDER = ["ID", "Nombre", "Marca", "Descripción", "Precio", "Imagen", "Producto ID", "Unidad", "Cantidad", "supplierId"]
        df = df[COLUMNS_ORDER]
        df.to_excel(config['OUTPUT_FILENAME'], index=False, engine='openpyxl')
        print(f"\n✨ EXCEL GENERADO: {len(data)} productos guardados en {config['OUTPUT_FILENAME']}")
        logging.info(f"Exportación exitosa. Archivo: {config['OUTPUT_FILENAME']}")
    except Exception as e:
        logging.error(f" ⚠️  Error al escribir en el archivo: {e}")

# ----------------------------------------------------------------------
# --- Bloque de ejecución principal (Logs Espaciados) ---
# ----------------------------------------------------------------------

if __name__ == "__main__":
    
    # 1. RASPADO DINÁMICO
    all_products_raw = scrape_with_selenium()
    
    if not all_products_raw:
        logging.critical(" 🛑  PROCESO TERMINADO: El raspado falló. No hay productos para procesar.")
        exit()

    print("\n" + "="*70)
    print(f" 🧩  INICIANDO PROCESO DE DATOS")
    print("="*70)
    
    logging.info(f"\nTotal de productos extraídos (Raw): {len(all_products_raw)}")
    
    # 2. DEDUPLICACIÓN
    final_unique_products = deduplicate_products(all_products_raw)
    duplicates_removed = len(all_products_raw) - len(final_unique_products)
    
    print(f"\n 🔢  DEDUPLICACIÓN: {duplicates_removed} duplicados eliminados.")
    logging.info(f"Productos únicos a procesar: {len(final_unique_products)}")
    
    # 3. BÚSQUEDA DE ID y LLAMADA A LA API
    products_to_export = []
    api_success_count = 0
    
    print(f"\n 🔗  INICIANDO LLAMADAS A API ({len(final_unique_products)} productos)")
    print(" -----------------------------------------------------------------")
    
    for product in final_unique_products:
        product_name = product["Nombre"]
        
        # Log para el producto actual
        print(f"\n   -> Procesando Producto: {product_name}")
        
        # Buscar el ID del producto (estrategia de 2 pasos)
        product_id = fetch_product_id(product_name)
        
        if product_id is not None:
            product["Producto ID"] = product_id
            
            # Realizar el POST a la API
            if post_to_api(product):
                api_success_count += 1
                products_to_export.append(product)
        else:
            print(f"\n      ⚠️  SALTANDO POST para {product_name}: No se pudo obtener el 'productId'.")
            
    print("\n -----------------------------------------------------------------")
    logging.info("Proceso de API POST completado.")
    print("\n" + "⭐"*35)
    print(f" ✅ PROCESO FINALIZADO.")
    print(f"    Productos únicos procesados: {len(final_unique_products)}")
    print(f"    Llamadas API POST exitosas: {api_success_count}")
    print("⭐"*35)

    # 4. EXPORTACIÓN A EXCEL
    if products_to_export:
        write_to_excel_file(products_to_export)