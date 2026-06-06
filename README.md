# CalcStocks

Python scripts for building and enriching LibreOffice Calc (`.ods`) stock analysis workbooks. Scripts manipulate ODS files directly via `zipfile` + `xml.etree.ElementTree` — no pandas or external dependencies required.

## Files

| File | Description |
|------|-------------|
| `JEPI-ETF.ods` | JEPI ETF price/volume workbook with embedded charts |
| `add_ma_chart.py` | Adds 50/100-day moving averages and a line chart |
| `add_vwap.py` | Adds cumulative VWAP ± 2 std-dev bands and a chart |
| `add_formulas.py` | Replaces pre-computed values with native Calc formulas |
| `fix_forecast.py` | Fixes the FORECAST.ETS formula in the Forecast sheet |
| `add_forecast_chart.py` | Adds a Close vs Forecast line chart to the Forecast sheet |
| `add_jepi_all_chart.py` | Adds an all-indicators line chart to the JEPI sheet |
| `JEPI-Weekly.ods` | JEPI weekly analysis workbook with indicators and chart |
| `jepi_us_d.csv` | Source daily JEPI price/volume data (Week_Start added) |
| `Ford.ods` | Ford stock analysis workbook |
| `income_stocks.ods` | Income/dividend ETF analysis workbook |
| `ecommerce_sales.ods` | E-commerce sales workbook |
| `DateTools.py` | Date utility helpers |

## Workbook Layout (JEPI-ETF.ods)

### JEPI sheet

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

Three embedded charts:

| Chart | Series |
|-------|--------|
| Object 1 — MA chart | Close (blue), MA_50 (red), MA_100 (amber) |
| Object 2 — VWAP chart | Close (blue), VWAP (green), VWAP+2σ (purple), VWAP-2σ (purple) |
| Object 4 — All indicators | Close, MA_50, MA_100, VWAP, VWAP+2σ (dashed), VWAP-2σ (dashed) |

---

## Workbook Layout (JEPI-Weekly.ods)

Built from `jepi_us_d.csv` using Python stdlib only (no pandas).

### JEPI sheet

| Column | Content |
|--------|---------|
| A | Week_Start (Monday of each trading week) |
| B | Date |
| C | Close |
| D | Volume |
| E | MA5 (5-day moving average) |
| F | MA100 (100-day moving average) |
| G | VWAP (cumulative volume-weighted average price) |
| H | VWAP + 2σ |
| I | VWAP − 2σ |

Embedded line chart (Object1) plots Close, MA5, MA100, VWAP, VWAP+2σ, and VWAP−2σ against Date.

---

### Forecast sheet

| Column | Content |
|--------|---------|
| A | Date (2025-05-27 → 2026-07-05) |
| B | Close (historical prices, rows 2–260) |
| C | Forecast (FORECAST.ETS formula, rows 261–290) |

The Forecast sheet contains 259 rows of historical JEPI close prices followed by
30 rows of future dates (2026-06-06 → 2026-07-05). Column C uses LibreOffice's
`FORECAST.ETS` function to project prices using exponential smoothing against the
historical close and date series.

An embedded line chart visualises both series on a shared date axis:
- **Blue solid line** — historical Close prices
- **Orange dashed line** — FORECAST.ETS projected values

## Usage

Run scripts in order against `JEPI-ETF.ods`:

```bash
# 1. Add moving averages and chart
python3 add_ma_chart.py

# 2. Add VWAP bands and chart
python3 add_vwap.py

# 3. Convert pre-computed values to Calc formulas
python3 add_formulas.py

# 4. Fix FORECAST.ETS formula in Forecast sheet (one-time fix)
python3 fix_forecast.py

# 5. Add Close vs Forecast line chart to Forecast sheet
python3 add_forecast_chart.py

# 6. Add all-indicators chart to JEPI sheet
python3 add_jepi_all_chart.py
```

Each script reads and overwrites `JEPI-ETF.ods` in place, using a temp directory under `/tmp/` during processing.

## Requirements

- Python 3 (standard library only)
- LibreOffice Calc (to open `.ods` files)
