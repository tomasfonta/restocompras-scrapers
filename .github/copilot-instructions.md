# restoCompras Scrapers - AI Agent Instructions

## Project Overview
A modular web scraping framework for food suppliers in Argentina with JSON-based configuration, dual scraping strategies (Selenium/Requests), and backend API integration. Designed for easy extensibility—adding new suppliers requires only a config file and a scraper class.

## Architecture & Design Principles

### Modular Structure
```
src/
├── core/          # Framework: ScraperBase, APIClient, DataParser, DataExporter
├── strategies/    # ScrapingStrategy interface: SeleniumStrategy, RequestsStrategy
├── suppliers/     # Supplier implementations: GreenShopScraper, LacteosGraneroScraper
├── config/        # ConfigLoader for JSON configs
└── utils/         # text_processing (deduplication), logger
```

### Key Design Patterns
- **Strategy Pattern**: `ScrapingStrategy` interface with concrete implementations for static (requests) vs dynamic (Selenium) sites
- **Template Method**: `ScraperBase.scrape()` orchestrates the workflow; suppliers override `extract_products()`
- **Configuration-Driven**: All supplier-specific data (URLs, selectors, strategy settings) lives in JSON files

### Two-Phase API Integration
1. **Search Phase**: `APIClient.fetch_product_id()` with dual-strategy lookup (full name → shortened name)
2. **Insert Phase**: `APIClient.post_item()` with complete product data
3. **Flow**: `ScraperBase._integrate_with_api()` coordinates both phases for deduplicated products

## Adding a New Supplier (3 Steps)

### 1. Create Config File
`configs/suppliers/your_supplier.json`:
```json
{
  "supplier_id": 2,
  "supplier_name": "Your Supplier",
  "scraping_strategy": "requests",  // or "selenium"
  "urls": ["https://yoursupplier.com/products"],
  "selectors": {
    "product_list": ".product-item",
    "title": ".product-title",
    "price": ".product-price",
    "image": ".product-image img"
  },
  "strategy_config": {
    "timeout": 15  // requests-specific
    // OR for selenium: "headless": true, "wait_time": 30
  }
}
```

### 2. Implement Scraper Class
`src/suppliers/your_supplier.py`:
```python
from ..core.scraper_base import ScraperBase
from ..strategies import RequestsStrategy  # or SeleniumStrategy

class YourSupplierScraper(ScraperBase):
    def __init__(self, config, api_client):
        super().__init__(config, api_client)
        self.strategy = RequestsStrategy(config.get('strategy_config', {}))
        self.selectors = config.get('selectors', {})
    
    def get_urls(self) -> List[str]:
        return self.config.get('urls', [])
    
    def _fetch_html(self, url: str) -> str:
        return self.strategy.fetch_html(url)
    
    def extract_products(self, html_content: str, url: str) -> List[Dict]:
        # Parse HTML with BeautifulSoup + selectors
        # Return list of dicts with keys: name, price, unit, quantity, image
```

### 3. Register in `main.py`
```python
SCRAPER_REGISTRY = {
    'your_supplier': YourSupplierScraper,  # Add this line
}
```

## Critical Workflows

### Running Scrapers
```bash
# Run single supplier
python3 main.py greenshop

# List available suppliers
python3 main.py --list

# Custom directories
python3 main.py greenshop --config-dir ./configs --output-dir ./output
```

### Configuration Management
- **API Config**: `configs/api_config.json` contains JWT token (expires frequently—update here)
- **Supplier Configs**: `configs/suppliers/*.json` define all supplier-specific settings
- **No Hardcoding**: All supplier data comes from JSON (URLs, selectors, strategy params)

### Data Processing Pipeline
1. **Fetch**: Strategy pattern determines requests vs Selenium
2. **Extract**: Supplier class uses BeautifulSoup + CSS selectors
3. **Parse**: `DataParser.parse_product_title()` → standardizes units (gr→G, kg→KG)
4. **Deduplicate**: `deduplicate_products()` on `(name, unit, quantity)` tuple
5. **API Lookup**: Dual-strategy product ID search (full name, then first 2 words)
6. **Post**: Only products with valid `productId` are posted
7. **Export**: `DataExporter.export_to_excel()` → timestamped Excel file in `output/`

## Technology Selection Guide

### Use RequestsStrategy When:
- Site serves complete HTML without JavaScript rendering
- Example: Green Shop (static product listings)
- Faster, less resource-intensive

### Use SeleniumStrategy When:
- Content loads dynamically via JavaScript
- Example: Lácteos Granero (React/Vue-based catalog)
- Slower, requires ChromeDriver, but handles dynamic content
- Strategy includes auto-scrolling for lazy-loaded content

## Key Implementation Details

### ScraperBase Workflow
```python
scrape() → get_urls() → _fetch_html() → extract_products() → 
_process_products() (dedup) → _integrate_with_api() (ID lookup + POST)
```

### APIClient Dual-Strategy Lookup
```python
fetch_product_id("Tomate Cherry 500 gr")
  → _search_product("Tomate Cherry 500 gr")  # Attempt 1
  → _search_product("Tomate Cherry")         # Attempt 2 (if fail)
  → return productId or None
```

### DataParser Standardization
- **Units**: `gr|gramos → G`, `kilos|kg → KG`, `un|u → G`, default → `UNIT`
- **Prices**: Remove `$`, normalize `.` (thousands) and `,` (decimal)
- **Titles**: Strip leading codes (`001 Producto`), remove "por kilo" suffix

## Legacy Code (Preserved)
- `caliber-scraper/` and `green-shop-scrapper/` contain original versioned scripts
- These are functional but monolithic (hardcoded configs)
- **New development**: Use the modular `src/` structure
- **Migration**: Existing scrapers refactored into `src/suppliers/`

## Common Tasks

### Update JWT Token
Edit `configs/api_config.json`:
```json
{"auth_token": "NEW_TOKEN_HERE"}
```

### Debug Scraper
1. Check `logs/scraper_TIMESTAMP.log` for detailed execution logs
2. For Selenium issues: Set `"headless": false` in supplier config to see browser
3. Verify selectors match current site structure (websites change frequently)

### Handle Missing Products
- Check API logs for 404 responses (product not in backend DB)
- Scrapers skip products with no `productId` (logged as warnings)
- Verify `PRODUCTS_API_SEARCH` endpoint is correct in `api_config.json`

## Dependencies
```bash
pip3 install -r requirements.txt
# Key: requests, beautifulsoup4, selenium, pandas, openpyxl
```

When extending the framework, follow the established patterns: configuration-driven, strategy-based scraping, and centralized API/export logic. The goal is maximum reusability—most supplier additions should only require config + minimal extraction logic.