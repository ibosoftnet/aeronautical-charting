"""
Tip sınıflandırma ve dikey-limit ayrıştırma yardımcıları.

`airspace_type` — isim (ve opsiyonel Jeppesen ham tipi) üzerinden ortak tip
tespiti; öncelik sıralı ilk-eşleşen. Jeppesen ve LH paylaşır. Eşleşme yoksa
None döner (fallback 'OTHER' çağıran modülün kararıdır).
"""
import re


def _norm(name: str) -> str:
    """QGIS filtrelerindeki normalizasyon: parantezleri boşluğa çevir, sınırla."""
    return " " + re.sub(r"[()]", " ", (name or "").lower()) + " "


def _kw(nn: str, token: str) -> bool:
    """Normalize edilmiş isimde ' token ' geçiyor mu (kelime sınırlı)."""
    return f" {token} " in nn


def airspace_type(name: str, jtype: str = None):
    """
    Ortak hava sahası tip sınıflandırıcı — öncelik sıralı ilk-eşleşen.
    jtype = Jeppesen ham `type` (yoksa None; LH'de None).
    Eşleşme yoksa None.
    """
    nn = _norm(name)
    jt = (jtype or "").strip()
    jl = jt.lower()

    # İsim anahtar kelimeleri — kontrol/zon sahaları (ham tipten önce).
    if _kw(nn, "ctr") or _kw(nn, "mctr") or jl == "mctr":
        return "CTR"
    if _kw(nn, "tma") or _kw(nn, "mtma"):
        return "TMA"
    if _kw(nn, "cta") or _kw(nn, "mcta"):
        return "CTA"
    if _kw(nn, "uta"):
        return "UTA"
    if _kw(nn, "adiz"):
        return "ADIZ"
    if _kw(nn, "atz") or _kw(nn, "matz"):
        return "ATZ"
    if _kw(nn, "rmz"):
        return "RMZ"
    if _kw(nn, "tmz"):
        return "TMZ"

    # Jeppesen ham tip tabanlı — kısıtlama tipleri isimden önceliklidir.
    if jt == "P":
        return "P"
    if jt == "R":
        return "R"
    if jt == "DA":
        return "D"
    if jt == "AL":
        return "A"
    if jt == "W":
        return "W"
    if jt in ("TR", "M", "CN") or _kw(nn, "sua"):
        return "RAS"

    # İsim tabanlı — okyanusal/advisory ham tipten SONRA, FRA'dan önce.
    if _kw(nn, "moa"):
        return "MOA"
    if _kw(nn, "oca") or "oceanic control" in nn:
        return "OCA"
    if _kw(nn, "ota") or "oceanic transition" in nn:
        return "OTA"
    if _kw(nn, "ada") or _kw(nn, "adv") or "advisory" in nn:
        return "ADV"
    if "free rt" in nn:
        return "FRA"
    if "sector" in nn:
        return "SECTOR"

    return None


# LH açık TYPE alanı -> ortak tip
LH_TYPE_MAP = {
    "PROHIBITED": "P",
    "RESTRICTED": "R",
    "DANGER": "D",
}

# LH başlık tabanlı tip çıkarımı (TYPE alanı yok/eşleşmiyorsa). Jeppesen'in
# strict ' tma ' filtresinden farklı olarak, LH başlıklarında tip token'ı
# rakam/tire ile bitişiktir (TMA2A, TMA-120, MTMA3A, CTA2, MCTR) — bu yüzden
# öncelik sıralı, suffix toleranslı desenlerle eşleştirilir.
_LH_TITLE_PATTERNS = [
    (re.compile(r"\bM?CTR", re.I), "CTR"),
    (re.compile(r"\bM?TMA", re.I), "TMA"),
    (re.compile(r"\bM?CTA", re.I), "CTA"),
    (re.compile(r"\bUTA", re.I), "UTA"),
    (re.compile(r"\bOCA", re.I), "OCA"),
    (re.compile(r"\bADIZ", re.I), "ADIZ"),
    (re.compile(r"\bM?ATZ", re.I), "ATZ"),
    (re.compile(r"\bRMZ", re.I), "RMZ"),
    (re.compile(r"\bTMZ", re.I), "TMZ"),
    (re.compile(r"\bMOA", re.I), "MOA"),
    (re.compile(r"free rt", re.I), "FRA"),
    (re.compile(r"\bSECTOR", re.I), "SECTOR"),
]


def lh_type_from_title(title: str):
    """LH başlığından tip çıkar (suffix toleranslı). Eşleşme yoksa None."""
    t = title or ""
    for rx, typ in _LH_TITLE_PATTERNS:
        if rx.search(t):
            return typ
    if "oceanic control" in t.lower():
        return "OCA"
    return None

# Jeppesen ham type -> AIXM sınıfı (classification)
_JEPP_CLASS = {"CA": "A", "CB": "B", "CC": "C", "CD": "D", "CE": "E", "CF": "F", "CG": "G"}


def jeppesen_classification(jtype: str) -> str:
    return _JEPP_CLASS.get((jtype or "").strip(), "")


def derive_uom(reference: str) -> str:
    """LT: referanstan uom türet. STD->FL, MSL/SFC->FT, aksi halde ''."""
    r = (reference or "").strip().upper()
    if r == "STD":
        return "FL"
    if r in ("MSL", "SFC"):
        return "FT"
    return ""


def normalize_vref(reference: str) -> str:
    """
    Dikey referansı AIXM CodeVerticalReferenceType'a normalize et.
    Geçerli AIXM değerleri: SFC, MSL, W84, STD. Ham kaynaklardaki 'AGL'
    (yer üstü) AIXM'de SFC ile ifade edilir -> SFC'ye çevrilir. Diğerleri
    olduğu gibi (upper, boş dahil) bırakılır.
    """
    r = (reference or "").strip().upper()
    return "SFC" if r == "AGL" else r


_LH_ALT_RE = re.compile(r"(\d+)\s*ft", re.IGNORECASE)
_LH_REF_RE = re.compile(r"\b(STD|MSL|AGL)\b", re.IGNORECASE)


def parse_lh_altitude(s: str):
    """
    LH TOPS/BASE ayrıştır -> (value, uom, reference).
    'GND ALT' -> ('GND','',''); 'UNL' -> ('UNL','','');
    '19501ft STD ALT' -> ('19501','FT','STD').
    """
    s = (s or "").strip()
    up = s.upper()
    if "GND" in up:
        return "GND", "", ""
    if "UNL" in up:
        return "UNL", "", ""
    m = _LH_ALT_RE.search(s)
    value = m.group(1) if m else ""
    rm = _LH_REF_RE.search(s)
    ref = normalize_vref(rm.group(1) if rm else "")
    if value and ref == "STD":
        # STD referansı = uçuş seviyesi. LH verisi feet cinsinden ve ±1 ft
        # sınır offset'i taşır (19501 ft ≈ FL195, 15499 ft ≈ FL155); en yakın
        # FL'e yuvarlanır, uom=FL. AIXM: STD daima FL ile eşleşir.
        value = str(round(int(value) / 100))
        uom = "FL"
    else:
        uom = "FT" if value else ""
    return value, uom, ref
