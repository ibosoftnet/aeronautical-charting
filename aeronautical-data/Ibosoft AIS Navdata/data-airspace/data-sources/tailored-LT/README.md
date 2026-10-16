# tailored-LT — elle düzenlenen AIXM kaynağı

`tailored-lt-airspace-aixm.xml` bu kaynağın **kendisidir**: JSON ya da üretici yoktur, dosya elle
düzenlenir (kullanıcı kararı). Originator: DHMİ Türkiye; 115 Airspace: ilk 113'ü eski `Common Airspaces` tailored.json'dan üretildi;
ANKARA (LTAA) ve İSTANBUL (LTBB) FIR'ları elle eklendi (aşağıda).

## Düzenleme kuralları

- Biçim, alan sırası ve XML iskeletleri: [`../../docs/AIXM_Airspace_How_To_Add.md`](../../docs/AIXM_Airspace_How_To_Add.md).
- `gml:identifier` (UUID) **kalıcıdır**: mevcut kayıtta değiştirilmez; yeni
  kayda yeni bir UUID yazılır. `gml:id`'ler dosyada tekil olmalı.
- Her feature'ın TimeSlice'ının **sonunda** provenance kutusu
  (`ibosoftais:AirspaceDataProvenance`) bulunmalı; yoksa birleştirici durur.
- `name`/`localType` yalnız ASCII (Türkçe harf şemaya aykırı), ≤ 60 karakter.
- AIRAC değişince her kutudaki `ibosoftais:dataEffectivity` güncellenir
  (bugünkü değer: 03 SEP 2026 (AIRAC 2609) ve kayda göre diğerleri).
- Düzenlemeden sonra doğrulayın:

```bash
py ../../../common/data_build_common/validate_aixm.py tailored-lt-airspace-aixm.xml
```

## LTAA / LTBB FIR (elle eklendi)

- Geometri: ICAO-FIR-UIR verisindeki Surface'in birebir kopyası; ICAO
  kayıtları birleştiricide `excludes/icao-fir-lt.json` ile düşer.
- Dikey sınırlar: `GND` – `UNL`; `upperLowerSeparation` = FL285 (remark 6).
- Sınıf: `C`, `associatedLevels` FL305–FL660 (STD); diğer seviyeler sınıfsız
  (ikinci bir `class` yazılmadı).
- Remark'lar AIP'de yayımlandığı gibi, **metin değiştirilmeden** (yalnız satır
  sonları birleştirildi): her paragraf ayrı bir `Note` (REMARK), dil `lang`
  niteliğinde. Aynı numaranın Türkçe ve İngilizcesi ayrı notlardır (iki kez
  `(2)` / `(3)` doğrudur).
- `regionIcao`/`regionSupProc` = `EUR` (ICAO verisindeki değer).
- Provenance: Ibosoft AIS / DHMİ Türkiye / `06 AUG 2026 (AIRAC 2608)`.
- UUID: uuid5(`TailoredLtAirspace:FIR:<designator>`); `gml:id` `TAIL_LT_AS_FIR_<designator>`.
