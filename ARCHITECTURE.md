# Architecture Diagram

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         main.py (CLI)                           │
│                                                                 │
│  Commands:                                                      │
│  - python main.py greenshop                                    │
│  - python main.py lacteos_granero                              │
│  - python main.py --list                                       │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ConfigLoader                               │
│                                                                 │
│  Loads:                                                         │
│  - configs/api_config.json                                     │
│  - configs/suppliers/{supplier}.json                           │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                   SupplierScraper                               │
│                   (GreenShop / LacteosGranero)                  │
│                                                                 │
│  Inherits from: ScraperBase                                     │
│  Implements:                                                    │
│  - get_urls()                                                   │
│  - _fetch_html()                                                │
│  - extract_products()                                           │
└─────────┬───────────────────────────────────────┬───────────────┘
          │                                       │
          ▼                                       ▼
┌──────────────────────┐              ┌──────────────────────┐
│  ScrapingStrategy    │              │     APIClient        │
│                      │              │                      │
│  ┌────────────────┐ │              │  - fetch_product_id()│
│  │ RequestsStrategy│ │              │  - post_item()       │
│  └────────────────┘ │              │  - Dual-strategy     │
│  ┌────────────────┐ │              │    lookup            │
│  │SeleniumStrategy│ │              └──────────┬───────────┘
│  └────────────────┘ │                         │
└──────────┬───────────┘                         │
           │                                     │
           ▼                                     ▼
    ┌──────────────┐                    ┌──────────────┐
    │   Website    │                    │ Backend API  │
    │              │                    │              │
    │ - HTML/JS    │                    │ - Search     │
    │ - Products   │                    │ - Insert     │
    └──────────────┘                    └──────────────┘
           │
           ▼
    ┌──────────────────────┐
    │   BeautifulSoup      │
    │   (HTML Parsing)     │
    └──────────┬───────────┘
               │
               ▼
    ┌──────────────────────┐
    │    DataParser        │
    │                      │
    │  - parse_title()     │
    │  - clean_price()     │
    │  - standardize()     │
    └──────────┬───────────┘
               │
               ▼
    ┌──────────────────────┐
    │  deduplicate()       │
    │  (utils)             │
    └──────────┬───────────┘
               │
               ▼
    ┌──────────────────────┐
    │   DataExporter       │
    │                      │
    │  - Excel export      │
    │  - JSON export       │
    └──────────────────────┘
```

## Component Responsibilities

### 1. **main.py** (Entry Point)
- Parse command-line arguments
- Initialize ConfigLoader
- Create APIClient
- Instantiate appropriate scraper
- Coordinate execution

### 2. **ConfigLoader** (Configuration)
- Load JSON configurations
- Validate required fields
- Provide supplier list
- Manage config paths

### 3. **ScraperBase** (Template)
- Define scraping workflow
- Orchestrate steps:
  1. Get URLs
  2. Fetch HTML
  3. Extract products
  4. Process (deduplicate)
  5. Integrate with API
  6. Return results

### 4. **SupplierScraper** (Implementation)
- Choose scraping strategy
- Define CSS selectors
- Implement extraction logic
- Handle supplier-specific quirks

### 5. **ScrapingStrategy** (Strategy Pattern)
- **RequestsStrategy**: Fast, for static sites
- **SeleniumStrategy**: Full browser, for dynamic sites

### 6. **APIClient** (Integration)
- Product ID lookup (2 strategies)
- Post products to backend
- Handle authentication
- Manage errors

### 7. **DataParser** (Utilities)
- Parse product titles
- Clean prices
- Standardize units
- Format data

### 8. **DataExporter** (Output)
- Export to Excel
- Export to JSON
- Timestamped filenames
- Consistent structure

## Data Flow

```
Website HTML
    │
    ▼
Extract raw data
    │
    ├─ Name: "Tomate Cherry 500 gr"
    ├─ Price: "$1.234,50"
    └─ Image: "/images/product.jpg"
    │
    ▼
Parse & Clean
    │
    ├─ Name: "Tomate Cherry"
    ├─ Quantity: "500"
    ├─ Unit: "G"
    ├─ Price: 1234.50
    └─ Image: "https://site.com/images/product.jpg"
    │
    ▼
Deduplicate
    │
    └─ Remove duplicates by (name, unit, quantity)
    │
    ▼
API Lookup
    │
    ├─ Search: "Tomate Cherry 500 gr" → productId: 123
    └─ If not found, search: "Tomate Cherry" → productId: 123
    │
    ▼
API Post
    │
    └─ POST /api/item with full product data
    │
    ▼
Export
    │
    └─ Excel file in output/
```

## Strategy Selection

```
┌──────────────────────────────────────┐
│   Is the site JavaScript-heavy?     │
│   (React, Vue, lazy loading, etc.)  │
└──────────────┬───────────────────────┘
               │
       ┌───────┴───────┐
       │               │
      YES             NO
       │               │
       ▼               ▼
┌─────────────┐  ┌────────────┐
│  Selenium   │  │  Requests  │
│  Strategy   │  │  Strategy  │
│             │  │            │
│ - Slower    │  │ - Faster   │
│ - Renders   │  │ - Simpler  │
│   JS        │  │ - Less     │
│ - Auto-     │  │   overhead │
│   scroll    │  │            │
└─────────────┘  └────────────┘
```

## Extension Points

### Add New Strategy
```python
# src/strategies/playwright_strategy.py
class PlaywrightStrategy(ScrapingStrategy):
    def fetch_html(self, url: str) -> str:
        # Use Playwright instead of Selenium
```

### Add New Exporter
```python
# src/core/exporter.py
def export_to_csv(products, supplier_name):
    # Export to CSV format
```

### Add Authentication
```python
# src/strategies/requests_strategy.py
def fetch_html_with_auth(self, url: str, username: str, password: str):
    # Handle login before scraping
```

### Add Rate Limiting
```python
# src/strategies/scraping_strategy.py
def fetch_with_delay(self, url: str, delay: int = 2):
    time.sleep(delay)
    return self.fetch_html(url)
```

## Configuration Flow

```
configs/api_config.json
    │
    ├─ auth_token ─────────────┐
    ├─ base_url ───────────────┤
    └─ endpoints ──────────────┤
                               │
configs/suppliers/greenshop.json    │
    │                          │
    ├─ supplier_id ────────────┤
    ├─ urls ───────────────────┤
    ├─ selectors ──────────────┤
    └─ strategy_config ────────┤
                               │
                               ▼
                        ┌──────────────┐
                        │   Scraper    │
                        │  Instance    │
                        └──────────────┘
```

## Error Handling

```
Try Scrape
    │
    ├─ Network Error ──────► Log & Continue to next URL
    │
    ├─ Parse Error ────────► Log & Skip product
    │
    ├─ API 404 ────────────► Log & Skip product (not in DB)
    │
    ├─ API 401 ────────────► Log & STOP (token expired)
    │
    └─ Success ────────────► Continue
```

## Logging Levels

```
DEBUG   → Detailed scraping info (saved to file)
INFO    → Progress updates (console + file)
WARNING → Skipped products, fallback strategies
ERROR   → Failed operations, exceptions
CRITICAL→ System failures
```
