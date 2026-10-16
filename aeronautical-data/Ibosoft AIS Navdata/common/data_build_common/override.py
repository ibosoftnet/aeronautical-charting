"""Override indeksi — ek kaynak kaydının ana kaynak kaydının yerine geçmesi.

Kaynakların UUID uzayları bağımsız olduğu için eşleştirme **doğal anahtarla**
yapılır. Anahtarın ne olduğu projeye özgüdür (ATS: `data-ats/merge/keys.py`,
airspace: `data-airspace/merge.py`); bu modül yalnızca anahtar → kazanan kayıt
eşlemesini ve isteğe bağlı konum yedeğini tutar.
"""

from collections import defaultdict


class OverrideIndex:
    """Ek kaynakların ürettiği override anahtarları.

    Ana kaynak taranırken her feature bu indekste sorgulanır; eşleşen kayıt
    atlanır (yerine ek kaynağınki yazılacaktır).
    """

    def __init__(self):
        self._keys: dict = {}
        # Doğal anahtar tutmadığında yedek: konum tabanlı arama.
        # (layer, designator) → [(source_name, gml_id, uuid, position, esik_nm)]
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
        KENDİ eşiği içinde kalan TEK adayı döner: `(hit, adet)`. Eşik içinde
        birden fazla aday varsa SEÇİM YAPILMAZ (`hit=None`, `adet>1`) — yanlış
        kayda bağlamak sessiz veri hatası olur; çağıran taraf bunu loglar.
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
