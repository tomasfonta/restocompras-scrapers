# Adding a New Supplier

Quick guide to add a new supplier scraper in 3 steps.

## Step 1: Create Configuration

Create `configs/suppliers/supplier_name.json`:

### Static Site (requests)
```json
{
  "scraping_strategy": "requests",
  "urls": ["https://example.com/products"],
  "selectors": {
    "product_list": ".product-item",
    "title": ".product-title", 
    "price": ".product-price",
    "image": ".product-image img"
  },
  "strategy_config": {
    "timeout": 15
  },
  "credentials": {
    "email": "supplier@restocompras.com",
    "password": "password"
  }
}
```

### Dynamic Site (selenium)
```json
{
  "scraping_strategy": "selenium",
  "urls": ["https://example.com/products"],
  "selectors": {
    "product_list": "div.product-card",
    "title": "h2.title",
    "price": "span[class*='price']", 
    "image": "img.product-img"
  },
  "strategy_config": {
    "headless": true,
    "wait_time": 30,
    "scroll_attempts": 3
  },
  "credentials": {
    "email": "supplier@restocompras.com", 
    "password": "password"
  }
}
```

## Step 2: Create Scraper Class

Create `src/suppliers/supplier_name.py`:

```python
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from ..core.scraper_base import ScraperBase
from ..core.parser import DataParser
from ..strategies import RequestsStrategy  # or SeleniumStrategy


class SupplierNameScraper(ScraperBase):
    def __init__(self, config: Dict[str, Any], api_client: 'APIClient'):
        super().__init__(config, api_client)
        
        strategy_config = config.get('strategy_config', {})
        self.strategy = RequestsStrategy(strategy_config)  # or SeleniumStrategy
        self.selectors = config.get('selectors', {})
        self.parser = DataParser()
        self.base_url = config['urls'][0].split('/products')[0] if config.get('urls') else ''
    
    def get_urls(self) -> List[str]:
        return self.config.get('urls', [])
    
    def _fetch_html(self, url: str) -> str:
        return self.strategy.fetch_html(url)
    
    def extract_products(self, html_content: str, url: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html_content, 'html.parser')
        products = []
        
        product_items = soup.select(self.selectors['product_list'])
        
        for item in product_items:
            try:
                # Extract data
                title_element = item.select_one(self.selectors['title'])
                price_element = item.select_one(self.selectors['price'])
                image_element = item.select_one(self.selectors['image'])
                
                if not title_element or not price_element:
                    continue
                
                # Parse data
                title = title_element.get_text(strip=True)
                price_text = price_element.get_text(strip=True)
                
                name, quantity, unit = self.parser.parse_product_title(title)
                price, _ = self.parser.clean_price(price_text)
                
                if price <= 0:
                    continue
                
                # Handle image URL
                image_url = ''
                if image_element:
                    image_url = image_element.get('src', '')
                    if image_url and not image_url.startswith('http'):
                        image_url = urljoin(self.base_url, image_url)
                
                # Build product
                product = {
                    'name': name,
                    'price': price,
                    'unit': unit,
                    'quantity': quantity,
                    'supplierId': self.config.get('supplier_id', 0),
                    'brand': self.config.get('supplier_name', ''),
                    'description': name,
                    'image': image_url
                }
                
                products.append(product)
                
            except Exception as e:
                self.logger.error(f"Error extracting product: {e}")
                continue
        
        return products
    
    def __del__(self):
        if hasattr(self, 'strategy'):
            self.strategy.close()
```

## Step 3: Register Scraper

Add to `main.py`:

```python
from src.suppliers import (
    GreenShopScraper,
    LacteosGraneroScraper, 
    DistribuidoraPopScraper,
    TynaScraper,
    SupplierNameScraper  # Add import
)

SCRAPER_REGISTRY = {
    'greenshop': GreenShopScraper,
    'lacteos_granero': LacteosGraneroScraper,
    'distribuidora_pop': DistribuidoraPopScraper,
    'tyna': TynaScraper,
    'supplier_name': SupplierNameScraper,  # Add here
}
```

## Testing

1. **Create supplier in backend first** with matching email/password
2. **Test the scraper**:
   ```bash
   python3 main.py supplier_name
   ```
3. **Check output**: Excel file in `output/` and logs in `logs/`

## Finding Selectors

Use browser DevTools (F12):
1. Right-click on product → Inspect
2. Find unique CSS selectors for:
   - Product container (wraps each product)
   - Product title/name
   - Product price 
   - Product image
3. Test in console: `document.querySelectorAll('.your-selector')`

## Common Issues

- **No products found**: Check selectors match website structure
- **Authentication failed**: Verify supplier exists in backend with correct credentials
- **Price parsing errors**: Clean price text before parsing
- **Selenium issues**: Install ChromeDriver (`brew install chromedriver`)

## Strategy Choice

- **Use `requests`**: If product data is visible in page source (static HTML)
- **Use `selenium`**: If products load via JavaScript (dynamic content)

**Time estimate**: 30-60 minutes for simple sites
