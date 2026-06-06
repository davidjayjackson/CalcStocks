#!/usr/bin/env python3
"""Replace pre-computed values in JEPI-ETF.ods with LibreOffice Calc formulas.

Columns after this script:
  A = Date    B = Close   C = Volume
  D = MA_50   E = MA_100
  F = VWAP    G = VWAP+2σ   H = VWAP-2σ
"""

import zipfile, shutil, os, math, csv
import xml.etree.ElementTree as ET

SRC = '/home/davidj/Projects/CalcStocks/JEPI-ETF.ods'
DST = '/home/davidj/Projects/CalcStocks/JEPI-ETF.ods'
TMP = '/tmp/jepi_formulas'

# ── Namespaces ────────────────────────────────────────────────────────────────
NS = {
    'office':  'urn:oasis:names:tc:opendocument:xmlns:office:1.0',
    'table':   'urn:oasis:names:tc:opendocument:xmlns:table:1.0',
    'text':    'urn:oasis:names:tc:opendocument:xmlns:text:1.0',
    'calcext': 'urn:org:documentfoundation:names:experimental:calc:xmlns:calcext:1.0',
    'style':   'urn:oasis:names:tc:opendocument:xmlns:style:1.0',
    'fo':      'urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0',
    'draw':    'urn:oasis:names:tc:opendocument:xmlns:drawing:1.0',
    'svg':     'urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0',
    'xlink':   'http://www.w3.org/1999/xlink',
    'chart':   'urn:oasis:names:tc:opendocument:xmlns:chart:1.0',
    'number':  'urn:oasis:names:tc:opendocument:xmlns:datastyle:1.0',
    'loext':   'urn:org:documentfoundation:names:experimental:office:xmlns:loext:1.0',
}
for p, u in NS.items():
    ET.register_namespace(p, u)

EXTRA_NS = {
    'presentation': 'urn:oasis:names:tc:opendocument:xmlns:presentation:1.0',
    'css3t':'http://www.w3.org/TR/css3-text/',
    'grddl':'http://www.w3.org/2003/g/data-view#',
    'xhtml':'http://www.w3.org/1999/xhtml',
    'xsi':  'http://www.w3.org/2001/XMLSchema-instance',
    'xsd':  'http://www.w3.org/2001/XMLSchema',
    'xforms':'http://www.w3.org/2002/xforms',
    'dom':  'http://www.w3.org/2001/xml-events',
    'script':'urn:oasis:names:tc:opendocument:xmlns:script:1.0',
    'form': 'urn:oasis:names:tc:opendocument:xmlns:form:1.0',
    'math': 'http://www.w3.org/1998/Math/MathML',
    'ooo':  'http://openoffice.org/2004/office',
    'ooow': 'http://openoffice.org/2004/writer',
    'oooc': 'http://openoffice.org/2004/calc',
    'drawooo':'http://openoffice.org/2010/draw',
    'dc':   'http://purl.org/dc/elements/1.1/',
    'of':   'urn:oasis:names:tc:opendocument:xmlns:of:1.2',
    'tableooo':'http://openoffice.org/2009/table',
    'dr3d': 'urn:oasis:names:tc:opendocument:xmlns:dr3d:1.0',
    'rpt':  'http://openoffice.org/2005/report',
    'formx':'urn:openoffice:names:experimental:ooxml-odf-interop:xmlns:form:1.0',
    'field':'urn:openoffice:names:experimental:ooo-ms-interop:xmlns:field:1.0',
    'meta': 'urn:oasis:names:tc:opendocument:xmlns:meta:1.0',
}
for p, u in EXTRA_NS.items():
    ET.register_namespace(p, u)

def q(ns_key, local):
    return f'{{{NS[ns_key]}}}{local}'

ONS   = NS['office']
TNS   = NS['table']
TXTNS = NS['text']
CALCNS= NS['calcext']


# ── Pre-compute cached values (for LibreOffice to display without recalc) ─────
closes, volumes = [], []
with open('/tmp/JEPI-ETF.csv') as f:
    for row in csv.DictReader(f):
        closes.append(float(row['Close']))
        volumes.append(float(row['Volume']))

n = len(closes)

def sma(prices, window, idx):
    if idx + 1 < window:
        return None
    return round(sum(prices[idx+1-window:idx+1]) / window, 4)

cum_pv, cum_v, cum_pv2 = 0.0, 0.0, 0.0
vwap_cache, upper_cache, lower_cache = [], [], []
for i in range(n):
    cum_pv  += closes[i] * volumes[i]
    cum_v   += volumes[i]
    cum_pv2 += closes[i] ** 2 * volumes[i]
    vwap = cum_pv / cum_v
    var  = max((cum_pv2 / cum_v) - vwap ** 2, 0.0)
    std  = math.sqrt(var)
    vwap_cache.append(round(vwap, 4))
    upper_cache.append(round(vwap + 2 * std, 4))
    lower_cache.append(round(vwap - 2 * std, 4))


