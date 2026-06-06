# CalcStocks

Python scripts for building and enriching LibreOffice Calc (`.ods`) stock analysis workbooks. Scripts manipulate ODS files directly via `zipfile` + `xml.etree.ElementTree` — no pandas or external dependencies required.

## Files

| File | Description |
|------|-------------|
| `JEPI-ETF.ods` | JEPI ETF price/volume workbook with embedded charts |
| `add_ma_chart.py` | Adds 50/100-day moving averages and a line chart |
| `add_vwap.py` | Adds cumulative VWAP ± 2 std-dev bands and a chart |
| `add_formulas.py` | Replaces pre-computed values with native Calc formulas |
| `Ford.ods` | Ford stock analysis workbook |
| `income_stocks.ods` | Income/dividend ETF analysis workbook |
| `ecommerce_sales.ods` | E-commerce sales workbook |
| `DateTools.py` | Date utility helpers |

## Workbook Column Layout (JEPI-ETF.ods)

| Column | Content |
|--------|---------|
| A | Date |
| B | Close |
| C | Volume |
| D | MA_50 |
| E | MA_100 |
| F | VWAP |
| G | VWAP + 2σ |
| H | VWAP − 2σ |

## Usage

Run scripts in order against `JEPI-ETF.ods`:

```bash
# 1. Add moving averages and chart
python3 add_ma_chart.py

# 2. Add VWAP bands and chart
python3 add_vwap.py

# 3. Convert pre-computed values to Calc formulas
python3 add_formulas.py
```

Each script reads and overwrites `JEPI-ETF.ods` in place, using a temp directory under `/tmp/` during processing.

## Requirements

- Python 3 (standard library only)
- LibreOffice Calc (to open `.ods` files)
