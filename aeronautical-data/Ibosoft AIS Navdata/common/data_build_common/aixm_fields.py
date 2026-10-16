"""AIXM → GeoPackage satırı: projelerden bağımsız ortak sütun aileleri.

Burada yalnızca HER katmanda aynı biçimde eşlenen yapılar durur:

* `annotation*`  — `annotation/Note` → purpose'a göre 4 sütun
* `data_*`       — provenance kutusu → 3 sütun
* `aixm_*`       — feature kimliği + TimeSlice/feature tabanı
* tekrarlanan (0..∞) yapıların JSON'a çevrilmesi (`element_to_dict`)

Katmana özgü eşleme her projenin kendi `mapper`'ındadır.
"""

import json

from .aixm_reader import A, G, X, local

# ── Basit okuyucular ───────────────────────────────────────────────────────

def text(parent, name):
    if parent is None:
        return None
    el = parent.find(A + name)
    return el.text.strip() if el is not None and el.text else None


def value_uom(parent, name):
    """`<aixm:x uom="NM">12</aixm:x>` → (değer, uom)."""
    if parent is None:
        return None, None
    el = parent.find(A + name)
    if el is None:
        return None, None
    return (el.text.strip() if el.text else None), el.get("uom")


def number(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except ValueError:
        return None


# ── Tekrarlanan yapılar → JSON ─────────────────────────────────────────────

def element_to_dict(el):
    """Bir AIXM alt ağacını sade bir sözlüğe çevirir (JSON sütunları için).

    * Metin taşıyan yaprak → `{"value": …, "uom": …}` veya düz metin
    * `xlink:href` taşıyan eleman → `{"href": "<uuid>"}`
    * Tekrarlanan kardeşler listeye toplanır
    Hiçbir alt alan atılmaz; `gml:id` gibi teknik nitelikler dışarıda bırakılır.
    """
    node = {}
    href = el.get(X + "href")
    if href:
        node["href"] = href[len("urn:uuid:"):] if href.startswith("urn:uuid:") else href
    uom = el.get("uom")
    if uom:
        node["uom"] = uom
    indeterminate = el.get("indeterminatePosition")
    if indeterminate:
        node["indeterminatePosition"] = indeterminate

    children = [c for c in el if isinstance(c.tag, str)]
    if not children:
        txt = (el.text or "").strip()
        if txt and not node:
            return txt
        if txt:
            node["value"] = txt
        return node or None

    for child in children:
        name = local(child.tag)
        if name == "id":
            continue
        value = element_to_dict(child)
        if value is None:
            continue
        if name in node:
            if not isinstance(node[name], list):
                node[name] = [node[name]]
            node[name].append(value)
        else:
            node[name] = value
    return node or None


def json_list(ts, name):
    """0..∞ alanı → JSON dizisi metni (boşsa None)."""
    if ts is None:
        return None
    items = []
    for el in ts.findall(A + name):
        # Sarmalayıcının tek çocuğu asıl nesnedir (örn. availability → Navaid…).
        inner = [c for c in el if isinstance(c.tag, str)]
        value = element_to_dict(inner[0]) if len(inner) == 1 else element_to_dict(el)
        if value is not None:
            items.append(value)
    return json.dumps(items, ensure_ascii=False) if items else None


# ── annotation ─────────────────────────────────────────────────────────────

ANNOTATION_PURPOSES = ("Description", "Remark", "Warning", "Disclaimer")
#: Katman öneksiz — annotation yapısı her katmanda aynı 4 purpose'a indirgenir.
ANNOTATION_COLUMNS = [f"annotation{p}" for p in ANNOTATION_PURPOSES]

#: Aynı feature içindeki, aynı purpose'a düşen notların ayırıcısı: her not
#: yeni satırda (kullanıcı kararı; eskiden " | " idi).
NOTE_SEPARATOR = "\n"
#: Farklı feature'lardan gelen notların ayırıcısı: arada bir boş satır.
FEATURE_SEPARATOR = "\n\n"


def annotations(ts, row):
    """`annotation` → 4 sabit sütun (Description/Remark/Warning/Disclaimer).

    `purpose` yoksa REMARK sayılır. Aynı feature içindeki aynı purpose'lu notlar
    `NOTE_SEPARATOR` ile birleşir. Fonksiyon aynı satır için birden fazla kez
    çağrılabilir: sonraki çağrılar mevcut değerin üzerine yazmaz,
    `FEATURE_SEPARATOR` ile ekler. Hiçbir not kaybolmaz.

    Yalnızca TimeSlice'ın DOĞRUDAN `annotation` alt elemanlarına bakılır; iç
    içe nesnelerin (volume, activation, …) notları o nesnenin JSON'undadır.
    """
    if ts is None:
        return
    buckets = {}
    for ann in ts.findall(A + "annotation"):
        note = ann.find(A + "Note")
        if note is None:
            continue
        purpose = (text(note, "purpose") or "REMARK").capitalize()
        texts = [n.text.strip() for n in note.iter(A + "note")
                 if n.text and n.text.strip()]
        if not texts:
            continue
        buckets.setdefault(purpose, []).extend(texts)
    for purpose, values in buckets.items():
        column = f"annotation{purpose}"
        yeni = NOTE_SEPARATOR.join(values)
        mevcut = row.get(column)
        row[column] = f"{mevcut}{FEATURE_SEPARATOR}{yeni}" if mevcut else yeni


# ── provenance ─────────────────────────────────────────────────────────────

#: Katman öneksiz; değerler feature'ın `ibosoftais:<F>DataProvenance` kutusundan.
PROVENANCE_COLUMNS = ["data_provider", "data_originator", "data_effectivity"]


def provenance(row, entry):
    """`provenance.read()` sözlüğü → 3 sütun. Kutuda olmayan originator NULL."""
    for column in PROVENANCE_COLUMNS:
        row[column] = entry.get(column)


# ── aixm_* : kimlik + TimeSlice/feature tabanı ─────────────────────────────

#: `aixm_gml_id`  : `gml:id` (belge içi, kaynak önekli)
#: `aixm_uuid`    : `gml:identifier` (belgeden bağımsız kalıcı kimlik)
IDENTITY_COLUMNS = ["aixm_gml_id", "aixm_uuid"]

#: AIXM'in her feature'ında bulunan taban alanlar (AbstractAIXMFeature* ve
#: AbstractAIXMTimeSlice* tipleri, `AIXM_AbstractGML_ObjectTypes.xsd`).
#: Zaman alanlarında metin yoksa GML'in `indeterminatePosition` değeri
#: (`unknown`, `now`, `before`, `after`) aynı sütuna yazılır.
BASE_COLUMNS = [
    "aixm_validTimeBegin", "aixm_validTimeEnd",
    "aixm_interpretation", "aixm_sequenceNumber", "aixm_correctionNumber",
    "aixm_featureLifetimeBegin", "aixm_featureLifetimeEnd",
    "aixm_timeSliceMetadata",            # JSON
    "aixm_featureMetadata",              # JSON
    "aixm_description",                  # gml:description
    "aixm_name",                         # gml:name (0..∞) → JSON dizisi
]
INTEGER_BASE_COLUMNS = frozenset({"aixm_sequenceNumber",
                                  "aixm_correctionNumber"})


def _time_value(el):
    if el is None:
        return None
    if el.text and el.text.strip():
        return el.text.strip()
    return el.get("indeterminatePosition")


def _period(holder):
    """`gml:TimePeriod` (begin/end) ya da `gml:TimeInstant` → (begin, end)."""
    if holder is None:
        return None, None
    period = holder.find(G + "TimePeriod")
    if period is not None:
        return (_time_value(period.find(G + "beginPosition")),
                _time_value(period.find(G + "endPosition")))
    instant = holder.find(G + "TimeInstant")
    if instant is not None:
        return _time_value(instant.find(G + "timePosition")), None
    return None, None


def _int(value):
    try:
        return int(value) if value not in (None, "") else None
    except ValueError:
        return None


def base_columns(row, feature, ts):
    """Kimlik dışındaki `aixm_*` taban sütunlarını doldurur."""
    if ts is not None:
        row["aixm_validTimeBegin"], row["aixm_validTimeEnd"] = \
            _period(ts.find(G + "validTime"))
        row["aixm_interpretation"] = text(ts, "interpretation")
        row["aixm_sequenceNumber"] = _int(text(ts, "sequenceNumber"))
        row["aixm_correctionNumber"] = _int(text(ts, "correctionNumber"))
        row["aixm_featureLifetimeBegin"], row["aixm_featureLifetimeEnd"] = \
            _period(ts.find(A + "featureLifetime"))
        meta = ts.find(A + "timeSliceMetadata")
        if meta is not None:
            value = element_to_dict(meta)
            row["aixm_timeSliceMetadata"] = (
                json.dumps(value, ensure_ascii=False) if value else None)
    if feature is not None:
        meta = feature.find(A + "featureMetadata")
        if meta is not None:
            value = element_to_dict(meta)
            row["aixm_featureMetadata"] = (
                json.dumps(value, ensure_ascii=False) if value else None)
        desc = feature.find(G + "description")
        if desc is not None and desc.text and desc.text.strip():
            row["aixm_description"] = desc.text.strip()
        names = [n.text.strip() for n in feature.findall(G + "name")
                 if n.text and n.text.strip()]
        if names:
            row["aixm_name"] = json.dumps(names, ensure_ascii=False)
