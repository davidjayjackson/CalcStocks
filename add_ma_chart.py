#!/usr/bin/env python3
"""Add 50/100-day moving averages and a line chart to JEPI-ETF.ods."""

import csv
import zipfile
import shutil
import os
import xml.etree.ElementTree as ET
from collections import deque

SRC = '/home/davidj/Projects/CalcStocks/JEPI-ETF.ods'
DST = '/home/davidj/Projects/CalcStocks/JEPI-ETF.ods'
TMP = '/tmp/jepi_work'

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

# Register all namespaces so ElementTree preserves prefixes
for prefix, uri in NS.items():
    ET.register_namespace(prefix, uri)

# Extra namespaces already in the file that we just need to preserve
EXTRA_NS = {
    'presentation': 'urn:oasis:names:tc:opendocument:xmlns:presentation:1.0',
    'css3t': 'http://www.w3.org/TR/css3-text/',
    'grddl': 'http://www.w3.org/2003/g/data-view#',
    'xhtml': 'http://www.w3.org/1999/xhtml',
    'xsi':   'http://www.w3.org/2001/XMLSchema-instance',
    'xsd':   'http://www.w3.org/2001/XMLSchema',
    'xforms':'http://www.w3.org/2002/xforms',
    'dom':   'http://www.w3.org/2001/xml-events',
    'script':'urn:oasis:names:tc:opendocument:xmlns:script:1.0',
    'form':  'urn:oasis:names:tc:opendocument:xmlns:form:1.0',
    'math':  'http://www.w3.org/1998/Math/MathML',
    'ooo':   'http://openoffice.org/2004/office',
    'ooow':  'http://openoffice.org/2004/writer',
    'oooc':  'http://openoffice.org/2004/calc',
    'drawooo':'http://openoffice.org/2010/draw',
    'dc':    'http://purl.org/dc/elements/1.1/',
    'of':    'urn:oasis:names:tc:opendocument:xmlns:of:1.2',
    'tableooo':'http://openoffice.org/2009/table',
    'dr3d':  'urn:oasis:names:tc:opendocument:xmlns:dr3d:1.0',
    'rpt':   'http://openoffice.org/2005/report',
    'formx': 'urn:openoffice:names:experimental:ooxml-odf-interop:xmlns:form:1.0',
    'field': 'urn:openoffice:names:experimental:ooo-ms-interop:xmlns:field:1.0',
    'meta':  'urn:oasis:names:tc:opendocument:xmlns:meta:1.0',
}
for prefix, uri in EXTRA_NS.items():
    ET.register_namespace(prefix, uri)


def q(prefix, local):
    return f'{{{NS[prefix]}}}{local}'


# ── 1. Read close prices from CSV ─────────────────────────────────────────────
close_prices = []
dates = []
with open('/tmp/JEPI-ETF.csv') as f:
    reader = csv.DictReader(f)
    for row in reader:
        dates.append(row['Date'])
        close_prices.append(float(row['Close']))

n = len(close_prices)
print(f"Loaded {n} rows of data")


def sma(prices, window):
    """Return list of SMA values; None for indices without enough data."""
    result = []
    buf = deque()
    total = 0.0
    for p in prices:
        buf.append(p)
        total += p
        if len(buf) > window:
            total -= buf.popleft()
        if len(buf) == window:
            result.append(round(total / window, 4))
        else:
            result.append(None)
    return result


ma50  = sma(close_prices, 50)
ma100 = sma(close_prices, 100)


# ── 2. Extract ODS ────────────────────────────────────────────────────────────
if os.path.exists(TMP):
    shutil.rmtree(TMP)
os.makedirs(TMP)
with zipfile.ZipFile(SRC, 'r') as z:
    z.extractall(TMP)


# ── 3. Parse content.xml ──────────────────────────────────────────────────────
content_path = os.path.join(TMP, 'content.xml')
tree = ET.parse(content_path)
root = tree.getroot()

ONS   = NS['office']
TNS   = NS['table']
TXTNS = NS['text']
CALCNS= NS['calcext']
STNS  = NS['style']

body        = root.find(f'{{{ONS}}}body')
spreadsheet = body.find(f'{{{ONS}}}spreadsheet')
table       = spreadsheet.find(f'{{{TNS}}}table')
rows        = table.findall(f'{{{TNS}}}table-row')

print(f"Sheet name: {table.get(f'{{{TNS}}}name')}")
print(f"XML rows: {len(rows)}")

