"""Birleştiricilerin ortak hata günlüğü — `errored-features.csv`.

Her aşama (1, 2A, 2B) aynı dosyaya yazar. Sütunlar:
`stage, layer, record_identifier, field, value, violation, severity`.
"""

import csv
from collections import Counter
from pathlib import Path


class BuildLog:
    COLUMNS = ("stage", "layer", "record_identifier", "field", "value",
               "violation", "severity")

    def __init__(self, path: Path):
        self._fh = open(path, "w", encoding="utf-8", newline="")
        self._csv = csv.writer(self._fh)
        self._csv.writerow(self.COLUMNS)
        self.counts = Counter()

    def log(self, stage, layer, ident, field, value, violation, severity):
        self.counts[violation] += 1
        self._csv.writerow([stage, layer, ident, field, value, violation, severity])

    def error(self, stage, layer, ident, field, value, violation):
        self.log(stage, layer, ident, field, value, violation, "error")

    def warning(self, stage, layer, ident, field, value, violation):
        self.log(stage, layer, ident, field, value, violation, "warning")

    def info_count(self, violation):
        """Yalnızca sayaç (dosyaya satır yazmaz)."""
        self.counts[violation] += 1

    def summary(self):
        return dict(sorted(self.counts.items()))

    def close(self):
        self._fh.close()
