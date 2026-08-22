"""Ek kaynakların ana kaynak kayıtlarını geçersiz kılması (override).

Kaynakların UUID uzayları bağımsız olduğu için eşleştirme **doğal anahtarla**
yapılır (`keys.override_key`), UUID eşitliğiyle değil.

`override_base_originator`: ek kaynağın kendi provenance originator'ı ile ana
kaynakta aranacak dize farklı olabilir — bu yüzden her ek kaynak için ayrı
ayarlanır, koda gömülmez. LT'de doğrulandı: kendi `data.json`'ı
`"DHMİ Türkiye"` derken EAD tarafındaki karşılığı `"DHMI TURKIYE"` yazımıyla
geçiyor.
"""

from collections import defaultdict

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


class OverrideIndex:
    """Ek kaynakların ürettiği override anahtarları.

    Ana kaynak taranırken her feature bu indekste sorgulanır; eşleşen kayıt
    atlanır (yerine ek kaynağınki yazılacaktır).
    """

    def __init__(self):
        self._keys: dict = {}
        # Doğal anahtar (designator+originator) tutmadığında yedek: konum
        # tabanlı arama. (layer, designator) → [(source_name, gml_id, uuid,
        # position, esik_nm), …]. Originator yazımı kaynaktan kaynağa
        # değişebildiği için (EAD'de aynı nokta "EUROCONTROL NMOC", "INITIAL"
        # veya bir ulusal sağlayıcı adıyla geçebiliyor) tam anahtar birçok LT
        # noktasında tutmuyor; bu yüzden konum yedeği gerekli — bkz.
        # `proximity_lookup`.
        self._positions: dict = {}
        self.consumed: dict = defaultdict(int)

    def add(self, key, source_name: str, gml_id: str, uuid_value: str):
        if key is None:
            return
        self._keys[key] = (source_name, gml_id, uuid_value)

    def add_position(self, layer, designator, source_name: str, gml_id: str,
                     uuid_value: str, position, esik_nm: float):
        if not (layer and designator and position and esik_nm):
            return
        self._positions.setdefault((layer, designator), []).append(
            (source_name, gml_id, uuid_value, position, esik_nm))

    def __len__(self):
        return len(self._keys)

    def peek(self, key):
        """Sayaç artırmadan bakar (ön tarama için)."""
        return self._keys.get(key) if key is not None else None

    def lookup(self, key):
        hit = self.peek(key)
        if hit:
            self.consumed[hit[0]] += 1
        return hit

    def proximity_lookup(self, layer, designator, position, geod):
        """Doğal anahtar tutmadığında konum tabanlı yedek eşleştirme.

        Aynı `(layer, designator)` altında kayıtlı ek kaynak adayları arasından
        KENDİ eşiği içinde kalan TEK adayı döner: `(hit, adet)`. `hit`,
        `peek()`/`lookup()` ile aynı biçimde `(source_name, gml_id, uuid)`.
        Eşik içinde birden fazla aday varsa SEÇİM YAPILMAZ (`hit=None`,
        `adet>1`) — yanlış kayda bağlamak sessiz veri hatası olur; çağıran
        taraf bunu loglar.
        """
        if position is None:
            return None, 0
        adaylar = self._positions.get((layer, designator), [])
        yakin = []
        for source_name, gml_id, uuid_value, pos, esik in adaylar:
            _, _, mesafe = geod.inv(position[1], position[0], pos[1], pos[0])
            if mesafe / 1852.0 <= esik:
                yakin.append((source_name, gml_id, uuid_value))
        if len(yakin) == 1:
            return yakin[0], 1
        return None, len(yakin)


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