# ── 4. Add style for MA number columns ────────────────────────────────────────
auto_styles = root.find(f'{{{ONS}}}automatic-styles')

# Column style for new MA columns
col_style = ET.SubElement(auto_styles, f'{{{STNS}}}style')
col_style.set(f'{{{STNS}}}name', 'co_ma')
col_style.set(f'{{{STNS}}}family', 'table-column')
col_props = ET.SubElement(col_style, f'{{{STNS}}}table-column-properties')
col_props.set(f'{{{NS["fo"]}}}break-before', 'auto')
col_props.set(f'{{{STNS}}}column-width', '1.0in')

# ── 5. Modify header row (row 0) ──────────────────────────────────────────────
header_row = rows[0]
header_cells = header_row.findall(f'{{{TNS}}}table-cell')

# Remove the trailing repeated empty cell if present
for cell in header_cells:
    rep = cell.get(f'{{{TNS}}}number-columns-repeated')
    if rep:
        del cell.attrib[f'{{{TNS}}}number-columns-repeated']
        # Only keep this cell once (it's the empty trailing one we'll replace)

def make_string_cell(text, style='ce4'):
    cell = ET.Element(f'{{{TNS}}}table-cell')
    cell.set(f'{{{TNS}}}style-name', style)
    cell.set(f'{{{ONS}}}value-type', 'string')
    cell.set(f'{{{CALCNS}}}value-type', 'string')
    p = ET.SubElement(cell, f'{{{TXTNS}}}p')
    p.text = text
    return cell


def make_float_cell(value, style='ce5'):
    cell = ET.Element(f'{{{TNS}}}table-cell')
    cell.set(f'{{{TNS}}}style-name', style)
    cell.set(f'{{{ONS}}}value-type', 'float')
    cell.set(f'{{{ONS}}}value', str(value))
    cell.set(f'{{{CALCNS}}}value-type', 'float')
    p = ET.SubElement(cell, f'{{{TXTNS}}}p')
    p.text = str(value)
    return cell


def make_empty_cell():
    return ET.Element(f'{{{TNS}}}table-cell')


# Remove trailing empty/repeated cells from header and append MA headers
# Find and remove repeated empty cells at end of header
to_remove = []
for cell in header_row:
    tag = cell.tag.split('}')[-1]
    if tag == 'table-cell':
        rep = cell.get(f'{{{TNS}}}number-columns-repeated')
        has_content = cell.find(f'{{{TXTNS}}}p') is not None
        if rep and not has_content:
            to_remove.append(cell)

for cell in to_remove:
    header_row.remove(cell)

header_row.append(make_string_cell('MA_50'))
header_row.append(make_string_cell('MA_100'))

# ── 6. Add MA values to data rows 1..n ───────────────────────────────────────
for i, row in enumerate(rows[1:], start=0):
    if i >= n:
        break  # skip blank trailing rows

    # Remove trailing repeated empty cells
    cells = list(row)
    to_remove = []
    for cell in cells:
        tag = cell.tag.split('}')[-1]
        if tag == 'table-cell':
            rep = cell.get(f'{{{TNS}}}number-columns-repeated')
            has_content = cell.find(f'{{{TXTNS}}}p') is not None
            if rep and not has_content:
                to_remove.append(cell)
    for cell in to_remove:
        row.remove(cell)

    # Append MA_50
    if ma50[i] is not None:
        row.append(make_float_cell(ma50[i]))
    else:
        row.append(make_empty_cell())

    # Append MA_100
    if ma100[i] is not None:
        row.append(make_float_cell(ma100[i]))
    else:
        row.append(make_empty_cell())

# Add column width declarations for the two new columns (insert after last table-column)
col_els = table.findall(f'{{{TNS}}}table-column')
last_col = col_els[-1] if col_els else None
insert_idx = list(table).index(last_col) + 1 if last_col is not None else 0

for _ in range(2):
    new_col = ET.Element(f'{{{TNS}}}table-column')
    new_col.set(f'{{{TNS}}}style-name', 'co_ma')
    new_col.set(f'{{{TNS}}}default-cell-style-name', 'Default')
    table.insert(insert_idx, new_col)
    insert_idx += 1

# ── 7. Add a draw:frame with an embedded chart after the table ────────────────
# The chart references cells JEPI.$A$1:$D$<n+1>
total_rows = n + 1  # header + data
chart_range = f'JEPI.$A$1:$D${total_rows}'

DRAWNS  = NS['draw']
SVGNS   = NS['svg']
XLINKNS = NS['xlink']
CHARTNS = NS['chart']

