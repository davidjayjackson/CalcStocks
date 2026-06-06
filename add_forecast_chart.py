#!/usr/bin/env python3
"""Add a line chart to the Forecast sheet of JEPI-ETF.ods.

Chart shows:
  - Blue line:   Close price (historical, B2:B290)
  - Orange line: Forecast (ETS formula values, C2:C290)
  - X-axis:      Dates (A2:A290)
"""

import zipfile, shutil, os
import xml.etree.ElementTree as ET
from datetime import date

SRC = '/home/davidj/Projects/CalcStocks/JEPI-ETF.ods'
TMP = '/tmp/jepi_forecast_chart'
DST = '/home/davidj/Projects/CalcStocks/JEPI-ETF.ods'

# ── ODS namespace map ─────────────────────────────────────────────────────────
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

# Excel/LibreOffice serial date epoch
EPOCH = date(1899, 12, 30)

def date_serial(iso_str):
    """Convert ISO date string (YYYY-MM-DD) to LibreOffice serial number."""
    y, m, d = map(int, iso_str.split('-'))
    return (date(y, m, d) - EPOCH).days

# ── Extract ODS ───────────────────────────────────────────────────────────────
if os.path.exists(TMP):
    shutil.rmtree(TMP)
with zipfile.ZipFile(SRC) as z:
    z.extractall(TMP)

# ── Read Forecast sheet data ──────────────────────────────────────────────────
content_path = os.path.join(TMP, 'content.xml')
tree = ET.parse(content_path)
root = tree.getroot()

sheets = root.findall(f'.//{q("table","table")}')
forecast_sheet = next(s for s in sheets
                      if s.attrib.get(q('table','name')) == 'Forecast')

rows = forecast_sheet.findall(q('table', 'table-row'))

# Collect date serials and Close values for local-table (rows 2–290 = idx 1–289)
data_rows = []  # list of (serial, close_str_or_None)
for row in rows[1:290]:
    cells = row.findall(q('table', 'table-cell'))
    # Column A: date
    date_val = cells[0].attrib.get(q('office', 'date-value'), '') if cells else ''
    serial = date_serial(date_val) if date_val else ''
    # Column B: close (float or empty)
    close = ''
    if len(cells) > 1:
        close = cells[1].attrib.get(q('office', 'value'), '')
    data_rows.append((serial, close))

n_points    = len(data_rows)        # 289
n_hist      = 259                   # rows 2–260 have actual Close
first_serial = data_rows[0][0]      # x-axis minimum

print(f"Data rows: {n_points}, historical: {n_hist}, first serial: {first_serial}")

# ── Build local-table rows XML ────────────────────────────────────────────────
def local_table_rows(data):
    lines = []
    for i, (serial, close) in enumerate(data):
        lines.append('        <table:table-row>')
        # Date cell (category)
        lines.append(f'          <table:table-cell office:value-type="float" office:value="{serial}">'
                     f'<text:p>{serial}</text:p>'
                     + (f'<draw:g><svg:desc>Forecast.A{i+2}:Forecast.A{i+2}</svg:desc></draw:g>' if i == 0 else '')
                     + '</table:table-cell>')
        # Close cell
        if close:
            lines.append(f'          <table:table-cell office:value-type="float" office:value="{close}">'
                         f'<text:p>{close}</text:p>'
                         + (f'<draw:g><svg:desc>Forecast.B{2}:Forecast.B{n_hist+1}</svg:desc></draw:g>' if i == 0 else '')
                         + '</table:table-cell>')
        else:
            lines.append('          <table:table-cell office:value-type="string" office:string-value="">'
                         '<text:p>NaN</text:p></table:table-cell>')
        # Forecast cell (always NaN in local-table; LibreOffice computes from formula)
        lines.append('          <table:table-cell office:value-type="string" office:string-value="">'
                     '<text:p>NaN</text:p></table:table-cell>')
        lines.append('        </table:table-row>')
    return '\n'.join(lines)

