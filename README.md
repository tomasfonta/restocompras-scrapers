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

### Usar la API REST (nuevo)

#### 1. Configuración
```bash
# Copiar archivo de configuración
cp .env.example .env

# Editar .env con tu API key
export API_KEY_SECRET="tu-clave-secreta"
export FLASK_PORT=5000
export FLASK_ENV=dev
```

#### 2. Iniciar servidor Flask
```bash
python app.py
```

#### 3. Ejemplos de uso

**Verificar salud del servidor:**
```bash
curl http://localhost:5000/health
```

**Listar proveedores disponibles:**
```bash
curl -H "Authorization: Bearer tu-clave-secreta" \
  http://localhost:5000/api/suppliers
```

**Realizar scraping de un proveedor (retorna items, sin guardar):**
```bash
curl -X POST \
  http://localhost:5000/api/scrape/delparque
```

> **Nota:** El endpoint extrae y transforma items automáticamente. Los items se devuelven en JSON sin guardarse en la base de datos. No hace POST a la API backend, solo devuelve los datos.

**Respuesta JSON típica:**
```json
{
  "status": "success",
  "supplier": "delparque",
  "supplier_id": 47,
  "supplier_name": "Del Parque Bebidas",
  "item_count": 42,
  "items": [
    {
      "name": "Bebida 500ml",
      "price": 150.50,
      "brand": "Del Parque",
      "description": "...",
      "image": "https://example.com/image.jpg",
      "productId": 123,
      "unit": "ML",
      "quantity": 500,
      "supplierId": 47
    }
  ]
}
```

#### 4. Testing de la API
```bash
# Ejecutar suite completa de tests
python test_api.py
```

---

### CLI tradicional (antiguo)

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

## API Restocompras Backend

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

---

## API REST de Scrapers (Flask)

### Autenticación

Algunos endpoints requieren un token Bearer:

```
Authorization: Bearer <API_KEY_SECRET>
```

**Endpoints públicos (sin autenticación):**
- `GET /health` - Health check
- `GET /api/scrape` - Información de uso
- `POST /api/scrape/<supplier_name>` - Realizar scraping

**Endpoints protegidos (requieren API key):**
- `GET /api/suppliers` - Listar proveedores

### Endpoints Disponibles

#### `GET /health`
Verificar estado del servicio (sin auth).

**Respuesta:**
```json
{
  "status": "healthy",
  "timestamp": "2026-04-04T10:30:00",
  "service": "restocompras-scrapers-api"
}
```

#### `GET /api/scrape`
Información sobre el endpoint de scraping (sin auth).

**Respuesta:**
```json
{
  "status": "info",
  "message": "Use POST /api/scrape/<supplier_name> to scrape a supplier",
  "example": { ... },
  "available_suppliers": ["greenshop", "delparque", ...]
}
```

#### `GET /api/suppliers`
Listar todos los proveedores disponibles (requiere autenticación).

**Headers:** `Authorization: Bearer <API_KEY>`

**Respuesta (200 OK):**
```json
{
  "status": "success",
  "suppliers": ["greenshop", "delparque", "distribuidora_pop", ...],
  "count": 10
}
```

#### `POST /api/scrape/<supplier_name>`
Realizar scraping de un proveedor y extraer items.

**Importante:** Este endpoint EXTRAE, BUSCA IDs en el backend y TRANSFORMA items pero NO los guarda. Solo devuelve los datos en JSON.

**Parámetros:**
- `supplier_name` (path): Nombre del proveedor (ej: `delparque`, `greenshop`)

**Headers:** (Sin autenticación requerida)

**Proceso:**
1. Se conecta con el backend API
2. Extrae productos del sitio del proveedor
3. Para cada producto, busca su ID en el backend (fetch_product_id)
4. Transforma los productos usando ItemBuilder (normalización, precios, cantidades, etc)
5. Devuelve los items transformados en JSON SIN guardarlos en base de datos

**Respuesta Exitosa (200 OK):**
```json
{
  "status": "success",
  "supplier": "delparque",
  "supplier_id": 47,
  "supplier_name": "Del Parque Bebidas",
  "item_count": 42,
  "items": [
    {
      "name": "Bebida 500ml",
      "price": 150.50,
      "brand": "Del Parque",
      "description": "Bebida refrescante",
      "image": "https://...",
      "productId": 123,
      "unit": "ML",
      "quantity": 500,
      "supplierId": 47
    }
  ]
}
```

**Errores Posibles:**

| Código | Situación |
|--------|-----------|
| 400 | Request inválido |
| 401 | API key inválida o faltante |
| 404 | Proveedor no existe |
| 500 | Error durante scraping |

---

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
