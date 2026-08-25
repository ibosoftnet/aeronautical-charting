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
import json
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
# XSD'den türetilemez. Örnek: `AzimuthPropertyGroup` frekans TANIMLAMAZ, bu
# yüzden MLS'te yalnızca kanal etiketlenir.
#
# Bu tablolar artık SÜTUN ÜRETMEZ — `haveFreq`/`haveChannel`/`haveDmeElev`
# bayrakları kullanıcı kararıyla kaldırıldı (alan geçerli değilse değer zaten
# NULL kalıyor, ayrı bir bayrak bilgi katmıyordu). Tablolar İÇERİDE kapı
# görevini sürdürür: bir alanın o tip için hesaplanıp hesaplanmayacağını
# bunlar belirler. Kaldırılsalardı örneğin MLS Azimuth'a kanal, NDB'ye kanal
# gibi anlamsız değerler sızardı.

#: `navaids_type` → (haveFreq, haveChannel, haveDmeElev)
NAVAID_LABELS = {
    "VOR":     (1, 1, 0),   "DME":     (1, 1, 1),
    "TACAN":   (1, 1, 0),   "ILS":     (1, 1, 0),
    "ILS_DME": (1, 1, 0),   "VORTAC":  (1, 1, 0),
    "VOR_DME": (1, 1, 1),   "LOC":     (1, 1, 0),
    "LOC_DME": (1, 1, 0),   "SDF":     (1, 1, 0),
    "MLS":     (0, 1, 0),   "MLS_DME": (1, 1, 0),
    "NDB":     (1, 0, 0),   "MKR":     (1, 0, 0),
    # NDB_DME ve NDB_MKR birer NDB sayilir: NDB frekansi etiketlenir, bagli
    # DME'nin kanali/frekansi onemsizdir (kullanici karari). Bunlar bir sure
    # tabloda hic yoktu ve sessizce (0,0,0)'a dusuyorlardi — "bu bir NDB'dir"
    # deyip NDB frekansini gizliyorlardi.
    "NDB_DME": (1, 0, 0),   "NDB_MKR": (1, 0, 0),
    # Asagidakiler ACIKCA kapalidir; varsayilana dusmesinler diye yazildilar.
    # Ikisinde de AIXM'de frekans YOKTUR:
    #   DF  -> DirectionFinderPropertyGroup: doppler, informationProvision
    #   TLS -> karsilik gelen bir ekipman alt-turu tanimli degil
    "TLS":     (0, 0, 0),   "DF":      (0, 0, 0),
}
# Tabloda olmayan tipler (MKR, NDB_DME, NDB_MKR, TLS, DF) ve `type`'ı NULL
# olan kayıtlar → üç bayrak da 0.

#: `navaidComponents_equipmentType` → (haveFreq, haveChannel, haveDmeElev)
EQUIPMENT_LABELS = {
    "VOR": (1, 1, 0), "DME": (1, 1, 1), "TACAN": (1, 1, 0),
    "Localizer": (1, 1, 0), "Glidepath": (1, 1, 0), "SDF": (1, 1, 0),
    "NDB": (1, 0, 0),
    "MarkerBeacon": (1, 0, 0),   # 75 MHz sabiti yaziliyor; kanali yok
    # MLS: ikisi de AIXM'de frekans TASIMAZ, degerler MLS kanalindan turetilir.
    "Azimuth": (1, 1, 0),        # kendi channel'indan
    "Elevation": (1, 1, 0),      # kardes Azimuth'un channel'indan (C gecisi)
}
# DirectionFinder → hepsi 0 (`DirectionFinderPropertyGroup`: doppler,
# informationProvision — frekans/kanal yok).

#: Kendi `frequency` alanını taşıyan ekipmanlar. Diğerlerinde (DME/TACAN)
#: frekans yalnızca eşleştirme tablosundan gelir.
_OWN_FREQUENCY = frozenset({"VOR", "Localizer", "Glidepath", "NDB", "SDF",
                            "MarkerBeacon"})

