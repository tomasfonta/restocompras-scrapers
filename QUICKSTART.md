# Quick Start Guide

Get up and running with restoCompras scrapers in 5 minutes.

## Prerequisites

- Python 3.8 or higher
- Chrome browser (for Selenium-based scrapers)
- Backend API running (for data integration)

## Installation

```bash
# 1. Navigate to project directory
cd restocompras-scrapers

# 2. Install dependencies
pip3 install -r requirements.txt

# 3. Verify installation
python3 main.py --list
```

Expected output:
```
Available suppliers:
----------------------------------------
✓ greenshop
✓ lacteos_granero
----------------------------------------
```

## Configuration

### Update API Token

Edit `configs/api_config.json` and replace `YOUR_JWT_TOKEN_HERE` with your actual token:

```json
{
  "base_url": "http://localhost:8080",
  "auth_token": "eyJhbGciOiJIUzUxMiJ9...",
  "search_endpoint": "/api/products/search/best-match",
  "item_endpoint": "/api/item",
  "timeout": 10
}
```

💡 **Tip**: Your JWT token can be found in your backend admin panel or authentication response.

## Run Your First Scraper

### Green Shop (Fast - Static Site)

```bash
python3 main.py greenshop
```

This will:
1. ✅ Scrape 6 product categories from Green Shop
2. ✅ Extract ~100-200 products
3. ✅ Deduplicate based on name/unit/quantity
4. ✅ Look up product IDs from your API
5. ✅ Post valid products to your backend
6. ✅ Export results to Excel

**Output files:**
- `output/green_shop_export_TIMESTAMP.xlsx` - Product data
- `logs/scraper_TIMESTAMP.log` - Detailed logs

### Lácteos Granero (Slower - Dynamic Site)

```bash
python3 main.py lacteos_granero
```

This uses Selenium (headless Chrome) to handle JavaScript-rendered content.

## Understanding the Output

### Console Output

```
INFO - Starting scraper for: greenshop
INFO - Loading API config from configs/api_config.json
INFO - API config loaded successfully
INFO - Supplier config loaded for Green Shop
INFO - ======================================================================
INFO - STARTING SCRAPE: Green Shop
INFO - ======================================================================
INFO - Scraping URL: https://greenshop.ar/categoria-producto/frutas/todas-las-frutas/
INFO - Extracted 45 products from https://greenshop.ar/...
INFO - Total products extracted: 180
INFO - Processing 180 products...
INFO - Removed 12 duplicate products
INFO - Integrating 168 products with API...
INFO - Successfully posted 156 products to API
INFO - Exported 156 products to output/green_shop_export_20250124_143022.xlsx
INFO - ======================================================================
INFO - SCRAPING COMPLETED SUCCESSFULLY
INFO - Total products: 156
INFO - Export file: output/green_shop_export_20250124_143022.xlsx
INFO - ======================================================================
```

### Excel Output

The Excel file contains columns:
- **Nombre**: Product name (cleaned)
- **Marca**: Brand (supplier name)
- **Descripción**: Description
- **Precio**: Price (numeric)
- **Imagen**: Image URL
- **Producto ID**: Backend product ID
- **Unidad**: Unit (G, KG, UNIT)
- **Cantidad**: Quantity
- **supplierId**: Supplier ID

### Log Files

Check `logs/scraper_TIMESTAMP.log` for:
- Detailed request/response logs
- Error messages with stack traces
- Product processing details
- API interaction logs

## Common Issues

### ❌ "Auth token expired"

**Solution**: Update `configs/api_config.json` with a fresh JWT token.

### ❌ "No products found"

**Possible causes:**
1. Website structure changed → Update selectors in supplier config
2. Network issues → Check internet connection
3. Site blocking scrapers → Try different user agent

**Debug**: Set `"headless": false` in Selenium configs to watch the browser.

### ❌ "ChromeDriver not found" (Selenium scrapers only)

**macOS:**
```bash
brew install chromedriver
```

**Ubuntu/Debian:**
```bash
sudo apt-get install chromium-chromedriver
```

**Windows:**
Download from [ChromeDriver downloads](https://chromedriver.chromium.org/downloads)

### ❌ "Module not found"

**Solution**: Make sure you're running from project root:
```bash
cd restocompras-scrapers
python3 main.py greenshop
```

## Next Steps

### 1. Add a New Supplier

See full guide in `README.md`, but here's the quick version:

```bash
# 1. Create config
cat > configs/suppliers/nuevo_proveedor.json << EOF
{
  "supplier_id": 3,
  "supplier_name": "Nuevo Proveedor",
  "scraping_strategy": "requests",
  "urls": ["https://nuevoproveedor.com/productos"],
  "selectors": {
    "product_list": ".product",
    "title": ".title",
    "price": ".price",
    "image": "img"
  },
  "strategy_config": {"timeout": 15}
}
EOF

# 2. Create scraper (see README.md for template)
# 3. Register in main.py
# 4. Test
python3 main.py nuevo_proveedor
```

### 2. Schedule Regular Scraping

**Using cron (Linux/macOS):**
```bash
# Edit crontab
crontab -e

# Run daily at 2 AM
0 2 * * * cd /path/to/restocompras-scrapers && /usr/bin/python3 main.py greenshop
0 3 * * * cd /path/to/restocompras-scrapers && /usr/bin/python3 main.py lacteos_granero
```

**Using Windows Task Scheduler:**
1. Open Task Scheduler
2. Create Basic Task
3. Trigger: Daily
4. Action: Start a program
5. Program: `python`
6. Arguments: `main.py greenshop`
7. Start in: `C:\path\to\restocompras-scrapers`

### 3. Monitor Performance

Check log files regularly:
```bash
# View latest log
ls -lt logs/ | head -1 | awk '{print $NF}' | xargs cat

# Count successful runs today
grep "COMPLETED SUCCESSFULLY" logs/scraper_$(date +%Y%m%d)*.log | wc -l

# Find errors
grep "ERROR" logs/scraper_*.log
```

## Getting Help

- 📖 **Full documentation**: `README.md`
- 🔧 **Architecture details**: `.github/copilot-instructions.md`
- 🚀 **Migration guide**: `MIGRATION.md`
- 💬 **Issues**: Check logs first, then contact your team

Happy scraping! 🎉
