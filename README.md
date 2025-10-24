# restoCompras Scrapers

A modular, configurable web scraping framework for food suppliers in Argentina. Built to be easily extensible with support for both static (requests) and dynamic (Selenium) websites.

## Features

- **Modular Architecture**: Easy to add new suppliers without modifying core code
- **Dual Scraping Strategies**: Supports both static (requests) and dynamic (Selenium) websites
- **JSON Configuration**: All supplier-specific settings in external config files
- **API Integration**: Automatic product ID lookup and posting to backend API
- **Deduplication**: Intelligent product deduplication based on name, unit, and quantity
- **Data Export**: Exports to Excel with standardized format
- **Comprehensive Logging**: Detailed logs for debugging and monitoring

## Project Structure

```
restocompras-scrapers/
├── src/
│   ├── core/              # Core framework components
│   │   ├── scraper_base.py    # Base scraper class
│   │   ├── api_client.py      # API communication
│   │   ├── parser.py          # Data parsing utilities
│   │   └── exporter.py        # Export functionality
│   ├── strategies/        # Scraping strategies
│   │   ├── scraping_strategy.py   # Base strategy interface
│   │   ├── selenium_strategy.py   # For dynamic sites
│   │   └── requests_strategy.py   # For static sites
│   ├── suppliers/         # Supplier implementations
│   │   ├── greenshop.py
│   │   └── lacteos_granero.py
│   ├── config/            # Configuration management
│   │   └── config_loader.py
│   └── utils/             # Utility functions
│       ├── text_processing.py
│       └── logger.py
├── configs/               # Configuration files
│   ├── api_config.json        # API settings
│   └── suppliers/             # Supplier configs
│       ├── greenshop.json
│       └── lacteos_granero.json
├── output/                # Export files (generated)
├── logs/                  # Log files (generated)
├── main.py                # CLI entry point
└── requirements.txt
```

## Installation

1. **Clone the repository**

```bash
cd restocompras-scrapers
```

2. **Install dependencies**

```bash
pip3 install -r requirements.txt
```

3. **Verify installation** (optional but recommended)

```bash
python3 test_setup.py
```

4. **Configure API settings**

Edit `configs/api_config.json` with your JWT token:

```json
{
  "base_url": "http://localhost:8080",
  "auth_token": "YOUR_JWT_TOKEN_HERE",
  "search_endpoint": "/api/products/search/best-match",
  "item_endpoint": "/api/item",
  "timeout": 10
}
```

## Usage

### Basic Usage

```bash
# Scrape Green Shop
python3 main.py greenshop

# Scrape Lácteos Granero
python3 main.py lacteos_granero

# List available suppliers
python3 main.py --list
```

### Advanced Usage

```bash
# Use custom config directory
python3 main.py greenshop --config-dir ./my_configs

# Specify output directory
python3 main.py greenshop --output-dir ./my_output

# Specify log directory
python3 main.py greenshop --log-dir ./my_logs
```

## Adding a New Supplier

Adding a new supplier is straightforward and requires three steps:

### 1. Create Supplier Configuration

Create `configs/suppliers/your_supplier.json`:

```json
{
  "supplier_id": 2,
  "supplier_name": "Your Supplier Name",
  "scraping_strategy": "requests",
  "urls": [
    "https://yoursupplier.com/products"
  ],
  "selectors": {
    "product_list": ".product-item",
    "title": ".product-title",
    "price": ".product-price",
    "image": ".product-image img"
  },
  "strategy_config": {
    "timeout": 15
  }
}
```

**Strategy Options:**
- `"requests"` - For static HTML sites (faster)
- `"selenium"` - For JavaScript-rendered sites (slower but handles dynamic content)

### 2. Create Scraper Class

Create `src/suppliers/your_supplier.py`:

