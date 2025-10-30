# Running All Suppliers

This directory includes scripts to run scrapers for all configured suppliers automatically.

## Available Scripts

### 1. Bash Script (Unix/Linux/macOS)
```bash
./run_all_suppliers.sh
```

### 2. Python Script (Cross-platform)
```bash
python3 run_all_suppliers.py
```

Or:
```bash
./run_all_suppliers.py
```

## What It Does

Both scripts will:
1. Run scrapers for all 5 suppliers sequentially:
   - Green Shop
   - Lácteos Granero
   - Distribuidora Pop
   - TYNA
   - Piala

2. Display progress in real-time with color-coded output:
   - 🟢 Green for successful scrapers
   - 🔴 Red for failed scrapers
   - 🟡 Yellow for current scraper being executed

3. Generate a summary report showing:
   - Total execution time
   - Number of successful/failed scrapers
   - List of which suppliers succeeded/failed

4. Save all output to:
   - `output/` - Excel files with scraped data
   - `logs/` - Detailed log files for each scraper

## Exit Codes

- `0` - All scrapers completed successfully
- `1` - One or more scrapers failed

## Running Individual Suppliers

To run a single supplier instead:
```bash
python3 main.py <supplier_name>
```

Examples:
```bash
python3 main.py greenshop
python3 main.py tyna
python3 main.py piala
```

## Listing Available Suppliers

```bash
python3 main.py --list
```

## Prerequisites

- All dependencies installed: `pip3 install -r requirements.txt`
- Backend API running on `localhost:8080`
- Valid credentials configured in `configs/suppliers/*.json`
- Valid authentication token in `configs/api_config.json`

## Troubleshooting

If a scraper fails:
1. Check the log file in `logs/scraper_TIMESTAMP.log`
2. Verify supplier credentials are correct
3. Ensure the backend API is running and accessible
4. Check if the supplier website is accessible
5. Review selector configurations in `configs/suppliers/`

## Scheduling Automated Runs

### Using Cron (Linux/macOS)

Edit crontab:
```bash
crontab -e
```

Add entry to run daily at 2 AM:
```
0 2 * * * cd /path/to/scrapers && /usr/bin/python3 run_all_suppliers.py >> cron.log 2>&1
```

### Using Task Scheduler (Windows)

1. Open Task Scheduler
2. Create new task
3. Set trigger (e.g., daily at 2 AM)
4. Set action: Run `python3 run_all_suppliers.py`
5. Set start directory to scraper folder

## Performance Considerations

- Each scraper runs sequentially (not in parallel)
- Total execution time depends on:
  - Number of products per supplier
  - Network speed
  - Backend API response time
- Typical execution time: 5-15 minutes for all suppliers

## Output Files

After running, check the `output/` directory for Excel files:
- `greenshop_YYYYMMDD_HHMMSS.xlsx`
- `lacteos_granero_YYYYMMDD_HHMMSS.xlsx`
- `distribuidora_pop_YYYYMMDD_HHMMSS.xlsx`
- `tyna_YYYYMMDD_HHMMSS.xlsx`
- `piala_YYYYMMDD_HHMMSS.xlsx`
