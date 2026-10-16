"""Jenerik AIXM 5.2 okuyucu — kaynağa ve feature türüne özel mantık içermez.

Kaynak dosyalar 1. aşamada üretilmiş, XSD'ye karşı doğrulanmış AIXM 5.2
mesajlarıdır: `message:AIXMBasicMessage` → `message:hasMember` →
`aixm:<Feature>` → `gml:identifier` + `aixm:timeSlice` →
`aixm:<Feature>TimeSlice`.

Bellek: büyük dosyalar (EAD-SDO ~500 MB) akış (streaming) modunda okunur;
işlenen eleman hemen bellekten atılır.
"""

from pathlib import Path

from lxml import etree

NS_MESSAGE = "http://www.aixm.aero/schema/5.2/message"
NS_AIXM = "http://www.aixm.aero/schema/5.2"
NS_GML = "http://www.opengis.net/gml/3.2"
NS_XLINK = "http://www.w3.org/1999/xlink"

#: Projenin KENDİ AIXM extension namespace'i. Namespace URI bir adres değil,
#: kimliktir; karşılaştırma birebir dizgi karşılaştırmasıdır. Değer yalnızca
#: burada tanımlanır (üreticiler de buradan alır).
NS_IBOSOFTAIS = ("https://cdn.ibosoft.net.tr/aviation-data"
                 "/schema/aixm/5.2/extension")

M = "{%s}" % NS_MESSAGE
A = "{%s}" % NS_AIXM
G = "{%s}" % NS_GML
X = "{%s}" % NS_XLINK
I = "{%s}" % NS_IBOSOFTAIS

HAS_MEMBER = M + "hasMember"


def local(tag: str) -> str:
    """'{ns}Name' → 'Name'."""
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def iter_members(path: Path):
    """`hasMember` elemanlarını akış modunda üretir.

    Her adımda eleman ve önceki kardeşleri bellekten silinir. Tüketici, eleman
    üzerinde yalnızca kendi döngü adımı içinde çalışmalıdır.
    """
    context = etree.iterparse(str(path), events=("end",), tag=HAS_MEMBER)
    for _, member in context:
        yield member
        member.clear()
        while member.getprevious() is not None:
            del member.getparent()[0]


def feature_of(member):
    """`hasMember` → içindeki `aixm:<Feature>` elemanı."""
    return member[0] if len(member) else None


def time_slice(feature):
    """`aixm:<Feature>TimeSlice` elemanı (yoksa None)."""
    wrapper = feature.find(A + "timeSlice")
    return wrapper[0] if wrapper is not None and len(wrapper) else None


def uuid_of(feature) -> str | None:
    el = feature.find(G + "identifier")
    return el.text.strip().upper() if el is not None and el.text else None


def gml_id_of(el) -> str | None:
    return el.get(G + "id")


def text_of(ts, name: str) -> str | None:
    """TimeSlice'ın doğrudan alt elemanının metni (yoksa None)."""
    if ts is None:
        return None
    el = ts.find(A + name)
    return el.text.strip() if el is not None and el.text else None


def href_of(el) -> str | None:
    """`xlink:href="urn:uuid:…"` → UUID (büyük harf)."""
    if el is None:
        return None
    href = el.get(X + "href")
    if not href or not href.startswith("urn:uuid:"):
        return None
    return href[len("urn:uuid:"):].strip().upper()
