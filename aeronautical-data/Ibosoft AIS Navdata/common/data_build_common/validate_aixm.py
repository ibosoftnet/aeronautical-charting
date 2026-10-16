r"""AIXM dosyalarını AIXM 5.2 XSD seti + Ibosoft AIS extension şemasına karşı
doğrular. Tüm projelerin (data-ats, data-airspace) tek doğrulayıcısıdır.

Kullanım:
    py validate_aixm.py <dosya> [<dosya> …]

Notlar:
  * `lxml` gerekir (`pip install lxml`).
  * AIXM 5.2 şeması GML 3.2.1'i **uzaktan** import eder
    (http://schemas.opengis.net/gml/3.2.1/gml.xsd) — şema derlemesi internet
    gerektirir ve birkaç dakika sürebilir. Derleme bir kez yapılır.
  * Extension şeması (`common/schemas/ibosoftais-extension.xsd`) HER ZAMAN
    derlemeye katılır: üretilen her feature bir provenance kutusu taşıdığı
    için şemasız doğrulama her dosyayı geçersiz sayardı. Şema yoksa doğrulama
    durur (eksik şemayla "geçerli" demek yanıltıcı olurdu).
  * Dosya akış (streaming) modunda doğrulanır; ilk hatada durur ve hatanın
    satırını bildirir.
"""

import sys
import time
from pathlib import Path

try:
    from lxml import etree
except ImportError:
    print("HATA: lxml kurulu degil.  pip install lxml")
    raise SystemExit(1)

COMMON_DIR = Path(__file__).resolve().parent.parent

XSD = Path(
    r"D:\Belgeler\Havacılık Kütüphanesi\Charts, Guides, Regulations"
    r"\Other Documents\Aeronautical Information Exchange Model (AIXM)"
    r"\Scheme and Data AIXM 5.2\aixm_5_2_0_xsd\message\AIXM_BasicMessage.xsd"
)
HAS_MEMBER = "{http://www.aixm.aero/schema/5.2/message}hasMember"

EXTENSION_XSD = COMMON_DIR / "schemas" / "ibosoftais-extension.xsd"
EXTENSION_NS = ("https://cdn.ibosoft.net.tr/aviation-data"
                "/schema/aixm/5.2/extension")

#: Hem AIXM setini hem extension şemasını tek derlemede toplayan sarmalayıcı
#: (XSD "schema assembly" deseni). Extension şeması `aixm` namespace'ini
#: schemaLocation'sız import ettiği için asıl AIXM dosyasını buradaki import
#: sağlar; makineye özgü mutlak yol tek yerde (bu dosyada) kalır.
_WRAPPER = """<?xml version="1.0" encoding="UTF-8"?>
<schema xmlns="http://www.w3.org/2001/XMLSchema">
  <import namespace="http://www.aixm.aero/schema/5.2/message"
          schemaLocation="{message}"/>
  <import namespace="http://www.aixm.aero/schema/5.2"
          schemaLocation="{aixm}"/>
  <import namespace="{ext_ns}" schemaLocation="{ext}"/>
</schema>
"""


def load_schema():
    """Doğrulama şemasını derler (AIXM 5.2 + extension)."""
    if not XSD.exists():
        raise SystemExit(f"HATA: XSD bulunamadi:\n  {XSD}")
    if not EXTENSION_XSD.exists():
        raise SystemExit(f"HATA: extension semasi bulunamadi:\n  {EXTENSION_XSD}")
    wrapper = _WRAPPER.format(
        message=XSD.as_uri(),
        aixm=(XSD.parent.parent / "AIXM_Features.xsd").as_uri(),
        ext_ns=EXTENSION_NS,
        ext=EXTENSION_XSD.as_uri(),
    )
    return etree.XMLSchema(etree.fromstring(wrapper.encode("utf-8")))


def validate_file(schema, path: Path) -> bool:
    """Tek dosya; sonucu yazdırır, geçerliyse True."""
    if not path.exists():
        print(f"ATLANDI  {path.name} (dosya yok)")
        return False
    t = time.time()
    n = 0
    try:
        ctx = etree.iterparse(str(path), events=("end",), schema=schema,
                              tag=HAS_MEMBER)
        for _, el in ctx:
            n += 1
            el.clear()
            while el.getprevious() is not None:
                del el.getparent()[0]
        print(f"GECERLI  0 hata  {path.name}  "
              f"({n} feature, {time.time() - t:.0f} sn)", flush=True)
        return True
    except etree.XMLSyntaxError as e:
        print(f"GECERSIZ {path.name}  ({n} feature islendikten sonra)")
        print(f"   {e}", flush=True)
        return False


def main(targets):
    if not targets:
        print(__doc__)
        return 2
    t0 = time.time()
    print("Sema derleniyor (GML 3.2.1 uzaktan indiriliyor, birkac dakika)...",
          flush=True)
    schema = load_schema()
    print(f"  + extension semasi: {EXTENSION_XSD.name}")
    print(f"Sema hazir ({time.time() - t0:.0f} sn)\n", flush=True)
    failed = sum(0 if validate_file(schema, Path(t)) else 1 for t in targets)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