# ── Build chart content.xml ───────────────────────────────────────────────────
CHART_NS = '''xmlns:css3t="http://www.w3.org/TR/css3-text/" xmlns:grddl="http://www.w3.org/2003/g/data-view#" xmlns:xhtml="http://www.w3.org/1999/xhtml" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xforms="http://www.w3.org/2002/xforms" xmlns:dom="http://www.w3.org/2001/xml-events" xmlns:script="urn:oasis:names:tc:opendocument:xmlns:script:1.0" xmlns:form="urn:oasis:names:tc:opendocument:xmlns:form:1.0" xmlns:math="http://www.w3.org/1998/Math/MathML" xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:ooo="http://openoffice.org/2004/office" xmlns:chartooo="http://openoffice.org/2010/chart" xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0" xmlns:ooow="http://openoffice.org/2004/writer" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:drawooo="http://openoffice.org/2010/draw" xmlns:oooc="http://openoffice.org/2004/calc" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:calcext="urn:org:documentfoundation:names:experimental:calc:xmlns:calcext:1.0" xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" xmlns:of="urn:oasis:names:tc:opendocument:xmlns:of:1.2" xmlns:tableooo="http://openoffice.org/2009/table" xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0" xmlns:dr3d="urn:oasis:names:tc:opendocument:xmlns:dr3d:1.0" xmlns:rpt="http://openoffice.org/2005/report" xmlns:formx="urn:openoffice:names:experimental:ooxml-odf-interop:xmlns:form:1.0" xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0" xmlns:chart="urn:oasis:names:tc:opendocument:xmlns:chart:1.0" xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" xmlns:meta="urn:oasis:names:tc:opendocument:xmlns:meta:1.0" xmlns:loext="urn:org:documentfoundation:names:experimental:office:xmlns:loext:1.0" xmlns:number="urn:oasis:names:tc:opendocument:xmlns:datastyle:1.0" xmlns:field="urn:openoffice:names:experimental:ooo-ms-interop:xmlns:field:1.0"'''

