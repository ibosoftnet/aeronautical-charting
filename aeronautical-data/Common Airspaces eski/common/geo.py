"""
Geometri ve ayrıştırma yardımcıları — tüm kaynak modülleri paylaşır.

Antimeridian işleme (make_geometry / _unroll_coords / _to_standard) ve
gpkg_geom, mevcut Airspaces/Jeppesen/export_airspaces.py'den taşınmıştır.
"""
import html
import re
import struct

from shapely.geometry import Polygon, MultiPolygon
from shapely.geometry import box as _box


def gpkg_geom(wkb: bytes, srs_id: int = 4326) -> bytes:
    """Standart WKB'yi minimal GeoPackage Binary header ile sar."""
    return b"GP" + bytes([0, 0x01]) + struct.pack("<i", srs_id) + wkb


# ---------------------------------------------------------------------------
# Antimeridian handling  (export_airspaces.py'den birebir)
# ---------------------------------------------------------------------------

def _unroll_coords(coords):
    """lon dizisini sürekli yap — 180°'den büyük sıçramaları yok et."""
    result = [coords[0]]
    for lon, lat in coords[1:]:
        prev = result[-1][0]
        while lon - prev > 180:
            lon -= 360
        while prev - lon > 180:
            lon += 360
        result.append((lon, lat))
    return result


def _to_standard(ring_coords, east_piece=False):
    """Unrolled [0,360] koordinatları [-180,180]'e çevir."""
    if east_piece:
        return [(x - 360, y) for x, y in ring_coords]
    return [(x, y) for x, y in ring_coords]


def make_geometry(coords):
    """
    Kapalı bir halkadan Polygon/MultiPolygon üret; antimeridian geçişlerini
    doğru işle. Bozuk girişte None döner.
    """
    coords_360 = [(lon % 360, lat) for lon, lat in coords]
    unrolled = _unroll_coords(coords_360)
    lons = [x for x, _ in unrolled]
    min_lon, max_lon = min(lons), max(lons)

    if max_lon - min_lon > 360:
        return None

    p = Polygon(unrolled)
    if not p.is_valid:
        p = p.buffer(0)
    if p.is_empty:
        return None

    if max_lon <= 180:
        return Polygon(_to_standard(unrolled, east_piece=False))
    if min_lon >= 180:
        return Polygon(_to_standard(unrolled, east_piece=True))

    west_clip = _box(min_lon - 1, -90, 180, 90)
    east_clip = _box(180, -90, max_lon + 1, 90)

    parts = []
    for clip, is_east in [(west_clip, False), (east_clip, True)]:
        piece = p.intersection(clip)
        if piece.is_empty:
            continue
        geoms = list(piece.geoms) if piece.geom_type == "MultiPolygon" else [piece]
        for sub in geoms:
            if sub.geom_type != "Polygon" or sub.is_empty:
                continue
            ext = _to_standard(sub.exterior.coords, is_east)
            holes = [_to_standard(ring.coords, is_east) for ring in sub.interiors]
            parts.append(Polygon(ext, holes))

    if not parts:
        return None
    return parts[0] if len(parts) == 1 else MultiPolygon(parts)


def to_multipolygon(geom):
    """Polygon veya MultiPolygon'u her zaman MultiPolygon'a çevir (şema tipi)."""
    if geom is None or geom.is_empty:
        return None
    if geom.geom_type == "Polygon":
        return MultiPolygon([geom])
    if geom.geom_type == "MultiPolygon":
        return geom
    return None


# ---------------------------------------------------------------------------
# Merkezi antimeridyen koruması — TÜM kaynaklara insert_record'da uygulanır.
# Kaynak modülleri ham (±180 sıçraması içerebilen) shapely geometri besler;
# burası güvenli MultiPolygon'a çevirir. Web haritasının "sapıtmaması" için.
# ---------------------------------------------------------------------------

def _crosses_am(geom):
    """Herhangi bir dış/iç halkada ardışık |Δlon| > 180° var mı?"""
    polys = geom.geoms if geom.geom_type == "MultiPolygon" else [geom]
    for poly in polys:
        if poly.geom_type != "Polygon":
            continue
        for ring in [poly.exterior, *poly.interiors]:
            xs = [c[0] for c in ring.coords]
            if any(abs(xs[i] - xs[i - 1]) > 180 for i in range(1, len(xs))):
                return True
    return False


def _standardize(poly, shift):
    """poly'yi lon += shift ile kaydır, [-180,180]'e getir; Polygon listesi döner."""
    ext = [(x + shift, y) for x, y in poly.exterior.coords]
    holes = [[(x + shift, y) for x, y in r.coords] for r in poly.interiors]
    p = Polygon(ext, holes)
    if not p.is_valid:
        p = p.buffer(0)
    if p.is_empty:
        return []
    return list(p.geoms) if p.geom_type == "MultiPolygon" else [p]


