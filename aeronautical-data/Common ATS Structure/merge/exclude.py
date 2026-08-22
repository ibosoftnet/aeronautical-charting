"""İptal (exclude) modülü — kural dosyalarına uyan kayıtları çıkarır.

Ana kaynaklar yüklendikten sonra, ek kaynaklar eklenmeden önce çalışır.

Kural dosyaları `data-sources/excludes/*.json` altındadır. Her dosya bir kural
listesi taşır; her kural bir `layer` ve bir `match` sözlüğüdür. `match`
içindeki tüm alanlar feature'ın doğal anahtar alanlarıyla (`keys.natural_fields`)
eşleşirse kayıt çıkarılır.

Yapı bilinçli olarak jeneriktir — yalnızca rota segmentine özel değildir.
Şu an klasör boş, dolayısıyla modül no-op çalışır.

Örnek kural dosyası:

```json
[
  { "layer": "routeSegments",
    "match": { "route": "UL210", "start": "UMIMI", "end": "BORDO" } },
  { "layer": "designatedPoints",
    "match": { "designator": "ABCDE", "originator": "EUROCONTROL NMOC" } }
]
```
"""

import json
from pathlib import Path


class ExcludeRules:
    """Yüklenmiş iptal kuralları; `matches()` ile sorgulanır."""

    def __init__(self, rules=None):
        self.rules = rules or []
        self.hits = 0
        self.per_rule = [0] * len(self.rules)

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
                rules.append({"layer": rule.get("layer"),
                              "match": rule["match"],
                              "source": path.name})
        return cls(rules)

    def __len__(self):
        return len(self.rules)

    def matches(self, fields: dict) -> dict | None:
        """Eşleşen ilk kuralı döner (yoksa None)."""
        for n, rule in enumerate(self.rules):
            if rule["layer"] and rule["layer"] != fields.get("layer"):
                continue
            if all(fields.get(k) == v for k, v in rule["match"].items()):
                self.hits += 1
                self.per_rule[n] += 1
                return rule
        return None

    def summary(self) -> list[tuple[str, int]]:
        return [(f'{r["source"]}:{r.get("layer") or "*"}', n)
                for r, n in zip(self.rules, self.per_rule)]