chart_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<office:document-content {CHART_NS} office:version="1.4">
<office:automatic-styles>
  <number:number-style style:name="N0"><number:number number:min-integer-digits="1"/></number:number-style>
  <number:date-style style:name="N49">
    <number:year number:style="long"/><number:text>-</number:text>
    <number:month number:style="long"/><number:text>-</number:text>
    <number:day number:style="long"/>
  </number:date-style>
  <!-- ch1: chart container -->
  <style:style style:name="ch1" style:family="chart">
    <style:graphic-properties draw:stroke="none"/>
  </style:style>
  <!-- ch2: legend -->
  <style:style style:name="ch2" style:family="chart">
    <style:chart-properties chart:auto-position="true"/>
    <style:graphic-properties draw:stroke="none" svg:stroke-color="#b3b3b3" draw:fill="none" draw:fill-color="#e6e6e6"/>
    <style:text-properties fo:font-size="10pt" style:font-size-asian="10pt" style:font-size-complex="10pt"/>
  </style:style>
  <!-- ch3: plot area -->
  <style:style style:name="ch3" style:family="chart">
    <style:chart-properties chart:include-hidden-cells="false" chart:auto-position="true" chart:auto-size="true"
      chart:treat-empty-cells="leave-gap" chart:right-angled-axes="true"/>
  </style:style>
  <!-- ch4: x-axis (date) -->
  <style:style style:name="ch4" style:family="chart" style:data-style-name="N49">
    <style:chart-properties chart:display-label="true" chart:logarithmic="false"
      chart:minimum="{first_serial}" chart:origin="0" chart:reverse-direction="false"
      text:line-break="false" loext:try-staggering-first="false"
      chart:link-data-style-to-source="true" chart:axis-position="0"/>
    <style:graphic-properties svg:stroke-color="#b3b3b3"/>
    <style:text-properties fo:font-size="10pt" style:font-size-asian="10pt" style:font-size-complex="10pt"/>
  </style:style>
  <!-- ch5: y-axis -->
  <style:style style:name="ch5" style:family="chart" style:data-style-name="N0">
    <style:chart-properties chart:display-label="true" chart:logarithmic="false"
      chart:minimum="53" chart:origin="0" chart:reverse-direction="false"
      text:line-break="false" loext:try-staggering-first="false"
      chart:link-data-style-to-source="true" chart:axis-position="0"/>
    <style:graphic-properties svg:stroke-color="#b3b3b3"/>
    <style:text-properties fo:font-size="10pt" style:font-size-asian="10pt" style:font-size-complex="10pt"/>
  </style:style>
  <!-- ch6: y-axis grid -->
  <style:style style:name="ch6" style:family="chart">
    <style:graphic-properties svg:stroke-color="#b3b3b3"/>
  </style:style>
  <!-- ch7: Close series (blue) -->
  <style:style style:name="ch7" style:family="chart" style:data-style-name="N0">
    <style:chart-properties chart:symbol-type="none" chart:link-data-style-to-source="true"/>
    <style:graphic-properties svg:stroke-width="0.08cm" svg:stroke-color="#004586"
      draw:fill-color="#004586" dr3d:edge-rounding="5%"/>
    <style:text-properties fo:font-size="10pt" style:font-size-asian="10pt" style:font-size-complex="10pt"/>
  </style:style>
  <!-- ch8: Forecast series (orange dashed) -->
  <style:style style:name="ch8" style:family="chart" style:data-style-name="N0">
    <style:chart-properties chart:symbol-type="none" chart:link-data-style-to-source="true"/>
    <style:graphic-properties svg:stroke-width="0.08cm" svg:stroke-color="#ff6600"
      draw:stroke="dash" draw:stroke-dash="Dash" draw:fill-color="#ff6600" dr3d:edge-rounding="5%"/>
    <style:text-properties fo:font-size="10pt" style:font-size-asian="10pt" style:font-size-complex="10pt"/>
  </style:style>
  <!-- ch9: chart wall -->
  <style:style style:name="ch9" style:family="chart">
    <style:graphic-properties draw:stroke="solid" svg:stroke-color="#b3b3b3"
      draw:fill="none" draw:fill-color="#e6e6e6"/>
  </style:style>
  <!-- ch10: chart floor -->
  <style:style style:name="ch10" style:family="chart">
    <style:graphic-properties svg:stroke-color="#b3b3b3" draw:fill-color="#cccccc"/>
  </style:style>
