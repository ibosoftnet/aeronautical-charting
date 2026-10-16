"""Birleşik AIXM'deki Airspace geometrisini okur ve hesaplar.

AIXM'de bir Airspace'in geometrisi `geometryComponent` listesidir; her bileşen
bir `AirspaceVolume` ile bir işlem (`operation`) ve sıra (`operationSequence`)
taşır. Sonuç geometri bileşenlerin sırayla uygulanmasıdır (kullanıcı kararı):

    BASE ile başla → UNION (birleşim) / SUBTR (fark) / INTERS (kesişim)

Bir bileşenin poligonu `horizontalProjection`'dadır (`aixm:Surface` →
`gml:PolygonPatch`'ler). Poligonu olmayan bileşen (yalnız `centreline`/`width`
koridoru ya da `contributorAirspace` ile başka sahadan devralınan geometri)
HESAPLANAMAZ: poligon uydurulmaz, `GeometryError` yükselir.
"""

from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.polygon import orient

from data_build_common.aixm_reader import A, G

from airspace_geo import antimeridian_safe

OPERATIONS = ("BASE", "UNION", "SUBTR", "INTERS")


class GeometryError(ValueError):
    """Geometri hesaplanamadı (gerekçe mesajda; birleştirici loglar)."""


def _pairs(text):
    values = [float(v) for v in text.split()]
    if len(values) % 2:
        raise GeometryError("posList tek sayida deger")
    lats, lons = values[0::2], values[1::2]
    return list(zip(lons, lats))                     # shapely: (lon, lat)


def _ring(holder):
    pos_list = holder.find(f"{G}LinearRing/{G}posList")
    if pos_list is None or not pos_list.text:
        raise GeometryError("LinearRing/posList yok")
    return _pairs(pos_list.text)


def surface_geometry(volume):
    """`AirspaceVolume/horizontalProjection` → shapely Polygon/MultiPolygon."""
    surface = volume.find(f"{A}horizontalProjection/{A}Surface")
    if surface is None:
        return None
    polygons = []
    for patch in surface.iter(G + "PolygonPatch"):
        exterior = patch.find(G + "exterior")
        if exterior is None:
            raise GeometryError("PolygonPatch exterior yok")
        holes = [_ring(i) for i in patch.findall(G + "interior")]
        polygons.append(Polygon(_ring(exterior), holes or None))
    if not polygons:
        return None
    return polygons[0] if len(polygons) == 1 else MultiPolygon(polygons)


def components(ts):
    """TimeSlice → [(operation, sequence, component_el, volume_el)] sıralı."""
    out = []
    for holder in ts.findall(A + "geometryComponent"):
        comp = holder.find(A + "AirspaceGeometryComponent")
        if comp is None:
            continue
        op = (comp.findtext(A + "operation") or "").strip()
        seq_text = (comp.findtext(A + "operationSequence") or "").strip()
        try:
            seq = int(seq_text)
        except ValueError:
            raise GeometryError(f"operationSequence sayi degil: {seq_text!r}")
        volume = comp.find(f"{A}theAirspaceVolume/{A}AirspaceVolume")
        out.append((op, seq, comp, volume))
    return sorted(out, key=lambda c: c[1])


def airspace_geometry(ts):
    """Bileşenleri sırayla uygular → (antimeridyen güvenli MultiPolygon,
    BASE bileşeninin volume elemanı)."""
    comps = components(ts)
    if not comps:
        raise GeometryError("geometryComponent yok")
    seqs = [c[1] for c in comps]
    if len(set(seqs)) != len(seqs):
        raise GeometryError(f"operationSequence tekrar ediyor: {seqs}")
    if comps[0][0] != "BASE" or sum(1 for c in comps if c[0] == "BASE") != 1:
        raise GeometryError("ilk bilesen tek bir BASE degil: "
                            f"{[c[0] for c in comps]}")

    result, base_volume = None, comps[0][3]
    for op, seq, _, volume in comps:
        if op not in OPERATIONS:
            raise GeometryError(f"bilinmeyen operation: {op!r}")
        geom = surface_geometry(volume) if volume is not None else None
        if geom is None:
            raise GeometryError(f"bilesen {seq} ({op}) horizontalProjection "
                                "tasimiyor; poligon uydurulmaz")
        if not geom.is_valid:
            geom = geom.buffer(0)
        if op == "BASE":
            result = geom
        elif op == "UNION":
            result = result.union(geom)
        elif op == "SUBTR":
            result = result.difference(geom)
        else:
            result = result.intersection(geom)

    safe = antimeridian_safe(result)
    if safe is None:
        raise GeometryError("sonuc geometri bos")
    # Birleşik AIXM zaten RFC 7946 yönündedir (orient_member); burada yeniden
    # uygulanır çünkü UNION/SUBTR/INTERS ve antimeridyen bölmesi yönü
    # değiştirebilir.
    return orient_rfc7946(safe), base_volume


# ── Halka yönü (RFC 7946 §3.1.6) ──────────────────────────────────────────
#
# Kural (kullanıcı kararı): dış halka saat yönünün TERSİ, delikler saat yönü.
# Yön harita düzleminde hesaplanır: x = boylam (doğu), y = enlem (kuzey).
# AIXM `posList` "enlem boylam" sırasındadır — ham sayı sırasıyla hesaplamak
# yönü ters çıkarırdı.

def orient_rfc7946(geometry):
    """shapely (lon, lat) MultiPolygon → RFC 7946 yönlü MultiPolygon."""
    return MultiPolygon([orient(p, sign=1.0) for p in geometry.geoms])


def _signed_area_latlon(values):
    """posList değerleri (enlem boylam …) → x=boylam, y=enlem düzleminde
    işaretli alan (pozitif = saat yönünün tersi)."""
    lats, lons = values[0::2], values[1::2]
    n = len(lons)
    return sum(lons[i] * lats[(i + 1) % n] - lons[(i + 1) % n] * lats[i]
               for i in range(n)) / 2.0


def _orient_pos_list(pos_list, want_ccw):
    """Halkayı gerekiyorsa ters çevirir; değerler metin olarak korunur
    (yalnız nokta SIRASI değişir). Çevrildiyse True."""
    tokens = pos_list.text.split()
    area = _signed_area_latlon([float(t) for t in tokens])
    if area == 0 or (area > 0) == want_ccw:
        return False
    pairs = [tokens[i:i + 2] for i in range(0, len(tokens), 2)]
    pos_list.text = " ".join(" ".join(p) for p in reversed(pairs))
    return True


def orient_member(feature):
    """Airspace feature'ının TÜM `horizontalProjection` yüzeylerini RFC 7946
    yönüne getirir (yerinde). Döner: ters çevrilen halka sayısı."""
    reversed_rings = 0
    for patch in feature.iter(G + "PolygonPatch"):
        for side, want_ccw in (("exterior", True), ("interior", False)):
            for holder in patch.findall(G + side):
                pos_list = holder.find(f"{G}LinearRing/{G}posList")
                if pos_list is not None and pos_list.text:
                    reversed_rings += _orient_pos_list(pos_list, want_ccw)
    return reversed_rings
