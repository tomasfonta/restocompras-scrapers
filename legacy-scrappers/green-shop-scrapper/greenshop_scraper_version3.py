import requests
from bs4 import BeautifulSoup
import re
import os
import pandas as pd # Import the pandas library

# The URL to scrape
URL = "https://greenshop.ar/categoria-producto/frutas/todas-las-frutas/"

# The name of the output file
OUTPUT_FILENAME = "greenshop_frutas_data.xlsx" # Changed to .xlsx for Excel

def parse_product_title(full_title):
    """
    Separates the product name from its quantity and unit.
    """
    # Regex to capture a number, followed by a space, followed by a unit (gr., kilos, etc.)
    match = re.search(r'(\d+)\s*(gr|kilos|kg|un\.|u\.|lb)\.?$', full_title, re.IGNORECASE)
    
    if match:
        quantity = match.group(1).strip()
        unit = match.group(2).strip()
        # Remove the quantity and unit part from the name
        name = re.sub(r'\s*(\d+)\s*(gr|kilos|kg|un\.|u\.|lb)\.?$', '', full_title, flags=re.IGNORECASE).strip()
    else:
        # Simple check for cases like "2 kilos" where the number and unit are inseparable
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

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.60 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status() 
    except requests.exceptions.RequestException as e:
        print(f"Error fetching the page: {e}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    product_items = soup.select('.product-small')

    if not product_items:
        print("No product items found.")
        return []

    for item in product_items:
        title_tag = item.select_one('.product-title a')
        full_title = title_tag.text.strip() if title_tag else "N/A"
        
        name, quantity, unit = parse_product_title(full_title)
        
        # Description: Using the product category as a basic 'description'
        category_tag = item.select_one('.box-category a')
        description = category_tag.text.strip() if category_tag else "Fruta"
        
        # Price
        price_tag = item.select_one('.price .amount') or item.select_one('.price bdi')
        price_text = price_tag.text.strip() if price_tag else "N/A"
        
        # Status
        status = "AGOTADO" if item.select_one('.out-of-stock-label') else "EN STOCK"
            
        # Image URL (Check 'data-src' for lazy loading, then 'src')
        img_tag = item.select_one('.box-image img')
        image_url = img_tag.get('data-src') or img_tag.get('src') if img_tag else "N/A"
        
        # Construct full URL if it's a relative path
        if image_url and image_url.startswith('/'):
            image_url = requests.compat.urljoin(url, image_url)
            
        # Append data to the list
        products_data.append({
            "Name": name,
            "Description": description,
            "Unit": unit,
            "Quantity": quantity,
            "Price": f"{price_text} ({status})", # Combine price and status for the column
            "Image URL": image_url
        })
    
    return products_data

def write_to_excel_file(data, filename):
    """Writes the extracted product data to an Excel file using pandas."""
    try:
        # 1. Convert the list of dictionaries to a pandas DataFrame
        df = pd.DataFrame(data)
        
        # 2. Reorder columns to match the request
        df = df[["Name", "Description", "Unit", "Quantity", "Price", "Image URL"]]
        
        # 3. Write the DataFrame to an Excel file
        df.to_excel(filename, index=False, engine='openpyxl')
        
        print(f"\n✅ Successfully scraped {len(data)} products.")
        print(f"✅ Data saved to: {os.path.abspath(filename)}")

    except IOError as e:
        print(f"Error writing to file: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

# Main execution block
if __name__ == "__main__":
    print(f"Iniciando raspado de: {URL}")
    products = scrape_products(URL)
    
    if products:
        write_to_excel_file(products, OUTPUT_FILENAME)
    else:
        print("El raspado falló o no se extrajo ningún dato.")