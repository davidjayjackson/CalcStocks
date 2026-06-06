#!/usr/bin/env python3
"""Add cumulative VWAP ± 2 std-dev bands to JEPI-ETF.ods and embed a chart."""

import csv, zipfile, shutil, os, math
import xml.etree.ElementTree as ET

SRC = '/home/davidj/Projects/CalcStocks/JEPI-ETF.ods'
DST = '/home/davidj/Projects/CalcStocks/JEPI-ETF.ods'
TMP = '/tmp/jepi_vwap'

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
for prefix, uri in NS.items():
    ET.register_namespace(prefix, uri)

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


def q(ns_key, local):
    return f'{{{NS[ns_key]}}}{local}'


# ── 1. Read CSV data ──────────────────────────────────────────────────────────
closes, volumes = [], []
with open('/tmp/JEPI-ETF.csv') as f:
    for row in csv.DictReader(f):
        closes.append(float(row['Close']))
        volumes.append(float(row['Volume']))

n = len(closes)
print(f"Loaded {n} rows")


# ── 2. Compute cumulative VWAP and ±2σ bands ──────────────────────────────────
#
#  VWAP_i   = Σ(close_j * vol_j, j≤i) / Σ(vol_j, j≤i)
#  Var_i    = Σ(vol_j * (close_j - VWAP_i)², j≤i) / Σ(vol_j, j≤i)
#  σ_i      = sqrt(Var_i)
#  Upper_i  = VWAP_i + 2σ_i
#  Lower_i  = VWAP_i - 2σ_i
#
vwap_vals, upper_vals, lower_vals = [], [], []
cum_pv  = 0.0   # Σ price*volume
cum_v   = 0.0   # Σ volume
cum_pv2 = 0.0   # Σ price²*volume  (for variance via E[x²] - E[x]²)

for i in range(n):
    cum_pv  += closes[i] * volumes[i]
    cum_v   += volumes[i]
    cum_pv2 += closes[i] ** 2 * volumes[i]

    vwap = cum_pv / cum_v
    var  = (cum_pv2 / cum_v) - vwap ** 2
    std  = math.sqrt(max(var, 0.0))

    vwap_vals.append(round(vwap, 4))
    upper_vals.append(round(vwap + 2 * std, 4))
    lower_vals.append(round(vwap - 2 * std, 4))

print(f"VWAP sample (last): {vwap_vals[-1]}  +2σ: {upper_vals[-1]}  -2σ: {lower_vals[-1]}")


# ── 3. Extract ODS ────────────────────────────────────────────────────────────
if os.path.exists(TMP):
    shutil.rmtree(TMP)
os.makedirs(TMP)
with zipfile.ZipFile(SRC, 'r') as z:
    z.extractall(TMP)


# ── 4. Parse content.xml ──────────────────────────────────────────────────────
content_path = os.path.join(TMP, 'content.xml')
tree = ET.parse(content_path)
root = tree.getroot()

ONS   = NS['office']
TNS   = NS['table']
TXTNS = NS['text']
CALCNS= NS['calcext']
STNS  = NS['style']
DRAWNS= NS['draw']
SVGNS = NS['svg']
XLNS  = NS['xlink']

body        = root.find(f'{{{ONS}}}body')
spreadsheet = body.find(f'{{{ONS}}}spreadsheet')
table       = spreadsheet.find(f'{{{TNS}}}table')
rows_els    = table.findall(f'{{{TNS}}}table-row')
total_rows  = n + 1  # header + data rows


# ── 5. Cell constructors ──────────────────────────────────────────────────────
def make_string_cell(text, style='ce4'):
    cell = ET.Element(q('table', 'table-cell'))
    cell.set(q('table', 'style-name'), style)
    cell.set(q('office', 'value-type'), 'string')
    cell.set(q('calcext', 'value-type'), 'string')
    ET.SubElement(cell, q('text', 'p')).text = text
    return cell


def make_float_cell(value, style='ce5'):
    cell = ET.Element(q('table', 'table-cell'))
    cell.set(q('table', 'style-name'), style)
    cell.set(q('office', 'value-type'), 'float')
    cell.set(q('office', 'value'), str(value))
    cell.set(q('calcext', 'value-type'), 'float')
    ET.SubElement(cell, q('text', 'p')).text = str(value)
    return cell