frame = ET.Element(f'{{{DRAWNS}}}frame')
frame.set(f'{{{DRAWNS}}}name', 'Object1')
frame.set(f'{{{SVGNS}}}x', '0.1417in')
frame.set(f'{{{SVGNS}}}y', f'{(n + 3) * 0.178 + 0.1}in')
frame.set(f'{{{SVGNS}}}width', '8in')
frame.set(f'{{{SVGNS}}}height', '4.5in')
frame.set(f'{{{DRAWNS}}}z-index', '0')

obj_el = ET.SubElement(frame, f'{{{DRAWNS}}}object')
obj_el.set(f'{{{XLINKNS}}}href', './Object1')
obj_el.set(f'{{{XLINKNS}}}type', 'simple')
obj_el.set(f'{{{XLINKNS}}}show', 'embed')
obj_el.set(f'{{{XLINKNS}}}actuate', 'onLoad')

img_el = ET.SubElement(frame, f'{{{DRAWNS}}}image')
img_el.set(f'{{{XLINKNS}}}href', './Thumbnails/thumbnail.png')
img_el.set(f'{{{XLINKNS}}}type', 'simple')
img_el.set(f'{{{XLINKNS}}}show', 'embed')
img_el.set(f'{{{XLINKNS}}}actuate', 'onLoad')

# Insert frame before the named-expressions element
named_expr = spreadsheet.find(f'{{{TNS}}}named-expressions')
if named_expr is not None:
    idx = list(spreadsheet).index(named_expr)
    spreadsheet.insert(idx, frame)
else:
    spreadsheet.append(frame)

# ── 8. Write updated content.xml ──────────────────────────────────────────────
tree.write(content_path, encoding='UTF-8', xml_declaration=True)
print("Wrote updated content.xml")


# ── 9. Create chart object (Object1/content.xml) ──────────────────────────────
obj_dir = os.path.join(TMP, 'Object1')
os.makedirs(obj_dir, exist_ok=True)

# Build cell range addresses for each series
# Col B = Close, Col C = MA_50, Col D = MA_100, Col A = dates
# ODS chart cell range format: SheetName.$COL$ROW
close_range = f'JEPI.$B$2:.$B${total_rows}'
ma50_range  = f'JEPI.$C$2:.$C${total_rows}'
ma100_range = f'JEPI.$D$2:.$D${total_rows}'
date_range  = f'JEPI.$A$1:.$A${total_rows}'

