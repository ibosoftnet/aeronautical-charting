"""DHMİ → AIXM 5.2 değer ve enum eşleme tabloları.

Buradaki her eşleme ya kaynak değerin AIXM enum'unda birebir bulunmasına
(doğrudan), ya da kullanıcı tarafından açıkça onaylanmış bir yoruma dayanır.
Gerekçeler DHMI_to_AIXM_Mapping.md dosyasında belgelenmiştir.
"""

import re

# ── AIXM 5.2 enum listeleri (XSD'den birebir) ────────────────────────────────
CODE_LEVEL = {"UPPER", "LOWER", "BOTH"}
CODE_VERTICAL_REFERENCE = {"SFC", "MSL", "W84", "STD"}
CODE_ATC_REPORTING = {"COMPULSORY", "ON_REQUEST", "NO_REPORT"}
CODE_NAVAID_SERVICE = {
    "VOR", "DME", "NDB", "TACAN", "MKR", "ILS", "ILS_DME", "MLS", "MLS_DME",
    "VORTAC", "VOR_DME", "NDB_DME", "TLS", "LOC", "LOC_DME", "NDB_MKR", "DF", "SDF",
}
CODE_DESIGNATED_POINT = {"ICAO", "COORD", "CNF", "TERMINAL", "BRG_DIST", "VRP"}
CODE_ROUTE_SEGMENT_PATH = {"GRC", "RHL", "GDS"}
CODE_ROUTE = {"ATS", "NAT"}
CODE_FLIGHT_RULE = {"IFR", "VFR", "ALL"}
CODE_DESIGN_STANDARD = {"PANS_OPS", "TERPS", "CANADA_TERPS", "NATO"}
CODE_NAVIGATION_TYPE = {"CONV", "TACAN", "PBN"}
CODE_NAVIGATION_SPECIFICATION = {
    "RNAV_10", "RNAV_5", "RNAV_2", "RNAV_1", "RNP_4", "RNP_2", "RNP_APCH",
    "RNP_AR_APCH", "RNAV", "RNP", "RNP_1", "A_RNP", "RNP_0_3",
}
CODE_BEARING = {"TRUE", "MAG", "RDL", "TRK", "HDG"}
CODE_DIRECTION_REFERENCE = {"TO", "FROM"}
CODE_DISTANCE_INDICATION = {"DME", "GEODETIC"}
CODE_REFERENCE_ROLE = {"INTERSECTION", "RECNAV", "ATD", "RAD_DME"}

# Route designator ikinci harfi (CodeRouteDesignatorLetterType)
CODE_ROUTE_DESIGNATOR_LETTER = set("ABGHJLMNPQRTVWYZ")
# Route designator öneki (CodeRouteDesignatorPrefixType)
CODE_ROUTE_DESIGNATOR_PREFIX = set("KUST")


# ── DHMİ → AIXM eşlemeleri ───────────────────────────────────────────────────

# DHMİ NAVIGATION TYPE → AircraftCharacteristic/navigationType.
# CONV doğrudan geçerli. RNAV, CodeNavigationType enum'unda yok; kullanıcı
# onayıyla PBN'e eşlenir (RNAV'ın güncel ICAO karşılığı).
NAVIGATION_TYPE = {"CONV": "CONV", "RNAV": "PBN"}

# DHMİ REQUIRED NAVIGATION PERFORMANCE → AircraftCharacteristic/navigationSpecification.
# Kaynakta yalnızca RNAV satırlarında dolu (CONV'da hep boş) — doğrulandı.
NAVIGATION_SPECIFICATION = {"5": "RNAV_5", "1": "RNAV_1"}

# DHMİ UPPER LIMIT özel değeri. 999 gerçek bir uçuş seviyesi değil; kullanıcı
# onayıyla ValDistanceVerticalType'ın "UNL" (unlimited) özel değerine eşlenir.
VERTICAL_LIMIT_SPECIAL = {"999": "UNL"}

# Rota kodu ayrıştırma deseni: önek + ikinci harf + numara + çoklu tanımlayıcı.
ROUTE_DESIGNATOR_RE = re.compile(
    r"^([KUST])?\s*([ABGHJLMNPQRTVWYZ])\s*(\d+)\s*([A-Z])?$"
)

# VFR nokta açıklamasındaki navaid radyal/mesafe deseni: "DAL R270/D22.51"
VFR_FIX_RE = re.compile(r"([A-Z]{2,4})\s*R(\d+(?:\.\d+)?)\s*/\s*D(\d+(?:\.\d+)?)")


def vertical_uom(reference: str) -> str:
    """Dikey limit için ölçü birimi.

    Kaynak doğrulaması: STD referanslı değerler uçuş seviyesi (055…999),
    MSL/SFC referanslı değerler fit (3000…14000).
    """
    return "FL" if reference == "STD" else "FT"


def vertical_limit(value: str) -> str:
    """Dikey limit değerini AIXM'e uygun hale getirir (999 → UNL)."""
    value = (value or "").strip()
    if value in VERTICAL_LIMIT_SPECIAL:
        return VERTICAL_LIMIT_SPECIAL[value]
    return number(value)


def number(value: str) -> str:
    """Sayısal metni normalize eder ("003" → "3", "22.51" → "22.51")."""
    value = (value or "").strip()
    if not value:
        return ""
    try:
        f = float(value)
    except ValueError:
        return value
    return str(int(f)) if f == int(f) else str(f)


def decompose_route_designator(designator: str):
    """"UA 285" → ("U", "A", "285", None). Desene uymazsa None döner."""
    m = ROUTE_DESIGNATOR_RE.match((designator or "").strip())
    if not m:
        return None
    prefix, letter, num, multiple = m.groups()
    return prefix, letter, num, multiple


# AIXM TextNameType deseni yalnızca ASCII kabul eder
# ([A-Z]|[a-z]|[0-9]| noktalama). DHMİ VFR nokta adlarında Türkçe karakter
# bulunduğu için ASCII karşılıklarına çevrilir; orijinal yazım kullanıcı
# kararıyla annotation/Note içinde korunur (veri kaybı olmaz).
ASCII_FOLD = str.maketrans({
    "Ç": "C", "ç": "c", "Ğ": "G", "ğ": "g", "İ": "I", "ı": "i",
    "Ö": "O", "ö": "o", "Ş": "S", "ş": "s", "Ü": "U", "ü": "u",
    "Â": "A", "â": "a", "Î": "I", "î": "i", "Û": "U", "û": "u",
})


def ascii_name(text: str) -> str:
    """Adı ASCII'ye çevirir. Değişiklik yoksa girdiyi aynen döndürür."""
    return (text or "").translate(ASCII_FOLD)


def is_ascii(text: str) -> bool:
    return all(ord(c) < 128 for c in (text or ""))


def reciprocal(bearing: str) -> str:
    """Bir kerterizin ters yönü ((deger + 180) mod 360)."""
    return number(str((float(bearing) + 180) % 360))


def parse_vfr_fix(description: str):
    """VFR nokta açıklamasından (navaid, radyal, mesafe) üçlülerini çıkarır.

    "DAL R270/D22.51"                    → [("DAL", "270", "22.51")]
    "BIG R200/D30.43 EDR R010/D16.72"    → iki üçlü (kesişim noktası)
    """
    return VFR_FIX_RE.findall(description or "")
