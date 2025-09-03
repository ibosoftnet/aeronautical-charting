#!/usr/bin/env python3
"""
sdo_to_kml.py

XML (SdoReportResponse) içindeki her <Record> öğesini işleyip KML dosyası üretir.
Her Record içindeki tüm alt etiketler (ve varsa alt-alt etiketler) "ana.alt" biçiminde düzleştirilip
Placemark içinde hem HTML tablosu (description) hem de ExtendedData (attribute olarak QGIS'te görünür) olarak eklenir.

Kullanım:
    python sdo_to_kml.py input.xml output.kml

Notlar:
 - Eğer bir Record'ta geoLat veya geoLong yoksa o kayıt atlanır.
 - Script sadece Python standart kütüphanesini kullanır.
"""
import sys
import xml.etree.ElementTree as ET
import html
from typing import Optional


def parse_coord(s: Optional[str]) -> Optional[float]:
    """Convert values like '68.72184720N' or '052.78474720W' to signed float degrees."""
    if s is None:
        return None
    s = s.strip()
    if len(s) == 0:
        return None
    dir_char = s[-1].upper()
    if dir_char in ('N', 'S', 'E', 'W'):
        num = s[:-1]
        try:
            val = float(num)
        except ValueError:
            val = float(num.replace(',', '.'))
        if dir_char in ('S', 'W'):
            val = -val
        return val
    else:
        try:
            return float(s)
        except ValueError:
            try:
                return float(s.replace(',', '.'))
            except Exception:
                return None


def flatten_element(elem, prefix=None, out=None):
    if out is None:
        out = {}
    tag = elem.tag if prefix is None else f"{prefix}.{elem.tag}"
    text = elem.text.strip() if elem.text and elem.text.strip() else None
    if len(list(elem)) == 0:
        out[tag] = text
    else:
        for child in elem:
            flatten_element(child, prefix=tag, out=out)
        if text:
            out[tag] = text
    return out


def record_to_properties(record):
    props = {}
    for child in record:
        tagname = child.tag
        if any(k == tagname or k.startswith(tagname + '.') for k in props.keys()):
            i = 1
            while True:
                key = f"{tagname}[{i}]"
                if not any(k == key or k.startswith(key + '.') for k in props.keys()):
                    break
                i += 1
            flatten = flatten_element(child, prefix=key)
            props.update(flatten)
        else:
            flatten = flatten_element(child, prefix=tagname)
            props.update(flatten)
    return props


def make_description_html(props: dict) -> str:
    rows = []
    for k in sorted(props.keys()):
        v = props[k] if props[k] is not None else ''
        rows.append(f"<tr><th style=\"text-align:left;padding:2px 6px;border:1px solid #ccc\">{html.escape(k)}</th>"
                    f"<td style=\"padding:2px 6px;border:1px solid #ccc\">{html.escape(v)}</td></tr>")
    table = "<table style=\"border-collapse:collapse;font-family:Arial,Helvetica,sans-serif;font-size:12px\">"
    table += ''.join(rows)
    table += '</table>'
    return table


def make_extended_data(props: dict) -> str:
    parts = ["<ExtendedData>"]
    for k in sorted(props.keys()):
        v = props[k] if props[k] is not None else ''
        parts.append(f"<Data name=\"{html.escape(k)}\"><value>{html.escape(v)}</value></Data>")
    parts.append("</ExtendedData>")
    return "\n".join(parts)


def main(argv):
    if len(argv) < 3:
        print("Kullanım: python sdo_to_kml.py input.xml output.kml")
        sys.exit(1)

    input_xml = argv[1]
    output_kml = argv[2]

    tree = ET.parse(input_xml)
    root = tree.getroot()

    kml_parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<kml xmlns="http://www.opengis.net/kml/2.2">',
        '<Document>'
    ]

    record_count = 0
    skipped = 0

    for record in root.findall('.//Record'):
        props = record_to_properties(record)
        lat_raw = props.get('geoLat') or props.get('Record.geoLat')
        lon_raw = props.get('geoLong') or props.get('Record.geoLong')
        if lat_raw is None:
            for k in props:
                if k.lower().endswith('geolat'):
                    lat_raw = props[k]
                if k.lower().endswith('geolong'):
                    lon_raw = props[k]
        if lat_raw is None or lon_raw is None:
            skipped += 1
            continue

        lat = parse_coord(lat_raw)
        lon = parse_coord(lon_raw)
        if lat is None or lon is None:
            skipped += 1
            continue

        name = props.get('txtName') or props.get('Record.txtName') or props.get('txtNameCitySer') or props.get('codeId') or 'NO_NAME'
        description = make_description_html(props)
        extended_data = make_extended_data(props)

        placemark = []
        placemark.append('<Placemark>')
        placemark.append(f'<name>{html.escape(name)}</name>')
        placemark.append(f'<description><![CDATA[{description}]]></description>')
        placemark.append(extended_data)
        placemark.append('<Point>')
        placemark.append(f'<coordinates>{lon},{lat},0</coordinates>')
        placemark.append('</Point>')
        placemark.append('</Placemark>')

        kml_parts.append('\n'.join(placemark))
        record_count += 1

    kml_parts.append('</Document>')
    kml_parts.append('</kml>')

    with open(output_kml, 'w', encoding='utf-8') as f:
        f.write('\n'.join(kml_parts))

    print(f"Tamamlandı: {record_count} placemark oluşturuldu, {skipped} kayıt atlandı. Çıktı: {output_kml}")


if __name__ == '__main__':
    main(sys.argv)
