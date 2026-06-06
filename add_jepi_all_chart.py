#!/usr/bin/env python3
"""Add a single all-indicators chart to the JEPI sheet of JEPI-ETF.ods.

Series: Close, MA_50, MA_100, VWAP, VWAP+2σ, VWAP-2σ
Date axis: JEPI.A2:JEPI.A260  (259 trading days)
Placed below the two existing charts at x=8.5in, y=8.1in.
"""

import zipfile, shutil, os
import xml.etree.ElementTree as ET
from datetime import date

SRC = '/home/davidj/Projects/CalcStocks/JEPI-ETF.ods'
TMP = '/tmp/jepi_all_chart'
DST = '/home/davidj/Projects/CalcStocks/JEPI-ETF.ods'

NS = {
    'table':   'urn:oasis:names:tc:opendocument:xmlns:table:1.0',
    'text':    'urn:oasis:names:tc:opendocument:xmlns:text:1.0',
    'office':  'urn:oasis:names:tc:opendocument:xmlns:office:1.0',
    'calcext': 'urn:org:documentfoundation:names:experimental:calc:xmlns:calcext:1.0',
    'style':   'urn:oasis:names:tc:opendocument:xmlns:style:1.0',
    'draw':    'urn:oasis:names:tc:opendocument:xmlns:drawing:1.0',
    'svg':     'urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0',
    'xlink':   'http://www.w3.org/1999/xlink',
    'chart':   'urn:oasis:names:tc:opendocument:xmlns:chart:1.0',
    'number':  'urn:oasis:names:tc:opendocument:xmlns:datastyle:1.0',
    'loext':   'urn:org:documentfoundation:names:experimental:office:xmlns:loext:1.0',
    'fo':      'urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0',
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

EPOCH = date(1899, 12, 30)

def date_serial(iso_str):
    y, m, d = map(int, iso_str.split('-'))
    return (date(y, m, d) - EPOCH).days

# ── Extract ───────────────────────────────────────────────────────────────────
if os.path.exists(TMP):
    shutil.rmtree(TMP)
with zipfile.ZipFile(SRC) as z:
    z.extractall(TMP)

# ── Read JEPI sheet data ──────────────────────────────────────────────────────
content_path = os.path.join(TMP, 'content.xml')
tree = ET.parse(content_path)
root = tree.getroot()

sheets = root.findall(f'.//{q("table","table")}')
jepi_sheet = next(s for s in sheets if s.attrib.get(q('table','name')) == 'JEPI')
rows = jepi_sheet.findall(q('table', 'table-row'))

OFF = q('office', 'value')
DATE_VAL = q('office', 'date-value')

# col indices: A=0 B=1 C=2 D=3 E=4 F=5 G=6 H=7
COL_NAMES  = ['Close', 'MA_50', 'MA_100', 'VWAP', 'VWAP+2σ', 'VWAP-2σ']
COL_IDXS   = [1, 3, 4, 5, 6, 7]   # B D E F G H
# Sheet reference letters
COL_LETTERS = ['B', 'D', 'E', 'F', 'G', 'H']

data_rows = []   # list of (serial, [val_B, val_D, val_E, val_F, val_G, val_H])
for row in rows[1:260]:
    cells = row.findall(q('table', 'table-cell'))
    serial = date_serial(cells[0].attrib.get(DATE_VAL, '')) if cells else ''
    vals = []
    for ci in COL_IDXS:
        v = cells[ci].attrib.get(OFF, '') if len(cells) > ci else ''
        vals.append(v)
    data_rows.append((serial, vals))

n_points    = len(data_rows)
first_serial = data_rows[0][0]
print(f"Data rows: {n_points}, first serial: {first_serial}")

# ── Build local-table rows ────────────────────────────────────────────────────
def local_table_rows(data):
    lines = []
    for i, (serial, vals) in enumerate(data):
        lines.append('        <table:table-row>')
        # Category (date)
        desc = (f'<draw:g><svg:desc>JEPI.A{i+2}:JEPI.A{i+2}</svg:desc></draw:g>' if i == 0 else '')
        lines.append(f'          <table:table-cell office:value-type="float" office:value="{serial}">'
                     f'<text:p>{serial}</text:p>{desc}</table:table-cell>')
        # Series columns
        for j, v in enumerate(vals):
            if v:
                desc2 = (f'<draw:g><svg:desc>JEPI.{COL_LETTERS[j]}2:JEPI.{COL_LETTERS[j]}{n_points+1}'
                         f'</svg:desc></draw:g>' if i == 0 else '')
                lines.append(f'          <table:table-cell office:value-type="float" office:value="{v}">'
                             f'<text:p>{v}</text:p>{desc2}</table:table-cell>')
            else:
                lines.append('          <table:table-cell office:value-type="string" '
                             'office:string-value=""><text:p>NaN</text:p></table:table-cell>')
        lines.append('        </table:table-row>')
    return '\n'.join(lines)

# ── Series colours ────────────────────────────────────────────────────────────
# Close=blue, MA_50=red, MA_100=amber, VWAP=green, VWAP+2σ=purple dashed, VWAP-2σ=purple dashed
SERIES_STYLES = [
    ('ch7',  '#004586', 'solid',  '0.08cm'),  # Close – blue
    ('ch8',  '#ff420e', 'solid',  '0.08cm'),  # MA_50 – red
    ('ch9',  '#ffd320', 'solid',  '0.08cm'),  # MA_100 – amber
    ('ch10', '#579d1c', 'solid',  '0.08cm'),  # VWAP – green
    ('ch11', '#7e0021', 'dash',   '0.06cm'),  # VWAP+2σ – dark red dashed
    ('ch12', '#7e0021', 'dash',   '0.06cm'),  # VWAP-2σ – dark red dashed
]

def series_style_xml(name, color, stroke, width):
    stroke_attr = 'draw:stroke="dash" draw:stroke-dash="Dash" ' if stroke == 'dash' else ''
    return (f'<style:style style:name="{name}" style:family="chart" style:data-style-name="N0">'
            f'<style:chart-properties chart:symbol-type="none" chart:link-data-style-to-source="true"/>'
            f'<style:graphic-properties svg:stroke-width="{width}" svg:stroke-color="{color}" '
            f'{stroke_attr}draw:fill-color="{color}" dr3d:edge-rounding="5%"/>'
            f'<style:text-properties fo:font-size="10pt" style:font-size-asian="10pt" '
            f'style:font-size-complex="10pt"/></style:style>')

series_styles_xml = '\n  '.join(
    series_style_xml(name, color, stroke, width)
    for name, color, stroke, width in SERIES_STYLES
)

# ── Build series XML ──────────────────────────────────────────────────────────
def series_xml(style, col_letter, col_name):
    return (f'<chart:series chart:style-name="{style}" '
            f'chart:values-cell-range-address="JEPI.{col_letter}2:JEPI.{col_letter}260" '
            f'chart:label-cell-address="JEPI.{col_letter}1:JEPI.{col_letter}1" '
            f'chart:class="chart:line">'
            f'<chart:data-point chart:repeated="{n_points}"/></chart:series>')

all_series_xml = '\n      '.join(
    series_xml(SERIES_STYLES[i][0], COL_LETTERS[i], COL_NAMES[i])
    for i in range(len(COL_NAMES))
)

# ── Build header row for local-table ─────────────────────────────────────────
def header_cell(col_letter, label):
    return (f'<table:table-cell office:value-type="string"><text:p>{label}</text:p>'
            f'<draw:g><svg:desc>JEPI.{col_letter}1:JEPI.{col_letter}1</svg:desc></draw:g>'
            f'</table:table-cell>')

header_cells = '\n          '.join(
    header_cell(COL_LETTERS[i], COL_NAMES[i]) for i in range(len(COL_NAMES))
)

# ── Assemble chart content.xml ────────────────────────────────────────────────
CHART_NS = (
    'xmlns:css3t="http://www.w3.org/TR/css3-text/" '
    'xmlns:grddl="http://www.w3.org/2003/g/data-view#" '
    'xmlns:xhtml="http://www.w3.org/1999/xhtml" '
    'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
    'xmlns:xsd="http://www.w3.org/2001/XMLSchema" '
    'xmlns:xforms="http://www.w3.org/2002/xforms" '
    'xmlns:dom="http://www.w3.org/2001/xml-events" '
    'xmlns:script="urn:oasis:names:tc:opendocument:xmlns:script:1.0" '
    'xmlns:form="urn:oasis:names:tc:opendocument:xmlns:form:1.0" '
    'xmlns:math="http://www.w3.org/1998/Math/MathML" '
    'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
    'xmlns:ooo="http://openoffice.org/2004/office" '
    'xmlns:chartooo="http://openoffice.org/2010/chart" '
    'xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0" '
    'xmlns:ooow="http://openoffice.org/2004/writer" '
    'xmlns:xlink="http://www.w3.org/1999/xlink" '
    'xmlns:drawooo="http://openoffice.org/2010/draw" '
    'xmlns:oooc="http://openoffice.org/2004/calc" '
    'xmlns:dc="http://purl.org/dc/elements/1.1/" '
    'xmlns:calcext="urn:org:documentfoundation:names:experimental:calc:xmlns:calcext:1.0" '
    'xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" '
    'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" '
    'xmlns:of="urn:oasis:names:tc:opendocument:xmlns:of:1.2" '
    'xmlns:tableooo="http://openoffice.org/2009/table" '
    'xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0" '
    'xmlns:dr3d="urn:oasis:names:tc:opendocument:xmlns:dr3d:1.0" '
    'xmlns:rpt="http://openoffice.org/2005/report" '
    'xmlns:formx="urn:openoffice:names:experimental:ooxml-odf-interop:xmlns:form:1.0" '
    'xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0" '
    'xmlns:chart="urn:oasis:names:tc:opendocument:xmlns:chart:1.0" '
    'xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" '
    'xmlns:meta="urn:oasis:names:tc:opendocument:xmlns:meta:1.0" '
    'xmlns:loext="urn:org:documentfoundation:names:experimental:office:xmlns:loext:1.0" '
    'xmlns:number="urn:oasis:names:tc:opendocument:xmlns:datastyle:1.0" '
    'xmlns:field="urn:openoffice:names:experimental:ooo-ms-interop:xmlns:field:1.0"'
)

chart_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<office:document-content {CHART_NS} office:version="1.4">
<office:automatic-styles>
  <number:number-style style:name="N0"><number:number number:min-integer-digits="1"/></number:number-style>
  <number:date-style style:name="N49">
    <number:year number:style="long"/><number:text>-</number:text>
    <number:month number:style="long"/><number:text>-</number:text>
    <number:day number:style="long"/>
  </number:date-style>
  <style:style style:name="ch1" style:family="chart">
    <style:graphic-properties draw:stroke="none"/>
  </style:style>
  <style:style style:name="ch2" style:family="chart">
    <style:chart-properties chart:auto-position="true"/>
    <style:graphic-properties draw:stroke="none" svg:stroke-color="#b3b3b3"
      draw:fill="none" draw:fill-color="#e6e6e6"/>
    <style:text-properties fo:font-size="10pt" style:font-size-asian="10pt"
      style:font-size-complex="10pt"/>
  </style:style>
  <style:style style:name="ch3" style:family="chart">
    <style:chart-properties chart:include-hidden-cells="false" chart:auto-position="true"
      chart:auto-size="true" chart:treat-empty-cells="leave-gap"
      chart:right-angled-axes="true"/>
  </style:style>
  <style:style style:name="ch4" style:family="chart" style:data-style-name="N49">
    <style:chart-properties chart:display-label="true" chart:logarithmic="false"
      chart:minimum="{first_serial}" chart:origin="0" chart:reverse-direction="false"
      text:line-break="false" loext:try-staggering-first="false"
      chart:link-data-style-to-source="true" chart:axis-position="0"/>
    <style:graphic-properties svg:stroke-color="#b3b3b3"/>
    <style:text-properties fo:font-size="10pt" style:font-size-asian="10pt"
      style:font-size-complex="10pt"/>
  </style:style>
  <style:style style:name="ch5" style:family="chart" style:data-style-name="N0">
    <style:chart-properties chart:display-label="true" chart:logarithmic="false"
      chart:minimum="54" chart:origin="0" chart:reverse-direction="false"
      text:line-break="false" loext:try-staggering-first="false"
      chart:link-data-style-to-source="true" chart:axis-position="0"/>
    <style:graphic-properties svg:stroke-color="#b3b3b3"/>
    <style:text-properties fo:font-size="10pt" style:font-size-asian="10pt"
      style:font-size-complex="10pt"/>
  </style:style>
  <style:style style:name="ch6" style:family="chart">
    <style:graphic-properties svg:stroke-color="#b3b3b3"/>
  </style:style>
  {series_styles_xml}
  <style:style style:name="ch13" style:family="chart">
    <style:graphic-properties draw:stroke="solid" svg:stroke-color="#b3b3b3"
      draw:fill="none" draw:fill-color="#e6e6e6"/>
  </style:style>
  <style:style style:name="ch14" style:family="chart">
    <style:graphic-properties svg:stroke-color="#b3b3b3" draw:fill-color="#cccccc"/>
  </style:style>
</office:automatic-styles>
<office:body><office:chart>
  <chart:chart svg:width="25.4cm" svg:height="14cm"
    xlink:href=".." xlink:type="simple"
    chart:class="chart:line" chart:style-name="ch1">
    <chart:legend chart:legend-position="top" svg:x="4cm" svg:y="0.2cm"
      style:legend-expansion="wide" chart:style-name="ch2"/>
    <chart:plot-area chart:style-name="ch3"
      svg:x="0.25cm" svg:y="1.2cm" svg:width="24.9cm" svg:height="12.3cm">
      <chart:coordinate-region svg:x="2cm" svg:y="1cm"
        svg:width="22cm" svg:height="10cm"/>
      <chart:axis chart:dimension="x" chart:name="primary-x"
        chart:style-name="ch4" chartooo:axis-type="date">
        <chartooo:date-scale/>
        <chart:categories table:cell-range-address="JEPI.A2:JEPI.A260"/>
      </chart:axis>
      <chart:axis chart:dimension="y" chart:name="primary-y" chart:style-name="ch5">
        <chart:grid chart:style-name="ch6" chart:class="major"/>
      </chart:axis>
      {all_series_xml}
      <chart:wall chart:style-name="ch13"/>
      <chart:floor chart:style-name="ch14"/>
    </chart:plot-area>
    <table:table table:name="local-table">
      <table:table-header-columns><table:table-column/></table:table-header-columns>
      <table:table-columns>
        <table:table-column table:number-columns-repeated="{len(COL_NAMES)}"/>
      </table:table-columns>
      <table:table-header-rows>
        <table:table-row>
          <table:table-cell><text:p/></table:table-cell>
          {header_cells}
        </table:table-row>
      </table:table-header-rows>
      <table:table-rows>
{local_table_rows(data_rows)}
      </table:table-rows>
    </table:table>
  </chart:chart>
</office:chart></office:body>
</office:document-content>
'''

# ── Write Object 4 ────────────────────────────────────────────────────────────
obj4_dir = os.path.join(TMP, 'Object 4')
os.makedirs(obj4_dir, exist_ok=True)

with open(os.path.join(obj4_dir, 'content.xml'), 'w', encoding='UTF-8') as f:
    f.write(chart_content)

with open(os.path.join(obj4_dir, 'meta.xml'), 'w', encoding='UTF-8') as f:
    f.write('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<office:document-meta xmlns:meta="urn:oasis:names:tc:opendocument:xmlns:meta:1.0" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" '
            'xmlns:chartooo="http://openoffice.org/2010/chart" '
            'xmlns:xlink="http://www.w3.org/1999/xlink" '
            'xmlns:ooo="http://openoffice.org/2004/office" '
            'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
            'office:version="1.4"><office:meta>'
            '<meta:generator>LibreOffice/25.2.3.2$Linux_X86_64</meta:generator>'
            '</office:meta></office:document-meta>\n')

with open(os.path.join(obj4_dir, 'styles.xml'), 'w', encoding='UTF-8') as f:
    f.write('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<office:document-styles '
            'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
            'office:version="1.4"><office:styles/></office:document-styles>\n')

os.makedirs(os.path.join(TMP, 'ObjectReplacements'), exist_ok=True)
open(os.path.join(TMP, 'ObjectReplacements', 'Object 4'), 'wb').close()

# ── Add draw:frame to JEPI sheet ──────────────────────────────────────────────
notify = ('JEPI.A2:JEPI.A260 '
          'JEPI.B1:JEPI.B1 JEPI.B2:JEPI.B260 '
          'JEPI.D1:JEPI.D1 JEPI.D2:JEPI.D260 '
          'JEPI.E1:JEPI.E1 JEPI.E2:JEPI.E260 '
          'JEPI.F1:JEPI.F1 JEPI.F2:JEPI.F260 '
          'JEPI.G1:JEPI.G1 JEPI.G2:JEPI.G260 '
          'JEPI.H1:JEPI.H1 JEPI.H2:JEPI.H260')

frame_xml = (
    f'<draw:frame '
    f'xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0" '
    f'xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0" '
    f'xmlns:xlink="http://www.w3.org/1999/xlink" '
    f'xmlns:loext="urn:org:documentfoundation:names:experimental:office:xmlns:loext:1.0" '
    f'draw:z-index="2" draw:style-name="gr1" draw:text-style-name="P1" '
    f'svg:width="10in" svg:height="5.5in" svg:x="8.5in" svg:y="8.1in">'
    f'<draw:object draw:notify-on-update-of-ranges="{notify}" '
    f'xlink:href="./Object 4" xlink:type="simple" '
    f'xlink:show="embed" xlink:actuate="onLoad"><loext:p/></draw:object>'
    f'<draw:image xlink:href="./ObjectReplacements/Object 4" '
    f'xlink:type="simple" xlink:show="embed" xlink:actuate="onLoad"/>'
    f'</draw:frame>'
)

jepi_sheet.append(ET.fromstring(frame_xml))
print("draw:frame appended to JEPI sheet")

# ── Update manifest.xml ───────────────────────────────────────────────────────
manifest_path = os.path.join(TMP, 'META-INF', 'manifest.xml')
manifest_tree = ET.parse(manifest_path)
manifest_root = manifest_tree.getroot()
MAN = 'urn:oasis:names:tc:opendocument:xmlns:manifest:1.0'
ET.register_namespace('manifest', MAN)

for path, media in [
    ('ObjectReplacements/Object 4',
     'application/x-openoffice-gdimetafile;windows_formatname="GDIMetaFile"'),
    ('Object 4/meta.xml',    'text/xml'),
    ('Object 4/styles.xml',  'text/xml'),
    ('Object 4/content.xml', 'text/xml'),
    ('Object 4/',            'application/vnd.oasis.opendocument.chart'),
]:
    el = ET.SubElement(manifest_root, f'{{{MAN}}}file-entry')
    el.set(f'{{{MAN}}}full-path', path)
    el.set(f'{{{MAN}}}media-type', media)

manifest_tree.write(manifest_path, xml_declaration=True, encoding='UTF-8')

# ── Save ──────────────────────────────────────────────────────────────────────
tree.write(content_path, xml_declaration=True, encoding='UTF-8')

shutil.copy2(DST, DST + '.bak')
with zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED) as zout:
    for root_dir, dirs, files in os.walk(TMP):
        for fname in files:
            fpath = os.path.join(root_dir, fname)
            zout.write(fpath, os.path.relpath(fpath, TMP))

shutil.rmtree(TMP)
print(f"Saved: {DST}  ({n_points} data points, 6 series)")