def make_empty_cell():
    return ET.Element(q('table', 'table-cell'))


def strip_trailing_empties(row_el):
    """Remove repeated-empty cells at the end of a row."""
    for cell in list(row_el):
        if cell.tag.split('}')[-1] == 'table-cell':
            if (cell.get(q('table', 'number-columns-repeated'))
                    and cell.find(q('text', 'p')) is None):
                row_el.remove(cell)


# ── 6. Add headers ────────────────────────────────────────────────────────────
header_row = rows_els[0]
strip_trailing_empties(header_row)
for label in ('VWAP', 'VWAP+2σ', 'VWAP-2σ'):
    header_row.append(make_string_cell(label))


# ── 7. Add VWAP data to each row ──────────────────────────────────────────────
for i, row_el in enumerate(rows_els[1:], start=0):
    if i >= n:
        break
    strip_trailing_empties(row_el)
    row_el.append(make_float_cell(vwap_vals[i]))
    row_el.append(make_float_cell(upper_vals[i]))
    row_el.append(make_float_cell(lower_vals[i]))


# ── 8. Add column-width declarations for the 3 new columns ───────────────────
auto_styles = root.find(f'{{{ONS}}}automatic-styles')
col_style = ET.SubElement(auto_styles, q('style', 'style'))
col_style.set(q('style', 'name'), 'co_vwap')
col_style.set(q('style', 'family'), 'table-column')
cp = ET.SubElement(col_style, q('style', 'table-column-properties'))
cp.set(q('fo', 'break-before'), 'auto')
cp.set(q('style', 'column-width'), '1.0in')

col_els = table.findall(q('table', 'table-column'))
insert_idx = list(table).index(col_els[-1]) + 1
for _ in range(3):
    nc = ET.Element(q('table', 'table-column'))
    nc.set(q('table', 'style-name'), 'co_vwap')
    nc.set(q('table', 'default-cell-style-name'), 'Default')
    table.insert(insert_idx, nc)
    insert_idx += 1


# ── 9. Add chart frame (Object2) to the spreadsheet ──────────────────────────
# Columns: A=Date B=Close C=Volume D=MA_50 E=MA_100 F=VWAP G=VWAP+2σ H=VWAP-2σ
# Chart will show B (Close), F (VWAP), G (VWAP+2σ), H (VWAP-2σ)

chart_y_in = (n + 3) * 0.178 + 5.0   # place below the MA chart
frame2 = ET.Element(q('draw', 'frame'))
frame2.set(q('draw', 'name'), 'Object2')
frame2.set(q('svg', 'x'), '0.1417in')
frame2.set(q('svg', 'y'), f'{chart_y_in:.2f}in')
frame2.set(q('svg', 'width'), '8in')
frame2.set(q('svg', 'height'), '4.5in')
frame2.set(q('draw', 'z-index'), '1')

obj2 = ET.SubElement(frame2, q('draw', 'object'))
obj2.set(q('xlink', 'href'), './Object2')
obj2.set(q('xlink', 'type'), 'simple')
obj2.set(q('xlink', 'show'), 'embed')
obj2.set(q('xlink', 'actuate'), 'onLoad')

img2 = ET.SubElement(frame2, q('draw', 'image'))
img2.set(q('xlink', 'href'), './Thumbnails/thumbnail.png')
img2.set(q('xlink', 'type'), 'simple')
img2.set(q('xlink', 'show'), 'embed')
img2.set(q('xlink', 'actuate'), 'onLoad')

named_expr = spreadsheet.find(q('table', 'named-expressions'))
if named_expr is not None:
    idx = list(spreadsheet).index(named_expr)
    spreadsheet.insert(idx, frame2)
else:
    spreadsheet.append(frame2)

tree.write(content_path, encoding='UTF-8', xml_declaration=True)
print("Wrote updated content.xml")


