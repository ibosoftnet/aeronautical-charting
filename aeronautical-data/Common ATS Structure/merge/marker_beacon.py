"""Marker beacon eşleştirme — Jeppesen `marker` verisini LOC/ILS'e bağlar.

Bu modül **bu işe özgüdür**: config'deki `special_sources` girdisinde
`marker_beacon_matching: true` olduğunda devreye girer, aksi halde hiç
çalışmaz.

## Neden ayrı bir modül

Bir marker beacon tek başına anlamlı değildir; ilişkili olduğu LOC/ILS
navaid'inin `navaidComponent`'i olarak yer alması gerekir. Hangi LOC/ILS'e
bağlanacağı ancak **birleşik** veride bilinebilir — marker Jeppesen'den,
hedef navaid EAD-SDO'dan gelir. Bu yüzden Jeppesen üreticisi marker'ı AIXM'e
yazmaz, yalnızca kimlikleriyle birlikte `jeppesen-marker.json`'a döker;
eşleştirme ve AIXM üretimi burada yapılır.

## Eşleştirme kuralı

`designator + yakınlık`. "Ülke kodu" kullanılamıyor: birleşik verideki 550
LOC/ILS navaid'inin 548'inde `codeICAOCountry` boş (EAD bu alanı hiç
doldurmuyor). Yakınlık bu boşluğu kapatıyor ve ölçümle doğrulandı:

  * eşleşen marker mesafeleri 1,41 – 6,89 NM (medyan 2,62) — outer/middle
    marker için tam beklenen aralık
  * eşik içinde **birden fazla aday olan hiç yok**
  * aynı ident'i taşıyıp uzakta olan 88 yanlış aday doğru şekilde eleniyor
  * eşik 15 / 25 / 40 NM → sonuç hep aynı; eşik kısıtlayıcı değil

Eşleşemeyen marker **yazılmaz** (kullanıcı kararı) ve loglanır. Ayrı `MKR`
navaid üretilmez: veride tek bir enroute marker (FAN/Z) yok, 913'ün tamamı
ILS yaklaşma marker'ı — "enroute" demek uydurma sınıflandırma olurdu.

## XSD sırası (uyulması zorunlu)

  * `NavaidPropertyGroup`: … touchDownLiftOff → **navaidEquipment** → location …
  * `NavaidComponentType`: collocationGroup → **markerPosition** →
    providesNavigableLocation → annotation → theNavaidEquipment
  * `MarkerBeaconPropertyGroup`: class → frequency → **axisBearing** →
    auralMorseCode
"""

import json

from lxml import etree

from .aixm_reader import A, G, NS_AIXM, NS_GML, NS_MESSAGE, NS_XLINK, X

SRS_NAME = "urn:ogc:def:crs:EPSG::4326"

NSMAP = {"message": NS_MESSAGE, "aixm": NS_AIXM,
         "gml": NS_GML, "xlink": NS_XLINK}

#: Marker'ın bağlanabileceği Navaid tipleri (config'den geçersiz kılınabilir).
DEFAULT_TARGET_TYPES = ("ILS", "ILS_DME", "LOC", "LOC_DME")

#: `NavaidPropertyGroup` içinde `navaidEquipment`'tan SONRA gelen elemanlar.
#: Yeni bileşen bunlardan ilkinin ÖNÜNE eklenir; hiçbiri yoksa sona eklenir.
_AFTER_NAVAID_EQUIPMENT = ("location", "runwayDirection", "servedAirport",
                           "availability", "annotation", "codeICAOCountry",
                           "extension")


def is_enabled(source: dict) -> bool:
    return bool(source.get("enabled", True)
                and source.get("marker_beacon_matching"))


