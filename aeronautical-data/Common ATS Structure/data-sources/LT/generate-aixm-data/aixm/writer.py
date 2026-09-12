"""AIXM 5.2 XML yazım çekirdeği.

Element sırası XSD'deki <sequence> sırasına birebir uymak ZORUNDA; sıra dışı
yazım şema doğrulamasını kırar. Bu yüzden her feature modülü alanları XSD
sırasında yazar ve boş değerleri atlar.
"""

import xml.etree.ElementTree as ET

NS_MESSAGE = "http://www.aixm.aero/schema/5.2/message"
NS_AIXM = "http://www.aixm.aero/schema/5.2"
NS_GML = "http://www.opengis.net/gml/3.2"
NS_XLINK = "http://www.w3.org/1999/xlink"

#: Bu projenin KENDİ AIXM extension namespace'i — `aixm:extension` altında
#: yazdığımız, çekirdek AIXM'de karşılığı olmayan alanlar buraya aittir
#: (şu an: ChangeOverPoint'in ikinci mesafesi, bkz. aixm/change_over_point.py).
#:
#: Namespace URI bir ADRES DEĞİL, kimliktir: XML ayrıştırıcıları onu hiçbir
#: zaman indirmez ve bir dosyanın yayımlanmış olması gerekmez (AIXM'in kendi
#: `http://www.aixm.aero/schema/5.2` namespace'i gibi). Değer, şema ileride
#: dışarıya açılırsa konulacağı yere göre seçilmiştir (kullanıcı kararı).
#:
#: DİKKAT: namespace karşılaştırması birebir DİZGİ karşılaştırmasıdır —
#: `http`/`https` farkı veya sondaki `/` ayrı namespace sayılır. Bu yüzden
#: değer yalnızca burada tanımlanır, hiçbir yerde elle tekrar yazılmaz.
NS_IBOSOFTAIS = ("https://cdn.ibosoft.net.tr/aviation-data"
                 "/schema/aixm/5.2/extension")

SRS_NAME = "urn:ogc:def:crs:EPSG::4326"

for prefix, uri in (("message", NS_MESSAGE), ("aixm", NS_AIXM),
                    ("gml", NS_GML), ("xlink", NS_XLINK),
                    ("ibosoftais", NS_IBOSOFTAIS)):
    ET.register_namespace(prefix, uri)


def q(ns, tag):
    return f"{{{ns}}}{tag}"


def aixm(tag):
    return q(NS_AIXM, tag)


def gml(tag):
    return q(NS_GML, tag)


def ibosoftais(tag):
    """Bu projenin kendi extension namespace'indeki eleman adı."""
    return q(NS_IBOSOFTAIS, tag)


def sub(parent, tag, text=None, **attrs):
    """Alt element ekler. attrs anahtarlarındaki '__' namespace ayıracıdır."""
    el = ET.SubElement(parent, tag)
    if text is not None:
        el.text = str(text)
    for k, v in attrs.items():
        if v is None:
            continue
        el.set(k, str(v))
    return el


def opt(parent, tag, value, **attrs):
    """Değer boş/None değilse element yazar, aksi halde hiç yazmaz."""
    if value is None:
        return None
    value = str(value).strip()
    if not value:
        return None
    return sub(parent, tag, value, **attrs)


def xlink_ref(parent, tag, uuid_value):
    """Boş içerikli association elementi: <tag xlink:href="urn:uuid:…"/>"""
    el = ET.SubElement(parent, tag)
    el.set(q(NS_XLINK, "href"), f"urn:uuid:{uuid_value}")
    return el


def pos(parent, lat, lon):
    """gml:pos — AIXM/EPSG:4326 sırası ENLEM BOYLAM (GeoJSON'un tersi)."""
    return sub(parent, gml("pos"), f"{lat} {lon}")


def time_period(parent, tag, gml_id, begin):
    el = ET.SubElement(parent, tag)
    tp = sub(el, gml("TimePeriod"))
    tp.set(q(NS_GML, "id"), gml_id)
    sub(tp, gml("beginPosition"), begin)
    sub(tp, gml("endPosition"), None, indeterminatePosition="unknown")
    return el


def note(parent, gml_id, text, purpose="REMARK"):
    """aixm:annotation → Note (propertyName, purpose, translatedNote)."""
    ann = ET.SubElement(parent, aixm("annotation"))
    n = ET.SubElement(ann, aixm("Note"))
    n.set(q(NS_GML, "id"), gml_id)
    sub(n, aixm("purpose"), purpose)
    tn = ET.SubElement(n, aixm("translatedNote"))
    ln = ET.SubElement(tn, aixm("LinguisticNote"))
    ln.set(q(NS_GML, "id"), gml_id + "_LN")
    sub(ln, aixm("note"), text)
    return ann


class MessageBuilder:
    """AIXMBasicMessage zarfı ve feature/timeSlice iskeleti."""

    def __init__(self, message_id, effective_begin, ids):
        self.root = ET.Element(q(NS_MESSAGE, "AIXMBasicMessage"))
        self.root.set(q(NS_GML, "id"), message_id)
        self.effective_begin = effective_begin
        self.ids = ids

    def add_feature(self, feature_name, gml_id, feature_uuid):
        """hasMember → Feature → timeSlice → FeatureTimeSlice döndürür.

        TimeSlice'ın zorunlu başlangıç elemanları (validTime, interpretation)
        burada yazılır; feature'a özgü alanlar çağıran modülde eklenir.
        """
        member = ET.SubElement(self.root, q(NS_MESSAGE, "hasMember"))
        feature = ET.SubElement(member, aixm(feature_name))
        feature.set(q(NS_GML, "id"), gml_id)
        ident = sub(feature, gml("identifier"), feature_uuid)
        ident.set("codeSpace", "urn:uuid:")

        ts_wrapper = ET.SubElement(feature, aixm("timeSlice"))
        ts = ET.SubElement(ts_wrapper, aixm(f"{feature_name}TimeSlice"))
        ts.set(q(NS_GML, "id"), gml_id + "_TS")
        time_period(ts, gml("validTime"), gml_id + "_TP", self.effective_begin)
        sub(ts, aixm("interpretation"), "BASELINE")
        sub(ts, aixm("sequenceNumber"), "1")
        sub(ts, aixm("correctionNumber"), "0")
        return ts

    def write(self, path, header_comment):
        ET.indent(self.root, space="  ")
        body = ET.tostring(self.root, encoding="unicode", xml_declaration=False)
        with open(path, "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write(f"<!-- {header_comment} -->\n")
            f.write(body)
            f.write("\n")
