"""AŞAMA 2B — `RoutePortion` geometrisi: rota aralığının çizgisi.

`ChangeOverPoint` bir rota **aralığında** tanımlıdır (`start` → `end`) ve kendi
koordinatı AIXM'de yazılmaz (bkz. `docs/AIXM_ChangeOverPoint_Attributes.md`
§7.2). Bu yüzden COP'un GeoPackage geometrisi o aralığın **çizgisidir**; sembol
çizgi boyunca bir yüzdeyle kaydırılarak yerine konur.

Çizgi, aralığı kapsayan `RouteSegment`'lerin `curveExtent` geometrilerinin
birleştirilmesiyle kurulur. İki şey kritiktir:

**1. Yön.** Çizgi `start` ucundan başlamak ZORUNDADIR, yoksa sembol yanlış
uçtan ölçülür. Kaynaktaki segmentler rotanın kendi yönünde kayıtlıdır ve bu
yön COP'un start→end yönüyle aynı olmak zorunda değildir — ölçüldü: örnek bir
COP'ta zincirdeki 7 segmentin **tamamı** ters yöndeydi. Bu yüzden her segment
gerektiğinde ters çevrilerek eklenir.

**2. Dallanma.** Rota dallanıyorsa "en kısa yol" sessizce yanlış kolu
seçebilir. AIXM'in bunun için alanı vardır: `RoutePortion.intermediatePoint`
(*"to be used when necessary to distinguish between alternative branches of a
route"*). Verilmişse yol onun ÜZERİNDEN geçer. Verilmemiş ve birden fazla eşit
uzunlukta yol varsa **seçim yapılmaz** — çağıran taraf bunu loglar ve geometri
boş kalır; yanlış kolu çizmek sessiz bir veri hatası olurdu.

Bu modül veritabanı bilmez: girdisi segment listesi, çıktısı koordinat dizisi.
"""

from collections import deque

from pyproj import Geod

#: Projede kullanılan elipsoid (`merge/antimeridian.py`, `merge/override.py`
#: ile aynı).
_GEOD = Geod(ellps="WGS84")

#: Bir rota aralığının çözülmüş hâli.
#: `coords`  : [(lat, lon), …] — start ucundan başlar
#: `length_nm`: geodezik uzunluk
#: `segments`: zincir sırasında [(row_id, uuid), …]
class Portion:
    __slots__ = ("coords", "length_nm", "segments")

    def __init__(self, coords, length_nm, segments):
        self.coords = coords
        self.length_nm = length_nm
        self.segments = segments

    @property
    def row_ids(self):
        return [s[0] for s in self.segments]

    @property
    def uuids(self):
        return [s[1] for s in self.segments]


class Ambiguous(Exception):
    """Aynı uzunlukta birden fazla yol var — seçim yapılmaz."""


def _graph(segments):
    """uuid → [(komşu uuid, segment indeksi, ters mi)] komşuluk sözlüğü."""
    adj = {}
    for i, seg in enumerate(segments):
        start, end = seg["start_uuid"], seg["end_uuid"]
        if not (start and end):
            continue
        adj.setdefault(start, []).append((end, i, False))
        adj.setdefault(end, []).append((start, i, True))
    return adj


def _shortest(adj, start, end):
    """start → end en kısa zincir: [(segment indeksi, ters mi), …].

    Yol yoksa None döner. Aynı uzunlukta birden fazla yol varsa `Ambiguous`.
    """
    if start == end:
        return []
    if start not in adj:
        return None

    # BFS: her düğüme kaç FARKLI en kısa yolla ulaşıldığını da sayar.
    dist = {start: 0}
    yol_sayisi = {start: 1}
    onceki = {start: None}
    q = deque([start])
    while q:
        node = q.popleft()
        for nxt, idx, ters in adj.get(node, []):
            if nxt not in dist:
                dist[nxt] = dist[node] + 1
                yol_sayisi[nxt] = yol_sayisi[node]
                onceki[nxt] = (node, idx, ters)
                q.append(nxt)
            elif dist[nxt] == dist[node] + 1:
                # Aynı uzunlukta ikinci bir yol bulundu.
                yol_sayisi[nxt] += yol_sayisi[node]

    if end not in dist:
        return None
    if yol_sayisi[end] > 1:
        raise Ambiguous(f"{yol_sayisi[end]} esit uzunlukta yol")

    zincir = []
    node = end
    while onceki[node] is not None:
        prev, idx, ters = onceki[node]
        zincir.append((idx, ters))
        node = prev
    zincir.reverse()
    return zincir


def _birlestir(segments, zincir):
    """Zincirdeki segmentleri yönlerini düzelterek tek koordinat dizisine ekler."""
    coords = []
    kullanilan = []
    for idx, ters in zincir:
        seg = segments[idx]
        pos = seg["positions"]
        if not pos:
            return None, None
        if ters:
            pos = pos[::-1]
        # Ek noktasındaki tekrar eden düğüm atlanır.
        coords.extend(pos if not coords else pos[1:])
        kullanilan.append((seg["row_id"], seg["uuid"]))
    return coords, kullanilan


def length_nm(coords):
    """Koordinat dizisinin geodezik uzunluğu (NM)."""
    total = 0.0
    for (lat1, lon1), (lat2, lon2) in zip(coords, coords[1:]):
        total += _GEOD.inv(lon1, lat1, lon2, lat2)[2]
    return total / 1852.0


def build(segments, start_uuid, end_uuid, intermediate_uuid=None):
    """Rota aralığının çizgisini kurar.

    `segments`: aynı Route'a ait
        `[{"start_uuid", "end_uuid", "positions", "row_id", "uuid"}, …]`

    Döner: `Portion` — kurulamazsa `None`, belirsizse `Ambiguous` fırlatır.
    """
    if not (segments and start_uuid and end_uuid):
        return None

    adj = _graph(segments)
    if intermediate_uuid:
        # AIXM'in ara noktası dallanma netleştiricisidir: yol ONUN ÜZERİNDEN
        # geçmek zorundadır. Yok sayılırsa dallanan bir rotada yanlış kol
        # çizilir — bu alanın varlık sebebi tam olarak budur.
        ilk = _shortest(adj, start_uuid, intermediate_uuid)
        if ilk is None:
            return None
        ikinci = _shortest(adj, intermediate_uuid, end_uuid)
        if ikinci is None:
            return None
        zincir = ilk + ikinci
    else:
        zincir = _shortest(adj, start_uuid, end_uuid)
        if zincir is None:
            return None

    coords, kullanilan = _birlestir(segments, zincir)
    if not coords or len(coords) < 2:
        return None
    return Portion(coords, length_nm(coords), kullanilan)
