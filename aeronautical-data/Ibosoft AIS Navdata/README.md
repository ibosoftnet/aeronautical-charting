# Ibosoft AIS Navdata

Ibosoft AIS'in navigasyon verisi üretim projeleri. Her proje birden çok
kaynağın ham verisini **AIXM 5.2**'ye çevirir, kaynakları tek bir AIXM
dosyasında birleştirir ve QGIS/harita servisleri için **GeoPackage** üretir.

```
Ibosoft AIS Navdata/
├── common/          ortak altyapı: Python paketi, AIXM extension şeması, ortak dokümanlar
├── data-ats/        ATS yapısı: designated point, navaid, rota, change over point
└── data-airspace/   hava sahaları
```

## Akış (iki projede de aynı)

```
ham veri ──▶ AŞAMA 1  kaynak üreticileri ──▶ data-sources/<kaynak>/<…>-aixm.xml
             (her kaynak kendi başına XSD-geçerli AIXM 5.2 yazar; her feature
              kendi veri kökeni (provenance) kutusunu taşır)
                         │
             AŞAMA 2A  birleştirici ──▶ navdata/<proje>-aixm.xml
             (ana kaynaklar → iptal kuralları → ek kaynaklar / override)
                         │
             AŞAMA 2B  GeoPackage ──▶ navdata/<proje>.gpkg
             (yalnızca birleşik AIXM'den, saf şema eşlemesi)
```

| Proje | Çalıştırma | Çıktı (`navdata/`) |
|---|---|---|
| `data-ats` | `start-full-build.bat` ya da `py build_common_ats.py --sources --merge --gpkg` | `ibosoft-ais-navdata-ats-aixm.xml`, `ibosoft-ais-navdata-ats.gpkg` (log: `logs/errored-features.csv`) |
| `data-airspace` | `start-full-build.bat` ya da `py build_common_airspaces.py --sources --merge --gpkg` | `ibosoft-ais-navdata-airspaces-aixm.xml`, `ibosoft-ais-navdata-airspaces.gpkg` (log: `logs/errored-features.csv`) |

Aşamalar ayrı ayrı da çalıştırılabilir (`--sources`, `--merge`, `--gpkg`).
GeoPackage QGIS'te açıksa dosya kilitli olur; önce kapatın.

## Dokümanlar

| Ne | Nerede |
|---|---|
| Ortak paket, iptal kuralı biçimi | [`common/README.md`](common/README.md) |
| AIXM extension şeması (provenance kutusu, COP, Airspace) | [`common/docs/Ibosoft_AIS_Extension.md`](common/docs/Ibosoft_AIS_Extension.md) |
| İki projenin ortak kullandığı AIXM yapıları | [`common/docs/`](common/docs/) |
| ATS builder davranışı / GeoPackage şeması | [`data-ats/Common_Builder_Behaviour.md`](data-ats/Common_Builder_Behaviour.md), [`data-ats/AIXM_to_GeoPackage_Schema_Design.md`](data-ats/AIXM_to_GeoPackage_Schema_Design.md) |
| ATS AIXM kılavuzları | [`data-ats/docs/`](data-ats/docs/) |
| Airspace builder davranışı / GeoPackage şeması | [`data-airspace/Common_Builder_Behaviour.md`](data-airspace/Common_Builder_Behaviour.md), [`data-airspace/AIXM_to_GeoPackage_Schema_Design.md`](data-airspace/AIXM_to_GeoPackage_Schema_Design.md) |
| Airspace AIXM kılavuzu | [`data-airspace/docs/`](data-airspace/docs/) |
| Ham veri → AIXM eşlemeleri | her projede `data-sources/<kaynak>/generate-aixm-data/*_Mapping.md` |

**Doküman yerleşim kuralı:** `common/docs/` yalnızca iki projenin de kullandığı
yapıları anlatır; bir feature'a özgü kılavuz o feature'ı işleyen projenin
`docs/` dizinindedir.

## Ham veriyi kim yazar

| Kaynak | İndirici | Hedef |
|---|---|---|
| DHMİ (LT) ATS + hava sahası | `D:\ibosoft\AIS\navdata-data-downloaders\lt-dhmi` | `data-ats/data-sources/LT/raw-data`, `data-airspace/data-sources/LT/raw-data` (+ iki `data.json`'ın `data_effectivity`'si) |
| EUROCONTROL EAD SDO | `D:\ibosoft\AIS\navdata-eurocontrol-sdo-downloader` | `data-ats/data-sources/EAD-SDO/raw-data` (+ `data.json`) |
| Jeppesen (Navigraph) | elle | `aeronautical-data/Jeppesen Data/jeppesen.sqlite` (+ `data.json`) — iki proje de okur |

İndiriciler üretici çalıştırmaz; yeni veriden sonra ilgili projenin tam
build'i çalıştırılır.

> Eski `aeronautical-data/Common Airspaces` projesi silinmedi ama artık
> güncellenmiyor (indirici yeni yere yazıyor). Eski `Common ATS Structure`
> dizini `data-ats`'e taşındı.
