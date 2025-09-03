# Havacılık Haritası Üretimi İçin Kaynaklar ve QGIS Şablonu


## Amaç:

Bu proje, bireysel kullanıcıların, ICAO standartları ve SARP'ları doğrultusunda hobi amaçlı kendi havacılık haritalarını hazırlayabilmesini amaçlamaktadır.

![](Images%20About%20Project/Example-2.png)

## Dokümantasyon:

Proje henüz erken ssafhada olduğundan dokümantasyon henüz hazırlanmamıştır.

## Hedeflenen Özellikler:

### Tamamlanan Hedefler:

* ICAO Annex 4'den çıkarılan SVG semboller ve QGIS kütüphane dosyası (Nokta sembollerinin tamamına yakını kapsanmaktadır, çizgi ve alan sembolojisinde henüz eksiklikler vardır.)

### Üzerinde Uğraşılanlar:
* QGIS için şablon dosya.

### Planlanan Hedefler:
* Eksik Annex 4 sembolojilerinin tamamlanması.
* ICAO Doc 8697 doğrutusunda farklı renklendirmelerin, semboller veya QGIS şablonu üzerinden ayarlanması.
* ICAO Doc 8697 ile uyumlu ADC, PRKG, IAC, SID, STAR chartları için QGZ baskı düzeninin oluşturulması.
* ICAO doc 8126 ile uyumlu boş AIP şablonu. (MS Office Word için.)
* QGIS için PANS-OSP uyumlu AMA hesaplayıcı.
* QGIS için ICAO PANS-OPS uyumlu PAR OCS alanı oluşturucu.

### Daha Sonrası İçin Hedefler:
* AOC, PATC, ENC, WAC, VAC, ATCSMAC chartları için QGZ baskı düzenleri.
* NATO/MIPS sembolojisi.
* QGIS için ICAO PANS-OPS uyumlu MSA hesaplayıcı.
* QGIS için ICAO PANS-OPS uyumlu Circling alanı hesaplayıcı.
* QGIS için MIPS uyumlu Emergency Safe Altitude 100 NM hesaplayıcı.
* Havacılık verisi için diğer kaynaklar yerine gerçek AIXM verilerinin kullanımı.

## Test Verisi Hakkında:
Şablonda görsellik oluşturması için bir test verisi sağlanmaktadır. İlgili katmanların kaynakalrını değiştirerek kendi verilerinizi de kullanabilirsiniz.

Test verisi, Türkiye'yi kapsayacak şekilde şu kaynaklardan alınmıştır:
* Topoğrafya için Antalya bölgesini kapsayacak şekilde, ölçü birimi fit'e dönüştürülmüş SRTM 1 Arc-Second Global 30 m doğrulukla GeoTIFF DEM verisi.
* Hidrografya için Geofabrik ve Overpass Turbo aracılığıyla çıktı alınan OSM verileri.
* Kültür verisi için Overpass Turbo aracılığıyla çıktı alınan OSM verileri.
* Havacılık verisi için EUROCONTROL EAD BAsic'den elde edilen SDO verileri.

## Diğer Bilgiler:

### QGIS Chart Üretimi İle Alakalı Faydalı Repository:
* https://github.com/FLYGHT7/qpansopy/
Bu repository, aletli yaklaşma ile alakalı çok daha ileri düzey hesaplayıcıları içeren bir QGIS eklentisidir. Bizim projemiz ise bu eklenti tarafından kapsanan hesaplayıcıları halihazırda yapıldığı için kapsamayacaktır.

### Bize Ait Bazı Kaynaklar:
* QGIS dışı hesaplayıcılar için https://ais.ibosoft.net.tr
* Kaynaklar ve bilgi edinme için https://egitim.ibosoft.net.tr

### Chart Üretimi İçin Yararlanılan Kaynakalar:
* ICAO Annex 4, Aeronautical Charts - 11th edition, July 2009, amend 62
* ICAO Annex 15, Aeronautical Information Services - 16th edition, July 2018
* ICAO doc 8126 Aeronautical Information Services Manual, 7th Ed, 2022, amend 1
* ICAO doc 8697 Aeronautical Chart Manual 3rd Ed, 2016, Amend 1, Corr 1
* ICAO doc 8168 (PANS OPS) Aircraft Operations volume I 6th ed. amend 11, 2024
* ICAO doc 8168 (PANS OPS) Aircraft Operations volume II 7th ed. amend 10 corr 2, 2024

### Örnek Görseller:
Görseller güncel olmayabilir.
#### Genel Harita Görünümü
![](Images%20About%20Project/Example-1.png)
![](Images%20About%20Project/Example-2.png)
#### Tamamlanan ICAO Annex 4 Sembolleri:
![](Images%20About%20Project/Symbology-1.png)
![](Images%20About%20Project/Symbology-2.png)
![](Images%20About%20Project/Symbology-3.png)
![](Images%20About%20Project/Symbology-4.png)
![](Images%20About%20Project/Symbology-5.png)
![](Images%20About%20Project/Symbology-6.png)
![](Images%20About%20Project/Symbology-7.png)
![](Images%20About%20Project/Symbology-8.png)