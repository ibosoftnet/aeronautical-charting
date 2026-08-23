"""AŞAMA 2B — `navaidLabeling_*`: harita etiketi için türetilmiş alanlar.

Bir navaid kutusu çizilirken hangi öğelerin gösterileceği navaid **tipine**
göre değişir: NDB'de kanal yoktur, DME yüksekliği yalnızca mesafe ekipmanı
taşıyan tiplerde anlamlıdır, MLS'te kanal etiketlenir ama frekans etiketlenmez.

Bu bilgi AIXM'de **yoktur** — AIXM neyin var olduğunu söyler, neyin
etiketleneceğini söylemez. Ayrıca AIXM'de frekans ve kanal Navaid feature'ında
değil **bağlı ekipmanda** durur (`NavaidPropertyGroup`'ta `frequency`/`channel`
yok), oysa harita etiketi navaid düzeyinde çizilir. Bu yüzden modül iki geçişli
çalışır: önce `navaidComponents`, sonra `navaids` (bileşenlerin çözülmüş
değerlerini devralır).

`atsStatus_*` ile aynı desen: tablolar yazıldıktan SONRA, `schema.finalize`'dan
ÖNCE çalışır (yeni sütunların index'i orada kuruluyor).
"""

import csv
from pathlib import Path
from gpkg import schema

#: `UomFrequencyType` enum'unun tamamı (AIXM_DataTypes.xsd) → MHz katsayısı.
#: Listede olmayan/eksik birim **tahmin edilmez**: loglanır, alan NULL kalır.
_TO_MHZ = {"HZ": 1e-6, "KHZ": 1e-3, "MHZ": 1.0, "GHZ": 1e3}

#: Etiket frekansının yazılacağı birim. NDB kHz, diğer her tip MHz
#: (kullanıcı kararı). Navaid tipi ve ekipman tipi için aynı ad kullanılıyor.
_KHZ_TYPES = frozenset({"NDB"})

# ── Geçerlilik tabloları ────────────────────────────────────────────────────
# ELLE KÜRATÖRLÜ: bu bir harita etiketleme kararıdır, şema kararı değil ve
# XSD'den türetilemez. İki yönde de ayrışır:
#   * `MarkerBeaconPropertyGroup` frekans TANIMLAR ama MKR'de frekans
#     etiketlenmez (kullanıcı kararı).
#   * `AzimuthPropertyGroup` frekans TANIMLAMAZ; MLS'te yalnızca kanal
#     etiketlenir.
#
# Bayraklar TİP BAZLIDIR: alan o tip için geçerliyse değer boş olsa bile 1
# kalır ("tanımlı fakat boşsa true").

#: `navaids_type` → (haveFreq, haveChannel, haveDmeElev)
NAVAID_LABELS = {
    "VOR":     (1, 1, 0),   "DME":     (1, 1, 1),
    "TACAN":   (1, 1, 0),   "ILS":     (1, 1, 0),
    "ILS_DME": (1, 1, 0),   "VORTAC":  (1, 1, 0),
    "VOR_DME": (1, 1, 1),   "LOC":     (1, 1, 0),
    "LOC_DME": (1, 1, 0),   "SDF":     (1, 1, 0),
    "MLS":     (0, 1, 0),   "MLS_DME": (0, 1, 0),
    "NDB":     (1, 0, 0),
}
# Tabloda olmayan tipler (MKR, NDB_DME, NDB_MKR, TLS, DF) ve `type`'ı NULL
# olan kayıtlar → üç bayrak da 0.

#: `navaidComponents_equipmentType` → (haveFreq, haveChannel, haveDmeElev)
EQUIPMENT_LABELS = {
    "VOR": (1, 1, 0), "DME": (1, 1, 1), "TACAN": (1, 1, 0),
    "Localizer": (1, 1, 0), "Glidepath": (1, 1, 0), "SDF": (1, 1, 0),
    "NDB": (1, 0, 0),
    "MarkerBeacon": (0, 0, 0),   # AIXM'de frequency var, etiketlenmiyor
    "Azimuth": (0, 1, 0),        # channel kendi alanı, AIXM'de frequency yok
    "Elevation": (0, 0, 0),      # AIXM'de ne channel ne frequency
}
# DirectionFinder → hepsi 0 (`DirectionFinderPropertyGroup`: doppler,
# informationProvision — frekans/kanal yok).

#: Kendi `frequency` alanını taşıyan ekipmanlar. Diğerlerinde (DME/TACAN)
#: frekans yalnızca eşleştirme tablosundan gelir.
_OWN_FREQUENCY = frozenset({"VOR", "Localizer", "Glidepath", "NDB", "SDF"})