</office:automatic-styles>
<office:body><office:chart>
  <chart:chart svg:width="25.4cm" svg:height="14cm"
    xlink:href=".." xlink:type="simple"
    chart:class="chart:line" chart:style-name="ch1">
    <chart:legend chart:legend-position="top" svg:x="5cm" svg:y="0.2cm"
      style:legend-expansion="wide" chart:style-name="ch2"/>
    <chart:plot-area chart:style-name="ch3"
      svg:x="0.25cm" svg:y="1cm" svg:width="24.9cm" svg:height="12.5cm">
      <chart:coordinate-region svg:x="2cm" svg:y="1cm" svg:width="22cm" svg:height="10cm"/>
      <chart:axis chart:dimension="x" chart:name="primary-x" chart:style-name="ch4"
        chartooo:axis-type="date">
        <chartooo:date-scale/>
        <chart:categories table:cell-range-address="Forecast.A2:Forecast.A290"/>
      </chart:axis>
      <chart:axis chart:dimension="y" chart:name="primary-y" chart:style-name="ch5">
        <chart:grid chart:style-name="ch6" chart:class="major"/>
      </chart:axis>
      <chart:series chart:style-name="ch7"
        chart:values-cell-range-address="Forecast.B2:Forecast.B290"
        chart:label-cell-address="Forecast.B1:Forecast.B1"
        chart:class="chart:line">
        <chart:data-point chart:repeated="{n_points}"/>
      </chart:series>
      <chart:series chart:style-name="ch8"
        chart:values-cell-range-address="Forecast.C2:Forecast.C290"
        chart:label-cell-address="Forecast.C1:Forecast.C1"
        chart:class="chart:line">
        <chart:data-point chart:repeated="{n_points}"/>
      </chart:series>
      <chart:wall chart:style-name="ch9"/>
      <chart:floor chart:style-name="ch10"/>
    </chart:plot-area>
    <table:table table:name="local-table">
      <table:table-header-columns><table:table-column/></table:table-header-columns>
      <table:table-columns>
        <table:table-column table:number-columns-repeated="2"/>
      </table:table-columns>
      <table:table-header-rows>
        <table:table-row>
          <table:table-cell><text:p/></table:table-cell>
          <table:table-cell office:value-type="string">
            <text:p>Close</text:p>
            <draw:g><svg:desc>Forecast.B1:Forecast.B1</svg:desc></draw:g>
          </table:table-cell>
          <table:table-cell office:value-type="string">
            <text:p>Forecast</text:p>
            <draw:g><svg:desc>Forecast.C1:Forecast.C1</svg:desc></draw:g>
          </table:table-cell>
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

# ── Write Object 3 files ──────────────────────────────────────────────────────
obj3_dir = os.path.join(TMP, 'Object 3')
os.makedirs(obj3_dir, exist_ok=True)

with open(os.path.join(obj3_dir, 'content.xml'), 'w', encoding='UTF-8') as f:
    f.write(chart_content)

with open(os.path.join(obj3_dir, 'meta.xml'), 'w', encoding='UTF-8') as f:
    f.write('''<?xml version="1.0" encoding="UTF-8"?>
<office:document-meta xmlns:grddl="http://www.w3.org/2003/g/data-view#" xmlns:meta="urn:oasis:names:tc:opendocument:xmlns:meta:1.0" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:chartooo="http://openoffice.org/2010/chart" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:ooo="http://openoffice.org/2004/office" xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" office:version="1.4"><office:meta><meta:generator>LibreOffice/25.2.3.2$Linux_X86_64 LibreOffice_project/520$Build-2</meta:generator></office:meta></office:document-meta>
''')

with open(os.path.join(obj3_dir, 'styles.xml'), 'w', encoding='UTF-8') as f:
    f.write('''<?xml version="1.0" encoding="UTF-8"?>
<office:document-styles xmlns:css3t="http://www.w3.org/TR/css3-text/" xmlns:grddl="http://www.w3.org/2003/g/data-view#" xmlns:xhtml="http://www.w3.org/1999/xhtml" xmlns:dom="http://www.w3.org/2001/xml-events" xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:ooo="http://openoffice.org/2004/office" xmlns:chartooo="http://openoffice.org/2010/chart" xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0" xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" xmlns:ooow="http://openoffice.org/2004/writer" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:drawooo="http://openoffice.org/2010/draw" xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" xmlns:of="urn:oasis:names:tc:opendocument:xmlns:of:1.2" xmlns:tableooo="http://openoffice.org/2009/table" xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0" xmlns:dr3d="urn:oasis:names:tc:opendocument:xmlns:dr3d:1.0" xmlns:rpt="http://openoffice.org/2005/report" xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0" xmlns:chart="urn:oasis:names:tc:opendocument:xmlns:chart:1.0" xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" xmlns:loext="urn:org:documentfoundation:names:experimental:office:xmlns:loext:1.0" xmlns:oooc="http://openoffice.org/2004/calc" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:calcext="urn:org:documentfoundation:names:experimental:calc:xmlns:calcext:1.0" xmlns:number="urn:oasis:names:tc:opendocument:xmlns:datastyle:1.0" xmlns:field="urn:openoffice:names:experimental:ooo-ms-interop:xmlns:field:1.0" xmlns:script="urn:oasis:names:tc:opendocument:xmlns:script:1.0" office:version="1.4"><office:styles/></office:document-styles>
''')

