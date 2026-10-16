"""EAD-SDO → AIXM 5.2 değer ve enum eşleme tabloları.

Buradaki her eşleme ya kaynak değerin AIXM enum'unda birebir bulunmasına
(doğrudan), ya da kullanıcı tarafından açıkça onaylanmış bir yoruma dayanır.
Gerekçeler EAD-SDO_Field_Mapping.md dosyasında belgelenmiştir.
"""

import re

# ── AIXM 5.2 enum listeleri (XSD'den birebir) ────────────────────────────────
CODE_NAVAID_SERVICE = {
    "VOR", "DME", "NDB", "TACAN", "MKR", "ILS", "ILS_DME", "MLS", "MLS_DME",
    "VORTAC", "VOR_DME", "NDB_DME", "TLS", "LOC", "LOC_DME", "NDB_MKR", "DF", "SDF",
}
CODE_DESIGNATED_POINT = {"ICAO", "COORD", "CNF", "TERMINAL", "BRG_DIST", "VRP"}
CODE_VERTICAL_REFERENCE = {"SFC", "MSL", "W84", "STD"}
CODE_VOR = {"VOR", "DVOR", "VOT"}
CODE_NORTH_REFERENCE = {"TRUE", "MAG", "GRID"}
CODE_RADIO_EMISSION = {
    "A2", "A3A", "A3B", "A3E", "A3H", "A3J", "A3L", "A3U", "J3E", "NONA1A",
    "NONA2A", "PON", "A8W", "A9W", "NOX", "G1D",
}
CODE_ILS_BACK_COURSE = {"YES", "NO", "RSTR"}
CODE_TIME_REFERENCE = {"UTC"}
CODE_DAY = {"ANY", "MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"}
UOM_DISTANCE_VERTICAL = {"FT", "M", "FL", "SM"}

# ── EAD-SDO → AIXM eşlemeleri ────────────────────────────────────────────────

# DesignatedPoint codeType. Kaynakta bulunan değerler: ICAO, COORD, ADHP, OTHER.
# AIXM CodeDesignatedPointType enum'u: ICAO, COORD, CNF, TERMINAL, BRG_DIST, VRP
# (+ OTHER deseni).
#
# ADHP → TERMINAL: kaynaktaki ADHP kayıtları beş alfanümerik karakterli terminal
#   saha noktalarıdır (15NAT, AA408, AA415 …). XSD'nin TERMINAL tanımı birebir
#   budur: "maximum of five alphanumeric characters, unique in the context of
#   the terminal area where it is used". Uzatma desenine gerek yok.
# OTHER → OTHER: kaynaktaki OTHER kayıtları yaklaşma/kalkış prosedür
#   noktalarıdır (001AB "2.0NM TO RW25", 001DC "MAPT VOR APCH RWY04 1.0 DME
#   DND"). Enum'da karşılığı yok; düz OTHER doğru değerdir — alt kod eklemek
#   bilgi katmıyordu.
DP_TYPE = {
    "ICAO": "ICAO",
    "COORD": "COORD",
    "ADHP": "TERMINAL",
    "OTHER": "OTHER",
}

# RouteSegment dikey limit referansı. Kaynak: STD, ALT, HEI, QNH, OTHER.
# AIXM CodeVerticalReferenceType: SFC, MSL, W84, STD (+OTHER deseni).
# Kullanıcı onaylı eşleme.
VERTICAL_REFERENCE = {
    "STD": "STD",
    "ALT": "MSL",
    "HEI": "SFC",
    "QNH": "OTHER:QNH",
    "OTHER": "OTHER",
}

# Localizer arka kurs kullanımı. Kaynak: N (137), Y (5), R (4).
# AIXM CodeILSBackCourseType: YES, NO, RSTR.
BACK_COURSE = {"N": "NO", "Y": "YES", "R": "RSTR"}

# Rota uç noktası codeType yazım varyantları (kaynakta ikisi de geçiyor).
ENDPOINT_TYPE_ALIAS = {"DME/VOR": "VOR/DME", "TACVOR": "VORTAC"}

