r"""Üretilen AIXM dosyasını AIXM 5.2 XSD setine karşı doğrular.

Kullanım:
    py validate_aixm.py              → ../ead-sdo-aixm.xml
    py validate_aixm.py <dosya> …    → belirtilen dosyalar

Notlar:
  * `lxml` gerekir (`pip install lxml`).
  * AIXM 5.2 şeması GML 3.2.1'i **uzaktan** import eder
    (http://schemas.opengis.net/gml/3.2.1/gml.xsd) — şema derlemesi internet
    gerektirir ve birkaç dakika sürebilir. Derleme bir kez yapılır.
  * Dosya akış (streaming) modunda doğrulanır; 460 MB'lik çıktı da düşük
    bellekle işlenir.
"""

import sys
import time
from pathlib import Path

try:
    from lxml import etree
except ImportError:
    print("HATA: lxml kurulu degil.  pip install lxml")
    raise SystemExit(1)

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_TARGET = BASE_DIR.parent / "ead-sdo-aixm.xml"

XSD = Path(
    r"D:\Belgeler\Havacılık Kütüphanesi\Charts, Guides, Regulations"
    r"\Other Documents\Aeronautical Information Exchange Model (AIXM)"
    r"\Scheme and Data AIXM 5.2\aixm_5_2_0_xsd\message\AIXM_BasicMessage.xsd"
)
HAS_MEMBER = "{http://www.aixm.aero/schema/5.2/message}hasMember"

#: Bu projenin kendi AIXM extension şeması. AIXM'in resmi genişletme
#: mekanizmasıyla (`aixm:AbstractExtension` ikame grubu) yazdığımız alanlar
#: burada tanımlıdır; şema DERLEMEYE KATILMAZSA bu alanları taşıyan dosyalar
#: "geçersiz" görünür — çünkü stok AIXM seti bizim elemanımızı tanımaz.
#: Dosya yoksa doğrulama eskisi gibi yalnız stok AIXM setiyle yapılır.
EXTENSION_XSD = (BASE_DIR.parent.parent.parent
                 / "schemas" / "ibosoftais-extension.xsd")

#: Hem AIXM setini hem extension şemasını tek derlemede toplayan sarmalayıcı.
#: Kendi targetNamespace'i yoktur — yalnızca iki şemayı aynı küme içine alır
#: (XSD "schema assembly" deseni). Extension şeması `aixm` namespace'ini
#: schemaLocation'sız import ettiği için asıl AIXM dosyasını buradaki import
#: sağlar; böylece makineye özgü mutlak yol tek yerde (bu dosyada) kalır.
_WRAPPER = """<?xml version="1.0" encoding="UTF-8"?>
<schema xmlns="http://www.w3.org/2001/XMLSchema">
  <import namespace="http://www.aixm.aero/schema/5.2/message"
          schemaLocation="{message}"/>
  <import namespace="http://www.aixm.aero/schema/5.2"
          schemaLocation="{aixm}"/>
  <import namespace="{ext_ns}" schemaLocation="{ext}"/>
</schema>
"""

EXTENSION_NS = ("https://cdn.ibosoft.net.tr/aviation-data"
                "/schema/aixm/5.2/extension")


def _load_schema():
    """Doğrulama şemasını derler.

    Extension şeması varsa stok AIXM setiyle BİRLİKTE derlenir; yoksa
    yalnızca stok set kullanılır (eski davranış birebir korunur).
    """
    if not EXTENSION_XSD.exists():
        print(f"UYARI: extension semasi yok, yalnizca stok AIXM seti "
              f"derlenecek:\n  {EXTENSION_XSD}")
        return etree.XMLSchema(etree.parse(str(XSD)))

    wrapper = _WRAPPER.format(
        message=XSD.as_uri(),
        aixm=(XSD.parent.parent / "AIXM_Features.xsd").as_uri(),
        ext_ns=EXTENSION_NS,
        ext=EXTENSION_XSD.as_uri(),
    )
    print(f"  + extension semasi: {EXTENSION_XSD.name}", flush=True)
    return etree.XMLSchema(etree.fromstring(wrapper.encode("utf-8")))


def main(targets):
    if not XSD.exists():
        print(f"HATA: XSD bulunamadi:\n  {XSD}")
        return 1

    t0 = time.time()
    print("Sema derleniyor (GML 3.2.1 uzaktan indiriliyor, birkac dakika)...",
          flush=True)
    schema = _load_schema()
    print(f"Sema hazir ({time.time() - t0:.0f} sn)\n", flush=True)

    failed = 0
    for target in targets:
        path = Path(target)
        if not path.exists():
            print(f"ATLANDI  {path.name} (dosya yok)")
            failed += 1
            continue
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
                  f"({n} feature, {time.time() - t:.0f} sn)")
        except etree.XMLSyntaxError as e:
            failed += 1
            print(f"GECERSIZ {path.name}  ({n} feature islendikten sonra)")
            print(f"   {e}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:] or [DEFAULT_TARGET]))