#: Kendi `channel` alanını taşıyan ekipmanlar.
_OWN_CHANNEL = frozenset({"DME", "TACAN", "Azimuth"})

#: Navaid tipi → etiket frekansını sağlayan ekipman tipi.
FREQ_SOURCE = {
    "VOR": "VOR", "VOR_DME": "VOR", "VORTAC": "VOR",
    "DME": "DME", "TACAN": "TACAN",
    "ILS": "Localizer", "ILS_DME": "Localizer",
    "LOC": "Localizer", "LOC_DME": "Localizer",
    "SDF": "SDF", "NDB": "NDB", "MKR": "MarkerBeacon",
    "NDB_DME": "NDB", "NDB_MKR": "NDB",
}

#: Navaid tipi → etiket kanalını sağlayan ekipman tipi. Burada olmayan ama
#: `haveChannel=1` olan tipler (VOR, ILS, LOC, SDF) kanalı frekanstan
#: eşleştirir.
CHANNEL_SOURCE = {
    "VOR_DME": "DME", "VORTAC": "TACAN", "DME": "DME", "TACAN": "TACAN",
    "ILS_DME": "DME", "LOC_DME": "DME",
    "MLS": "Azimuth", "MLS_DME": "Azimuth",
}


# ── Tip etiketleri ──────────────────────────────────────────────────────────
# Ham AIXM enum'u haritada okunmaz (`VOR_DME`, `ILS_DME`); kartografik
# karsiligi gerekir. Elle kuratorlu — sema karari degil, harita karari.

#: `navaids_type` -> etiket metni.
NAVAID_TYPE_LABEL = {
    "VOR": "VOR",         "DME": "DME",         "NDB": "NDB",
    "TACAN": "TACAN",     "ILS": "ILS",         "ILS_DME": "ILS DME",
    "MLS": "MLS",         "MLS_DME": "MLS DME", "VORTAC": "VORTAC",
    "VOR_DME": "VOR DME", "NDB_DME": "NDB",     "TLS": "TLS",
    "LOC": "LOC",         "LOC_DME": "LOC DME", "NDB_MKR": "NDB",
    "DF": "DF",           "SDF": "SDF",
}

#: `navaidComponents_equipmentType` -> etiket metni. Ortak tipler navaid
#: tarafiyla ayni karsiligi alir; asagidakiler yalnizca ekipman duzeyinde var.
EQUIPMENT_TYPE_LABEL = {
    "VOR": "VOR", "DME": "DME", "NDB": "NDB", "TACAN": "TACAN",
    "SDF": "SDF", "DirectionFinder": "DF",
    "Glidepath": "GP", "Localizer": "LOC",
    "Elevation": "MLS ELEV", "Azimuth": "MLS AZM",
}

#: `NavaidComponent.markerPosition` -> etiket. Marker'in konumu ILS'e GORE
#: tanimlidir (marker'in kendi ozelligi degil), bu yuzden deger bilesende
#: durur — bkz. NavaidComponent.
MARKER_POSITION_LABEL = {
    "INNER": "IM", "MIDDLE": "MM", "OUTER": "OM", "BACKCOURSE": "BC MKR",
}
MARKER_FALLBACK = "MKR"     # markerPosition bos, OTHER veya taninmayan

#: NDB `class` degeri "L" ise locator'dur ve etiketi "L" olur (kullanici
#: karari). Kural BUTUN NDB tiplerinde gecerlidir: olculdu, locator'larin
#: hepsi duz `NDB` navaid'ine bagli ve veride hic `NDB_DME` yok — kurali
#: yalnizca `NDB_DME`'ye baglamak onu hic calistirmazdi.
LOCATOR_LABEL = "L"
NDB_TYPES = frozenset({"NDB", "NDB_DME", "NDB_MKR"})

