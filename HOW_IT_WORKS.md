# How the Scraper Module Works

## Overview
A modular web scraping framework for food suppliers in Argentina with JSON-based configuration, dual scraping strategies (Selenium/Requests), and backend API integration.

---

## Architecture

### Core Components

```
┌─────────────────┐
│    main.py      │  Entry point - CLI interface
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  ConfigLoader   │  Loads JSON configurations
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   APIClient     │  Handles backend communication
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  ScraperBase    │  Base scraper workflow
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│  Supplier Scrapers              │
│  - GreenShopScraper             │
│  - LacteosGraneroScraper        │
│  - DistribuidoraPopScraper      │
│  - TynaScraper                  │
└─────────┬───────────────────────┘
          │
    ┌─────┴─────┐
    ▼           ▼
┌─────────┐ ┌──────────┐
│Requests │ │ Selenium │  Scraping strategies
│Strategy │ │ Strategy │
└─────────┘ └──────────┘
```

### Key Design Patterns

1. **Strategy Pattern**: Different scraping approaches (Requests vs Selenium)
2. **Template Method**: `ScraperBase` defines the workflow, suppliers implement specifics
3. **Configuration-Driven**: All supplier settings in JSON files
4. **Backend Integration**: Automatic authentication and data synchronization

---

## Complete Workflow

### 1. Authentication Phase
```
Load API config
    ↓
Login with supplier credentials
    ↓
Receive JWT token
    ↓
Fetch supplier details from backend
    ↓
Get supplier ID and name from API
```

**Key Points:**
- Each supplier has unique credentials in their config file
- JWT token is automatically obtained and stored
- Supplier ID and name come from backend (NOT from config files)
- **Scraper aborts if authentication or supplier fetch fails**

### 2. Scraping Phase
```
Load supplier config
    ↓
Choose strategy (Requests or Selenium)
    ↓
For each URL:
    ↓
    Fetch HTML content
    ↓
    Parse with BeautifulSoup + CSS selectors
    ↓
    Extract products (name, price, image, etc.)
    ↓
Collect all products
```

**Strategy Selection:**
- **Requests**: Fast, for static HTML sites (e.g., Green Shop)
- **Selenium**: Slower, for JavaScript-heavy sites (e.g., Lácteos Granero)

### 3. Data Processing Phase
```
Raw products
    ↓
Parse titles: "Tomate Cherry 500 gr" → name="Tomate Cherry", quantity=500, unit="G"
    ↓
Clean prices: "$1.234,50" → 1234.50
    ↓
Standardize units: gr→G, kg→KG, un→UNIT
    ↓
Deduplicate by (name, unit, quantity)
```

### 4. API Integration Phase
```
For each product:
    ↓
    Search backend: "Tomate Cherry 500 gr"
    ↓
    If not found: Search again with "Tomate Cherry"
    ↓
    If found: Get productId
    ↓
    POST to /api/item with full data
    ↓
Skip products without productId
```

**Dual-Strategy Lookup:**
1. First attempt: Search with full name + quantity + unit
2. Second attempt: Search with only first 2 words of name
3. If still not found: Skip product (logged as warning)

### 5. Export Phase
```
Successful products
    ↓
Export to Excel: output/supplier_export_TIMESTAMP.xlsx
    ↓
Columns: Nombre, Marca, Precio, Imagen, Producto ID, Unidad, Cantidad, supplierId
```

---

## Directory Structure

```
scrapers/
├── main.py                    # Entry point
├── requirements.txt           # Python dependencies
│
├── configs/
│   ├── api_config.json       # API base URL, endpoints, global credentials
│   └── suppliers/            # One JSON file per supplier
│       ├── greenshop.json
│       ├── lacteos_granero.json
│       ├── distribuidora_pop.json
│       └── tyna.json
│
├── src/
│   ├── core/
│   │   ├── scraper_base.py   # Abstract base class
│   │   ├── api_client.py     # Backend API communication
│   │   ├── parser.py         # Data parsing utilities
│   │   └── exporter.py       # Excel/JSON export
│   │
│   ├── strategies/
│   │   ├── scraping_strategy.py      # Interface
│   │   ├── requests_strategy.py      # Static sites
│   │   └── selenium_strategy.py      # Dynamic sites
│   │
│   ├── suppliers/            # Supplier implementations
│   │   ├── greenshop.py
│   │   ├── lacteos_granero.py
│   │   ├── distribuidora_pop.py
│   │   └── tyna.py
│   │
│   ├── config/
│   │   └── config_loader.py  # JSON config loader
│   │
│   └── utils/
│       ├── logger.py         # Logging setup
│       └── text_processing.py # Deduplication
│
├── output/                   # Generated Excel files
├── logs/                     # Execution logs
└── legacy-scrappers/        # Old monolithic scripts (preserved)
```

