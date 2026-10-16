"""Veri kökeni (provenance) — `ibosoftais:<F>DataProvenance` extension kutusu.

AIXM'de veri sağlayıcısı / yayımcı / veri seti geçerliliği için alan yoktur.
Bu bilgiler her feature'ın TimeSlice'ına, AIXM'in resmi genişletme noktası
olan `aixm:extension` içinde AYRI bir kutu olarak yazılır:

    <aixm:extension>
      <ibosoftais:DesignatedPointDataProvenance gml:id="EAD_DP_X_PROV">
        <ibosoftais:dataProvider>EUROCONTROL EAD SDO</ibosoftais:dataProvider>
        <ibosoftais:dataOriginator>DHMI TURKIYE</ibosoftais:dataOriginator>
        <ibosoftais:dataEffectivity>01 OCT 2026 (AIRAC 2610)</ibosoftais:dataEffectivity>
      </ibosoftais:DesignatedPointDataProvenance>
    </aixm:extension>

Kutunun içi her feature tipinde aynıdır, adı tipe göre değişir (XSD 1.0'da bir
eleman tek bir soyut başlığa bağlanabilir). Şema:
`common/schemas/ibosoftais-extension.xsd`.

Fonksiyonlar hem `xml.etree.ElementTree` hem `lxml` elemanlarıyla çalışır:
yeni eleman `makeelement()` ile kurulur, iki API de bunu destekler.
"""

from .aixm_reader import A, G, I, local

#: Kutunun TimeSlice içindeki son ekleri (gml:id = <feature gml:id> + ek).
BOX_ID_SUFFIX = "_PROV"

PROVIDER = "dataProvider"
ORIGINATOR = "dataOriginator"
EFFECTIVITY = "dataEffectivity"


class ProvenanceError(ValueError):
    """Zorunlu provenance alanı eksik ya da kutu bulunamadı."""


def box_tag(kind: str) -> str:
    """Feature tipi → kutu elemanının tam adı."""
    return f"{I}{kind}DataProvenance"


def _time_slice(feature):
    wrapper = feature.find(A + "timeSlice")
    return wrapper[0] if wrapper is not None and len(wrapper) else None


def _sub(parent, tag, text=None, attrib=None):
    el = parent.makeelement(tag, attrib or {})
    if text is not None:
        el.text = text
    parent.append(el)
    return el


def append_box(feature, provider: str, originator: str | None,
               effectivity: str):
    """Feature'ın TimeSlice'ının SONUNA provenance kutusunu ekler.

    AIXM'de `extension` TimeSlice dizisinin son elemanıdır, bu yüzden kutu
    feature'ın diğer tüm alanları yazıldıktan sonra eklenmelidir.
    `provider` ve `effectivity` zorunludur — boşsa `ProvenanceError`
    (sessiz varsayılan değer yazılmaz). `originator` boşsa eleman yazılmaz.
    """
    provider = (provider or "").strip()
    effectivity = (effectivity or "").strip()
    originator = (originator or "").strip()
    feature_id = feature.get(G + "id")
    if not provider or not effectivity:
        raise ProvenanceError(
            f"{feature_id}: dataProvider/dataEffectivity zorunlu "
            f"(provider={provider!r}, effectivity={effectivity!r})")
    ts = _time_slice(feature)
    if ts is None:
        raise ProvenanceError(f"{feature_id}: TimeSlice yok")

    ext = _sub(ts, A + "extension")
    box = _sub(ext, box_tag(local(feature.tag)),
               attrib={G + "id": f"{feature_id}{BOX_ID_SUFFIX}"})
    _sub(box, I + PROVIDER, provider)
    if originator:
        _sub(box, I + ORIGINATOR, originator)
    _sub(box, I + EFFECTIVITY, effectivity)
    return box


def find_box(feature):
    """Feature'ın provenance kutusu (yoksa None)."""
    ts = _time_slice(feature)
    if ts is None:
        return None
    return ts.find(f"{A}extension/{box_tag(local(feature.tag))}")


def read(feature) -> dict | None:
    """Kutudaki değerler → `{data_provider, data_originator, data_effectivity}`.

    Kutu yoksa None. Yazılmamış `dataOriginator` None döner.
    """
    box = find_box(feature)
    if box is None:
        return None

    def text(name):
        el = box.find(I + name)
        return el.text.strip() if el is not None and el.text else None

    return {"data_provider": text(PROVIDER),
            "data_originator": text(ORIGINATOR),
            "data_effectivity": text(EFFECTIVITY)}


def require(feature) -> dict:
    """`read()` ile aynı; kutu yoksa `ProvenanceError`."""
    values = read(feature)
    if values is None:
        raise ProvenanceError(
            f"{feature.get(G + 'id')}: provenance kutusu yok")
    return values