# ── Cell constructors ─────────────────────────────────────────────────────────
def make_formula_float(formula, cached_value, style='ce5'):
    """Formula cell with a cached float result."""
    cell = ET.Element(q('table', 'table-cell'))
    cell.set(q('table', 'style-name'), style)
    cell.set(q('table', 'formula'), f'of:={formula}')
    cell.set(q('office', 'value-type'), 'float')
    cell.set(q('office', 'value'), str(cached_value))
    cell.set(q('calcext', 'value-type'), 'float')
    ET.SubElement(cell, q('text', 'p')).text = str(cached_value)
    return cell


def make_formula_string(formula, style='ce4'):
    """Formula cell whose result is a string (empty string for N/A rows)."""
    cell = ET.Element(q('table', 'table-cell'))
    cell.set(q('table', 'style-name'), style)
    cell.set(q('table', 'formula'), f'of:={formula}')
    cell.set(q('office', 'value-type'), 'string')
    cell.set(q('calcext', 'value-type'), 'string')
    ET.SubElement(cell, q('text', 'p')).text = ''
    return cell


def make_empty_cell():
    return ET.Element(q('table', 'table-cell'))


# ── Extract ODS ───────────────────────────────────────────────────────────────
if os.path.exists(TMP):
    shutil.rmtree(TMP)
os.makedirs(TMP)
with zipfile.ZipFile(SRC, 'r') as z:
    z.extractall(TMP)

content_path = os.path.join(TMP, 'content.xml')
tree = ET.parse(content_path)
root = tree.getroot()

body        = root.find(f'{{{ONS}}}body')
spreadsheet = body.find(f'{{{ONS}}}spreadsheet')
table       = spreadsheet.find(f'{{{TNS}}}table')
rows_els    = table.findall(f'{{{TNS}}}table-row')

print(f"Sheet has {len(rows_els)} XML rows, {n} data rows")


# ── Replace value cells with formula cells, one data row at a time ────────────
for i, row_el in enumerate(rows_els[1:], start=0):   # skip header row
    if i >= n:
        break

    r = i + 2   # spreadsheet row number (1=header, 2=first data row)

    cells = row_el.findall(q('table', 'table-cell'))
    if len(cells) < 8:
        print(f"Row {r} has only {len(cells)} cells — skipping")
        continue

    # ── MA_50 (cell index 3, column D) ────────────────────────────────────────
    if i + 1 >= 50:                    # need 50 data rows
        start = r - 49                 # first row of the 50-row window
        formula_50 = f'AVERAGE(B{start}:B{r})'
        new_cell = make_formula_float(formula_50, sma(closes, 50, i))
    else:
        new_cell = make_empty_cell()
    row_el.remove(cells[3])
    row_el.insert(3, new_cell)

    # ── MA_100 (cell index 4, column E) ───────────────────────────────────────
    if i + 1 >= 100:
        start = r - 99
        formula_100 = f'AVERAGE(B{start}:B{r})'
        new_cell = make_formula_float(formula_100, sma(closes, 100, i))
    else:
        new_cell = make_empty_cell()
    row_el.remove(cells[4])
    row_el.insert(4, new_cell)

    # ── VWAP (cell index 5, column F) ─────────────────────────────────────────
    # Cumulative: fixed start $B$2 : expanding end B{r}
    formula_vwap = f'SUMPRODUCT($B$2:B{r},$C$2:C{r})/SUM($C$2:C{r})'
    row_el.remove(cells[5])
    row_el.insert(5, make_formula_float(formula_vwap, vwap_cache[i]))

    # ── VWAP+2σ (cell index 6, column G) ─────────────────────────────────────
    # σ = SQRT( SUMPRODUCT(vol, (close-vwap)²) / SUM(vol) )
    formula_upper = (
        f'F{r}+2*SQRT(SUMPRODUCT($C$2:C{r},($B$2:B{r}-F{r})^2)/SUM($C$2:C{r}))'
    )
    row_el.remove(cells[6])
    row_el.insert(6, make_formula_float(formula_upper, upper_cache[i]))

    # ── VWAP-2σ (cell index 7, column H) ─────────────────────────────────────
    formula_lower = (
        f'F{r}-2*SQRT(SUMPRODUCT($C$2:C{r},($B$2:B{r}-F{r})^2)/SUM($C$2:C{r}))'
    )
    row_el.remove(cells[7])
    row_el.insert(7, make_formula_float(formula_lower, lower_cache[i]))

print("Formula cells written")

tree.write(content_path, encoding='UTF-8', xml_declaration=True)
print("Wrote content.xml")


# ── Repack ODS ────────────────────────────────────────────────────────────────
tmp_out = DST + '.tmp'
with zipfile.ZipFile(tmp_out, 'w', zipfile.ZIP_DEFLATED) as zout:
    mime = os.path.join(TMP, 'mimetype')
    zout.write(mime, 'mimetype', compress_type=zipfile.ZIP_STORED)
    for dirpath, _, filenames in os.walk(TMP):
        for filename in filenames:
            full = os.path.join(dirpath, filename)
            arcname = os.path.relpath(full, TMP)
            if arcname == 'mimetype':
                continue
            zout.write(full, arcname)

os.replace(tmp_out, DST)
print(f"Saved to {DST}")
