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


def main(targets):
    if not XSD.exists():
        print(f"HATA: XSD bulunamadi:\n  {XSD}")
        return 1

    t0 = time.time()
    print("Sema derleniyor (GML 3.2.1 uzaktan indiriliyor, birkac dakika)...",
          flush=True)
    schema = etree.XMLSchema(etree.parse(str(XSD)))
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
