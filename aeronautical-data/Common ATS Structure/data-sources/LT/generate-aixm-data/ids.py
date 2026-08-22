"""AIXM kimlik üretimi: okunabilir gml:id + deterministik gml:identifier (UUID5).

Kullanıcı kararı: DHMİ'nin kendi `kid` uuid'si kullanılmaz; tüm kimlikler
kaynak türü + anahtardan deterministik olarak üretilir (aynı girdi → aynı
kimlik, her çalıştırmada tutarlı).
"""

import re
import uuid

# Bu projeye özgü sabit UUID5 namespace'i (rastgele üretilmiş, sabitlenmiştir).
NAMESPACE = uuid.UUID("6f1c3b52-9d4a-5e77-b8c1-2a0e94f7d310")


def feature_uuid(kind: str, key: str) -> str:
    """Feature türü + anahtar için deterministik UUID5 (büyük harf)."""
    return str(uuid.uuid5(NAMESPACE, f"{kind}:{key}")).upper()


def _ncname(text: str) -> str:
    """gml:id için geçerli NCName üretir (harf/alt çizgi ile başlar)."""
    cleaned = re.sub(r"[^A-Za-z0-9_.-]", "_", (text or "").strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    if not cleaned or not re.match(r"[A-Za-z_]", cleaned):
        cleaned = "X" + cleaned
    return cleaned


class IdRegistry:
    """Okunabilir gml:id üretir ve benzersizliğini garanti eder.

    `source_prefix` her id'nin başına eklenir (örn. `LT_RS_0001`) — böylece
    farklı kaynaklardan gelen AIXM dosyaları tek bir GeoPackage'da birleşince
    gml:id'ler karışmaz. Türetilmiş id'ler (`_TS`, `_P`, `_NOTE` …) zaten
    önekli id'den üretildiği için öneki otomatik miras alır.
    """

    def __init__(self, source_prefix: str = ""):
        self._used: set[str] = set()
        self._source = source_prefix.strip("_")

    def make(self, prefix: str, key: str) -> str:
        # NCName temizliği birleşik id üzerinde yapılır; yalnızca anahtara
        # uygulanırsa "RS" + "0001" → gereksiz yere "RS_X0001" olurdu.
        return self._unique(_ncname("_".join(
            p for p in (self._source, prefix, key) if p)))

    def child(self, parent_id: str, suffix: str) -> str:
        """Bir feature'ın içindeki nesneler için türetilmiş id (benzersiz).

        `parent_id` zaten kaynak önekini taşıdığı için önek tekrar eklenmez.
        """
        return self._unique(_ncname(f"{parent_id}_{suffix}"))

    def _unique(self, base: str) -> str:
        candidate = base
        n = 1
        while candidate in self._used:
            n += 1
            candidate = f"{base}_{n}"
        self._used.add(candidate)
        return candidate
