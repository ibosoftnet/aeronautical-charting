"""AIXM 5.2 XML yazım çekirdeği (Jeppesen üreticisi için).

Element sırası XSD'deki <sequence> sırasına birebir uymak ZORUNDA; sıra dışı
yazım şema doğrulamasını kırar. Bu yüzden her yazıcı alanları XSD sırasında
yazar ve boş değerleri atlar.

Not: Bu modül LT üreticisindeki `aixm/writer.py` ile aynı felsefeyi taşır.
Üreticiler bilinçli olarak birbirinden bağımsız (self-contained) araçlardır —
ortak bir kütüphaneye bağlanmazlar ki biri değişince diğeri kırılmasın.
"""

import re
import uuid
import xml.etree.ElementTree as ET

NS_MESSAGE = "http://www.aixm.aero/schema/5.2/message"
NS_AIXM = "http://www.aixm.aero/schema/5.2"
NS_GML = "http://www.opengis.net/gml/3.2"
NS_XLINK = "http://www.w3.org/1999/xlink"

SRS_NAME = "urn:ogc:def:crs:EPSG::4326"

# Bu projeye özgü sabit UUID5 namespace'i (LT üreticisiyle aynı sabit —
# aynı namespace altında farklı `kind` önekleri kullanıldığı için çakışma olmaz).
UUID_NAMESPACE = uuid.UUID("6f1c3b52-9d4a-5e77-b8c1-2a0e94f7d310")

for _prefix, _uri in (("message", NS_MESSAGE), ("aixm", NS_AIXM),
                      ("gml", NS_GML), ("xlink", NS_XLINK)):
    ET.register_namespace(_prefix, _uri)


def q(ns, tag):
    return f"{{{ns}}}{tag}"


def aixm(tag):
    return q(NS_AIXM, tag)


def gml(tag):
    return q(NS_GML, tag)


def feature_uuid(kind: str, key: str) -> str:
    """Feature türü + anahtar için deterministik UUID5 (büyük harf)."""
    return str(uuid.uuid5(UUID_NAMESPACE, f"{kind}:{key}")).upper()


def _ncname(text: str) -> str:
    """gml:id için geçerli NCName üretir (harf/alt çizgi ile başlar)."""
    cleaned = re.sub(r"[^A-Za-z0-9_.-]", "_", (text or "").strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    if not cleaned or not re.match(r"[A-Za-z_]", cleaned):
        cleaned = "X" + cleaned
    return cleaned


class IdRegistry:
    """Okunabilir gml:id üretir ve benzersizliğini garanti eder.

    `source_prefix` her id'nin başına eklenir (örn. `JEPP_NAV_NDB_BBS_DA`) —
    böylece farklı kaynaklardan gelen AIXM dosyaları tek bir GeoPackage'da
    birleşince gml:id'ler karışmaz. Türetilmiş id'ler (`_TS`, `_EP`, `_NC` …)
    zaten önekli id'den üretildiği için öneki otomatik miras alır.
    """

    def __init__(self, source_prefix: str = ""):
        self._used: set[str] = set()
        self._source = source_prefix.strip("_")

    def make(self, prefix: str, key: str) -> str:
        parts = [p for p in (self._source, prefix, key) if p]
        base = _ncname("_".join(parts))
        candidate = base
        n = 1
        while candidate in self._used:
            n += 1
            candidate = f"{base}_{n}"
        self._used.add(candidate)
        return candidate


def sub(parent, tag, text=None, **attrs):
    """Alt element ekler."""
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


def elevated_point(parent, gml_id, lat, lon):
    """aixm:location → aixm:ElevatedPoint (Navaid ve NavaidEquipment için).

    gml:pos AIXM/EPSG:4326 sırasında ENLEM BOYLAM'dır.
    """
    loc = ET.SubElement(parent, aixm("location"))
    point = ET.SubElement(loc, aixm("ElevatedPoint"))
    point.set(q(NS_GML, "id"), gml_id)
    point.set("srsName", SRS_NAME)
    sub(point, gml("pos"), f"{lat} {lon}")
    return loc


def note(parent, gml_id, text, purpose="REMARK"):
    """aixm:annotation → Note (purpose, translatedNote/LinguisticNote/note)."""
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

    def __init__(self, message_id, effective_begin):
        self.root = ET.Element(q(NS_MESSAGE, "AIXMBasicMessage"))
        self.root.set(q(NS_GML, "id"), message_id)
        self.effective_begin = effective_begin

    def add_feature(self, feature_name, gml_id, uuid_value):
        """hasMember → Feature → timeSlice → <Feature>TimeSlice döndürür."""
        member = ET.SubElement(self.root, q(NS_MESSAGE, "hasMember"))
        feature = ET.SubElement(member, aixm(feature_name))
        feature.set(q(NS_GML, "id"), gml_id)
        ident = sub(feature, gml("identifier"), uuid_value)
        ident.set("codeSpace", "urn:uuid:")

        ts_wrapper = ET.SubElement(feature, aixm("timeSlice"))
        ts = ET.SubElement(ts_wrapper, aixm(f"{feature_name}TimeSlice"))
        ts.set(q(NS_GML, "id"), gml_id + "_TS")

        vt = ET.SubElement(ts, gml("validTime"))
        tp = sub(vt, gml("TimePeriod"))
        tp.set(q(NS_GML, "id"), gml_id + "_TP")
        # Jeppesen kayitlarinda feature BASINA yururluk tarihi YOKTUR.
        # data.json'daki AIRAC effectivity VERI SETININ gecerliligidir,
        # feature'in kendi yururlugu degil (EAD'de her kaydin kendi `dtWef`i
        # var, burada karsiligi yok). Bilinmeyen tarih yerine AIRAC tarihini
        # yazmak uydurma bir yururluk iddiasi olurdu — kullanici karari:
        # beginPosition bos birakilir, endPosition gibi belirsiz isaretlenir.
        sub(tp, gml("beginPosition"), None, indeterminatePosition="unknown")
        sub(tp, gml("endPosition"), None, indeterminatePosition="unknown")

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