#: Kendi `channel` alanını taşıyan ekipmanlar.
_OWN_CHANNEL = frozenset({"DME", "TACAN", "Azimuth"})

#: Navaid tipi → etiket frekansını sağlayan ekipman tipi.
FREQ_SOURCE = {
    "VOR": "VOR", "VOR_DME": "VOR", "VORTAC": "VOR",
    "DME": "DME", "TACAN": "TACAN",
    "ILS": "Localizer", "ILS_DME": "Localizer",
    "LOC": "Localizer", "LOC_DME": "Localizer",
    "SDF": "SDF", "NDB": "NDB",
}

#: Navaid tipi → etiket kanalını sağlayan ekipman tipi. Burada olmayan ama
#: `haveChannel=1` olan tipler (VOR, ILS, LOC, SDF) kanalı frekanstan
#: eşleştirir.
CHANNEL_SOURCE = {
    "VOR_DME": "DME", "VORTAC": "TACAN", "DME": "DME", "TACAN": "TACAN",
    "ILS_DME": "DME", "LOC_DME": "DME",
    "MLS": "Azimuth", "MLS_DME": "Azimuth",
}


def _parse_ids(value):
    """`"550,2181"` → `[550, 2181]`. Bos/None → bos liste."""
    if not value:
        return []
    out = []
    for part in str(value).split(schema.LIST_SEPARATOR):
        part = part.strip()
        if part.isdigit():
            out.append(int(part))
    return out


def _key(value) -> str:
    """Frekans arama anahtarı — kayan nokta gürültüsünü siler.

    Birim çevrimi (`332.3 KHZ → 0.3323 MHZ`) ve CSV ayrıştırması aynı sayıyı
    farklı ikili gösterimlerle üretebilir; sabit basamaklı dize her ikisini de
    aynı anahtara indirger.
    """
    return f"{round(float(value), 9):.9f}"


def _convert(value, from_uom, to_uom):
    """Frekansı birimler arası çevirir. Tanınmayan birimde None döner.

    Doğrudan çevrim yapılır (MHz üzerinden gidilmez): NDB'nin `KHZ → KHZ`
    yolu böylece birebir kimliktir, `356 → 0.356 → 355.99999999999994`
    yuvarlama zinciri hiç oluşmaz.
    """
    if value is None:
        return None
    src = _TO_MHZ.get((from_uom or "").upper())
    dst = _TO_MHZ.get((to_uom or "").upper())
    if src is None or dst is None:
        return None
    return round(float(value) * (src / dst), 9)


class Pairing:
    """`frequency-pairing.csv` — ICAO frekans/kanal eşleştirme tablosu.

    Sütun indeksleri (başlık satırından doğrulandı):
      0 = DME channel number, 1 = VHF frequency MHz,
      2 = MLS angle frequency MHz, 3 = MLS channel number,
      10 = GP Frequency MHz, 11 = LOC Sequence Number

    > Legacy `mapping.py:load_frequency_pairing` GP frekansını `parts[11]`'den
    > okuyor; orası "LOC Sequence Number" (1–20 arası sıra numaraları).
    > Doğrusu **index 10**. Ölçülen etki: `[11]` ile Glidepath eşleşmesi
    > 0/524, `[10]` ile 521/524.

    Tablodaki tüm frekanslar **MHz**'dir; arama yapmadan önce değer MHz'e
    çevrilmelidir. `col2` (MLS angle frequency) okunmaz — MLS'te frekans
    etiketlenmiyor.
    """

    def __init__(self, path: Path):
        self.vhf_to_channel: dict[str, str] = {}
        self.channel_to_vhf: dict[str, float] = {}
        self.gp_to_channel: dict[str, str] = {}
        self.dme_to_mls: dict[str, str] = {}

        with open(path, "r", encoding="utf-8", newline="") as fh:
            for row in csv.reader(fh):
                if not row:
                    continue
                channel = row[0].strip().upper()
                if not channel or channel.startswith("DME CHANNEL"):
                    continue

                def cell(index):
                    return row[index].strip() if len(row) > index else ""

                vhf, mls_channel, gp = cell(1), cell(3), cell(10)
                if vhf:
                    self.vhf_to_channel[_key(vhf)] = channel
                    self.channel_to_vhf[channel] = float(vhf)
                if gp:
                    self.gp_to_channel[_key(gp)] = channel
                if mls_channel:
                    self.dme_to_mls[channel] = mls_channel


def _channel_from_frequency(pairing, kind, mhz):
    """Frekanstan kanal. Glidepath GP sütununu, diğerleri VHF sütununu kullanır."""
    if mhz is None:
        return None
    table = pairing.gp_to_channel if kind == "Glidepath" else pairing.vhf_to_channel
    return table.get(_key(mhz))