def _split_polygon_am(poly):
    """Bir Polygon'u (delikleri koruyarak) antimeridyende böl -> Polygon listesi."""
    ext_un = _unroll_coords([(x % 360, y) for x, y in poly.exterior.coords])
    lons = [x for x, _ in ext_un]
    mn, mx = min(lons), max(lons)
    if mx - mn > 360:
        p = poly if poly.is_valid else poly.buffer(0)
        if p.is_empty:
            return []
        return list(p.geoms) if p.geom_type == "MultiPolygon" else [p]

    ref = ext_un[0][0]
    holes_un = []
    for hole in poly.interiors:
        h = []
        for x, y in hole.coords:
            lon = x % 360
            while lon - ref > 180:
                lon -= 360
            while ref - lon > 180:
                lon += 360
            h.append((lon, y))
        holes_un.append(h)

    P = Polygon(ext_un, holes_un)
    if not P.is_valid:
        P = P.buffer(0)
    if P.is_empty:
        return []

    if mx <= 180:
        return _standardize(P, 0)
    if mn >= 180:
        return _standardize(P, -360)

    parts = []
    for clip, shift in ((_box(mn - 1, -90, 180, 90), 0), (_box(180, -90, mx + 1, 90), -360)):
        piece = P.intersection(clip)
        if piece.is_empty:
            continue
        subs = piece.geoms if piece.geom_type == "MultiPolygon" else [piece]
        for sub in subs:
            if sub.geom_type == "Polygon" and not sub.is_empty:
                parts.extend(_standardize(sub, shift))
    return parts


def antimeridian_safe(geom):
    """
    Herhangi bir Polygon/MultiPolygon'u web-haritası güvenli MultiPolygon'a
    çevir. Antimeridyen geçişi yoksa (fast-path) geometriye dokunmadan
    MultiPolygon'a sarar (geçersizse buffer(0) ile onarır); geçiyorsa ±180'de
    böler. Bozuk/boş girişte None.
    """
    if geom is None or geom.is_empty:
        return None
    if not _crosses_am(geom):
        if not geom.is_valid:
            g = geom.buffer(0)
            if not g.is_empty:
                geom = g
        return to_multipolygon(geom)
    polys = geom.geoms if geom.geom_type == "MultiPolygon" else [geom]
    out = []
    for poly in polys:
        if poly.geom_type == "Polygon":
            out.extend(_split_polygon_am(poly))
    return MultiPolygon(out) if out else None


def polygon_from_geojson(geom_gj):
    """GeoJSON Polygon/MultiPolygon -> shapely (buffer(0) ile onarım)."""
    if not geom_gj:
        return None
    t = geom_gj.get("type")
    if t == "Polygon":
        rings = geom_gj.get("coordinates") or []
        if not rings:
            return None
        poly = Polygon(rings[0], rings[1:] or None)
        if not poly.is_valid:
            poly = poly.buffer(0)
        return None if poly.is_empty else poly
    if t == "MultiPolygon":
        polys = []
        for rings in geom_gj.get("coordinates") or []:
            if not rings:
                continue
            poly = Polygon(rings[0], rings[1:] or None)
            if not poly.is_valid:
                poly = poly.buffer(0)
            if not poly.is_empty:
                polys.append(poly)
        return MultiPolygon(polys) if polys else None
    return None


# ---------------------------------------------------------------------------
# Jeppesen boundary blob decode  (export_airspaces.py'den birebir)
# ---------------------------------------------------------------------------

def decode_polygon_blob(blob: bytes):
    """[BE uint32 N][N*(BE float32 lon,lat)] -> kapalı koordinat listesi."""
    if not blob or len(blob) < 4:
        return None
    n = struct.unpack(">I", blob[:4])[0]
    if n < 3 or len(blob) < 4 + n * 8:
        return None
    pts = struct.unpack(f">{n*2}f", blob[4:4 + n * 8])
    coords = list(zip(pts[0::2], pts[1::2]))
    if coords[0] != coords[-1]:
        coords.append(coords[0])
    if len(set(coords)) < 3:
        return None
    return coords


# ---------------------------------------------------------------------------
# LT `pic` HTML tablosu ve LH DMS ayrıştırma
# ---------------------------------------------------------------------------

_PIC_RE = re.compile(r"<b>\s*([^<:]+?)\s*:\s*</b>\s*([^<]*)")


def parse_pic(pic: str) -> dict:
    """
    LT `pic` HTML tablosundan '<b>ETIKET : </b>DEĞER<br>' çiftlerini çıkar.
    Etiket -> değer(ler) listesi (NAME çoklu olabilir). Etiketler UPPER-case.
    """
    out: dict = {}
    for m in _PIC_RE.finditer(html.unescape(pic or "")):
        label = m.group(1).strip().upper()
        out.setdefault(label, []).append(m.group(2).strip())
    return out


def parse_dms(token: str) -> float:
    """'N473849' / 'E0193152' (hemisphere + DDMMSS / DDDMMSS) -> ondalık derece."""
    token = token.strip()
    hemi, digits = token[0].upper(), token[1:]
    if hemi in ("N", "S"):
        dd, mm, ss = int(digits[0:2]), int(digits[2:4]), float(digits[4:] or 0)
        val = dd + mm / 60 + ss / 3600
        return -val if hemi == "S" else val
    dd, mm, ss = int(digits[0:3]), int(digits[3:5]), float(digits[5:] or 0)
    val = dd + mm / 60 + ss / 3600
    return -val if hemi == "W" else val
