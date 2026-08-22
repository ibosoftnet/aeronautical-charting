"""Provenance yan dosyası yazıcısı.

AIXM'de provenance alanı yoktur; ayrıca birleşik dosyada her feature farklı bir
kaynaktan geldiği için tek bir `data.json` da yeterli değildir. Bu yüzden 2A,
`gml:id` anahtarlı bir yan dosya üretir ve **üç alanı birden** taşır:
`data_provider`, `data_originator`, `data_effectivity`.

Dosya, sözlüğü bellekte biriktirmeden **akış modunda** yazılır — birleşik
dosyada ~285.000 feature var.
"""

import json


class ProvenanceWriter:
    """`{gml_id: {provider, originator, effectivity}}` JSON nesnesi."""

    def __init__(self, path):
        self._fh = open(path, "w", encoding="utf-8")
        self._fh.write("{\n")
        self.count = 0

    def add(self, gml_id: str, provider: str, originator: str, effectivity: str):
        entry = {
            "data_provider": provider or "",
            "data_originator": originator or "",
            "data_effectivity": effectivity or "",
        }
        prefix = "" if self.count == 0 else ",\n"
        self._fh.write(
            f'{prefix} {json.dumps(gml_id, ensure_ascii=False)}: '
            f'{json.dumps(entry, ensure_ascii=False)}')
        self.count += 1

    def close(self):
        self._fh.write("\n}\n")
        self._fh.close()