_OTHER_PREFIX = "OTHER:"

#: MLS bilesenleri. Ikisi de ayni RF kanalinda zaman bolmeli yayin yapar, bu
#: yuzden ayni aci frekansini alirlar.
_MLS_EQUIPMENT = frozenset({"Azimuth", "Elevation"})

#: Degerleri KARDES bilesenden geldigi icin A gecisinde atlanan tipler; C
#: gecisinde (`_resolve_mls_elevation`) doldurulurlar. `Elevation`'in AIXM'de
#: kendi kanali yoktur.
_DEFERRED = frozenset({"Elevation"})


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
    çevrilmelidir.

    MLS sütunları **TERS yönde** okunur: yetkili kaynak MLS kanalıdır
    (`col3`), DME kanalı (`col0`) ve açı frekansı (`col2`) ondan türetilir.
    Kaldırılan `dme_to_mls` bunun tersiydi — Azimuth eksikken MLS kanalını
    DME'den *uyduruyordu* ve izinsiz bir fallback'ti; geri gelmedi.
    """

    def __init__(self, path: Path):
        self.vhf_to_channel: dict[str, str] = {}
        self.channel_to_vhf: dict[str, float] = {}
        self.gp_to_channel: dict[str, str] = {}
        self.mls_to_dme: dict[str, str] = {}
        self.mls_to_freq: dict[str, float] = {}

        with open(path, "r", encoding="utf-8", newline="") as fh:
            for row in csv.reader(fh):
                if not row:
                    continue
                channel = row[0].strip().upper()
                if not channel or channel.startswith("DME CHANNEL"):
                    continue

                def cell(index):
                    return row[index].strip() if len(row) > index else ""

                vhf, mls_freq, mls_channel, gp = (cell(1), cell(2), cell(3),
                                                  cell(10))
                if vhf:
                    self.vhf_to_channel[_key(vhf)] = channel
                    self.channel_to_vhf[channel] = float(vhf)
                if gp:
                    self.gp_to_channel[_key(gp)] = channel
                if mls_channel:
                    self.mls_to_dme[mls_channel] = channel
                    if mls_freq:
                        self.mls_to_freq[mls_channel] = float(mls_freq)


class Morse:
    """ITU-R M.1677-1 mors alfabesi — `morse-itu.json`'dan okunur.

    Alfabe koda GOMULMEZ: tablo `frequency-pairing.csv` ile ayni desende ayri
    bir veri dosyasidir. Kodlar dosyada ASCII `.`/`-` ile tutulur; goruntu
    sembollerine cevrim burada, dosyanin `symbols` alanina gore yapilir —
    boylece sembol tercihi degisirse tablo degismez.

    Bosluk oranlari standardin 2.1-2.4 maddelerinden gelir: harf ici 1 nokta,
    harf arasi 3 nokta, kelime arasi 7 nokta.
    """

    def __init__(self, path: Path):
        data = json.loads(path.read_text(encoding="utf-8"))
        self.dot = data["symbols"]["dot"]
        self.dash = data["symbols"]["dash"]
        spacing = data["spacingDots"]
        self.symbol_gap = " " * spacing["intraCharacter"]
        self.letter_gap = " " * spacing["interCharacter"]
        self.word_gap = " " * spacing["interWord"]

        # Ident'te gecebilecek her sey tek sozlukte toplanir. `prosigns`
        # alinmaz: onlar isaret ADLARIDIR, karakter degil.
        self.codes = {}
        for group in ("letters", "digits", "punctuation"):
            for char, code in data[group].items():
                if not char.startswith("_"):
                    self.codes[char] = code

    def symbols(self, code: str) -> str:
        """`".-"` -> `"· −"` — tek kod dizisini sembollere cevirir."""
        return self.symbol_gap.join(
            self.dot if ch == "." else self.dash for ch in code)

    def from_ident(self, ident: str):
        """Ident -> mors. Cevrilemeyen karakter varsa `(None, karakter)`.

        Kismi deger YAZILMAZ: tek bir karakter bile cevrilemiyorsa alanin
        tamami NULL kalir ve loglanir — yarim mors kodu yaniltici olur.
        """
        words = []
        for word in str(ident).strip().upper().split():
            letters = []
            for char in word:
                code = self.codes.get(char)
                if code is None:
                    return None, char
                letters.append(self.symbols(code))
            words.append(self.letter_gap.join(letters))
        return (self.word_gap.join(words) or None), None

    def from_aural(self, raw: str):
        r"""`auralMorseCode` -> mors. HARF AYRIMI KONMAZ.

        AIXM deseni `([\-\.]*)` harf ayraci icermez; zaten bu alan harf
        yerine sabit bir bipleme deseni yayinlayan marker'lar icindir (ILS
        marker'lari ident yayinlamaz). Dolayisiyla dizi tek parcadir.
        """
        code = str(raw).strip()
        if not code or set(code) - set(".-"):
            return None, code
        return self.symbols(code), None


def _type_label(raw, table):
    """Ham AIXM tip degeri -> etiket. Bilinmiyorsa `None` (uydurulmaz).

    `OTHER` aynen gecer; `OTHER:<x>` sonekini AYNEN dondurur — kisaltilmaz,
    cunku sonek kaynagin kendi serbest metnidir.
    """
    if not raw:
        return None
    if raw == "OTHER":
        return "OTHER"
    if raw.startswith(_OTHER_PREFIX):
        # Sonek AYNEN dondurulur. Sonek BOSSA (`"OTHER:"`) ne dondurulecegi
        # tanimli degildir: `None` doner ve cagiran loglar — "OTHER" varsayimi
        # yapilmaz.
        return raw[len(_OTHER_PREFIX):] or None
    return table.get(raw)


def _mls_channel_label(pairing, mls_channel):
    """`"500"` -> `"18X 500"` (DME kanali, bosluk, MLS kanali).

    Tabloda esi yoksa `None` doner. Yalniz MLS kanalini yazmak bir FALLBACK
    olurdu, yapilmaz. Tablo `CodeMLSChannelType`'in 200 degerinin 200'unu de
    kapsadigi icin bu ancak enum disi (`OTHER:*`) bir degerde tetiklenir.
    """
    if not mls_channel:
        return None
    dme = pairing.mls_to_dme.get(mls_channel.strip())
    return f"{dme} {mls_channel.strip()}" if dme else None


def _channel_from_frequency(pairing, kind, mhz):
    """Frekanstan kanal. Glidepath GP sütununu, diğerleri VHF sütununu kullanır."""
    if mhz is None:
        return None
    table = pairing.gp_to_channel if kind == "Glidepath" else pairing.vhf_to_channel
    return table.get(_key(mhz))


def compute(con, log=None, csv_path=None):
    """`navaids` ve `navaidComponents` için `navaidLabeling_*` alanlarını türetir."""
    pairing = Pairing(csv_path or Path(__file__).with_name("frequency-pairing.csv"))
    morse = Morse(Path(__file__).with_name("morse-itu.json"))
    cur = con.cursor()
    counts = {"bilesen": 0, "navaid": 0, "dme_yukseklik_yok": 0,
              "ident_bastirildi": 0, "mls_elevation": 0}

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
    def _quoted(column):
        return chr(34) + column + chr(34)

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
        ' navaidComponents_markerPosition,'
        # `class` COALESCE EDILEMEZ: `NDB.class` (ENR/L/MAR) ile
        # `MarkerBeacon.class` (FAN/Z/...) ayri enum'lardir, tek degere
        # indirgenirse bir marker'in class'i locator sanilabilir.
        f' {_quoted(schema.equipment_column("NDB", "class"))},'
        f' {_quoted(schema.equipment_column("MarkerBeacon", "auralMorseCode"))},'
        ' gmlId FROM navaidComponents')

    payload, by_navaid = [], {}
    for (row_id, navaid_ids, kind, designator, name, frequency, frequency_uom,
         channel, elevation, elevation_uom, marker_position, ndb_class,
         aural, gml_id) in cur.fetchall():
        have_freq, have_channel, have_dme_elev = EQUIPMENT_LABELS.get(kind, (0, 0, 0))
        if kind in _DEFERRED:
            # Degerleri kardes bilesenden gelir; C gecisinde doldurulur.
            have_freq = have_channel = 0

        # -- frekans: kendi alanı, ya da (DME/TACAN) kanaldan eşleştirme --
        freq_value = freq_uom = freq_mhz = None
        if have_freq and kind in _MLS_EQUIPMENT:
            # MLS: frekans AIXM'de yok, MLS kanalindan turetilir.
            paired = pairing.mls_to_freq.get((channel or "").strip())
            if paired is None:
                note("navaidComponents", gml_id, "navaidLabeling_freq",
                     channel, "mls_frekans_eslestirmesi_bulunamadi")
            else:
                freq_value, freq_uom, freq_mhz = paired, "MHZ", paired
        elif have_freq:
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
            if kind == "Azimuth":
                # MLS kanali TEK BASINA yazilmaz: yanina esleştirilmis DME
                # kanali da konur -> "18X 500".
                channel_out = _mls_channel_label(pairing, channel)
                if channel_out is None:
                    note("navaidComponents", gml_id, "navaidLabeling_channel",
                         channel, "mls_kanal_eslestirmesi_bulunamadi")
            elif kind in _OWN_CHANNEL:
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

        # -- tip etiketi: marker konumu > NDB locator > tip tablosu --
        if kind == "MarkerBeacon":
            type_label = (_type_label(marker_position, MARKER_POSITION_LABEL)
                          or MARKER_FALLBACK)
        elif kind == "NDB" and ndb_class == "L":
            type_label = LOCATOR_LABEL
        else:
            type_label = _type_label(kind, EQUIPMENT_TYPE_LABEL)
            if type_label is None:
                note("navaidComponents", gml_id, "navaidLabeling_type",
                     kind, "tip_eslemesi_yok")

        # -- mors: marker'in aural deseni varsa ident YERINE o kullanilir --
        ident_out, morse_out = designator, None
        if kind == "MarkerBeacon" and aural:
            morse_out, bad = morse.from_aural(aural)
            if morse_out is None:
                note("navaidComponents", gml_id, "navaidLabeling_morseCode",
                     bad, "aural_morse_gecersiz_karakter")
            else:
                # Harf degil sabit bipleme deseni yayinlayan bir marker'in
                # yanina ident yazmak yaniltici olur (kullanici karari).
                # Sayac yalnizca GERCEKTEN bastirilan vakayi sayar: Jeppesen
                # ureticisi artik marker'a designator yazmadigi icin normalde
                # ortada bastirilacak bir deger olmaz.
                if ident_out is not None:
                    counts["ident_bastirildi"] += 1
                ident_out = None
        elif designator:
            morse_out, bad = morse.from_ident(designator)
            if morse_out is None:
                note("navaidComponents", gml_id, "navaidLabeling_morseCode",
                     bad, "mors_cevrilemeyen_karakter")

        target_uom = "KHZ" if kind in _KHZ_TYPES else "MHZ"
        out_freq = _convert(freq_value, freq_uom, target_uom)

        payload.append((name, ident_out,
                        out_freq, target_uom if out_freq is not None else None,
                        channel_out, dme_elev, dme_elev_uom,
                        type_label, morse_out, row_id))
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
                # B gecisi locator ve MKR kararlarini bunlardan verir
                "ndb_class": ndb_class, "marker_position": marker_position,
                # Azimuth'un HAM MLS kanali: MLS/MLS_DME navaid'i ve kardes
                # Elevation bileseni bunu kullanir.
                "mls_channel": channel if kind == "Azimuth" else None,
            }

    _write(cur, "navaidComponents", payload)
    counts["mls_elevation"] = _resolve_mls_elevation(cur, by_navaid, pairing, note)

    # ── B geçişi: navaids (bileşenlerin çözülmüş değerlerini devralır) ──────
    cur.execute('SELECT id, navaids_type, navaids_designator, navaids_name, gmlId'
                ' FROM navaids')

    payload = []
    for row_id, nav_type, designator, name, gml_id in cur.fetchall():
        have_freq, have_channel, have_dme_elev = NAVAID_LABELS.get(nav_type, (0, 0, 0))
        components = by_navaid.get(row_id, {})

        freq_value = freq_uom = freq_mhz = None
        if have_freq and nav_type == "MLS_DME":
            # MLS_DME frekansi = birlesik kanaldaki DME kanalinin VHF esi.
            # Elevation/Azimuth'un aci frekansindan (5031-5090.7) FARKLIDIR:
            # bu, pilotun cevirdigi VHF frekansidir.
            azimuth = components.get("Azimuth")
            raw = (azimuth or {}).get("mls_channel")
            dme = pairing.mls_to_dme.get((raw or "").strip())
            paired = pairing.channel_to_vhf.get(dme) if dme else None
            if paired is None:
                # `W`/`Z` sonekli DME kanallarinin VHF esi YOKTUR (200 MLS
                # kanalinin 100'u boyledir). Baska bir frekans ikame edilmez.
                note("navaids", gml_id, "navaidLabeling_freq",
                     dme or raw, "dme_esinin_vhf_frekansi_yok")
            else:
                freq_value, freq_uom, freq_mhz = paired, "MHZ", paired
        elif have_freq:
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
            if nav_type in ("MLS", "MLS_DME"):
                # Kanal Azimuth bileseninin HAM MLS kanalindan, birlesik
                # bicimde uretilir -> "18X 500".
                azimuth = components.get("Azimuth")
                channel_out = _mls_channel_label(
                    pairing, (azimuth or {}).get("mls_channel"))
            elif channel_out is None:
                # MLS HARIC: kanal, navaid'in frekansindan eslestirilir.
                #
                # MLS'te bu yapilmaz. MLS kanali (`CodeMLSChannelType`,
                # 500-699) ile DME/TACAN kanali (`1X`...`126Y`) AYRI
                # numaralandirma sistemleridir; MLS kanali yalnizca Azimuth
                # bileseninden gelir. Bagli DME'nin kanalindan turetmek
                # mumkun olurdu (CSV'de ayni satirdalar) ama IZIN VERILMEDI —
                # farkli alanlar farkli anlam tasir.
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

        # -- tip etiketi --
        if nav_type in NDB_TYPES:
            ndb = components.get("NDB")
            type_label = (LOCATOR_LABEL
                          if ndb is not None and ndb["ndb_class"] == "L"
                          else _type_label(nav_type, NAVAID_TYPE_LABEL))
        elif nav_type == "MKR":
            # `MKR` tip tablosunda yoktur: etiketi bagli MarkerBeacon
            # bileseninin ILS'e gore konumundan gelir.
            marker = components.get("MarkerBeacon")
            type_label = MARKER_FALLBACK
            if marker is not None:
                type_label = (_type_label(marker["marker_position"],
                                          MARKER_POSITION_LABEL)
                              or MARKER_FALLBACK)
        else:
            type_label = _type_label(nav_type, NAVAID_TYPE_LABEL)
            if type_label is None and nav_type:
                note("navaids", gml_id, "navaidLabeling_type",
                     nav_type, "tip_eslemesi_yok")

        # -- mors: navaid kendi ident'inden uretir --
        morse_out = None
        if designator:
            morse_out, bad = morse.from_ident(designator)
            if morse_out is None:
                note("navaids", gml_id, "navaidLabeling_morseCode",
                     bad, "mors_cevrilemeyen_karakter")

        target_uom = "KHZ" if nav_type in _KHZ_TYPES else "MHZ"
        out_freq = _convert(freq_value, freq_uom, target_uom)

        payload.append((name, designator,
                        out_freq, target_uom if out_freq is not None else None,
                        channel_out, dme_elev, dme_elev_uom,
                        type_label, morse_out, row_id))
        counts["navaid"] += 1

    _write(cur, "navaids", payload)
    con.commit()

    print(f"    navaids={counts['navaid']} navaidComponents={counts['bilesen']} "
          f"(dme yuksekligi kaynakta yok={counts['dme_yukseklik_yok']}, "
          f"aural morse nedeniyle ident bastirilan={counts['ident_bastirildi']})")
    return counts


def _resolve_mls_elevation(cur, by_navaid, pairing, note):
    """C geçişi — `Elevation` bileşenlerini KARDEŞ `Azimuth`'tan doldurur.

    `Elevation`'ın AIXM'de ne kanalı ne frekansı vardır (`ElevationPropertyGroup`
    = angleNominal, angleMinimum, angleSpan). İkisi de aynı MLS istasyonunun
    `Azimuth` bileşenindeki kanaldan türetilir; azimuth ve elevation aynı RF
    kanalında zaman bölmeli yayın yaptığı için frekans da **birebir aynıdır**.

    Kardeş bağı ancak A geçişi bitip `by_navaid` tamamlandığında bilinebildiği
    için ayrı bir geçiş gerekir.
    """
    cur.execute('SELECT id, associatedNavaid, gmlId FROM navaidComponents'
                ' WHERE navaidComponents_equipmentType = ?', ("Elevation",))
    rows = cur.fetchall()
    if not rows:
        return 0

    payload, resolved = [], 0
    for row_id, navaid_ids, gml_id in rows:
        mls_channel = None
        for parent in _parse_ids(navaid_ids):
            azimuth = by_navaid.get(parent, {}).get("Azimuth")
            if azimuth and azimuth.get("mls_channel"):
                mls_channel = azimuth["mls_channel"]
                break

        if mls_channel is None:
            note("navaidComponents", gml_id, "navaidLabeling_channel",
                 None, "mls_azimuth_bileseni_yok")
            continue

        channel_out = _mls_channel_label(pairing, mls_channel)
        if channel_out is None:
            note("navaidComponents", gml_id, "navaidLabeling_channel",
                 mls_channel, "mls_kanal_eslestirmesi_bulunamadi")
        freq = pairing.mls_to_freq.get(mls_channel.strip())
        if freq is None:
            note("navaidComponents", gml_id, "navaidLabeling_freq",
                 mls_channel, "mls_frekans_eslestirmesi_bulunamadi")
        payload.append((freq, "MHZ" if freq is not None else None,
                        channel_out, row_id))
        resolved += 1

    if payload:
        cur.executemany(
            'UPDATE "navaidComponents" SET "navaidLabeling_freq"=?,'
            ' "navaidLabeling_freqUom"=?, "navaidLabeling_channel"=?'
            ' WHERE id=?', payload)
    return resolved


def _write(cur, layer, payload):
    cur.executemany(
        f'UPDATE "{layer}" SET'
        ' "navaidLabeling_name"=?,'
        ' "navaidLabeling_ident"=?, "navaidLabeling_freq"=?,'
        ' "navaidLabeling_freqUom"=?, "navaidLabeling_channel"=?,'
        ' "navaidLabeling_dmeElev"=?, "navaidLabeling_dmeElevUom"=?,'
        ' "navaidLabeling_type"=?, "navaidLabeling_morseCode"=?'
        ' WHERE id=?', payload)
