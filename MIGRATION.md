# Migration Guide: Legacy Scripts → Modular Framework

This guide helps you transition from the legacy scrapers to the new modular framework.

## What Changed?

### Before (Legacy)
- Hardcoded configuration in each script
- Duplicate code across scrapers
- Manual execution of individual Python files
- JWT tokens hardcoded in multiple places
- Version numbers in filenames

### After (New Framework)
- JSON-based configuration
- Shared core components
- Single CLI entry point
- Centralized API configuration
- Version control through git

## Running Your Existing Scrapers

### Green Shop

**Old way:**
```bash
python3 greenshop_scraper_version12.py
```

**New way:**
```bash
# First, update the JWT token in configs/api_config.json
python3 main.py greenshop
```

### Lácteos Granero

**Old way:**
```bash
python3 lacteos_granero-scraper-version2.py
```

**New way:**
```bash
# First, update the JWT token in configs/api_config.json
python3 main.py lacteos_granero
```

## Configuration Migration

### Step 1: Update API Configuration

Create or edit `configs/api_config.json`:

```json
{
  "base_url": "http://localhost:8080",
  "auth_token": "YOUR_CURRENT_JWT_TOKEN",
  "search_endpoint": "/api/products/search/best-match",
  "item_endpoint": "/api/item",
  "timeout": 10
}
```

**Copy your JWT token** from the old scripts (the `AUTH_TOKEN` variable).

### Step 2: Verify Supplier Configs

The supplier configurations are already created:
- `configs/suppliers/greenshop.json`
- `configs/suppliers/lacteos_granero.json`

If your URLs or selectors have changed, edit these files.

## Feature Comparison

| Feature | Legacy Scripts | New Framework |
|---------|---------------|---------------|
| Configuration | Hardcoded in Python | JSON files |
| Add new supplier | ~200 lines of Python | Config file + ~50 lines |
| Update JWT token | Edit multiple files | Edit one config file |
| Logging | Print statements | Structured logging to file |
| Deduplication | Per-script | Shared utility function |
| API client | Per-script | Shared, reusable |
| Testing | Manual | Testable components |

## Installation

```bash
# Install dependencies
pip3 install -r requirements.txt

# Verify installation
python3 main.py --list
```

## Testing the Migration

1. **Update API token** in `configs/api_config.json`

2. **Test Green Shop:**
```bash
python3 main.py greenshop
```

3. **Test Lácteos Granero:**
```bash
python3 main.py lacteos_granero
```

4. **Check outputs:**
- Excel files in `output/` directory
- Logs in `logs/` directory

## Troubleshooting

### "No products found"

The website structure may have changed. Check the selectors in `configs/suppliers/*.json`.

**How to update selectors:**

1. Open the supplier website in a browser
2. Right-click on a product → Inspect
3. Find the CSS selectors for:
   - Product container
   - Product title
   - Price
   - Image
4. Update the selectors in the config file

### "Auth token expired"

Update `configs/api_config.json` with a fresh token.

### Import errors

Make sure you're running from the project root:
```bash
cd restocompras-scrapers
python3 main.py greenshop
```

## What to Do with Legacy Scripts

### Option 1: Keep for Reference
The legacy scripts in `caliber-scraper/` and `green-shop-scrapper/` can stay as documentation of the evolution.

### Option 2: Archive
Move them to an `archive/` directory:
```bash
mkdir archive
mv caliber-scraper archive/
mv green-shop-scrapper archive/
```

### Option 3: Delete
Once you've verified the new framework works:
```bash
rm -rf caliber-scraper/
rm -rf green-shop-scrapper/
```

## Benefits of the New System

1. **Easier to maintain**: One place to update logic
2. **Faster development**: Add suppliers with config files
3. **Better debugging**: Structured logs + proper error handling
4. **More reliable**: Shared, tested components
5. **Scalable**: Add 10 more suppliers without code duplication

## Getting Help

- Check `README.md` for detailed usage
- Review `.github/copilot-instructions.md` for architecture details
- Examine existing supplier implementations in `src/suppliers/`

## Next Steps

1. ✅ Install dependencies
2. ✅ Update API configuration
3. ✅ Test existing scrapers
4. ✅ Add your first new supplier using the new system
5. ✅ Archive or remove legacy scripts

Welcome to the new framework! 🚀
