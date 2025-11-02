# restoCompras Scrapers

A modular, configurable web scraping framework for food suppliers in Argentina. Built to be easily extensible with support for both static (requests) and dynamic (Selenium) websites.

## 📋 Table of Contents

- [Quick Start](#-quick-start)
- [Environment Management](#-environment-management)
- [Project Structure](#-project-structure)
- [How It Works](#-how-it-works)
- [Adding a New Supplier](#-adding-a-new-supplier)
- [API Configuration](#-api-configuration)
- [Running All Suppliers](#-running-all-suppliers)
- [Troubleshooting](#-troubleshooting)
- [Architecture](#-architecture)


## 🚀 Quick Start

### Installation

```bash
# 1. Navigate to project directory
cd restocompras-scrapers

# 2. Install dependencies
pip3 install -r requirements.txt

# 3. Configure API settings
# Edit configs/api_config.dev.json and configs/api_config.prod.json
```

### Run a Scraper

```bash
# Development (localhost:8080) - Default
python3 main.py greenshop
python3 main.py greenshop --env dev

# Production (restocompras2.onrender.com)
python3 main.py greenshop --env prod

# List available suppliers
python3 main.py --list

# Custom directories
python3 main.py greenshop --config-dir ./configs --output-dir ./output
```

### What Happens

1. ✅ **Authenticates** with backend using supplier credentials
2. ✅ **Fetches supplier details** (ID and name) from API
3. ✅ **Cleans database** - Removes all existing items for this supplier
4. ✅ **Scrapes** product pages using configured strategy
5. ✅ **Extracts** and standardizes product data
6. ✅ **Deduplicates** products
7. ✅ **Looks up** product IDs from backend
8. ✅ **Posts** validated products to API
9. ✅ **Exports** results to Excel (`output/` directory)

**Output**: 
- `output/supplier_name_export_TIMESTAMP.xlsx`
- `logs/scraper_TIMESTAMP.log`

---

## 🌍 Environment Management

The scraper supports multiple environments (development and production) with easy switching via command-line arguments.

### Configuration Files

```
configs/
├── api_config.dev.json       # Development environment (localhost:8080)
├── api_config.prod.json      # Production environment (restocompras2.onrender.com)
└── suppliers/
    ├── greenshop.json
    └── ...
```

### Development Config (`api_config.dev.json`)
```json
{
  "base_url": "http://localhost:8080",
  "auth_token": "",
  "login_endpoint": "/login",
  "search_endpoint": "/api/products/search/best-match",
  "item_endpoint": "/api/item",
  "supplier_search_endpoint": "/api/suppliers/search",
  "supplier_delete_endpoint": "/api/ites/supplier/{supplier_id}",
  "timeout": 10
}
```

### Production Config (`api_config.prod.json`)
```json
{
  "base_url": "https://restocompras2.onrender.com",
  "auth_token": "",
  "login_endpoint": "/login",
  "search_endpoint": "/api/products/search/best-match",
  "item_endpoint": "/api/item",
  "supplier_search_endpoint": "/api/suppliers/search",
  "supplier_delete_endpoint": "/api/ites/supplier/{supplier_id}",
  "timeout": 30
}
```

### Usage

```bash
# Test locally
python3 main.py greenshop --env dev

# Run in production
python3 main.py greenshop --env prod

# Run all suppliers in production
for supplier in greenshop lacteos_granero tyna; do
    python3 main.py $supplier --env prod
done
```

**Key Features:**
- Separate configurations for dev/prod
- Different timeouts (10s for dev, 30s for prod)
- Isolated JWT tokens per environment
- Default to dev for safety
- Clear logging of which environment is active

---

## 📦 Project Structure

```
scrapers/
├── main.py                    # CLI entry point
├── requirements.txt           # Dependencies
├── configs/
│   ├── api_config.dev.json   # Dev environment config
│   ├── api_config.prod.json  # Prod environment config
│   └── suppliers/            # One JSON per supplier
│       ├── greenshop.json
│       ├── lacteos_granero.json
│       ├── distribuidora_pop.json
│       ├── tyna.json
│       └── labebidadetusfiestas.json
├── src/
│   ├── core/
│   │   ├── scraper_base.py   # Abstract base class
│   │   ├── api_client.py     # Backend API communication
│   │   ├── parser.py         # Data parsing utilities
│   │   └── exporter.py       # Excel/JSON export
│   ├── strategies/
│   │   ├── scraping_strategy.py      # Interface
│   │   ├── requests_strategy.py      # Static sites
│   │   └── selenium_strategy.py      # Dynamic sites
│   ├── suppliers/            # Supplier implementations
│   │   ├── greenshop.py
│   │   ├── lacteos_granero.py
│   │   ├── distribuidora_pop.py
│   │   ├── tyna.py
│   │   └── labebidadetusfiestas.py
│   ├── config/
│   │   └── config_loader.py  # JSON config loader
│   └── utils/
│       ├── logger.py         # Logging setup
│       └── text_processing.py # Deduplication
├── output/                   # Generated Excel files
├── logs/                     # Execution logs
└── legacy-scrappers/        # Old monolithic scripts (preserved)
```

---

## 🔄 How It Works

### Complete Workflow

```
1. ✅ LOAD CONFIGURATIONS
   ├─ Load API config (environment-specific)
   └─ Load supplier config (URLs, selectors, credentials)

2. ✅ AUTHENTICATE WITH BACKEND API
   ├─ Login with supplier credentials
   ├─ Retrieve JWT token
   └─ Update auth_token in config file

3. ✅ FETCH SUPPLIER DETAILS
   ├─ Query backend API with supplier email
   ├─ Get supplier ID and name from backend
   └─ Store supplier information

4. 🆕 CLEAN DATABASE
   ├─ DELETE /api/ites/supplier/{supplier_id}
   ├─ Remove all existing items for this supplier
   └─ Prepare fresh database state
   
5. ✅ START SCRAPING PROCESS
   ├─ Fetch HTML from supplier website(s)
   ├─ Extract product data (name, price, unit, quantity, image)
   ├─ Parse and standardize data
   └─ Deduplicate products

6. ✅ INTEGRATE WITH API
   ├─ For each product:
   │  ├─ Search for product ID in backend
   │  └─ POST product to /api/item
   └─ Track successfully posted products

7. ✅ EXPORT RESULTS
   ├─ Generate Excel file with product data
   └─ Save to output/ directory

8. ✅ COMPLETE
   └─ Display summary
```

### Data Flow Example

**Website HTML:**
```html
<div class="product">
  <h3>Tomate Cherry 500 gr</h3>
  <span class="price">$1.234,50</span>
  <img src="/images/tomate.jpg">
</div>
```

**Step 1 - Extract:**
```python
{'title': 'Tomate Cherry 500 gr', 'price': '$1.234,50', 'image': '/images/tomate.jpg'}
```

**Step 2 - Parse & Clean:**
```python
{'name': 'Tomate Cherry', 'quantity': 500, 'unit': 'G', 'price': 1234.50, 'image': 'https://site.com/images/tomate.jpg'}
```

**Step 3 - API Lookup:**
```
→ POST /api/products/search/best-match {"query": "Tomate Cherry 500 gr"}
← Response: {"id": 123, "name": "Tomate Cherry"}
```

**Step 4 - Complete & Post:**
```python
{
  'name': 'Tomate Cherry', 'price': 1234.50, 'productId': 123,
  'unit': 'G', 'quantity': 500, 'supplierId': 1, 'brand': 'Green Shop',
  'image': 'https://site.com/images/tomate.jpg'
}
→ POST /api/item
← Response: 201 Created
```

### Dual-Strategy Lookup

The API client uses a smart two-phase lookup:

1. **First attempt**: Search with full name + quantity + unit
   - Example: "Tomate Cherry 500 gr"
   
2. **Second attempt**: Search with only first 2 words
   - Example: "Tomate Cherry"
   
3. **Skip if not found**: Product logged as warning and skipped

This ensures maximum matching with backend products.

---

## ➕ Adding a New Supplier

### Step 1: Create Configuration

Create `configs/suppliers/supplier_name.json`:

**For Static Sites (requests):**
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

**For Dynamic Sites (selenium):**
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

### Step 2: Create Scraper Class

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
        self.strategy = RequestsStrategy(strategy_config)
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

### Step 3: Register Scraper

Add to `main.py`:

```python
from src.suppliers import (
    GreenShopScraper,
    LacteosGraneroScraper, 
    SupplierNameScraper  # Add import
)

SCRAPER_REGISTRY = {
    'greenshop': GreenShopScraper,
    'lacteos_granero': LacteosGraneroScraper,
    'supplier_name': SupplierNameScraper,  # Add here
}
```

### Step 4: Test

1. **Create supplier in backend first** with matching email/password
2. **Test the scraper**:
   ```bash
   python3 main.py supplier_name --env dev
   ```
3. **Check output**: Excel file in `output/` and logs in `logs/`

### Finding Selectors

Use browser DevTools (F12):
1. Right-click on product → Inspect
2. Find unique CSS selectors for:
   - Product container
   - Product title/name
   - Product price 
   - Product image
3. Test in console: `document.querySelectorAll('.your-selector')`

### Strategy Choice

- **Use `requests`**: If product data is visible in page source (static HTML)
- **Use `selenium`**: If products load via JavaScript (dynamic content)

**Time estimate**: 30-60 minutes for simple sites

---

## 🔌 API Configuration

### Centralized Endpoints

All API endpoints are configured in environment-specific JSON files for easy management.

### Configuration Properties

| Property | Description | Example |
|----------|-------------|---------|
| `base_url` | Backend server URL | `http://localhost:8080` |
| `auth_token` | JWT token (auto-updated) | `eyJhbGciOiJIUzUxMiJ9...` |
| `login_endpoint` | Authentication endpoint | `/login` |
| `search_endpoint` | Product search endpoint | `/api/products/search/best-match` |
| `item_endpoint` | Product posting endpoint | `/api/item` |
| `supplier_search_endpoint` | Supplier lookup endpoint | `/api/suppliers/search` |
| `supplier_delete_endpoint` | Delete supplier items | `/api/ites/supplier/{supplier_id}` |
| `timeout` | Request timeout (seconds) | `10` (dev), `30` (prod) |

### Dynamic Placeholders

Some endpoints support placeholders replaced at runtime:

```json
{
  "supplier_delete_endpoint": "/api/ites/supplier/{supplier_id}"
}
```

**Runtime**: `/api/ites/supplier/10` (when supplier_id=10)

### Authentication

All API requests automatically include the Authorization header:

```python
{
    'Authorization': 'Bearer eyJhbGciOiJIUzUxMiJ9...',
    'Content-Type': 'application/json'
}
```

**Token Lifecycle:**
1. Load token from config
2. Login with credentials → Get new token
3. Update token in config and all requests
4. Token persists for subsequent requests

---

## 🚀 Running All Suppliers

### Run All Suppliers Scripts

**Python Script (Cross-platform):**
```bash
# Development (default)
python3 run_all_suppliers.py
python3 run_all_suppliers.py --env dev

# Production
python3 run_all_suppliers.py --env prod
```

**Bash Script (Unix/Linux/macOS):**
```bash
# Development (default)
./run_all_suppliers.sh
./run_all_suppliers.sh --env dev

# Production
./run_all_suppliers.sh --env prod
```

**What it does:**
- Runs all configured suppliers sequentially
- Shows real-time progress with color-coded output
- Displays environment being used
- Generates summary report with success/failure counts
- Exit code 0 if all succeed, 1 if any fail

### Manual Iteration

```bash
# Development
for supplier in greenshop lacteos_granero distribuidora_pop tyna labebidadetusfiestas; do
    python3 main.py "$supplier" --env dev
done

# Production
for supplier in greenshop lacteos_granero distribuidora_pop tyna labebidadetusfiestas; do
    python3 main.py "$supplier" --env prod
done
```

### Available Suppliers

**Web Scrapers (HTML-based):**
- ✅ **greenshop** - Green Shop (Requests strategy)
- ✅ **lacteos_granero** - Lácteos Granero (Selenium strategy)
- ✅ **distribuidora_pop** - Distribuidora Pop (Requests strategy)
- ✅ **tyna** - Tyna (Requests strategy)
- ✅ **labebidadetusfiestas** - La Bebida de Tus Fiestas (Requests strategy)
- ✅ **piala** - Piala (Requests strategy)
- ✅ **distribuidora_demarchi** - Distribuidora De Marchi (Requests strategy)
- ✅ **laduvalina** - La Duvalina (Requests strategy)

**File-Based Scrapers:**
- ✅ **irlanda** - Irlanda (PDF price list strategy)
- ✅ **el_chanar_carnes** - El Chañar Carnes (Excel price list strategy)

### Scheduling Automated Runs

**Using Cron (Linux/macOS):**
```bash
crontab -e
```

Add entry to run all suppliers daily at 2 AM in production:
```bash
0 2 * * * cd /path/to/scrapers && /usr/bin/python3 run_all_suppliers.py --env prod >> cron.log 2>&1
```

Or run individual supplier:
```bash
0 2 * * * cd /path/to/scrapers && /usr/bin/python3 main.py greenshop --env prod >> cron.log 2>&1
```

---

## � Testing File-Based Providers

The framework supports file-based scrapers for PDF and Excel price lists, in addition to web scraping.

### PDF Price Lists (Irlanda)

**Use Case**: Suppliers that provide price lists as PDF documents.

#### Setup
1. Place PDF file in `input/` directory:
   ```bash
   cp LISTAS_IRLANDA.pdf input/
   ```

2. Configuration (`configs/suppliers/irlanda.json`):
   ```json
   {
     "supplier_id": 5,
     "supplier_name": "Irlanda",
     "scraping_strategy": "pdf",
     "credentials": {
       "name": "irlanda@restocompras.com",
       "password": "password"
     },
     "file_config": {
       "filename": "LISTAS_IRLANDA.pdf",
       "input_dir": "input",
       "strategy_type": "pdf"
     },
     "pdf_config": {
       "text_mode": true,
       "table_settings": {
         "vertical_strategy": "text",
         "horizontal_strategy": "text"
       }
     }
   }
   ```

#### Run PDF Scraper
```bash
# Development
python3 main.py irlanda --env dev

# Production
python3 main.py irlanda --env prod
```

#### Expected Output
```
INFO - Extracted 834 raw records from PDF
INFO - Processing 834 raw records
INFO - Successfully extracted 625 products from PDF
INFO - ✅ Successfully posted 'SODA SIFON SOCIAL' (Product ID: 113, Supplier ID: 5)
INFO - Export file: output/irlanda_export_20251102_111344.xlsx
```

#### PDF Format Support
- **Text mode**: Line-by-line extraction with regex patterns
  - Format: `CODE DESCRIPTION........ PRICE`
  - Example: `0101137 SODA SIFON SOCIAL 2L.................. 5700.00`
- **Table mode**: Structured table extraction using pdfplumber
- Handles multi-page PDFs automatically

### Excel Price Lists (El Chañar Carnes)

**Use Case**: Suppliers that provide price lists as Excel spreadsheets.

#### Setup
1. Place Excel file in `input/` directory:
   ```bash
   cp "LISTA DE PRECIOS WHATSAPP Y OTROS.xlsx" input/
   ```

2. Configuration (`configs/suppliers/el_chanar_carnes.json`):
   ```json
   {
     "supplier_id": 6,
     "supplier_name": "El Chañar carnes",
     "scraping_strategy": "excel",
     "credentials": {
       "name": "elchanar@restocompras.com",
       "password": "password"
     },
     "file_config": {
       "filename": "LISTA DE PRECIOS WHATSAPP Y OTROS.xlsx",
       "input_dir": "input",
       "strategy_type": "excel"
     },
     "excel_config": {
       "sheet_name": 0,
       "header_row": null,
       "skip_rows": 3,
       "use_pandas": true
     },
     "column_mapping": {
       "name_columns": [1, 5],
       "price_columns": [2, 6],
       "process_mode": "paired"
     }
   }
   ```

#### Run Excel Scraper
```bash
# Development
python3 main.py el_chanar_carnes --env dev

# Production
python3 main.py el_chanar_carnes --env prod
```

#### Expected Output
```
INFO - Extracted 150 raw records from Excel
INFO - Processing 150 raw records in paired mode
INFO - Successfully extracted 75 products from Excel
INFO - ✅ Successfully posted 'Bife s/lomo' (Product ID: 1, Supplier ID: 6)
INFO - Export file: output/el_chañar_carnes_export_20251102_111358.xlsx
```

#### Excel Layout Support
**Paired Columns Mode** (Name1|Price1|Name2|Price2):
```
| Product A | $100 | Product C | $300 |
| Product B | $200 | Product D | $400 |
```

**Single Column Mode** (Name|Price):
```
| Product A | $100 |
| Product B | $200 |
```

Configure via `process_mode`: `"paired"` or `"single"`

### Adding New File-Based Suppliers

#### For PDF Price Lists

1. **Create config** (`configs/suppliers/supplier_name.json`):
   ```json
   {
     "supplier_id": 7,
     "supplier_name": "Supplier Name",
     "scraping_strategy": "pdf",
     "credentials": {
       "name": "supplier@restocompras.com",
       "password": "password"
     },
     "file_config": {
       "filename": "pricelist.pdf",
       "input_dir": "input",
       "strategy_type": "pdf"
     },
     "pdf_config": {
       "text_mode": true
     }
   }
   ```

2. **Place PDF file**: `input/pricelist.pdf`

3. **Test**:
   ```bash
   python3 main.py supplier_name --env dev
   ```

#### For Excel Price Lists

1. **Create config** (`configs/suppliers/supplier_name.json`):
   ```json
   {
     "supplier_id": 8,
     "supplier_name": "Supplier Name",
     "scraping_strategy": "excel",
     "credentials": {
       "name": "supplier@restocompras.com",
       "password": "password"
     },
     "file_config": {
       "filename": "pricelist.xlsx",
       "input_dir": "input",
       "strategy_type": "excel"
     },
     "excel_config": {
       "sheet_name": 0,
       "skip_rows": 0,
       "use_pandas": true
     },
     "column_mapping": {
       "name_columns": [0],
       "price_columns": [1],
       "process_mode": "single"
     }
   }
   ```

2. **Place Excel file**: `input/pricelist.xlsx`

3. **Test**:
   ```bash
   python3 main.py supplier_name --env dev
   ```

### File-Based Architecture

```
┌─────────────────┐
│  FileStrategy   │  Abstract base for file-based scraping
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌─────────┐ ┌──────────────┐
│  PDF    │ │    Excel     │
│Strategy │ │  Strategy    │
└─────────┘ └──────────────┘
    │              │
    ▼              ▼
┌─────────┐ ┌──────────────────┐
│ Irlanda │ │ El Chañar Carnes │
│ Scraper │ │    Scraper       │
└─────────┘ └──────────────────┘
```

### Dependencies for File Processing

```bash
# PDF processing
pip install pdfplumber>=0.10.0

# Excel processing (already included)
pip install pandas>=2.1.0
pip install openpyxl>=3.1.0
```

### Troubleshooting File-Based Scrapers

| Issue | Solution |
|-------|----------|
| **File not found** | Ensure file is in `input/` directory with exact filename from config |
| **Empty PDF extraction** | Try switching `text_mode` between `true` and `false` |
| **Excel column errors** | Verify column indices in `name_columns` and `price_columns` (0-based) |
| **No products extracted** | Check `skip_rows` setting, inspect file structure manually |
| **Price parsing errors** | Update `price_format` in config (decimal/thousands separators) |

---

## �🔧 Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| **Authentication failed** | Check credentials in supplier config, verify supplier exists in backend |
| **No products found** | Update selectors in config, check website structure with DevTools |
| **ChromeDriver not found** | Install: `brew install chromedriver` (macOS) or download manually |
| **Products not posted to API** | Ensure products exist in backend database, check logs for product ID lookup failures |
| **401 Unauthorized** | Token expired - Run scraper again to get fresh token |
| **Delete failed** | Check endpoint URL, verify supplier ID exists, review logs |
| **Wrong environment** | Check CLI argument: `--env dev` or `--env prod` |
| **Timeout errors** | Increase timeout in config (especially for production) |

### Debug Mode

Check logs for detailed information:
```bash
# View latest log
ls -t logs/scraper_*.log | head -1 | xargs cat

# Search for errors
grep "ERROR" logs/scraper_*.log

# Search for specific product
grep "Tomate Cherry" logs/scraper_*.log
```

### Verify Environment

```bash
python3 main.py greenshop --env prod 2>&1 | grep "Environment:"
# Should show: INFO - Environment: PROD
```

---

## 🏗️ Architecture

### Design Patterns

1. **Strategy Pattern**: Different scraping approaches (Requests vs Selenium)
2. **Template Method**: `ScraperBase` defines workflow, suppliers implement specifics
3. **Configuration-Driven**: All settings in JSON files
4. **Backend Integration**: Dynamic data fetching from API

### Component Diagram

```
┌─────────────────┐
│    main.py      │  CLI entry point
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  ConfigLoader   │  Environment-aware config loading
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   APIClient     │  Backend communication + Auth
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  ScraperBase    │  Base workflow (Template Method)
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│  Supplier Scrapers              │
│  - Strategy selection           │
│  - Selector configuration       │
│  - Product extraction logic     │
└─────────┬───────────────────────┘
          │
    ┌─────┴─────┐
    ▼           ▼
┌─────────┐ ┌──────────┐
│Requests │ │ Selenium │  Scraping strategies
│Strategy │ │ Strategy │
└─────────┘ └──────────┘
```

### Data Processing Pipeline

```
Website HTML
    ↓
Extract raw data (BeautifulSoup + CSS selectors)
    ↓
Parse titles ("Tomate 500 gr" → name, quantity, unit)
    ↓
Clean prices ("$1.234,50" → 1234.50)
    ↓
Standardize units (gr→G, kg→KG, un→UNIT)
    ↓
Deduplicate by (name, unit, quantity)
    ↓
API Lookup (dual-strategy: full name → short name)
    ↓
POST to backend (/api/item)
    ↓
Export to Excel
```

### Logging System

```
DEBUG   → Detailed scraping info (file only)
INFO    → Progress updates (console + file)
WARNING → Skipped products, fallback strategies
ERROR   → Failed operations, exceptions
CRITICAL→ System failures
```

**Log Format:**
- `→` Outgoing requests
- `←` Incoming responses
- `✓` Success indicators
- `✗` Error indicators
- `⚠` Warning indicators

---

## 📝 Summary

**restoCompras Scrapers** is a production-ready framework that:

✅ **Automates** supplier data collection  
✅ **Integrates** seamlessly with backend API  
✅ **Scales** easily - add suppliers in minutes  
✅ **Maintains** data quality through validation and deduplication  
✅ **Supports** multiple environments (dev/prod)  
✅ **Cleans** database before each scrape for fresh data  
✅ **Logs** comprehensive details for debugging  
✅ **Exports** standardized Excel reports  

**Key Philosophy**: Backend is the source of truth for business data; configs only contain technical scraping details.

---

## 📄 License

MIT