chart_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<office:document-content
  xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
  xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0"
  xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"
  xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0"
  xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0"
  xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0"
  xmlns:xlink="http://www.w3.org/1999/xlink"
  xmlns:dc="http://purl.org/dc/elements/1.1/"
  xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0"
  xmlns:chart="urn:oasis:names:tc:opendocument:xmlns:chart:1.0"
  xmlns:dr3d="urn:oasis:names:tc:opendocument:xmlns:dr3d:1.0"
  xmlns:math="http://www.w3.org/1998/Math/MathML"
  xmlns:form="urn:oasis:names:tc:opendocument:xmlns:form:1.0"
  xmlns:script="urn:oasis:names:tc:opendocument:xmlns:script:1.0"
  xmlns:ooo="http://openoffice.org/2004/office"
  xmlns:ooow="http://openoffice.org/2004/writer"
  xmlns:oooc="http://openoffice.org/2004/calc"
  xmlns:dom="http://www.w3.org/2001/xml-events"
  xmlns:rpt="http://openoffice.org/2005/report"
  xmlns:number="urn:oasis:names:tc:opendocument:xmlns:datastyle:1.0"
  xmlns:loext="urn:org:documentfoundation:names:experimental:office:xmlns:loext:1.0"
  office:version="1.4">
  <office:automatic-styles>
    <style:style style:name="ch1" style:family="chart">
      <style:chart-properties chart:symbol-type="none" chart:data-label-number="value"
        chart:mean-value="false" chart:error-indicator="none"/>
      <style:graphic-properties draw:stroke="solid" draw:stroke-color="#4472C4"
        draw:fill="none" draw:fill-color="#4472C4" svg:stroke-width="0.03in"/>
    </style:style>
    <style:style style:name="ch2" style:family="chart">
      <style:chart-properties chart:symbol-type="none"
        chart:mean-value="false" chart:error-indicator="none"/>
      <style:graphic-properties draw:stroke="solid" draw:stroke-color="#ED7D31"
        draw:fill="none" draw:fill-color="#ED7D31" svg:stroke-width="0.025in"/>
    </style:style>
    <style:style style:name="ch3" style:family="chart">
      <style:chart-properties chart:symbol-type="none"
        chart:mean-value="false" chart:error-indicator="none"/>
      <style:graphic-properties draw:stroke="solid" draw:stroke-color="#A9D18E"
        draw:fill="none" draw:fill-color="#A9D18E" svg:stroke-width="0.025in"/>
    </style:style>
    <style:style style:name="chplotarea" style:family="chart">
      <style:graphic-properties draw:fill="none" draw:stroke="none"/>
    </style:style>
    <style:style style:name="chwall" style:family="chart">
      <style:graphic-properties draw:fill="none" draw:stroke="solid"
        draw:stroke-color="#CCCCCC"/>
    </style:style>
  </office:automatic-styles>
  <office:body>
    <office:chart>
      <chart:chart
        chart:class="chart:line"
        svg:width="8in"
        svg:height="4.5in"
        chart:column-mapping="col"
        chart:data-source-has-labels="both">
        <chart:title>
          <text:p>JEPI-ETF Close Price with 50/100-Day Moving Averages</text:p>
        </chart:title>
        <chart:legend chart:legend-position="right"/>
        <chart:plot-area chart:style-name="chplotarea"
          chart:data-source-has-labels="both"
          table:cell-range-address="{chart_range}"
          chart:table-number-list="0">
          <chart:axis chart:dimension="x" chart:name="primary-x">
            <chart:categories table:cell-range-address="JEPI.$A$2:.$A${total_rows}"/>
          </chart:axis>
          <chart:axis chart:dimension="y" chart:name="primary-y">
            <chart:grid chart:class="major"/>
          </chart:axis>
          <chart:series
            chart:values-cell-range-address="JEPI.$B$2:.$B${total_rows}"
            chart:label-cell-address="JEPI.$B$1"
            chart:class="chart:line"
            chart:style-name="ch1"
            chart:attached-axis="primary-y">
            <chart:data-point chart:repeated="{n}"/>
          </chart:series>
          <chart:series
            chart:values-cell-range-address="JEPI.$C$2:.$C${total_rows}"
            chart:label-cell-address="JEPI.$C$1"
            chart:class="chart:line"
            chart:style-name="ch2"
            chart:attached-axis="primary-y">
            <chart:data-point chart:repeated="{n}"/>
          </chart:series>
          <chart:series
            chart:values-cell-range-address="JEPI.$D$2:.$D${total_rows}"
            chart:label-cell-address="JEPI.$D$1"
            chart:class="chart:line"
            chart:style-name="ch3"
            chart:attached-axis="primary-y">
            <chart:data-point chart:repeated="{n}"/>
          </chart:series>
          <chart:wall chart:style-name="chwall"/>
          <chart:floor/>
        </chart:plot-area>
      </chart:chart>
    </office:chart>
  </office:body>
</office:document-content>
'''

with open(os.path.join(obj_dir, 'content.xml'), 'w', encoding='UTF-8') as f:
    f.write(chart_content)
print("Wrote Object1/content.xml")


# ── 10. Update META-INF/manifest.xml ─────────────────────────────────────────
manifest_path = os.path.join(TMP, 'META-INF', 'manifest.xml')
with open(manifest_path, 'r', encoding='UTF-8') as f:
    manifest_text = f.read()

manifest_addition = '''   <manifest:file-entry manifest:full-path="Object1/" manifest:media-type="application/vnd.oasis.opendocument.chart"/>
   <manifest:file-entry manifest:full-path="Object1/content.xml" manifest:media-type="text/xml"/>
'''

manifest_text = manifest_text.replace('</manifest:manifest>', manifest_addition + '</manifest:manifest>')

with open(manifest_path, 'w', encoding='UTF-8') as f:
    f.write(manifest_text)
print("Updated manifest.xml")


# ── 11. Repack into ODS ───────────────────────────────────────────────────────
import tempfile
tmp_out = DST + '.tmp'
with zipfile.ZipFile(tmp_out, 'w', zipfile.ZIP_DEFLATED) as zout:
    # mimetype must be first and uncompressed
    mimetype_path = os.path.join(TMP, 'mimetype')
    zout.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)

    for dirpath, dirnames, filenames in os.walk(TMP):
        for filename in filenames:
            full = os.path.join(dirpath, filename)
            arcname = os.path.relpath(full, TMP)
            if arcname == 'mimetype':
                continue
            zout.write(full, arcname)

os.replace(tmp_out, DST)
print(f"Saved updated ODS to {DST}")
