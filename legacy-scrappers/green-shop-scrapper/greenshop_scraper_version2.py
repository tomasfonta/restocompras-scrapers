import requests
from bs4 import BeautifulSoup
import re
import os

# The URL to scrape
URL = "https://greenshop.ar/categoria-producto/frutas/todas-las-frutas/"

# The name of the output text file
OUTPUT_FILENAME = "greenshop_frutas_full_list.txt"

def parse_product_title(full_title):
    """
    Separates the product name from its quantity and unit.
    Examples:
    - "Manzana Roja 500 gr." -> Name: "Manzana Roja", Quantity: "500", Unit: "gr."
    - "Banana Bolivia 2 kilos" -> Name: "Banana Bolivia", Quantity: "2", Unit: "kilos"
    - "Palta (chilena)" -> Name: "Palta (chilena)", Quantity: "N/A", Unit: "N/A"
    """
    # Regex to capture a number, followed by a space, followed by a unit (gr., kilos, etc.)
    match = re.search(r'(\d+)\s*(gr|kilos|kg|un\.|u\.|lb)\.?$', full_title, re.IGNORECASE)
    
    if match:
        quantity = match.group(1).strip()
        unit = match.group(2).strip()
        # Remove the quantity and unit part from the name
        name = re.sub(r'\s*(\d+)\s*(gr|kilos|kg|un\.|u\.|lb)\.?$', '', full_title, flags=re.IGNORECASE).strip()
    else:
        # Check for products with only a unit like "2 kilos" but no specific number
        match_kilos = re.search(r'(\d+)\s*kilos$', full_title, re.IGNORECASE)
        if match_kilos:
            quantity = match_kilos.group(1).strip()
            unit = "kilos"
            name = re.sub(r'\s*\d+\s*kilos$', '', full_title, flags=re.IGNORECASE).strip()
        else:
            name = full_title.strip()
            quantity = "N/A"
            unit = "N/A"

    return name, quantity, unit

def scrape_products(url):
    """Fetches, parses, and extracts product data from the URL."""
    products_data = []

    # 1. Fetch the HTML content
    try:
        # Added a User-Agent to mimic a browser, which can help with some sites
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.60 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
    except requests.exceptions.RequestException as e:
        print(f"Error fetching the page: {e}")
        return []

    # 2. Parse the HTML
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Target each individual product box on the page.
    product_items = soup.select('.product-small')

    if not product_items:
        print("No product items found. The website structure may have changed.")
        return []

    # 3. Extract data for each product
    for item in product_items:
        # Full Title (e.g., "Manzana Roja 500 gr.")
        title_tag = item.select_one('.product-title a')
        full_title = title_tag.text.strip() if title_tag else "N/A"
        
        # Parse the title into name, quantity, and unit
        name, quantity, unit = parse_product_title(full_title)
        
        # Description: Using the product category as a basic 'description'
        category_tag = item.select_one('.box-category a')
        description = category_tag.text.strip() if category_tag else "Fruta"
        
        # Price
        price_tag = item.select_one('.price .amount') or item.select_one('.price bdi')
        price = price_tag.text.strip() if price_tag else "N/A"
        
        # Check if product is out of stock (agotado)
        if item.select_one('.out-of-stock-label'):
            status = "AGOTADO"
        else:
            status = "EN STOCK"
            
        # Image URL (Check 'data-src' for lazy loading, then 'src')
        img_tag = item.select_one('.box-image img')
        image_url = img_tag.get('data-src') or img_tag.get('src') if img_tag else "N/A"
        
        # Construct full URL if it's a relative path
        if image_url and image_url.startswith('/'):
            image_url = requests.compat.urljoin(url, image_url)
            
        products_data.append({
            "name": name,
            "description": description,
            "quantity": quantity,
            "unit": unit,
            "price": price,
            "status": status,
            "image_url": image_url
        })
    
    return products_data

def write_to_text_file(data, filename):
    """Writes the extracted product data to a plain text file."""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("========================================\n")
            f.write("GREENSHOP FRUTAS - SCRAPING RESULTS\n")
            f.write("========================================\n\n")

            for product in data:
                f.write(f"Nombre: {product['name']}\n")
                f.write(f"Descripción/Categoría: {product['description']}\n")
                f.write(f"Cantidad: {product['quantity']}\n")
                f.write(f"Unidad: {product['unit']}\n")
                f.write(f"Precio: {product['price']} ({product['status']})\n")
                f.write(f"URL de Imagen: {product['image_url']}\n")
                f.write("----------------------------------------\n")
        
        print(f"\n✅ Successfully scraped {len(data)} products.")
        print(f"✅ Data saved to: {os.path.abspath(filename)}")

    except IOError as e:
        print(f"Error writing to file: {e}")

# Main execution block
if __name__ == "__main__":
    print(f"Iniciando raspado de: {URL}")
    products = scrape_products(URL)
    
    if products:
        write_to_text_file(products, OUTPUT_FILENAME)
    else:
        print("El raspado falló o no se extrajo ningún dato.")