---

## Data Flow Example

### Input (Website)
```html
<div class="product">
  <h3 class="title">Tomate Cherry 500 gr</h3>
  <span class="price">$1.234,50</span>
  <img src="/images/tomate.jpg">
</div>
```

### Step 1: Extract
```python
{
  'title': 'Tomate Cherry 500 gr',
  'price': '$1.234,50',
  'image': '/images/tomate.jpg'
}
```

### Step 2: Parse & Clean
```python
{
  'name': 'Tomate Cherry',
  'quantity': 500,
  'unit': 'G',
  'price': 1234.50,
  'image': 'https://site.com/images/tomate.jpg'
}
```

### Step 3: API Lookup
```
→ POST /api/products/search/best-match
  {"query": "Tomate Cherry 500 gr"}
← Response: {"id": 123, "name": "Tomate Cherry"}
```

### Step 4: Complete & Post
```python
{
  'name': 'Tomate Cherry',
  'description': 'Tomate Cherry',
  'price': 1234.50,
  'image': 'https://site.com/images/tomate.jpg',
  'productId': 123,           # From API
  'unit': 'G',
  'quantity': 500,
  'supplierId': 1,            # From backend supplier details
  'brand': 'Green Shop'       # From backend supplier details
}

→ POST /api/item
  {above payload}
← Response: 201 Created
```

### Step 5: Excel Output
```
| Nombre         | Marca      | Precio  | Producto ID | Unidad | Cantidad |
|----------------|------------|---------|-------------|--------|----------|
| Tomate Cherry  | Green Shop | 1234.50 | 123         | G      | 500      |
```

---

## Logging System

### Log Levels
- **DEBUG**: Detailed request/response data (file only)
- **INFO**: Progress updates (console + file)
- **WARNING**: Skipped products, fallbacks
- **ERROR**: Failed operations
- **CRITICAL**: System failures

### Log Format
```
# Request logging (→ indicates outgoing)
→ POST http://localhost:8080/api/auth/login
  Request payload: {...}

# Response logging (← indicates incoming)
← Response status: 200
← Response body: {...}

# Success indicators
✓ Successfully posted Tomate Cherry (Product ID: 123, Supplier ID: 1)

# Error indicators
✗ API post failed for Tomate Cherry: Connection timeout

# Warning indicators
⚠ Product not found in backend: Producto Nuevo
```

### Log Files
- **Location**: `logs/scraper_TIMESTAMP.log`
- **Retention**: Manual cleanup
- **Contents**: Full request/response bodies, error stack traces, processing details

---

## Backend API Integration

### Required Endpoints

1. **Authentication**
   - `POST /api/auth/login`
   - Body: `{"email": "...", "password": "..."}`
   - Response: JWT token in header or body

2. **Supplier Details**
   - `GET /api/suppliers/search?email=supplier@email.com`
   - Returns: `{"id": 123, "name": "Supplier Name"}`
   - **MANDATORY**: Scraper aborts if this fails

3. **Product Search**
   - `POST /api/products/search/best-match`
   - Body: `{"query": "Product Name"}`
   - Returns: `{"id": 123, "name": "Product Name"}`
   - Used for dual-strategy lookup

4. **Item Creation**
   - `POST /api/item`
   - Body: Full product data
   - Returns: Created item

### Authentication Flow
```
1. Login with supplier credentials
2. Extract JWT token from response
3. Store token in Authorization header
4. Use for all subsequent requests
5. Token refreshed on each scraper run
```

---

## Error Handling

### Network Errors
- **Action**: Log error, skip URL, continue with next
- **Impact**: Some products may be missed

