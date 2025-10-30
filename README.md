# restoCompras Scrapers

A modular, configurable web scraping framework for food suppliers in Argentina. Built to be easily extensible with support for both static (requests) and dynamic (Selenium) websites.

## 📚 Documentation

- **[HOW_IT_WORKS.md](HOW_IT_WORKS.md)** - Complete architecture, workflow, and technical details
- **[ADDING_NEW_SUPPLIER.md](ADDING_NEW_SUPPLIER.md)** - Step-by-step guide with examples

## ✨ Features

- **Modular Architecture**: Add suppliers without modifying core code
- **Dual Scraping Strategies**: Static (requests) and dynamic (Selenium) websites
- **JSON Configuration**: All supplier settings in external config files
- **Backend Integration**: Automatic authentication and supplier details fetching
- **API Integration**: Product ID lookup and posting to backend API
- **Deduplication**: Intelligent deduplication by name, unit, and quantity
- **Data Export**: Excel exports with standardized format
- **Comprehensive Logging**: Detailed request/response logs for debugging

## 🚀 Quick Start

### Installation

```bash
# 1. Navigate to project directory
cd restocompras-scrapers

# 2. Install dependencies
pip3 install -r requirements.txt

# 3. Configure API settings
# Edit configs/api_config.json with your backend URL and credentials
```

### Run a Scraper

```bash
# Scrape a supplier
python3 main.py greenshop

# List available suppliers
python3 main.py --list

# Custom directories
python3 main.py greenshop --config-dir ./configs --output-dir ./output
```

### What Happens

1. ✅ Authenticates with backend using supplier credentials
2. ✅ Fetches supplier details (ID and name) from API
3. ✅ Scrapes product pages using configured strategy
4. ✅ Extracts and standardizes product data
5. ✅ Deduplicates products
6. ✅ Looks up product IDs from backend
7. ✅ Posts validated products to API
8. ✅ Exports results to Excel (`output/` directory)

**Output**: 
- `output/supplier_name_export_TIMESTAMP.xlsx`
- `logs/scraper_TIMESTAMP.log`

## 📖 Learn More

### Understanding the System
Read **[HOW_IT_WORKS.md](HOW_IT_WORKS.md)** to understand:
- Complete architecture and design patterns
- Detailed workflow (authentication → scraping → API integration)
- Data processing pipeline
- Logging system
- Backend API integration
- Error handling strategies

### Adding a New Supplier
Read **[ADDING_NEW_SUPPLIER.md](ADDING_NEW_SUPPLIER.md)** for:
- Complete step-by-step guide
- Configuration examples (requests vs selenium)
- Scraper implementation templates
- Testing and validation
- Troubleshooting common issues
- Production checklist

## 📦 Project Structure

```
scrapers/
├── main.py                    # CLI entry point
├── requirements.txt           # Dependencies
├── configs/
│   ├── api_config.json       # API base URL, endpoints, credentials
│   └── suppliers/            # One JSON per supplier
├── src/
│   ├── core/                 # Framework components
│   ├── strategies/           # Scraping strategies
│   ├── suppliers/            # Supplier implementations
│   ├── config/               # Config management
│   └── utils/                # Utilities
├── output/                   # Generated Excel files
└── logs/                     # Execution logs
```

## ⚙️ Configuration

### API Config (`configs/api_config.json`)
```json
{
  "base_url": "http://localhost:8080",
  "login_endpoint": "/api/auth/login",
  "supplier_search_endpoint": "/api/suppliers/search",
  "search_endpoint": "/api/products/search/best-match",
  "item_endpoint": "/api/item",
  "timeout": 10,
  "credentials": {
    "email": "global@restocompras.com",
    "password": "password"
  }
}
```

### Supplier Config (`configs/suppliers/*.json`)
```json
{
  "scraping_strategy": "requests",  // or "selenium"
  "urls": ["https://supplier.com/products"],
  "selectors": {
    "product_list": ".product",
    "title": ".title",
    "price": ".price",
    "image": "img"
  },
  "strategy_config": {
    "timeout": 15  // requests-specific
    // OR for selenium: "headless": true, "wait_time": 30
  },
  "credentials": {
    "email": "supplier@restocompras.com",
    "password": "password"
  }
}
```

**Note**: Supplier ID and name are **fetched from backend**, not stored in config files.

## 🔧 Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Authentication failed | Check credentials in config, verify supplier exists in backend |
| No products found | Update selectors in config, check website structure |
| ChromeDriver not found | Install: `brew install chromedriver` (macOS) |
| Products not posted to API | Ensure products exist in backend database |

**For detailed troubleshooting**, see [ADDING_NEW_SUPPLIER.md](ADDING_NEW_SUPPLIER.md#step-7-troubleshooting)

## 🤝 Contributing

To add a new supplier:
1. Create supplier in backend database
2. Create config file in `configs/suppliers/`
3. Implement scraper class in `src/suppliers/`
4. Register in `main.py`
5. Test and validate

**Full guide**: [ADDING_NEW_SUPPLIER.md](ADDING_NEW_SUPPLIER.md)

## 📋 Available Suppliers

- ✅ **greenshop** - Green Shop (Requests strategy)
- ✅ **lacteos_granero** - Lácteos Granero (Selenium strategy)
- ✅ **distribuidora_pop** - Distribuidora Pop
- ✅ **tyna** - Tyna

## 📝 License

MIT

---

**Need help?** Check the detailed documentation:
- [HOW_IT_WORKS.md](HOW_IT_WORKS.md) - Complete technical reference
- [ADDING_NEW_SUPPLIER.md](ADDING_NEW_SUPPLIER.md) - Step-by-step implementation guide