class MarkerBeaconMatcher:
    """Marker'ları LOC/ILS navaid'lerine bağlar.

    Kullanım sırası (`build_common_ats.run_merge` içinde):
      1. ana kaynak ön taraması sırasında `index_target(...)`
      2. ön tarama bitince `match(log)`
      3. ana kaynak yazımında, her üye için `inject(member, gml_id)`
      4. ana kaynaklar bitince `iter_features()`
    """

    def __init__(self, source: dict, root, geod):
        self.name = source.get("name", "jeppesen-mkr")
        self.geod = geod
        self.threshold_nm = float(source.get("match_by_proximity_nm") or 0)
        self.target_types = frozenset(
            source.get("target_navaid_types") or DEFAULT_TARGET_TYPES)

        path = root / source["file"]
        self.markers = json.loads(path.read_text(encoding="utf-8")) \
            if path.exists() else []
        self.missing_file = not path.exists()

        # designator → [(gml_id, uuid, (lat, lon))]
        self._targets: dict = {}
        # hedef navaid gml_id → [marker kaydı, …]
        self.pending: dict = {}
        self.matched = 0
        self.unmatched = 0
        self.ambiguous = 0

    # ── 1. ana kaynak ön taraması ───────────────────────────────────────────

    def index_target(self, info: dict, fields: dict) -> None:
        """Ana kaynak taranırken çağrılır; uygun Navaid'leri toplar."""
        if fields.get("layer") != "navaids":
            return
        if info.get("type") not in self.target_types:
            return
        designator = fields.get("designator")
        position = info.get("position")
        if not (designator and position and info.get("uuid")):
            return
        self._targets.setdefault(designator, []).append(
            (info["gml_id"], info["uuid"], position))

    # ── 2. eşleştirme ───────────────────────────────────────────────────────

    def match(self, log=None) -> None:
        """Her marker için tek adaylı yakınlık eşleşmesi arar."""
        if self.missing_file:
            if log:
                log.error("2A", "navaidComponents", self.name, "file",
                          "-", "marker_yan_dosyasi_yok")
            return

        for marker in self.markers:
            candidates = self._targets.get(marker["ident"], [])
            near = []
            for gml_id, uuid_value, (lat, lon) in candidates:
                _, _, metre = self.geod.inv(
                    marker["lon"], marker["lat"], lon, lat)
                if metre / 1852.0 <= self.threshold_nm:
                    near.append((gml_id, uuid_value))

            if len(near) == 1:
                self.pending.setdefault(near[0][0], []).append(marker)
                marker["_navaid_uuid"] = near[0][1]
                self.matched += 1
            elif len(near) > 1:
                # Yanlış tesise bağlamak sessiz veri hatası olur — seçim yapılmaz.
                self.ambiguous += 1
                if log:
                    log.warning("2A", "navaidComponents",
                                marker["equipment_gml_id"], "ident",
                                f'{marker["ident"]} ({len(near)} aday '
                                f'{self.threshold_nm} NM icinde)',
                                "marker_yakinlik_esiginde_birden_fazla_aday")
            else:
                self.unmatched += 1
                if log:
                    log.warning("2A", "navaidComponents",
                                marker["equipment_gml_id"], "ident",
                                f'{marker["ident"]}/{marker["region"]}',
                                "marker_ebeveyn_loc_ils_bulunamadi")

    # ── 3. hedef Navaid'e bileşen enjeksiyonu ───────────────────────────────

    def inject(self, member, gml_id: str) -> int:
        """Eşleşen Navaid'e `navaidEquipment/NavaidComponent` ekler.

        XSD sırası korunur: `navaidEquipment`, `location`'dan ÖNCE gelmelidir.
        Yeni eleman, kendisinden sonra gelmesi gereken ilk elemanın önüne
        yerleştirilir.
        """
        markers = self.pending.get(gml_id)
        if not markers:
            return 0

        ts = member.find(f".//{A}NavaidTimeSlice")
        if ts is None:
            return 0

        anchor = None
        for name in _AFTER_NAVAID_EQUIPMENT:
            found = ts.find(A + name)
            if found is not None:
                anchor = found
                break

        for marker in markers:
            holder = etree.Element(A + "navaidEquipment")
            component = etree.SubElement(holder, A + "NavaidComponent")
            component.set(
                G + "id", marker["equipment_gml_id"] + "_NC")
            # markerPosition, theNavaidEquipment'tan ÖNCE (XSD sırası)
            position = etree.SubElement(component, A + "markerPosition")
            position.text = marker["markerPosition"]
            link = etree.SubElement(component, A + "theNavaidEquipment")
            link.set(X + "href", "urn:uuid:" + marker["equipment_uuid"])

            if anchor is not None:
                anchor.addprevious(holder)
            else:
                ts.append(holder)
        return len(markers)

    # ── 4. MarkerBeacon feature'ları ────────────────────────────────────────

    def iter_features(self, log=None):
        """Eşleşen her marker için bir `hasMember`/`MarkerBeacon` üretir."""
        for markers in self.pending.values():
            for marker in markers:
                yield marker, self._build_feature(marker)

    def _build_feature(self, marker):
        gml_id = marker["equipment_gml_id"]
        member = etree.Element(NSMAP and f"{{{NS_MESSAGE}}}hasMember",
                               nsmap=NSMAP)
        feature = etree.SubElement(member, A + "MarkerBeacon")
        feature.set(G + "id", gml_id)

        identifier = etree.SubElement(feature, G + "identifier")
        identifier.set("codeSpace", "urn:uuid:")
        identifier.text = marker["equipment_uuid"]

        holder = etree.SubElement(feature, A + "timeSlice")
        ts = etree.SubElement(holder, A + "MarkerBeaconTimeSlice")
        ts.set(G + "id", gml_id + "_TS")

        # gml:validTime her TimeSlice'ta ZORUNLUDUR.
        self._write_valid_time(ts, gml_id)
        _text(ts, "interpretation", "BASELINE")
        _text(ts, "sequenceNumber", "1")
        _text(ts, "correctionNumber", "0")

        # NavaidEquipmentPropertyGroup: designator … location …
        _text(ts, "designator", marker["ident"])
        self._write_location(ts, gml_id, marker)

        # MarkerBeaconPropertyGroup XSD sırası:
        #   class → frequency → axisBearing → auralMorseCode
        # `frequency` kaynakta yoktur, ICAO Annex 10 gereği 75 MHz sabiti
        # olarak üreticide atanır. `class` ve `auralMorseCode` hâlâ yok ve
        # uydurulmaz (bkz. Jeppesen_to_AIXM_Mapping.md).
        if marker.get("frequency") is not None:
            frequency = _text(ts, "frequency", marker["frequency"])
            frequency.set("uom", marker.get("frequencyUom") or "MHZ")
        if marker.get("axisBearing") is not None:
            _text(ts, "axisBearing", marker["axisBearing"])
        return member

    @staticmethod
    def _write_valid_time(ts, gml_id):
        """`gml:validTime` — TimeSlice'ta ZORUNLU.

        `beginPosition` BOŞ bırakılır (`indeterminatePosition="unknown"`):
        Jeppesen kayıtlarında feature başına yürürlük tarihi yok. `data.json`
        AIRAC effectivity'si veri setinin geçerliliğidir, feature'ın kendi
        yürürlüğü değil — onu buraya yazmak uydurma bir iddia olurdu
        (kullanıcı kararı; NDB feature'ları da aynı şekilde).
        """
        valid = etree.SubElement(ts, G + "validTime")
        period = etree.SubElement(valid, G + "TimePeriod")
        period.set(G + "id", gml_id + "_TP")
        begin = etree.SubElement(period, G + "beginPosition")
        begin.set("indeterminatePosition", "unknown")
        end = etree.SubElement(period, G + "endPosition")
        end.set("indeterminatePosition", "unknown")

    @staticmethod
    def _write_location(ts, gml_id, marker):
        location = etree.SubElement(ts, A + "location")
        point = etree.SubElement(location, A + "ElevatedPoint")
        point.set(G + "id", gml_id + "_EP")
        point.set("srsName", SRS_NAME)
        pos = etree.SubElement(point, G + "pos")
        pos.text = f'{marker["lat"]} {marker["lon"]}'
        if marker.get("elevation") is not None:
            elevation = etree.SubElement(point, A + "elevation")
            elevation.set("uom", marker.get("elevationUom") or "FT")
            elevation.text = str(marker["elevation"])

    def summary(self) -> str:
        return (f"eslesen={self.matched} eslesemeyen={self.unmatched} "
                f"belirsiz={self.ambiguous}")


def _text(parent, name, value):
    el = etree.SubElement(parent, A + name)
    el.text = str(value)
    return el