def compute(con, log=None, csv_path=None):
    """`navaids` ve `navaidComponents` için `navaidLabeling_*` alanlarını türetir."""
    pairing = Pairing(csv_path or Path(__file__).with_name("frequency-pairing.csv"))
    cur = con.cursor()
    counts = {"bilesen": 0, "navaid": 0, "dme_yukseklik_yok": 0}

    def note(layer, gml_id, field, value, violation):
        if log is not None:
            log.warning("2B", layer, gml_id, field, value, violation)

    def missing_elevation():
        counts["dme_yukseklik_yok"] += 1
        if log is not None:
            # ~4.500 satırı ilgilendiriyor; `errored-features.csv`'yi
            # şişirmemek için satır yazılmaz, yalnızca sayılır.
            log.info_count("dme_yuksekligi_kaynakta_yok")

    # ── A geçişi: navaidComponents ──────────────────────────────────────────
    # `frequency`/`channel` artik alt-ture ozgu sutunlarda duruyor
    # (`navaidComponents_<AltTur>_frequency`). Bir satirda yalnizca KENDI
    # alt-turunun sutunu dolu oldugu icin COALESCE ile tek degere indirgenir —
    # sutun listesi `schema.EQUIPMENT_SUBTYPE_FIELDS`'ten turetilir, elle
    # yazilmaz.
    def _coalesce(field):
        cols = [schema.equipment_column(sub, field)
                for sub, fields in schema.EQUIPMENT_SUBTYPE_FIELDS.items()
                if field.removesuffix("Uom") in fields]
        return f'COALESCE({", ".join(chr(34) + c + chr(34) for c in cols)})' \
            if cols else 'NULL'

    cur.execute(
        'SELECT id, associatedNavaid, navaidComponents_equipmentType,'
        ' navaidComponents_designator, navaidComponents_name,'
        f' {_coalesce("frequency")}, {_coalesce("frequencyUom")},'
        f' {_coalesce("channel")},'
        ' navaidComponents_locationElevation, navaidComponents_locationElevationUom,'
        ' gmlId FROM navaidComponents')

    payload, by_navaid = [], {}
    for (row_id, navaid_ids, kind, designator, name, frequency, frequency_uom,
         channel, elevation, elevation_uom, gml_id) in cur.fetchall():
        have_freq, have_channel, have_dme_elev = EQUIPMENT_LABELS.get(kind, (0, 0, 0))

        # -- frekans: kendi alanı, ya da (DME/TACAN) kanaldan eşleştirme --
        freq_value = freq_uom = freq_mhz = None
        if have_freq:
            if kind in _OWN_FREQUENCY:
                if frequency is None:
                    note("navaidComponents", gml_id, "navaidLabeling_freq",
                         None, "frekans_kaynakta_yok")
                else:
                    freq_mhz = _convert(frequency, frequency_uom, "MHZ")
                    if freq_mhz is None:
                        note("navaidComponents", gml_id, "navaidLabeling_freq",
                             frequency_uom, "frekans_birimi_taninmiyor")
                    else:
                        freq_value, freq_uom = frequency, frequency_uom
            elif channel:
                paired = pairing.channel_to_vhf.get(channel.strip().upper())
                if paired is None:
                    note("navaidComponents", gml_id, "navaidLabeling_freq",
                         channel, "frekans_eslestirmesi_bulunamadi")
                else:
                    freq_value, freq_uom, freq_mhz = paired, "MHZ", paired
            else:
                # DME/TACAN'in AIXM'de `frequency` alani yok; kanali da yoksa
                # eslestirmeye girecek girdi hic yok demektir.
                note("navaidComponents", gml_id, "navaidLabeling_freq",
                     None, "frekans_icin_kanal_yok")

        # -- kanal: kendi alanı, ya da frekanstan eşleştirme --
        channel_out = None
        if have_channel:
            if kind in _OWN_CHANNEL:
                channel_out = channel
                if channel_out is None:
                    note("navaidComponents", gml_id, "navaidLabeling_channel",
                         None, "kanal_kaynakta_yok")
            else:
                channel_out = _channel_from_frequency(pairing, kind, freq_mhz)
                if channel_out is None and freq_mhz is not None:
                    note("navaidComponents", gml_id, "navaidLabeling_channel",
                         freq_mhz, "kanal_eslestirmesi_bulunamadi")

        # -- DME yüksekliği: kendi konum yüksekliği, birimi ÇEVRİLMEZ --
        dme_elev = dme_elev_uom = None
        if have_dme_elev:
            if elevation is None:
                missing_elevation()
            else:
                dme_elev, dme_elev_uom = elevation, elevation_uom

        target_uom = "KHZ" if kind in _KHZ_TYPES else "MHZ"
        out_freq = _convert(freq_value, freq_uom, target_uom)

        payload.append((have_freq, have_channel, have_dme_elev, name, designator,
                        out_freq, target_uom if out_freq is not None else None,
                        channel_out, dme_elev, dme_elev_uom, row_id))
        counts["bilesen"] += 1

        # `associatedNavaid` artik LISTE: bir ekipman birden fazla Navaid
        # tarafindan paylasilabiliyor (olculdu: 275 ekipman 2-7 navaid'e ait).
        # Etiket degeri ebeveynlerin HEPSINE tasinir — onceki tek-FK hali
        # bunlardan yalnizca birine tasiyordu.
        for parent in _parse_ids(navaid_ids):
            by_navaid.setdefault(parent, {})[kind] = {
                "freq_value": freq_value, "freq_uom": freq_uom, "freq_mhz": freq_mhz,
                "channel": channel_out,
                "elevation": elevation, "elevation_uom": elevation_uom,
            }

    _write(cur, "navaidComponents", payload)

    # ── B geçişi: navaids (bileşenlerin çözülmüş değerlerini devralır) ──────
    cur.execute('SELECT id, navaids_type, navaids_designator, navaids_name, gmlId'
                ' FROM navaids')

    payload = []
    for row_id, nav_type, designator, name, gml_id in cur.fetchall():
        have_freq, have_channel, have_dme_elev = NAVAID_LABELS.get(nav_type, (0, 0, 0))
        components = by_navaid.get(row_id, {})

        freq_value = freq_uom = freq_mhz = None
        if have_freq:
            source = components.get(FREQ_SOURCE.get(nav_type))
            if source is not None:
                freq_value = source["freq_value"]
                freq_uom = source["freq_uom"]
                freq_mhz = source["freq_mhz"]
            else:
                # Frekansi saglamasi gereken ekipman bu navaid'e hic bagli
                # degil. Bilesen duzeyinde loglanamaz (ortada kayit yok), bu
                # yuzden yalnizca burada gorunur.
                note("navaids", gml_id, "navaidLabeling_freq",
                     FREQ_SOURCE.get(nav_type), "frekans_bileseni_yok")

        channel_out = None
        if have_channel:
            source = components.get(CHANNEL_SOURCE.get(nav_type))
            if source is not None:
                channel_out = source["channel"]
            if channel_out is None:
                if nav_type in ("MLS", "MLS_DME"):
                    # Azimuth bileşeni yoksa MLS kanalı DME kanalından
                    # türetilir — CSV'de ikisi zaten aynı satırdadır.
                    dme = components.get("DME")
                    if dme is not None and dme["channel"]:
                        channel_out = pairing.dme_to_mls.get(
                            dme["channel"].strip().upper())
                else:
                    channel_out = _channel_from_frequency(pairing, None, freq_mhz)
            if channel_out is None:
                note("navaids", gml_id, "navaidLabeling_channel",
                     freq_mhz,
                     "kanal_eslestirmesi_bulunamadi" if freq_mhz is not None
                     else "kanal_kaynagi_yok")

        dme_elev = dme_elev_uom = None
        if have_dme_elev:
            dme = components.get("DME")
            if dme is not None and dme["elevation"] is not None:
                dme_elev, dme_elev_uom = dme["elevation"], dme["elevation_uom"]
            else:
                missing_elevation()

        target_uom = "KHZ" if nav_type in _KHZ_TYPES else "MHZ"
        out_freq = _convert(freq_value, freq_uom, target_uom)

        payload.append((have_freq, have_channel, have_dme_elev, name, designator,
                        out_freq, target_uom if out_freq is not None else None,
                        channel_out, dme_elev, dme_elev_uom, row_id))
        counts["navaid"] += 1

    _write(cur, "navaids", payload)
    con.commit()

    print(f"    navaids={counts['navaid']} navaidComponents={counts['bilesen']} "
          f"(dme yuksekligi kaynakta yok={counts['dme_yukseklik_yok']})")
    return counts


def _write(cur, layer, payload):
    cur.executemany(
        f'UPDATE "{layer}" SET'
        ' "navaidLabeling_haveFreq"=?, "navaidLabeling_haveChannel"=?,'
        ' "navaidLabeling_haveDmeElev"=?, "navaidLabeling_name"=?,'
        ' "navaidLabeling_ident"=?, "navaidLabeling_freq"=?,'
        ' "navaidLabeling_freqUom"=?, "navaidLabeling_channel"=?,'
        ' "navaidLabeling_dmeElev"=?, "navaidLabeling_dmeElevUom"=?'
        ' WHERE id=?', payload)