# Empty GDI replacement (LibreOffice regenerates it on open)
os.makedirs(os.path.join(TMP, 'ObjectReplacements'), exist_ok=True)
open(os.path.join(TMP, 'ObjectReplacements', 'Object 3'), 'wb').close()

# ── Add draw:frame to Forecast sheet ─────────────────────────────────────────
notify_ranges = (
    'Forecast.A2:Forecast.A290 '
    'Forecast.B1:Forecast.B1 Forecast.B2:Forecast.B290 '
    'Forecast.C1:Forecast.C1 Forecast.C2:Forecast.C290'
)

# Build the frame element as raw XML then parse it in
frame_xml = f'''<draw:frame
  xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0"
  xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0"
  xmlns:xlink="http://www.w3.org/1999/xlink"
  xmlns:loext="urn:org:documentfoundation:names:experimental:office:xmlns:loext:1.0"
  draw:z-index="0" draw:style-name="gr1" draw:text-style-name="P1"
  svg:width="10in" svg:height="5.5in" svg:x="4in" svg:y="0.3in">
  <draw:object
    draw:notify-on-update-of-ranges="{notify_ranges}"
    xlink:href="./Object 3" xlink:type="simple"
    xlink:show="embed" xlink:actuate="onLoad"><loext:p/></draw:object>
  <draw:image
    xlink:href="./ObjectReplacements/Object 3" xlink:type="simple"
    xlink:show="embed" xlink:actuate="onLoad"/>
</draw:frame>'''

frame_el = ET.fromstring(frame_xml)

# Find the Forecast sheet's table-row parent and insert the frame into a cell
# Charts in Calc live inside a draw:frame that is a child of the sheet element
forecast_sheet.append(frame_el)
print("draw:frame appended to Forecast sheet")

# ── Update manifest.xml ───────────────────────────────────────────────────────
manifest_path = os.path.join(TMP, 'META-INF', 'manifest.xml')
manifest_tree = ET.parse(manifest_path)
manifest_root = manifest_tree.getroot()
MAN = 'urn:oasis:names:tc:opendocument:xmlns:manifest:1.0'
ET.register_namespace('manifest', MAN)

new_entries = [
    ('ObjectReplacements/Object 3',
     'application/x-openoffice-gdimetafile;windows_formatname="GDIMetaFile"'),
    ('Object 3/meta.xml',    'text/xml'),
    ('Object 3/styles.xml',  'text/xml'),
    ('Object 3/content.xml', 'text/xml'),
    ('Object 3/',            'application/vnd.oasis.opendocument.chart'),
]
for path, media in new_entries:
    el = ET.SubElement(manifest_root, f'{{{MAN}}}file-entry')
    el.set(f'{{{MAN}}}full-path', path)
    el.set(f'{{{MAN}}}media-type', media)

manifest_tree.write(manifest_path, xml_declaration=True, encoding='UTF-8')

# ── Save content.xml ──────────────────────────────────────────────────────────
tree.write(content_path, xml_declaration=True, encoding='UTF-8')

# ── Repack ODS ────────────────────────────────────────────────────────────────
if os.path.exists(DST):
    shutil.copy2(DST, DST + '.bak')

with zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED) as zout:
    for root_dir, dirs, files in os.walk(TMP):
        for fname in files:
            fpath = os.path.join(root_dir, fname)
            arcname = os.path.relpath(fpath, TMP)
            zout.write(fpath, arcname)

shutil.rmtree(TMP)
print(f"Saved: {DST}")
print(f"Chart covers {n_points} data points ({n_hist} historical + {n_points - n_hist} forecast)")