# ── 10. Create Object2/content.xml (VWAP chart) ───────────────────────────────
obj2_dir = os.path.join(TMP, 'Object2')
os.makedirs(obj2_dir, exist_ok=True)

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
  xmlns:number="urn:oasis:names:tc:opendocument:xmlns:datastyle:1.0"
  xmlns:loext="urn:org:documentfoundation:names:experimental:office:xmlns:loext:1.0"
  office:version="1.4">
  <office:automatic-styles>
    <style:style style:name="close_ser" style:family="chart">
      <style:chart-properties chart:symbol-type="none"/>
      <style:graphic-properties draw:stroke="solid" draw:stroke-color="#2E75B6"
        draw:fill="none" svg:stroke-width="0.03in"/>
    </style:style>
    <style:style style:name="vwap_ser" style:family="chart">
      <style:chart-properties chart:symbol-type="none"/>
      <style:graphic-properties draw:stroke="solid" draw:stroke-color="#C00000"
        draw:fill="none" svg:stroke-width="0.03in"/>
    </style:style>
    <style:style style:name="upper_ser" style:family="chart">
      <style:chart-properties chart:symbol-type="none"/>
      <style:graphic-properties draw:stroke="dash" draw:stroke-color="#70AD47"
        draw:fill="none" svg:stroke-width="0.02in"/>
    </style:style>
    <style:style style:name="lower_ser" style:family="chart">
      <style:chart-properties chart:symbol-type="none"/>
      <style:graphic-properties draw:stroke="dash" draw:stroke-color="#FF0000"
        draw:fill="none" svg:stroke-width="0.02in"/>
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
        chart:data-source-has-labels="both">
        <chart:title>
          <text:p>JEPI-ETF: VWAP with ±2 Standard Deviation Bands</text:p>
        </chart:title>
        <chart:legend chart:legend-position="right"/>
        <chart:plot-area chart:style-name="chplotarea"
          chart:data-source-has-labels="both"
          table:cell-range-address="JEPI.$A$1:.$H${total_rows}">
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
            chart:style-name="close_ser"
            chart:attached-axis="primary-y">
            <chart:data-point chart:repeated="{n}"/>
          </chart:series>
          <chart:series
            chart:values-cell-range-address="JEPI.$F$2:.$F${total_rows}"
            chart:label-cell-address="JEPI.$F$1"
            chart:class="chart:line"
            chart:style-name="vwap_ser"
            chart:attached-axis="primary-y">
            <chart:data-point chart:repeated="{n}"/>
          </chart:series>
          <chart:series
            chart:values-cell-range-address="JEPI.$G$2:.$G${total_rows}"
            chart:label-cell-address="JEPI.$G$1"
            chart:class="chart:line"
            chart:style-name="upper_ser"
            chart:attached-axis="primary-y">
            <chart:data-point chart:repeated="{n}"/>
          </chart:series>
          <chart:series
            chart:values-cell-range-address="JEPI.$H$2:.$H${total_rows}"
            chart:label-cell-address="JEPI.$H$1"
            chart:class="chart:line"
            chart:style-name="lower_ser"
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

with open(os.path.join(obj2_dir, 'content.xml'), 'w', encoding='UTF-8') as f:
    f.write(chart_content)
print("Wrote Object2/content.xml")


# ── 11. Update manifest.xml ───────────────────────────────────────────────────
manifest_path = os.path.join(TMP, 'META-INF', 'manifest.xml')
with open(manifest_path) as f:
    manifest = f.read()

addition = (
    '   <manifest:file-entry manifest:full-path="Object2/" '
    'manifest:media-type="application/vnd.oasis.opendocument.chart"/>\n'
    '   <manifest:file-entry manifest:full-path="Object2/content.xml" '
    'manifest:media-type="text/xml"/>\n'
)
manifest = manifest.replace('</manifest:manifest>', addition + '</manifest:manifest>')
with open(manifest_path, 'w') as f:
    f.write(manifest)
print("Updated manifest.xml")


# ── 12. Repack ODS ────────────────────────────────────────────────────────────
tmp_out = DST + '.tmp'
with zipfile.ZipFile(tmp_out, 'w', zipfile.ZIP_DEFLATED) as zout:
    mimetype = os.path.join(TMP, 'mimetype')
    zout.write(mimetype, 'mimetype', compress_type=zipfile.ZIP_STORED)
    for dirpath, _, filenames in os.walk(TMP):
        for filename in filenames:
            full = os.path.join(dirpath, filename)
            arcname = os.path.relpath(full, TMP)
            if arcname == 'mimetype':
                continue
            zout.write(full, arcname)

os.replace(tmp_out, DST)
print(f"Saved to {DST}")