# Rota uç noktası codeType → kabul edilebilir AIXM Navaid.type KÜMESİ.
#
# Katı eşitlik DEĞİL, işlevsel eşdeğerlik (kullanıcı onaylı düzeltme). Aynı
# fiziksel tesis AIP'de ve EAD'de farklı tiplerle modellenebiliyor:
#
#   * UL573'ün ucu ham veride `VOR/DME`, ama EAD aynı tesisi (37.0167 N,
#     41.2053 E) `VORTAC` + ayrı `DME` olarak yayımlıyor. XSD tanımları:
#     `VOR_DME` = "VOR and DME collocated", `VORTAC` = "VOR and TACAN
#     collocated" — TACAN hem azimut hem mesafe verdiği için bir VORTAC,
#     rota ucu olarak VOR/DME'nin işlevsel karşılığıdır.
#   * `BAN` ailesinde tersi: ham `VOR`, EAD'de `VOR_DME`.
#
# Katı eşitlik bu adayları tamamen eliyor, geriye coğrafi olarak yanlış tek
# aday kalıyor ve yakınlık ayıklaması devreye giremiyordu (ölçüldü: 300 NM
# üstü 43 hatalı segmentin 34'ü bu sebepten).
ENDPOINT_TO_NAVAID_TYPES = {
    # VOR + mesafe: VOR_DME ile VORTAC birbirinin yerine geçebilir.
    "VOR/DME": ("VOR_DME", "VORTAC"),
    "VORTAC": ("VORTAC", "VOR_DME"),
    # Salt VOR isteniyorsa VOR taşıyan her bileşik tesis kabul edilir.
    "VOR": ("VOR", "VOR_DME", "VORTAC"),
    # Mesafe ölçen her tesis (TACAN'ın mesafe bileşeni DME'dir).
    "DME": ("DME", "VOR_DME", "VORTAC", "TACAN",
            "NDB_DME", "ILS_DME", "LOC_DME", "MLS_DME"),
    "TACAN": ("TACAN", "VORTAC"),
    "NDB": ("NDB", "NDB_DME"),
}

# Rota kodu ayrıştırma deseni (AIXM designator alanları).
ROUTE_DESIGNATOR_RE = re.compile(
    r"^([KUST])?\s*([ABGHJLMNPQRTVWYZ])\s*(\d+)\s*([A-Z])?$"
)

# Rota txtLocDesig içindeki ICAO bölge kodu çifti ("LT-LT" → {"LT"}).
LOC_DESIG_REGION_RE = re.compile(r"^([A-Z]{2})-([A-Z]{2})$")


def decompose_route_designator(designator: str):
    """"UA14" → ("U", "A", "14", None). Desene uymazsa None döner."""
    m = ROUTE_DESIGNATOR_RE.match((designator or "").strip().upper())
    if not m:
        return None
    return m.groups()


def regions_of(loc_designator: str) -> set[str]:
    """txtLocDesig'ten ICAO bölge kodlarını çıkarır ("LT-LT" → {"LT"})."""
    m = LOC_DESIG_REGION_RE.match((loc_designator or "").strip().upper())
    return {m.group(1), m.group(2)} if m else set()


def number(value) -> str:
    """Sayısal metni normalize eder ("003.00" → "3", "+15" → "15")."""
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        f = float(text)
    except ValueError:
        return text
    return str(int(f)) if f == int(f) else str(f)


def parse_dt_wef(value: str) -> str | None:
    """EAD "12/06/2025" (GG/AA/YYYY) → AIXM "2025-06-12T00:00:00Z".

    Format doğrulandı: gün alanında 27, 30 gibi değerler geçiyor, dolayısıyla
    sıra GG/AA/YYYY'dir (AA/GG değil).
    """
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", (value or "").strip())
    if not m:
        return None
    day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return None
    return f"{year:04d}-{month:02d}-{day:02d}T00:00:00Z"


def year_only(value: str) -> str:
    """dateMagVar → AIXM DateYearType (4 haneli yıl). Uymayan değer boş döner."""
    text = (value or "").strip()
    return text if re.fullmatch(r"[1-9][0-9]{3}", text) else ""


def load_frequency_pairing(csv_path):
    """frequency-pairing.csv'den bidirectional lookup sözlükleri üretir.

    Legacy `build_navaids_gpkg.py:849-901` fonksiyonundan birebir port edildi.
    CSV sütunları: 0 = DME kanal no, 1 = VHF frekansı (MHz), 11 = GP frekansı.
    """
    channel_to_vhf: dict[str, str] = {}
    vhf_to_channel: dict[str, str] = {}
    channel_to_gp: dict[str, str] = {}
    gp_to_channel: dict[str, str] = {}

    if not csv_path.exists():
        return channel_to_vhf, vhf_to_channel, channel_to_gp, gp_to_channel

    def norm_freq(s: str) -> str:
        try:
            return str(float(s))
        except ValueError:
            return s

    with open(csv_path, "r", encoding="utf-8") as f:
        next(f, None)                      # başlık satırı
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(",")
            if len(parts) < 2:
                continue
            channel = parts[0].strip().upper()
            vhf_raw = parts[1].strip()
            gp_raw = parts[11].strip() if len(parts) > 11 else ""

            if channel and vhf_raw:
                vhf_norm = norm_freq(vhf_raw)
                channel_to_vhf[channel] = vhf_norm
                vhf_to_channel[vhf_norm] = channel
            if channel and gp_raw:
                gp_norm = norm_freq(gp_raw)
                channel_to_gp[channel] = gp_norm
                gp_to_channel[gp_norm] = channel

    return channel_to_vhf, vhf_to_channel, channel_to_gp, gp_to_channel