```python
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from ..core.scraper_base import ScraperBase
from ..core.parser import DataParser
from ..strategies import RequestsStrategy  # or SeleniumStrategy


class YourSupplierScraper(ScraperBase):
    """Scraper for Your Supplier website."""
    
    def __init__(self, config: Dict[str, Any], api_client: 'APIClient'):
        super().__init__(config, api_client)
        
        # Initialize strategy
        strategy_config = config.get('strategy_config', {})
        self.strategy = RequestsStrategy(strategy_config)
        
        self.selectors = config.get('selectors', {})
        self.parser = DataParser()
    
    def get_urls(self) -> List[str]:
        """Get URLs from config."""
        return self.config.get('urls', [])
    
    def _fetch_html(self, url: str) -> str:
        """Fetch HTML using strategy."""
        return self.strategy.fetch_html(url)
    
    def extract_products(self, html_content: str, url: str) -> List[Dict[str, Any]]:
        """Extract products from HTML."""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        product_items = soup.select(self.selectors['product_list'])
        products = []
        
        for item in product_items:
            # Extract data using your selectors
            title = item.select_one(self.selectors['title']).text.strip()
            price_text = item.select_one(self.selectors['price']).text.strip()
            
            # Parse data
            name, quantity, unit = self.parser.parse_product_title(title)
            price, _ = self.parser.clean_price(price_text)
            
            if price > 0:
                products.append({
                    'name': name,
                    'price': price,
                    'unit': unit,
                    'quantity': quantity,
                    'supplierId': self.config['supplier_id'],
                    'brand': self.config['supplier_name'],
                    'description': name,
                    'image': ''  # Extract if needed
                })
        
        return products
    
    def __del__(self):
        """Clean up resources."""
        if hasattr(self, 'strategy'):
            self.strategy.close()
```

### 3. Register in Main

Add your scraper to `main.py`:

```python
from src.suppliers import GreenShopScraper, LacteosGraneroScraper, YourSupplierScraper

SCRAPER_REGISTRY = {
    'greenshop': GreenShopScraper,
    'lacteos_granero': LacteosGraneroScraper,
    'your_supplier': YourSupplierScraper,  # Add this line
}
```

That's it! You can now run:

```bash
python3 main.py your_supplier
```

## Configuration Reference

### API Configuration (`configs/api_config.json`)

```json
{
  "base_url": "http://localhost:8080",
  "auth_token": "YOUR_JWT_TOKEN",
  "search_endpoint": "/api/products/search/best-match",
  "item_endpoint": "/api/item",
  "timeout": 10
}
```

### Supplier Configuration

```json
{
  "supplier_id": 1,
  "supplier_name": "Supplier Name",
  "scraping_strategy": "requests|selenium",
  "urls": ["https://..."],
  "selectors": {
    "product_list": ".product",
    "title": ".title",
    "price": ".price",
    "image": "img"
  },
  "strategy_config": {
    // For requests strategy:
    "timeout": 15,
    
    // For selenium strategy:
    "headless": true,
    "wait_time": 30,
    "scroll_attempts": 3,
    "scroll_delay": 2
  }
}
```

## Architecture

### Core Components

- **ScraperBase**: Abstract base class defining the scraping workflow
- **APIClient**: Handles all backend API communication with dual-strategy product lookup
- **DataParser**: Standardizes product data extraction (titles, prices, units)
- **DataExporter**: Exports results to Excel/JSON formats

### Scraping Strategies

- **RequestsStrategy**: Fast, for static HTML sites
- **SeleniumStrategy**: Full browser automation for JavaScript-heavy sites

### Workflow

1. Load configurations (API + supplier)
2. Initialize scraper with appropriate strategy
3. Fetch HTML content from each URL
4. Extract products using BeautifulSoup + selectors
5. Deduplicate products
6. Lookup product IDs from API (dual-strategy: full name, then shortened)
7. Post valid products to API
8. Export results to Excel

## Logging

Logs are stored in the `logs/` directory with timestamps. Each run creates:
- Console output (INFO level)
- Detailed log file (DEBUG level)

## Troubleshooting

### JWT Token Expired

Update `configs/api_config.json` with a fresh token from your backend.

### Selenium/ChromeDriver Issues

Ensure Chrome and ChromeDriver are installed and compatible versions:

```bash
# macOS
brew install chromedriver

# Or download from: https://chromedriver.chromium.org/
```

### No Products Found

1. Check if selectors in config match the website structure
2. Try `headless: false` in selenium config to see what's happening
3. Check logs for detailed error messages

## Contributing

To add support for a new supplier:

1. Create supplier config in `configs/suppliers/`
2. Implement scraper class in `src/suppliers/`
3. Register in `main.py`
4. Test thoroughly
5. Update this README

## License

MIT