### Parsing Errors
- **Action**: Log error, skip product, continue
- **Impact**: Individual products skipped

### API Errors
- **404 (Product not found)**: Skip product, continue
- **401 (Unauthorized)**: Log error, ABORT (token expired)
- **500 (Server error)**: Log error, continue (backend issue)

### Strategy
- Fail gracefully for individual products
- Continue processing to maximize data collection
- Abort only for critical failures (authentication, supplier details)

---

## Performance Characteristics

### Requests Strategy (Static Sites)
- **Speed**: Fast (~2-5 seconds per URL)
- **Resource Usage**: Low
- **Use When**: Site serves complete HTML
- **Example**: Green Shop

### Selenium Strategy (Dynamic Sites)
- **Speed**: Slow (~15-30 seconds per URL)
- **Resource Usage**: High (launches Chrome browser)
- **Use When**: Content loaded via JavaScript
- **Features**: Auto-scrolling for lazy-loaded content
- **Example**: Lácteos Granero

### Typical Run Times
- **Green Shop**: ~30 seconds (6 URLs, ~150 products)
- **Lácteos Granero**: ~2-3 minutes (multiple pages, JavaScript rendering)

---

## Configuration Management

### Backend-Driven Data
✅ **Comes from Backend API:**
- Supplier ID
- Supplier Name
- Product IDs

❌ **NOT in Config Files:**
- No hardcoded IDs
- Single source of truth: Backend database

### Config File Contents
✅ **Only Technical Scraping Details:**
- Scraping strategy (requests/selenium)
- URLs to scrape
- CSS selectors
- Strategy-specific settings (timeouts, headless mode)
- Supplier credentials

### Why This Design?
1. **Data Consistency**: IDs always match backend database
2. **Automatic Updates**: Name changes in backend propagate automatically
3. **Simplified Maintenance**: Config files only have technical settings
4. **Validation**: Ensures supplier exists before scraping

---

## Running Scrapers

### Basic Commands
```bash
# Run a single supplier
python3 main.py greenshop

# List available suppliers
python3 main.py --list

# Custom directories
python3 main.py greenshop --config-dir ./configs --output-dir ./output
```

### What Happens When You Run
1. ✅ Load configurations
2. ✅ Authenticate with backend
3. ✅ Fetch supplier details
4. ✅ Start scraping URLs
5. ✅ Extract & process products
6. ✅ Deduplicate
7. ✅ API lookup & post
8. ✅ Export to Excel
9. ✅ Show summary

### Output Files
- **Excel**: `output/supplier_name_export_TIMESTAMP.xlsx`
- **Logs**: `logs/scraper_TIMESTAMP.log`

---

## Extension Points

### Add New Scraping Strategy
```python
# src/strategies/playwright_strategy.py
class PlaywrightStrategy(ScrapingStrategy):
    def fetch_html(self, url: str) -> str:
        # Use Playwright instead of Selenium
        pass
```

### Add New Export Format
```python
# src/core/exporter.py
def export_to_csv(products, supplier_name):
    # Export to CSV
    pass
```

### Add Rate Limiting
```python
# src/strategies/scraping_strategy.py
def fetch_with_delay(self, url: str, delay: int = 2):
    time.sleep(delay)
    return self.fetch_html(url)
```

---

## Key Benefits

### For Developers
- **Modular**: Add suppliers without touching core code
- **Testable**: Each component isolated and testable
- **Maintainable**: Clear separation of concerns
- **Extensible**: Easy to add new strategies or exporters

### For Operations
- **Automated**: Runs unattended with scheduling
- **Reliable**: Graceful error handling
- **Observable**: Comprehensive logging
- **Auditable**: Excel exports with timestamps

### For Business
- **Scalable**: Add suppliers in minutes
- **Accurate**: Deduplication and validation
- **Integrated**: Direct backend sync
- **Up-to-date**: Automatic supplier data refresh

---

## Summary

The scraper module is a **configuration-driven framework** that:
1. Authenticates automatically with backend
2. Fetches supplier details dynamically
3. Scrapes websites using appropriate strategies
4. Processes and standardizes product data
5. Syncs with backend via API
6. Exports results to Excel

**Key Philosophy**: Backend is the source of truth for business data; configs only contain technical scraping details.
