#!/usr/bin/env python3
"""Fix the FORECAST.ETS formula in the Forecast sheet of JEPI-ETF.ods.

Changes:
  - Switches COM.MICROSOFT.FORECAST.ETS → FORECAST.ETS (native LibreOffice)
  - Moves formula to column C (Forecast), leaving column B (Close) empty for future rows
  - Applies the formula to all 30 future rows (261–290)
"""

import zipfile, shutil, os
import xml.etree.ElementTree as ET

SRC = '/home/davidj/Projects/CalcStocks/JEPI-ETF.ods'
TMP = '/tmp/jepi_fix_forecast'
DST = '/home/davidj/Projects/CalcStocks/JEPI-ETF.ods'

NS = {
    'table':   'urn:oasis:names:tc:opendocument:xmlns:table:1.0',
    'text':    'urn:oasis:names:tc:opendocument:xmlns:text:1.0',
    'office':  'urn:oasis:names:tc:opendocument:xmlns:office:1.0',
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
EXTRA_NS = {
    'presentation': 'urn:oasis:names:tc:opendocument:xmlns:presentation:1.0',
    'css3t':  'http://www.w3.org/TR/css3-text/',
    'grddl':  'http://www.w3.org/2003/g/data-view#',
    'xhtml':  'http://www.w3.org/1999/xhtml',
    'xsi':    'http://www.w3.org/2001/XMLSchema-instance',
    'xsd':    'http://www.w3.org/2001/XMLSchema',
    'xforms': 'http://www.w3.org/2002/xforms',
    'dom':    'http://www.w3.org/2001/xml-events',
    'script': 'urn:oasis:names:tc:opendocument:xmlns:script:1.0',
    'form':   'urn:oasis:names:tc:opendocument:xmlns:form:1.0',
    'math':   'http://www.w3.org/1998/Math/MathML',
    'ooo':    'http://openoffice.org/2004/office',
    'ooow':   'http://openoffice.org/2004/writer',
    'oooc':   'http://openoffice.org/2004/calc',
    'drawooo':'http://openoffice.org/2010/draw',
    'dc':     'http://purl.org/dc/elements/1.1/',
    'of':     'urn:oasis:names:tc:opendocument:xmlns:of:1.2',
    'tableooo':'http://openoffice.org/2009/table',
    'dr3d':   'urn:oasis:names:tc:opendocument:xmlns:dr3d:1.0',
    'rpt':    'http://openoffice.org/2005/report',
    'formx':  'urn:openoffice:names:experimental:ooxml-odf-interop:xmlns:form:1.0',
    'field':  'urn:openoffice:names:experimental:ooo-ms-interop:xmlns:field:1.0',
    'meta':   'urn:oasis:names:tc:opendocument:xmlns:meta:1.0',
}
for p, u in {**NS, **EXTRA_NS}.items():
    ET.register_namespace(p, u)

def q(ns_key, local):
    return f'{{{NS[ns_key]}}}{local}'

# ── Extract ODS ───────────────────────────────────────────────────────────────
if os.path.exists(TMP):
    shutil.rmtree(TMP)
with zipfile.ZipFile(SRC) as z:
    z.extractall(TMP)

# ── Parse content.xml ─────────────────────────────────────────────────────────
tree = ET.parse(os.path.join(TMP, 'content.xml'))
root = tree.getroot()

sheets = root.findall(f'.//{q("table","table")}')
forecast_sheet = next(s for s in sheets
                      if s.attrib.get(q('table','name')) == 'Forecast')

rows = forecast_sheet.findall(q('table', 'table-row'))

# Historical data ends at row index 259 (spreadsheet row 260 = 2026-06-05)
# Forecast rows: index 260–289 (spreadsheet rows 261–290)
HIST_LAST_ROW = 260   # last historical spreadsheet row (used in formula range)
FORECAST_START = 260  # list index of first forecast row
FORECAST_END   = 289  # list index of last forecast row (inclusive)

for idx in range(FORECAST_START, FORECAST_END + 1):
    row = rows[idx]
    sheet_row = idx + 1  # 1-based spreadsheet row number

    formula = (
        f'of:=FORECAST.ETS([.A{sheet_row}];'
        f'[.B$2:.B${HIST_LAST_ROW}];'
        f'[.A$2:.A${HIST_LAST_ROW}];1;1;1)'
    )

    cells = row.findall(q('table', 'table-cell'))

    # Column A (index 0) — date cell, leave untouched
    # Column B (index 1) — Close; clear any old formula, keep empty
    # Column C (index 2) — Forecast; set the FORECAST.ETS formula

    if len(cells) >= 2:
        b_cell = cells[1]
        # Strip any old formula/value attributes from the Close cell
        for attr in list(b_cell.attrib.keys()):
            if 'formula' in attr or 'value' in attr or 'repeated' in attr:
                del b_cell.attrib[attr]
        # Remove any text:p children
        for child in list(b_cell):
            b_cell.remove(child)

    # Build/replace column C cell with the FORECAST.ETS formula
    if len(cells) >= 3:
        c_cell = cells[2]
        # Remove any repeated-columns attribute that was merging B+C
        for attr in list(c_cell.attrib.keys()):
            if 'repeated' in attr or 'formula' in attr or 'value' in attr:
                del c_cell.attrib[attr]
        for child in list(c_cell):
            c_cell.remove(child)
    else:
        # If B and C were merged (number-columns-repeated="2"), split them:
        # The existing cells[1] already represents column B (now cleared).
        # Create a new cell for column C.
        c_cell = ET.SubElement(row, q('table', 'table-cell'))

    c_cell.set(q('table', 'formula'), formula)
    p = ET.SubElement(c_cell, q('text', 'p'))
    p.text = ''

print(f"Updated FORECAST.ETS formula in {FORECAST_END - FORECAST_START + 1} rows "
      f"(spreadsheet rows {FORECAST_START+1}–{FORECAST_END+1})")

# ── Write content.xml and repack ──────────────────────────────────────────────
tree.write(os.path.join(TMP, 'content.xml'),
           xml_declaration=True, encoding='UTF-8')

if os.path.exists(DST):
    shutil.copy2(DST, DST + '.bak')

with zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED) as zout:
    for root_dir, dirs, files in os.walk(TMP):
        for fname in files:
            fpath = os.path.join(root_dir, fname)
            arcname = os.path.relpath(fpath, TMP)
            zout.write(fpath, arcname)

shutil.rmtree(TMP)
print(f"Saved: {DST}  (backup: {DST}.bak)")
