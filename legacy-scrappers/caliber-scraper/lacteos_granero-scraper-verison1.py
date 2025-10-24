import logging
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

# --- CONFIGURACIÓN DEL LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- CONFIGURACIÓN DE RASPADO ---
URL_BASE = "https://lacteos-garnero-rosario.callbell.shop/"
WAIT_TIME = 30 # Tiempo máximo para esperar la carga
# 🚨 SELECTOR CORREGIDO basado en la clase del contenedor principal
PRODUCT_LIST_SELECTOR = '.product' 
# Selector para el nombre
NAME_SELECTOR = '.product__details__top__name'
# Selector para el precio
PRICE_SELECTOR = '.product__details__price--legacy__current--legacy' 

def scrape_and_log_products(url):
    """
    Usa Selenium para cargar la página, espera, y luego extrae
    y loguea los nombres y precios usando los selectores específicos.
    """
    logging.info(f"Iniciando Selenium para URL: {url}")
    
    try:
        # 1. Configuración e Inicialización de WebDriver
        options = webdriver.ChromeOptions()
        options.add_argument('--headless') 
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

        driver = webdriver.Chrome(options=options)
        logging.info("WebDriver inicializado en modo Headless.")
        driver.get(url)
        
    except WebDriverException as e:
        logging.error(f"ERROR de WebDriver: Fallo al inicializar el driver. Detalles: {e}")
        return

    # 2. Esperar a que el contenido dinámico cargue
    logging.info(f"Esperando que el selector '{PRODUCT_LIST_SELECTOR}' cargue (máx. {WAIT_TIME} segundos)...")

    try:
        WebDriverWait(driver, WAIT_TIME).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, PRODUCT_LIST_SELECTOR))
        )
        logging.info("Contenedor de producto encontrado. Obteniendo HTML final.")
        
    except TimeoutException:
        logging.error(f"TIMEOUT: El selector no apareció en {WAIT_TIME} segundos. Los productos no cargaron.")
        driver.quit()
        return

    # 3. Obtener el HTML y cerrar el navegador
    html_content = driver.page_source
    driver.quit()
    logging.info("WebDriver cerrado.")

    # 4. Parsing con BeautifulSoup y Logueo
    soup = BeautifulSoup(html_content, 'html.parser')
    product_items = soup.select(PRODUCT_LIST_SELECTOR)
    
    if not product_items:
        logging.error("BeautifulSoup no encontró productos en el HTML final con el selector '.product'.")
        return
        
    logging.info(f"Productos encontrados: {len(product_items)}. Logueando datos...")

    for i, item in enumerate(product_items):
        
        # Nombre del Producto (usando el selector exacto)
        title_tag = item.select_one(NAME_SELECTOR)
        name = title_tag.text.strip() if title_tag else "N/A"
        
        # Precio (usando el selector exacto)
        price_tag = item.select_one(PRICE_SELECTOR)
        price = price_tag.text.strip() if price_tag else "Precio no encontrado"
        
        # Logueo
        logging.info(f"[{i+1}] Producto: {name} | Precio: {price}")
        
    logging.info("Logueo de productos completado.")

# --- Bloque de ejecución principal ---

if __name__ == "__main__":
    scrape_and_log_products(URL_BASE)