"""errored-features.log yazıcı. Her çalıştırmada dosya sıfırlanır."""

import re
from pathlib import Path

# AIXM'de her Code*Type bir union'dır: sabit enum listesi VEYA
# OTHER(:(\w|_){1,58})? deseni. Dolayısıyla "OTHER" ve "OTHER:XYZ" her
# enum alanında geçerli değerlerdir.
OTHER_RE = re.compile(r"^OTHER(:(\w|_){1,58})?$")


class ErrorLog:
    """Satır formatı: SEVERITY | feature | kimlik | alan | değer | ihlal"""

    def __init__(self, path: Path):
        self.path = path
        self.counts: dict[str, int] = {}
        # 'w' modu: her çalıştırmada sıfırlanır.
        self._fh = open(path, "w", encoding="utf-8")
        self._fh.write("SEVERITY | FEATURE | ID | FIELD | VALUE | VIOLATION\n")

    def log(self, severity, feature, ident, field, value, violation):
        self.counts[violation] = self.counts.get(violation, 0) + 1
        parts = [severity, feature, str(ident), str(field), str(value), violation]
        self._fh.write(" | ".join(p.replace("|", "/") for p in parts) + "\n")

    def error(self, feature, ident, field, value, violation):
        self.log("ERROR", feature, ident, field, value, violation)

    def warning(self, feature, ident, field, value, violation):
        self.log("WARNING", feature, ident, field, value, violation)

    def check_enum(self, feature, ident, field, value, allowed):
        """Değer enum'da veya OTHER deseninde değilse loglar ve False döner."""
        if not value:
            return True
        if value in allowed or OTHER_RE.match(value):
            return True
        self.error(feature, ident, field, value, "enum_disi_deger")
        return False

    def summary(self) -> dict:
        return dict(sorted(self.counts.items()))

    def close(self):
        self._fh.close()


class NotesFile:
    """not.txt — kaynak verisi bozuk olduğu için ALANI düşürülen kayıtların
    dökümü. Kayıt XML'e girer, yalnızca hatalı alan yazılmaz; doğru değerin
    elle eklenebilmesi için tüm kaynak alanları burada listelenir.
    Her çalıştırmada sıfırlanır."""

    def __init__(self, path: Path):
        self.path = path
        self.count = 0
        self._fh = open(path, "w", encoding="utf-8")
        self._fh.write(
            "HATALI ALANI DUSURULEN KAYITLAR\n"
            "Bu kayitlar XML'e eklenmistir, ancak kaynak degeri gecersiz olan\n"
            "alan(lar) yazilmamistir. Dogru degerler elle eklenmelidir.\n"
            "(Bozuk deger otomatik DUZELTILMEZ - her ay tekrar gelebilir.)\n"
            + "=" * 70 + "\n"
        )

    def add(self, feature, ident, reasons, source_record):
        self.count += 1
        self._fh.write(f"\n[{self.count}] {feature} / {ident}\n")
        for r in reasons:
            self._fh.write(f"  SEBEP: {r}\n")
        self._fh.write("  KAYNAK ALANLARI:\n")
        for k, v in source_record.items():
            self._fh.write(f"    {k} = {v}\n")

    def close(self):
        if self.count == 0:
            self._fh.write("\n(Bu calistirmada dusurulen alan yok.)\n")
        self._fh.close()
