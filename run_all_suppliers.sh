#!/bin/bash

# restoCompras Scrapers - Run All Suppliers
# This script runs scrapers for all available suppliers sequentially

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default environment
ENVIRONMENT="dev"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --env|--environment)
            ENVIRONMENT="$2"
            if [[ "$ENVIRONMENT" != "dev" && "$ENVIRONMENT" != "prod" ]]; then
                echo -e "${RED}Error: Environment must be 'dev' or 'prod'${NC}"
                echo "Usage: $0 [--env {dev|prod}]"
                exit 1
            fi
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [--env {dev|prod}]"
            echo ""
            echo "Options:"
            echo "  --env, --environment    Environment to use: dev (localhost) or prod (production). Default: dev"
            echo "  -h, --help              Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                    # Run all suppliers in dev environment"
            echo "  $0 --env dev          # Run all suppliers in dev environment"
            echo "  $0 --env prod         # Run all suppliers in prod environment"
            exit 0
            ;;
        *)
            echo -e "${RED}Error: Unknown option $1${NC}"
            echo "Usage: $0 [--env {dev|prod}]"
            exit 1
            ;;
    esac
done

# List of all suppliers
SUPPLIERS=("greenshop" "lacteos_granero" "distribuidora_pop" "tyna" "piala" "distribuidora_demarchi" "laduvalina" "labebidadetusfiestas")

# Counters
SUCCESS_COUNT=0
FAILED_COUNT=0
TOTAL_COUNT=${#SUPPLIERS[@]}

# Arrays to track results
SUCCESSFUL_SUPPLIERS=()
FAILED_SUPPLIERS=()

echo "======================================================================="
echo -e "${BLUE}restoCompras Scrapers - Running All Suppliers${NC}"
echo "======================================================================="
echo -e "Environment: ${YELLOW}${ENVIRONMENT^^}${NC}"
echo "Total suppliers to scrape: ${TOTAL_COUNT}"
echo "Start time: $(date '+%Y-%m-%d %H:%M:%S')"
echo "======================================================================="
echo ""

# Run each supplier
for supplier in "${SUPPLIERS[@]}"
do
    echo ""
    echo "-----------------------------------------------------------------------"
    echo -e "${YELLOW}Running scraper for: ${supplier} (env: ${ENVIRONMENT})${NC}"
    echo "-----------------------------------------------------------------------"
    
    # Run the scraper with environment argument
    python3 main.py "$supplier" --env "$ENVIRONMENT"
    EXIT_CODE=$?
    
    # Check if successful
    if [ $EXIT_CODE -eq 0 ]; then
        echo -e "${GREEN}✓ ${supplier} completed successfully${NC}"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        SUCCESSFUL_SUPPLIERS+=("$supplier")
    else
        echo -e "${RED}✗ ${supplier} failed with exit code ${EXIT_CODE}${NC}"
        FAILED_COUNT=$((FAILED_COUNT + 1))
        FAILED_SUPPLIERS+=("$supplier")
    fi
    
    echo ""
done

# Print summary
echo ""
echo "======================================================================="
echo -e "${BLUE}SCRAPING SUMMARY${NC}"
echo "======================================================================="
echo "End time: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""
echo "Total suppliers: ${TOTAL_COUNT}"
echo -e "${GREEN}Successful: ${SUCCESS_COUNT}${NC}"
echo -e "${RED}Failed: ${FAILED_COUNT}${NC}"
echo ""

if [ ${#SUCCESSFUL_SUPPLIERS[@]} -gt 0 ]; then
    echo -e "${GREEN}Successful suppliers:${NC}"
    for supplier in "${SUCCESSFUL_SUPPLIERS[@]}"; do
        echo "  ✓ $supplier"
    done
    echo ""
fi

if [ ${#FAILED_SUPPLIERS[@]} -gt 0 ]; then
    echo -e "${RED}Failed suppliers:${NC}"
    for supplier in "${FAILED_SUPPLIERS[@]}"; do
        echo "  ✗ $supplier"
    done
    echo ""
fi

echo "Output files saved to: output/"
echo "Log files saved to: logs/"
echo "======================================================================="

# Exit with error code if any scraper failed
if [ $FAILED_COUNT -gt 0 ]; then
    exit 1
else
    exit 0
fi
