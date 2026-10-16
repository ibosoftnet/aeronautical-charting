# common — ortak altyapı

`data-ats` ve `data-airspace` projelerinin ortak kullandığı kod, şema ve
dokümanlar. Buraya yalnızca **kaynaktan ve feature türünden bağımsız olduğu
doğrulanan** parçalar girer; bir projeye özgü mantık (ATS doğal anahtarları,
airspace geometri hesabı vb.) o projede kalır.

```
common/
├── data_build_common/       Python paketi
├── schemas/
│   └── ibosoftais-extension.xsd
└── docs/                    iki projenin ortak kullandığı AIXM konuları
```

## Kullanım

Paket kurulmaz; her betik `common/`'u dosya konumundan göreli olarak
`sys.path`'e ekler (makineye özgü mutlak yol yok):

```python
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR.parent / "common"))            # birleştirici
sys.path.insert(0, str(BASE_DIR.parents[3] / "common"))        # data-sources/<k>/generate-aixm-data/
```

## `data_build_common` modülleri

| Modül | İçerik | Kullanan |
|---|---|---|
| `aixm_reader.py` | Namespace'ler (`NS_IBOSOFTAIS` tek tanım yeri), akış modunda `iter_members`, `feature_of`, `time_slice`, `uuid_of`, `gml_id_of`, `text_of`, `href_of` | iki birleştirici, ATS `merge/aixm_reader.py` (üzerine ATS'ye özgü yardımcılar ekler) |
| `aixm_writer.py` | `MergedMessageWriter` (birleşik dosya, akış modu), `root_open_tag`, `strip_ns_declarations` | iki birleştirici, akış modunda yazan üreticiler |
| `provenance.py` | Provenance kutusunu yazma (`append_box`) / okuma (`read`, `require`) | tüm üreticiler, iki birleştirici, iki GeoPackage eşleyicisi |
| `exclude.py` | İptal kuralları (`ExcludeRules`) — aşağıda | iki birleştirici |
| `override.py` | `OverrideIndex`: doğal anahtar → kazanan kayıt, konum yedeği | iki birleştirici (anahtarın ne olduğu projeye özgü) |
| `aixm_fields.py` | Her katmanda aynı eşlenen sütun aileleri: `annotation*`, `data_*`, `aixm_*` (kimlik + TimeSlice/feature tabanı); tekrarlanan yapıların JSON'a çevrilmesi (`element_to_dict`, `json_list`) | iki GeoPackage eşleyicisi |
| `gpkg_writer.py` | GeoPackage 1.3: tablo kurulumu, satır yazımı, geometri blob'ları (nokta, çizgi, her shapely geometrisi), RTree + tüm sütunlarda B-tree index | iki 2B aşaması |
| `build_log.py` | `BuildLog` → `errored-features.csv` | iki birleştirici |
| `validate_aixm.py` | Tek XSD doğrulayıcı: AIXM 5.2 seti + extension şeması birlikte derlenir | elle ya da `validate.bat` ile |

### Doğrulama

```bash
py common/data_build_common/validate_aixm.py <aixm.xml> [<aixm.xml> …]
```

Extension şeması **her zaman** derlenir (üretilen her feature bir provenance
kutusu taşır; şemasız doğrulama her dosyayı geçersiz sayardı). Şema dosyası
yoksa doğrulama durur. AIXM 5.2 XSD'nin yolu modülün başındadır (`XSD`).

## İptal kuralları (`exclude.py`)

Kural dosyaları projenin `data-sources/excludes/*.json` dizinindedir. Kural
alanları:

| Alan | Zorunlu | Anlamı |
|---|---|---|
| `layer` | hayır | Yalnızca bu katmandaki kayıtlar |
| `match` | evet | Alan → değer. Eşleşme **kısmidir**: yalnızca yazılan alanlar karşılaştırılır, hepsi eşit olmalı. Bir kural birden çok kaydı eleyebilir — kural sayısı ≠ isabet sayısı |
| `within` | hayır | GeoJSON dosyası (kural dosyasının yanında). Kaydın **konumu** — nokta feature'ında kendi konumu, alan feature'ında alanın **merkezi** — dosyadaki poligonlardan birinin içindeyse koşul tutar |
| `except` | hayır | İstisna; kural tutsa bile kayıt elenmez. Desteklenen: `name_contains` (büyük/küçük harf duyarsız). Bilinmeyen anahtar yükleme sırasında hata verir |

`match` alanlarının adları projenin doğal alanlarıdır: ATS'de
`data-ats/merge/keys.py:natural_fields` (`designator`, `type`, `originator`,
`route`, `start`, `end` …), airspace'te `build_common_airspaces.describe`
(`provider`, `originator`, `type`, `designator`, `name`).

> **İptal `remap` üretmez.** İptal edilen bir kayda başka bir feature referans
> veriyorsa referans kırık kalır; kural yazmadan önce referanslar sayılmalıdır
> (ATS: `Common_Builder_Behaviour.md` §4.7).

`within` kuralının konumsuz bir kayda denk gelmesi (`location_missing`) ve
istisnayla korunan kayıtlar (`excepted`) sayılır ve birleştirici özetinde
basılır.

## Provenance kutusu

Tanım ve örnek: [`docs/Ibosoft_AIS_Extension.md`](docs/Ibosoft_AIS_Extension.md).
Kısaca: üretici her feature'ın TimeSlice'ının **sonuna** ayrı bir
`aixm:extension` içinde `ibosoftais:<F>DataProvenance` kutusu ekler;
birleştirici ve GeoPackage değerleri kutudan okur. Kutusu olmayan feature hata
sayılır — varsayılan değer atanmaz.
