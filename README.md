# Restocompras Scrapers

Scraper modular y configurable para sincronizar productos desde múltiples proveedores con la API de restocompras-back.

## Instalación

```bash
# Clonar proyecto
cd restocompras-scrapers

# Instalar dependencias
pip install -r requirements.txt

# Crear directorios necesarios
mkdir -p output logs
```

## Uso Rápido

### Testear un proveedor (dry-run)
```bash
python3 skills/test_scraper.py greenshop
```

### Testear todos los proveedores
```bash
python3 skills/test_batch.py
```

### Validar items desde JSON
```bash
python3 skills/validate.py output/greenshop_dry_run_results.json
```

## Estructura del Proyecto

### Lógica Base (`src/core/`)
- **scraper_base.py** - Clase base para todos los scrapers
- **item_builder.py** - Transforma productos usando configuración JSON
- **validator.py** - Valida datos antes de enviar a API
- **dry_run.py** - Modo de prueba sin hacer requests reales
- **api_client.py** - Cliente HTTP para restocompras-back
- **exporter.py** - Exporta resultados a JSON

### Proveedores (`src/suppliers/`)
Cada proveedor implementa:
- Scraper específico (ej: `greenshop.py`)
- Estrategia de scraping (requests, Selenium, Excel, PDF)
- Configuración JSON en `configs/suppliers/`

### Configuración de Proveedor

Cada proveedor tiene un JSON en `configs/suppliers/{proveedor}.json`:

```json
{
  "supplier_id": 45,
  "supplier_name": "Green Shop",
  "scraping_strategy": "requests",
  "scraping_config": {
    "url": "https://ejemplo.com",
    "headers": { "User-Agent": "..." }
  },
  "item_transform": {
    "field_mapping": {
      "name": "product_name",
      "price": "product_price"
    },
    "price_adjustments": {
      "markup_percent": 10,
      "rounding": "up",
      "min_price": 100,
      "max_price": 5000
    },
    "unit_mapping": {
      "kg": "KG",
      "lt": "LT"
    },
    "validations": {
      "required_fields": ["name", "price"],
      "min_price": 50,
      "max_price": 50000
    }
  }
}
```

### Estrategias de Scraping (`src/strategies/`)
- **requests_strategy.py** - HTTP requests (por defecto)
- **selenium_strategy.py** - JavaScript rendering
- **excel_strategy.py** - Archivos .xlsx
- **pdf_strategy.py** - Archivos .pdf

## Cómo Crear un Nuevo Scraper

1. **Crear archivo scraper** (`src/suppliers/mi_proveedor.py`):
```python
from src.core.scraper_base import ScraperBase

class MiProveedorScraper(ScraperBase):
    def _parse_products(self):
        # Retornar lista de productos
        return [
            {"name": "Producto 1", "price": 1000},
            {"name": "Producto 2", "price": 2000},
        ]
```

2. **Crear configuración** (`configs/suppliers/mi_proveedor.json`):
```json
{
  "supplier_id": 99,
  "supplier_name": "Mi Proveedor",
  "scraping_strategy": "requests",
  "scraping_config": { "url": "..." },
  "item_transform": { ... }
}
```

3. **Testear**:
```bash
python3 skills/test_scraper.py mi_proveedor
```

## Flujo de Scraping

```
1. SCRAPING       → Obtiene productos desde proveedor
2. BUILDING       → Transforma usando ItemBuilder + config JSON
3. VALIDATING     → Valida con ItemValidator antes de enviar
4. POSTING/PREVIEW → Envía a API o muestra preview (dry-run)
```

## Debugging

### Ver logs
```bash
tail -f logs/scraper.log
```

### Dry-run (sin API calls)
- Automático en `test_scraper.py` y `test_batch.py`
- Muestra preview de items sin modificar base de datos

### Validar items localmente
```bash
python3 skills/validate.py output/results.json --verbose
```

## Archivos Clave

| Archivo | Propósito |
|---------|-----------|
| `src/core/item_builder.py` | Transforma productos según config |
| `src/core/validator.py` | Valida antes de enviar |
| `src/core/dry_run.py` | Testing sin API calls |
| `skills/test_scraper.py` | CLI para testear un proveedor |
| `skills/test_batch.py` | CLI para testear todos |
| `skills/validate.py` | CLI para validar items |

## API Restocompras

**Endpoint**: POST `/api/items` (restocompras-back)

**Payload**: 
```json
{
  "supplier_id": 45,
  "sku": "ABC123",
  "name": "Producto",
  "price": 1500.00,
  "quantity": 0.5,
  "unit": "KG",
  "brand": "Green Shop"
}
```

## Troubleshooting

| Problema | Solución |
|----------|----------|
| `ModuleNotFoundError: No module named 'src'` | Ejecutar desde raíz del proyecto |
| Items no validan | Revisar `item_transform` en JSON de config |
| Scraper sin datos | Verificar URL en `scraping_config` |
| API error 401 | Revisar credenciales en `.env` |

## Próximos Pasos

- Agregar más proveedores con `src/suppliers/{proveedor}.py`
- Configurar restocompras-back en local (Docker Compose)
- Setup de CI/CD para validar scrapers automáticamente
