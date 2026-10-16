"""İptal (exclude) kuralları — kurala uyan kayıtlar birleşik veriye yazılmaz.

Kural dosyaları projenin `data-sources/excludes/*.json` dizinindedir. Her dosya
bir kural listesi taşır. Kural alanları:

| Alan | Zorunlu | Anlamı |
|---|---|---|
| `layer` | hayır | Yalnızca bu katmandaki kayıtlar (yoksa hepsi) |
| `match` | evet | Alan → değer sözlüğü. Eşleşme **kısmidir**: yalnızca burada yazılan alanlar karşılaştırılır, hepsi eşit olmalıdır. Boş sözlük her kaydı eşler. |
| `within` | hayır | GeoJSON dosyası (kural dosyasının yanında, göreli yol). Kaydın **konumu** (nokta feature'ında kendi konumu, alan feature'ında alanın merkezi) dosyadaki poligonlardan birinin içindeyse koşul tutar. |
| `except` | hayır | İstisna. Kural eşleşse bile istisna tutarsa kayıt ELENMEZ. Desteklenen anahtar: `name_contains` (kaydın `name` alanı bu metni içeriyorsa — büyük/küçük harf duyarsız). |

Konumu hesaplamak çağıranın işidir (`matches(fields, location=…)`):
alan merkezinin antimeridyene karşı güvenli geometriden alınması gibi kurallar
feature türüne özgüdür.

Örnek:

```json
[
  { "layer": "designatedPoints",
    "match": { "designator": "KULAR", "originator": "DHMI TURKIYE" } },
  { "layer": "airspaces",
    "match": { "provider": "Jeppesen" },
    "within": "lt-fir.geojson",
    "except": { "name_contains": "FREE RT" } }
]
```

Kurallar `remap` girdisi üretmez: iptal edilen bir kayda başka bir feature
referans veriyorsa referans kırık kalır. Kural yazmadan önce referanslar
sayılmalıdır.
"""

import json
from pathlib import Path

from shapely.geometry import Point, shape
from shapely.ops import unary_union
from shapely.prepared import prep

SUPPORTED_EXCEPT = {"name_contains"}


def _load_polygons(path: Path):
    """GeoJSON → hazırlanmış (prepared) tek geometri."""
    data = json.loads(path.read_text(encoding="utf-8"))
    features = data.get("features", []) if data.get("type") == "FeatureCollection" \
        else [data]
    geoms = [shape(f["geometry"]) for f in features if f.get("geometry")]
    geoms = [g if g.is_valid else g.buffer(0) for g in geoms]
    if not geoms:
        raise ValueError(f"{path.name}: poligon yok")
    return prep(unary_union(geoms))


class ExcludeRules:
    """Yüklenmiş iptal kuralları; `matches()` ile sorgulanır."""

    def __init__(self, rules=None):
        self.rules = rules or []
        self.hits = 0
        self.per_rule = [0] * len(self.rules)
        #: `within` kuralı konumsuz bir kayda denk geldi (test edilemedi).
        self.location_missing = 0
        #: Kural tuttu ama `except` kaydı korudu.
        self.excepted = [0] * len(self.rules)

    @classmethod
    def load(cls, directory: Path, log=None):
        rules = []
        if not directory.exists():
            return cls(rules)
        for path in sorted(directory.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except ValueError as exc:
                if log:
                    log.error("exclude", path.name, "-", str(exc),
                              "iptal_kurali_okunamadi")
                continue
            if isinstance(data, dict):
                data = data.get("rules", [])
            for rule in data:
                if not isinstance(rule, dict) or "match" not in rule:
                    if log:
                        log.error("exclude", path.name, "-", str(rule),
                                  "gecersiz_iptal_kurali")
                    continue
                exc = rule.get("except") or {}
                unknown = set(exc) - SUPPORTED_EXCEPT
                if unknown:
                    raise ValueError(f"{path.name}: desteklenmeyen except "
                                     f"anahtari {sorted(unknown)}")
                within = None
                if rule.get("within"):
                    within = _load_polygons(path.parent / rule["within"])
                rules.append({"layer": rule.get("layer"),
                              "match": rule["match"],
                              "within": within,
                              "within_file": rule.get("within"),
                              "except": exc,
                              "source": path.name})
        return cls(rules)

    def __len__(self):
        return len(self.rules)

    @staticmethod
    def _excepted(rule, fields) -> bool:
        needle = rule["except"].get("name_contains")
        if needle:
            name = fields.get("name") or ""
            if needle.upper() in name.upper():
                return True
        return False

    def matches(self, fields: dict, location=None) -> dict | None:
        """Eşleşen ilk kuralı döner (yoksa None).

        `location`: `within` kuralları için `(lon, lat)` — nokta feature'ında
        kendi konumu, alan feature'ında merkezi. Verilmezse `within` taşıyan
        kurallar bu kayıt için tutmaz ve `location_missing` sayacı artar.
        """
        for n, rule in enumerate(self.rules):
            if rule["layer"] and rule["layer"] != fields.get("layer"):
                continue
            if not all(fields.get(k) == v for k, v in rule["match"].items()):
                continue
            if rule["within"] is not None:
                if location is None:
                    self.location_missing += 1
                    continue
                if not rule["within"].contains(Point(location)):
                    continue
            if self._excepted(rule, fields):
                self.excepted[n] += 1
                continue
            self.hits += 1
            self.per_rule[n] += 1
            return rule
        return None

    def summary(self) -> list[tuple[str, int]]:
        return [(f'{r["source"]}:{r.get("layer") or "*"}', n)
                for r, n in zip(self.rules, self.per_rule)]
