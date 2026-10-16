"""Ek kaynakların ana kaynak kayıtlarını geçersiz kılması (override).

Kaynakların UUID uzayları bağımsız olduğu için eşleştirme **doğal anahtarla**
yapılır (`keys.override_key`), UUID eşitliğiyle değil. İndeks sınıfı
(`OverrideIndex`) ortak pakettedir; burada ATS'ye özgü config yardımcıları ve
indeksin ATS doğal anahtarlarıyla kurulması durur.

`override_base_originator`: ek kaynağın kendi provenance originator'ı ile ana
kaynakta aranacak dize farklı olabilir — bu yüzden her ek kaynak için ayrı
ayarlanır, koda gömülmez. LT'de doğrulandı: kendi `data.json`'ı
`"DHMİ Türkiye"` derken EAD tarafındaki karşılığı `"DHMI TURKIYE"` yazımıyla
geçiyor.
"""

from data_build_common.override import OverrideIndex

from .keys import layer_of, natural_fields, override_key

# `prefer_base_on_match` hiçbir zaman kaynağın tamamına uygulanmaz; hangi
# katmanlarda geçerli olduğu config'de `prefer_base_on_match_layers` ile
# belirtilir. Liste verilmezse bu varsayılan kullanılır.
DEFAULT_PREFER_BASE_LAYERS = ("navaids", "navaidComponents")


def prefer_base_layers(source: dict) -> frozenset:
    """Kaynağın `prefer_base_on_match` uyguladığı katmanlar."""
    if not source.get("prefer_base_on_match"):
        return frozenset()
    return frozenset(source.get("prefer_base_on_match_layers")
                     or DEFAULT_PREFER_BASE_LAYERS)


def prefers_base(source: dict, kind: str) -> bool:
    """Bu feature tipinde ANA KAYNAK mı kazanır?"""
    return layer_of(kind) in prefer_base_layers(source)


def proximity_nm(source: dict) -> float:
    """Yakınlık eşiği (NM). 0/yok ise yakınlık eşleştirmesi kapalıdır."""
    try:
        return float(source.get("match_by_proximity_nm") or 0)
    except (TypeError, ValueError):
        return 0.0


def prefer_base_originator(source: dict):
    """Devretme (prefer_base) yönünde aranacak originator dizesi.

    Override yönüyle **farklı** olabilir: bir ek kaynak, bir sağlayıcının
    kayıtlarını geçersiz kılarken bir başkasınınkine devredebilir. TRNC'de
    böyledir — Kıbrıs bölgesindeki noktalarda EAD'nin `CYPRUS DEPARTMENT OF
    CIVIL AVIATION` kaydı geçerli kalır.

    Ayrı değer verilmemişse `override_base_originator`'a düşer (LT'deki durum).
    """
    return (source.get("prefer_base_originator")
            or source.get("override_base_originator"))


def build_override_index(sources, log=None) -> OverrideIndex:
    """Override etkin ek kaynakları tarayıp indeksi kurar.

    `sources`: [{"name", "index", "features", "override_enabled",
                 "override_base_originator"}] — `features`, o kaynağın
    `(info, originator)` listesidir (ek kaynaklar küçük olduğu için bellekte
    tutulabilir: LT 4.368, TRNC henüz yok).
    """
    index = OverrideIndex()
    for source in sources:
        if not source.get("override_enabled"):
            continue
        base_originator = source.get("override_base_originator")
        iki_yonlu = (prefer_base_originator(source)
                     != source.get("override_base_originator"))
        esik = proximity_nm(source)
        for info, _originator in source["features"]:
            # `prefer_base_on_match_layers` katmanları normalde override'a
            # GİRMEZ — o katmanlarda ters yön geçerlidir. Ancak iki yön FARKLI
            # sağlayıcıyı hedefliyorsa ikisi de çalışır: kayıt önce devretme
            # için aranır, tutmazsa override eder. (TRNC: LT'ye devret, EAD'nin
            # Cyprus DCA kaydını override et.)
            if prefers_base(source, info["kind"]) and not iki_yonlu:
                continue
            # Ana kaynakta aranacak anahtar, ORADAKİ originator yazımıyla
            # kurulur — ek kaynağın kendi originator'ıyla değil.
            fields = natural_fields(info, base_originator, source["index"])
            key = override_key(fields)
            if key is not None:
                index.add(key, source["name"], info["gml_id"], info["uuid"])
            # Yakınlık yedeği: originator yazımı EAD'de kaynaktan kaynağa
            # değiştiği için (bkz. proximity_lookup docstring) designator
            # anahtarı tutsa da originator tutmayabilir. Şimdilik yalnızca
            # designatedPoints için — routeSegments'te "konum" tekil bir nokta
            # değil, curveExtent'tir; oraya proximity fallback uygulanmadı.
            if (esik and fields.get("layer") == "designatedPoints"
                    and fields.get("designator") and info.get("position")):
                index.add_position(fields["layer"], fields["designator"],
                                   source["name"], info["gml_id"],
                                   info["uuid"], info["position"], esik)
    return index
