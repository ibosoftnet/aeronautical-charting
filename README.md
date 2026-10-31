# Ibosoft Aeronautical Charting

QGIS projects, ICAO Annex 4 symbols and templates for producing aeronautical charts.
Havacılık haritası üretimi için QGIS projeleri, ICAO Annex 4 sembolleri ve şablonlar.

![](Images%20About%20Project/image-7.png)

*[Türkçe](#türkçe) aşağıdadır.*

---

## English

### Purpose

- To let individual users prepare their own aeronautical charts for hobby purposes,
  in line with ICAO Standards and Recommended Practices (SARPs).
- The project is also the foundation of the **Ibosoft AIS** interactive web map:
  <https://ibonav.aero/>

### Status

- **Web map:** largely complete. It can also be used to prepare paper ARC/ENC charts.
- **Navigation data:** the project now uses the common AIXM 5.2 based
  **Ibosoft AIS Navigation Data Set** (GeoPackage).
- **Paper chart templates:** AIP AD 2 and chart templates used for LT1401 Bolu Airport
  are included. The full Bolu project is not yet ready to share.
- **Documentation:** not prepared yet.

### Contents

| Item | Description |
|---|---|
| `ibosoft_qgis_aeronautical_web_map.qgz` | Ibosoft AIS web map project (aeronautical layers) |
| `ibosoft_qgis_aeronautical_map_culture.qgz` | Culture layers |
| `ibosoft_qgis_aeronautical_map_terrain.qgz` | Terrain / hydrography layers |
| `ibosoft_qgis_other_layers.qgz` | Other layers |
| `Symbols/` | ICAO Annex 4 SVG symbols, coloured variants, Ibosoft-specific and other symbols |
| `Ibosoft QGIS Symbol Library.xml` | QGIS symbol library |
| `AIP Templates/` | Generic AIP templates and templates used for Bolu AD 2 |
| `Print Layouts/` | Print layouts and legends |
| `README-SETTINGS.md` | QGIS / QGIS Server SVG path setup |

> For current symbol usage, see / Güncel sembol kullanımları için bakınız: <https://ibonav.aero/learn/user-guides/>

### Navigation data

The QGIS projects read the navigation data from a sibling folder:

```
ais-data/
├── aeronautical-charting/   (this repository)
└── aeronautical-data/
    └── Ibosoft AIS Navdata/navdata/   ibosoft-ais-navdata-*.gpkg
```

- **Sample data set** (for trying the project, not kept up to date, not valid for operational use):
  <https://github.com/ibosoftnet/Ibosoft-AIS-Navigation-Data-Set-Sample>
- **Current data set:** published on the Ibosoft AIS Developer Portal: <https://ibonav.aero/>

Place the downloaded `.gpkg` files under `aeronautical-data/Ibosoft AIS Navdata/navdata/`
next to this repository so the relative layer paths resolve.

### Attribute Names
Attribute names are absed on converted AIXM 5.2 feature attributes. If your data source is AIXM based but attribute names difefrs from us, you may need to map them accordingly.

The matching list used by our own data set can be found at: [ibonav.aero Developer Portal](https://dev.ibonav.aero/navdata/introduction)

### Completed

- SVG symbols extracted from ICAO Annex 4 and a QGIS symbol library.
- First charts for Bolu Airport: <https://ibonav.aero/aip-ibosoft>
- AIP AD 2 and chart templates used in the Bolu Airport publications.
- Ibosoft AIS web map with the common AIXM 5.2 based navigation data set.

### Useful links

- **AIXM** — Aeronautical Information Exchange Model (official site): <https://aixm.aero/>
- **qpansopy** — a QGIS plugin for instrument procedure design calculations:
  <https://github.com/FLYGHT7/qpansopy/>

---

## Türkçe

### Amaç

- Bireysel kullanıcıların, ICAO Standartları ve Tavsiye Edilen Uygulamaları (SARPs)
  doğrultusunda hobi amaçlı kendi havacılık haritalarını hazırlayabilmesi.
- Proje aynı zamanda **Ibosoft AIS** etkileşimli web haritasının temelidir:
  <https://ibonav.aero/>

### Durum

- **Web haritası:** büyük ölçüde tamamlandı; kağıt ARC/ENC hazırlamak için de kullanılabilir.
- **Navigasyon verisi:** proje artık AIXM 5.2 tabanlı ortak
  **Ibosoft AIS Navigasyon Veri Seti**'ni (GeoPackage) kullanıyor.
- **Kağıt harita şablonları:** LT1401 Bolu Havaalanı için kullanılan AIP AD 2 ve harita
  şablonları eklendi; Bolu projesinin tamamı henüz paylaşıma hazır değil.
- **Dokümantasyon:** henüz hazırlanmadı.

### Seyrüsefer verisi

QGIS projeleri seyrüsefer verisini kardeş klasörden okur
(`ais-data/aeronautical-data/Ibosoft AIS Navdata/navdata/ibosoft-ais-navdata-*.gpkg`).

- **Örnek veri seti** (projeyi denemek için; güncel tutulmaz, operasyonel olarak geçerli değildir):
  <https://github.com/ibosoftnet/Ibosoft-AIS-Navigation-Data-Set-Sample>
- **Güncel veri seti:** Ibosoft AIS Developer Portal'da yayımlanır: <https://ibonav.aero/>

İndirilen `.gpkg` dosyalarını bu deponun yanındaki
`aeronautical-data/Ibosoft AIS Navdata/navdata/` klasörüne koyun; katman yolları göreli çözülür.

### Öznitelik Adları

Öznitelik adları, dönüştürülmüş AIXM 5.2 özellik özniteliklerini temel alır. Veri kaynağınız AIXM tabanlı olsa bile öznitelik adları bizim kullandığımız adlardan farklı olabilir. Bu durumda, öznitelikleri uygun şekilde eşleştirmeniz gerekebilir.

Kendi veri kümemizde kullanılan eşleştirme listesini [ibonav.aero Geliştirici Portalı](https://dev.ibonav.aero/navdata/introduction?utm_source=chatgpt.com) üzerinden bulabilirsiniz.

### Tamamlananlar

- ICAO Annex 4'ten çıkarılan SVG semboller ve QGIS sembol kütüphanesi.
- Bolu Havaalanı için ilk haritalar: <https://ibonav.aero/aip-ibosoft>
- Bolu Havaalanı yayınlarında kullanılan AIP AD 2 ve harita şablonları.
- Ortak AIXM 5.2 tabanlı navigasyon veri setiyle Ibosoft AIS web haritası.

### Faydalı bağlantılar

- **AIXM** — Aeronautical Information Exchange Model (resmi site): <https://aixm.aero/>
- **qpansopy** — aletli prosedür tasarımı hesaplamaları için QGIS eklentisi:
  <https://github.com/FLYGHT7/qpansopy/>

---

## Related documents / İlgili kaynak dokümanlar

- ICAO Annex 4, Aeronautical Charts — 11th ed., July 2009, Amdt 62
- ICAO Annex 15, Aeronautical Information Services — 16th ed., July 2018
- ICAO Doc 8126, Aeronautical Information Services Manual — 7th ed., 2022, Amdt 1
- ICAO Doc 8697, Aeronautical Chart Manual — 3rd ed., 2016, Amdt 1, Corr 1
- ICAO Doc 8168 (PANS-OPS), Aircraft Operations Vol. I — 6th ed., Amdt 11, 2024
- ICAO Doc 8168 (PANS-OPS), Aircraft Operations Vol. II — 7th ed., Amdt 10, Corr 2, 2024
- ICAO Doc 10066 (PANS-AIM), Aeronautical Information Management — 1st ed., Amdt 3, 2024

## License / Lisans

See [LICENSE](LICENSE).

---

## Sample images / Örnek görseller

Images may not be current. / Görseller güncel olmayabilir.

#### Map views / Harita görünümleri
![](Images%20About%20Project/image-ais1.png)
![](Images%20About%20Project/image-ais2.png)
![](Images%20About%20Project/image_cop.png)
![](Images%20About%20Project/Example-2.png)
![](Images%20About%20Project/image-9847.png)
![](Images%20About%20Project/image-5621.png)
![](Images%20About%20Project/image-3014.png)
![](Images%20About%20Project/image-1.png)
![](Images%20About%20Project/image.png)

#### ICAO Annex 4 symbols / ICAO Annex 4 sembolleri
![](Images%20About%20Project/Symbology-1.png)
![](Images%20About%20Project/Symbology-2.png)
![](Images%20About%20Project/Symbology-3.png)
![](Images%20About%20Project/Symbology-4.png)
![](Images%20About%20Project/Symbology-5.png)
![](Images%20About%20Project/Symbology-6.png)
![](Images%20About%20Project/Symbology-7.png)
![](Images%20About%20Project/Symbology-8.png)

#### Other symbology / Diğer semboloji
![](Images%20About%20Project/image-2.png)
![](Images%20About%20Project/image-6.png)
![](Images%20About%20Project/image-5.png)
