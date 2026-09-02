# Havacılık Haritası Üretimi İçin Kaynaklar ve QGIS Şablonu

![](Images%20About%20Project/image-7.png)

## Amaç / Purpose

**TR:**  
* Bu projenin amacı, bireysel kullanıcıların ICAO standartları ve Standartları ve Tavsiye Edilen Uygulamaları (SARPs) doğrultusunda, hobi amaçlı kendi havacılık haritalarını hazırlayabilmesini sağlamaktır.
* Proje, aynı zamanda Ibosoft AIS etkileşimli haritasının temelini oluşturmaktadır.

**EN:**  
* The aim of this project is to allow individual users to create their own aeronautical charts for hobby purposes, in accordance with ICAO Standards and Recommended Practices (SARPs).
* The project also forms the foundation of the Ibosoft AIS interactive map.

https://ais.ibosoft.net.tr

## Duyuru / Announcement

**TR:**  
Proje aşamaları değiştirilmiştir. İlk olarak Ibosoft AIS web haritası için gerekli bileşenlerin hazırlanması planlanmaktadır. Sonrasında bazı hesaplama araçlarının geliştirilmesinin ardından, kağıt harita üretimi için şablonlar hazırlanacaktır.

**EN:**  
The project roadmap has been revised. The initial focus will be on preparing the components required for the Ibosoft AIS web map. After developing some calculation tools, templates for producing paper charts will be prepared.

## Duyuru 2 / Announcement 2

**TR:**

* Web haritası (Kağıt ARC/ENC hazırlamak için de kullanılabilir) büyük ölçüde tamamlanmıştır.
* Şu anki uğraşı ortak AIXM veritabanı hazırlamak ve projeyi onunla uyumlu hale getirmeye çalışıyorum.
* Kağıt harita üretimi için şablonları, örnek LT1401 - Bolu Havaalanı projemi henüz paylaşıma hazır hale getiremediğim için eksik olarak paylaştım, ileride tam proje dosyasını eklemeyi düşünüyorum.
* Dokümantasyon olmadığı için üzgünüm ne yazık ki henüz hazırlamaya vaktim olmadı.

**EN:**

* The web map (which can also be used to prepare paper ARC/ENC charts) is largely complete.
* I am currently working on preparing a common AIXM database and trying to make the project compatible with it.
* I have shared the templates for paper chart production, but the example LT1401 - Bolu Airport project is incomplete because I have not yet been able to prepare it for release. I plan to add the complete project files in the future.
* I apologize for the lack of documentation. Unfortunately, I have not yet had time to prepare it.

-----

## Dokümantasyon:

Proje henüz erken safhada olduğundan dokümantasyon henüz hazırlanmamıştır.

## Hedeflenen Özellikler:

### Tamamlanan Hedefler:

* ICAO Annex 4'den çıkarılan SVG semboller ve QGIS kütüphane dosyası.
* Bolu Havaalanı için ilk haritalar hazırlandı. [https://ais.ibosoft.net.tr/aip-ibosoft](https://ais.ibosoft.net.tr/aip-ibosoft)
* Bolu Havalanı yayınlarında kullanılan bazı AIP AD 2. ve harita şablonları eklendi. Proje dosyaları ve baskı düzenleri yeterince düzenli olmadığı için henüz paylaşılmadı.

### Üzerinde uğraşılanlar
* Minimum irtifa hesaplayıcı yapıldı, testleri sürüyor. (ICAO MSA, AMA; NATO MEF, Emergency Safe Altitude)

---

![](Images%20About%20Project/Example-2.png)
![](Images%20About%20Project/image-9847.png)
![](Images%20About%20Project/image-5621.png)
![](Images%20About%20Project/image-3014.png)
![](Images%20About%20Project/image-1.png)
![](Images%20About%20Project/image.png)


### ~~Planlanan Hedefler:~~
* ~~Eksik Annex 4 sembolojilerinin tamamlanması.~~
* ~~ICAO Doc 8697 doğrutusunda farklı renklendirmelerin, semboller veya QGIS şablonu üzerinden ayarlanması.~~
* ~~ICAO Doc 8697 ile uyumlu ADC, PRKG, IAC, SID, STAR chartları için QGZ baskı düzeninin oluşturulması.~~
* ~~QGIS için ICAO PANS-OSP uyumlu AMA hesaplayıcı.~~
* ~~QGIS için ICAO PANS-OPS uyumlu PAR OCS alanı oluşturucu.~~

### ~~Daha Sonrası İçin Hedefler:~~
* ~~AOC, PATC, ENC, ARC, VAC, ATCSMAC chartları için QGZ baskı düzenleri.~~
* ~~NATO/MIPS sembolojisi.~~
* ~~QGIS için ICAO PANS-OPS uyumlu MSA hesaplayıcı.~~
* ~~QGIS için ICAO PANS-OPS uyumlu Circling alanı hesaplayıcı.~~
* ~~QGIS için MIPS uyumlu Emergency Safe Altitude 100 NM hesaplayıcı.~~
* ~~Havacılık verisi için diğer kaynaklar yerine gerçek AIXM verilerinin kullanımı.~~

## ~~Test Verisi Hakkında:~~
~~Şablonda görsellik oluşturması için bir test verisi sağlanmaktadır. İlgili katmanların kaynaklarını değiştirerek kendi verilerinizi de kullanabilirsiniz.~~

~~Test verisi, Türkiye'yi kapsayacak şekilde şu kaynaklardan alınmıştır:~~
* ~~Topoğrafya için Antalya bölgesini kapsayacak şekilde, ölçü birimi fit'e dönüştürülmüş SRTM 1 Arc-Second Global 30 m doğruluklu GeoTIFF DEM verisi.~~
* ~~Hidrografya için Geofabrik ve Overpass Turbo aracılığıyla çıktı alınan OSM verileri.~~
* ~~Kültür verisi için Overpass Turbo aracılığıyla çıktı alınan OSM verileri.~~
* ~~Havacılık verisi için EUROCONTROL EAD BAsic'den elde edilen SDO verileri.~~
* ~~Havacılık engel verisi için ENR 5.4 ve Antalya AIXM engel verileri.~~

## Diğer Bilgiler:

### QGIS Chart Üretimi İle Alakalı Faydalı Repository:
* https://github.com/FLYGHT7/qpansopy/
Bu repository, aletli yaklaşma ile alakalı çok daha ileri düzey hesaplayıcıları içeren bir QGIS eklentisidir. Bizim projemiz ise bu eklenti tarafından kapsanan hesaplayıcıları halihazırda yapıldığı için kapsamayacaktır.

### Bize Ait Bazı Kaynaklar:
* QGIS dışı hesaplayıcılar için https://ais.ibosoft.net.tr
* Kaynaklar ve bilgi edinme için https://egitim.ibosoft.net.tr

--- 

# Resources and QGIS Template for Aeronautical Chart Production

## Announcement: Project stages have been changed. First of all, preparations for some requirements for the Ibosoft AIS web map are planned. Afterwards, following the preparation of some calculation tools, templates for paper map production will be prepared.

## Purpose:

This project aims to enable individual users to prepare their own aeronautical charts for hobby purposes in accordance with ICAO standards and SARPs.


## Documentation:

Documentation has not been prepared yet as the project is still in its early stages.

## Target Features:

### Completed Aims:

* SVG symbols extracted from ICAO Annex 4 and QGIS library file (Nearly all point symbols are covered, but there are still deficiencies in line and area symbology.)

### ~~Work in Progress:~~
* ~~Template file for QGIS.~~
* ~~Blank AIP template compatible with ICAO doc 8126 & 10066. (For MS Office Word.)~~

### ~~Planned Aims:~~
* ~~Completion of missing Annex 4 symbologies.~~
* ~~Setting up different colorations in accordance with ICAO Doc 8697 through symbols or QGIS template.~~
* ~~Creation of QGZ print layout for ADC, PRKG, IAC, SID, STAR charts compatible with ICAO Doc 8697.~~
* ~~ICAO PANS-OPS compatible AMA calculator for QGIS.~~
* ~~ICAO PANS-OPS compatible PAR OCS area generator for QGIS.~~

### ~~Future Aims:~~
* ~~QGZ print layouts for AOC, PATC, ENC, ARC, VAC, ATCSMAC charts.~~
* ~~NATO/MIPS symbology.~~
* ~~ICAO PANS-OPS compatible MSA calculator for QGIS.~~
* ~~ICAO PANS-OPS compatible Circling area calculator for QGIS.~~
* ~~MIPS compatible Emergency Safe Altitude 100 NM calculator for QGIS.~~
* ~~Use of real AIXM data instead of other sources for aeronautical data.~~

## ~~About Test Data:~~
~~Test data is provided to create visuality in the template. You can also use your own data by changing the sources of the relevant layers.~~

~~Test data has been obtained from the following sources to cover Turkey:~~
* ~~SRTM 1 Arc-Second Global 30m accuracy GeoTIFF DEM data converted to feet unit covering the Antalya region for topography.~~
* ~~OSM data extracted through Geofabrik and Overpass Turbo for hydrography.~~
* ~~OSM data extracted through Overpass Turbo for cultural data.~~
* ~~SDO data obtained from EUROCONTROL EAD Basic for aeronautical data.~~
* ~~ENR 5.4 and Antalya AIXM obstacle data for aeronautical obstacle data.~~

## Other Information:

### Useful Repository Related to QGIS Chart Production:
* https://github.com/FLYGHT7/qpansopy/
This repository is a QGIS plugin that contains much more advanced calculators related to instrument approach. Our project will not cover calculators that are already covered by this plugin.

### Some of Our Resources:
* For calculators outside QGIS https://ais.ibosoft.net.tr
* For resources and information https://egitim.ibosoft.net.tr

---

## İlgili Kaynak Dokümanlar / Related Resources
* ICAO Annex 4, Aeronautical Charts - 11th edition, July 2009, amend 62
* ICAO Annex 15, Aeronautical Information Services - 16th edition, July 2018
* ICAO doc 8126 Aeronautical Information Services Manual, 7th Ed, 2022, amend 1
* ICAO doc 8697 Aeronautical Chart Manual 3rd Ed, 2016, Amend 1, Corr 1
* ICAO doc 8168 (PANS OPS) Aircraft Operations volume I 6th ed. amend 11, 2024
* ICAO doc 8168 (PANS OPS) Aircraft Operations volume II 7th ed. amend 10 corr 2, 2024
* ICAO doc 10066 (PANS AIM) Aeronautical Information Management 1st ed. amend 3, 2024

---

## Örnek Görseller / Sample Images:
Görseller güncel olmayabilir. / Images may not be current.
#### General Map View
![](Images%20About%20Project/Example-1.png)
![](Images%20About%20Project/Example-2.png)
#### Completed ICAO Annex 4 Symbols:
![](Images%20About%20Project/Symbology-1.png)
![](Images%20About%20Project/Symbology-2.png)
![](Images%20About%20Project/Symbology-3.png)
![](Images%20About%20Project/Symbology-4.png)
![](Images%20About%20Project/Symbology-5.png)
![](Images%20About%20Project/Symbology-6.png)
![](Images%20About%20Project/Symbology-7.png)
![](Images%20About%20Project/Symbology-8.png)
#### Other Symbology:
![](Images%20About%20Project/image-2.png)
![](Images%20About%20Project/image-6.png)
![](Images%20About%20Project/image-5.png)
